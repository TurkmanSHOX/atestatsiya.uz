import random
from datetime import datetime, timedelta
from app.extensions import db
from app.models.user import User
from app.models.test import Test, TestType, TestBlueprint, TestBlueprintRule, TestQuestion
from app.models.question import Question, QuestionOption, QuestionType, Topic, Subject
from app.models.session import TestSession, SessionStatus, TestAnswer
from app.models.result import Result, ResultDetail, UserQuestionStat, UserTopicStat
from app.services.ai_service import AIService

class TestEngineService:
    @staticmethod
    def validate_test(test_id: int):
        """
        Testni ACTIVE qilishdan oldin yetarli savollar mavjudligini tekshirish.
        """
        test = Test.query.get(test_id)
        if not test:
            return {'valid': False, 'reasons': ["Test topilmadi."]}

        reasons = []
        if test.blueprint and test.blueprint.rules:
            total_needed = test.blueprint.total_questions
            rules_total = sum(r.questions_count for r in test.blueprint.rules)
            if rules_total != total_needed:
                reasons.append(f"Blueprint qoidalari yig'indisi ({rules_total}) umumiy savollar soniga ({total_needed}) mos kelmaydi.")

            for rule in test.blueprint.rules:
                query = Question.query.filter_by(subject_id=rule.subject_id, status='ACTIVE', is_approved=True)
                if rule.topic_id:
                    query = query.filter_by(topic_id=rule.topic_id)
                if rule.difficulty and rule.difficulty != 'ANY':
                    query = query.filter_by(difficulty=rule.difficulty)
                
                available_count = query.count()
                if available_count < rule.questions_count:
                    subj_name = rule.subject.name if rule.subject else f"Fan ID {rule.subject_id}"
                    top_name = f", Mavzu: {rule.topic.name}" if rule.topic else ""
                    reasons.append(f"Yetarli savollar mavjud emas ({subj_name}{top_name}): Kerak: {rule.questions_count}, Mavjud: {available_count}.")
        else:
            # Standart fan yoki mavzu testi uchun bazadagi savollar sonini tekshirish
            query = Question.query.filter_by(status='ACTIVE', is_approved=True)
            if test.subject_id:
                query = query.filter_by(subject_id=test.subject_id)
            if test.topic_id:
                query = query.filter_by(topic_id=test.topic_id)

            available = query.count()
            if available < min(test.total_questions, 5):
                reasons.append(f"Ushbu test uchun bazada kamida 5 ta savol bo'lishi kerak. Hozir mavjud: {available} ta.")

        return {
            'valid': len(reasons) == 0,
            'reasons': reasons
        }

    @staticmethod
    def start_session(user_id: int, test_id: int, ip_address: str = None, user_agent: str = None):
        """
        Test sessiyasini boshlash, huquqni tekshirish, savollarni tanlash va sessiyani yaratish.
        """
        user = User.query.get(user_id)
        test = Test.query.get(test_id)

        if not user or not test:
            raise ValueError("Foydalanuvchi yoki test topilmadi.")

        # 1. Huquq (Entitlement) tekshirish: bepul bo'lmasa, paket talab qilinadi
        if not test.is_free:
            if not user.has_subject_access(test.subject_id):
                raise ValueError("Ushbu testdan foydalanish uchun faol obuna (paket) talab etiladi. Iltimos, paket xarid qiling.")

        # 2. Mavjud faol va muddati o'tmagan sessiya bormi? (Sessiyani tiklash)
        existing = TestSession.query.filter_by(
            user_id=user.id,
            test_id=test.id,
            status=SessionStatus.IN_PROGRESS
        ).order_by(TestSession.started_at.desc()).first()

        if existing:
            if not existing.is_expired:
                existing.last_heartbeat_at = datetime.utcnow()
                db.session.commit()
                return existing
            else:
                TestEngineService.finish_session(existing.id, auto_expire=True)

        # 3. Savollarni tanlash
        selected_questions = TestEngineService._select_questions(user_id, test)
        if not selected_questions:
            raise ValueError("Ushbu test uchun savollar topilmadi. Tez orada savollar banki to'ldiriladi.")

        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=test.duration_minutes)

        session = TestSession(
            user_id=user.id,
            test_id=test.id,
            started_at=now,
            expires_at=expires_at,
            status=SessionStatus.IN_PROGRESS,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(session)
        db.session.flush()

        # Savollar tartibi
        if test.shuffle_questions:
            random.shuffle(selected_questions)

        for q in selected_questions:
            answer = TestAnswer(
                session_id=session.id,
                question_id=q.id,
                is_flagged=False
            )
            db.session.add(answer)

        # Agar foydalanuvchida testlar soni cheklangan paket bo'lsa, bitta kamaytirish
        entitlement = user.get_active_entitlement(test.subject_id)
        if entitlement and entitlement.tests_remaining is not None and entitlement.tests_remaining > 0:
            entitlement.tests_remaining -= 1

        db.session.commit()
        return session

    @staticmethod
    def _select_questions(user_id: int, test: Test):
        """Test turiga qarab savollarni tanlash"""
        # A. Agar Blueprint bo'lsa
        if test.blueprint and test.blueprint.rules:
            selected = []
            for rule in test.blueprint.rules:
                q_query = Question.query.filter_by(subject_id=rule.subject_id, status='ACTIVE', is_approved=True)
                if rule.topic_id:
                    q_query = q_query.filter_by(topic_id=rule.topic_id)
                if rule.difficulty and rule.difficulty != 'ANY':
                    q_query = q_query.filter_by(difficulty=rule.difficulty)

                pool = q_query.all()
                k = min(len(pool), rule.questions_count)
                if k > 0:
                    selected.extend(random.sample(pool, k))
            return selected

        # B. TestType = XATOLAR (Foydalanuvchi ilgari xato qilgan savollardan)
        if test.test_type == TestType.XATOLAR:
            mistake_stats = UserQuestionStat.query.filter_by(user_id=user_id, is_last_correct=False).all()
            q_ids = [s.question_id for s in mistake_stats]
            if q_ids:
                return Question.query.filter(Question.id.in_(q_ids), Question.status == 'ACTIVE').limit(test.total_questions).all()
            # Agar xatolar bo'lmasa, umumiy fandan oladi
            return Question.query.filter_by(status='ACTIVE', is_approved=True).limit(test.total_questions).all()

        # C. TestType = ZAIF_MAVZULAR
        if test.test_type == TestType.ZAIF_MAVZULAR:
            weak_stats = UserTopicStat.query.filter_by(user_id=user_id)\
                .filter(UserTopicStat.accuracy_percentage < 60.0).all()
            t_ids = [s.topic_id for s in weak_stats]
            if t_ids:
                pool = Question.query.filter(Question.topic_id.in_(t_ids), Question.status == 'ACTIVE', Question.is_approved == True).all()
                k = min(len(pool), test.total_questions)
                return random.sample(pool, k) if k > 0 else []

        # D. TestType = SIMULYATSIYA (Attestatsiya formati: 50 ta savol, 20 oson, 20 o'rta, 10 qiyin)
        if test.test_type == TestType.SIMULYATSIYA:
            query = Question.query.filter_by(status='ACTIVE', is_approved=True)
            if test.subject_id:
                query = query.filter_by(subject_id=test.subject_id)

            easy_qs = query.filter_by(difficulty='EASY').all()
            med_qs = query.filter_by(difficulty='MEDIUM').all()
            hard_qs = query.filter_by(difficulty='HARD').all()

            selected = []
            selected.extend(random.sample(easy_qs, min(len(easy_qs), 20)))
            selected.extend(random.sample(med_qs, min(len(med_qs), 20)))
            selected.extend(random.sample(hard_qs, min(len(hard_qs), 10)))

            # Agar qiyinlik bo'yicha yetmasa, ixtiyoriylari bilan to'ldirish
            if len(selected) < test.total_questions:
                all_qs = query.all()
                remaining_needed = test.total_questions - len(selected)
                pool = [q for q in all_qs if q not in selected]
                selected.extend(random.sample(pool, min(len(pool), remaining_needed)))
            return selected

        # E. Standart: Fan yoki Mavzu testi
        query = Question.query.filter_by(status='ACTIVE', is_approved=True)
        if test.subject_id:
            query = query.filter_by(subject_id=test.subject_id)
        if test.topic_id:
            query = query.filter_by(topic_id=test.topic_id)

        pool = query.all()
        k = min(len(pool), test.total_questions)
        return random.sample(pool, k) if k > 0 else []

    @staticmethod
    def get_session_payload(session_id: str):
        """Test topshirish oynasi uchun savollar va sessiya ma'lumotlarini tayyorlash"""
        session = TestSession.query.get(session_id)
        if not session:
            return None

        test = session.test
        answers = sorted(session.answers, key=lambda a: a.id)

        questions_payload = []
        for idx, ans in enumerate(answers, start=1):
            q = ans.question
            options = []
            for opt in q.options:
                options.append({
                    'id': opt.id,
                    'key': opt.key,
                    'text': opt.text
                })

            if test.shuffle_options:
                random.shuffle(options)

            questions_payload.append({
                'number': idx,
                'question_id': q.id,
                'question_type': q.question_type,
                'text': q.text,
                'difficulty': q.difficulty,
                'subject_name': q.subject.name if q.subject else "",
                'topic_name': q.topic.name if q.topic else "",
                'options': options,
                'selected_option_ids': ans.selected_option_ids or [],
                'text_answer': ans.text_answer or '',
                'is_flagged': ans.is_flagged
            })

        return {
            'session_id': session.id,
            'test_id': test.id,
            'title': test.title,
            'test_type': test.test_type,
            'remaining_seconds': session.remaining_seconds,
            'total_questions': len(questions_payload),
            'questions': questions_payload
        }

    @staticmethod
    def save_answer(session_id: str, question_id: int, selected_option_ids: list, text_answer: str = None, is_flagged: bool = False, time_spent: int = 0):
        """Foydalanuvchi javobini orqa fonda avtomatik saqlash"""
        session = TestSession.query.get(session_id)
        if not session or session.status != SessionStatus.IN_PROGRESS:
            return {'success': False, 'message': "Sessiya faol emas."}

        if session.is_expired:
            TestEngineService.finish_session(session_id, auto_expire=True)
            return {'success': False, 'message': "Test vaqti tugadi."}

        answer = TestAnswer.query.filter_by(session_id=session.id, question_id=question_id).first()
        if not answer:
            answer = TestAnswer(session_id=session.id, question_id=question_id)
            db.session.add(answer)

        answer.selected_option_ids = selected_option_ids
        answer.text_answer = text_answer
        answer.is_flagged = is_flagged
        answer.time_spent_seconds += time_spent
        answer.answered_at = datetime.utcnow()

        session.last_heartbeat_at = datetime.utcnow()
        db.session.commit()

        return {'success': True, 'saved_at': answer.answered_at.strftime('%H:%M:%S')}

    @staticmethod
    def finish_session(session_id: str, auto_expire: bool = False):
        """
        Sessiyani yakunlash, javoblarni baholash, xatolar va mavzular statistikasini yangilash.
        """
        session = TestSession.query.get(session_id)
        if not session:
            return None

        if session.status == SessionStatus.SUBMITTED and session.result:
            return session.result

        now = datetime.utcnow()
        session.finished_at = now
        session.status = SessionStatus.EXPIRED if auto_expire else SessionStatus.SUBMITTED

        total_questions = len(session.answers)
        correct_count = 0
        incorrect_count = 0
        unanswered_count = 0
        total_score = 0.0

        topic_stats_map = {} # topic_id -> {'total': X, 'correct': Y, 'subject_id': Z}

        for ans in session.answers:
            q = ans.question
            t_id = q.topic_id
            s_id = q.subject_id

            if t_id not in topic_stats_map:
                topic_stats_map[t_id] = {'total': 0, 'correct': 0, 'subject_id': s_id}
            topic_stats_map[t_id]['total'] += 1

            correct_opt_ids = set(q.get_correct_option_ids())
            selected_ids = set(ans.selected_option_ids or [])

            # Javob berilmaganmi?
            if not selected_ids and not (ans.text_answer and ans.text_answer.strip()):
                unanswered_count += 1
                ans.is_correct = False
                ans.awarded_points = 0.0
                is_corr = False
            elif correct_opt_ids and selected_ids == correct_opt_ids:
                correct_count += 1
                ans.is_correct = True
                ans.awarded_points = float(q.points)
                total_score += float(q.points)
                topic_stats_map[t_id]['correct'] += 1
                is_corr = True
            else:
                incorrect_count += 1
                ans.is_correct = False
                ans.awarded_points = 0.0
                is_corr = False

            # Foydalanuvchining savol statistikasi (Xatolarim uchun)
            q_stat = UserQuestionStat.query.filter_by(user_id=session.user_id, question_id=q.id).first()
            if not q_stat:
                q_stat = UserQuestionStat(
                    user_id=session.user_id,
                    question_id=q.id,
                    attempts_count=1,
                    correct_count=1 if is_corr else 0,
                    incorrect_count=0 if is_corr else 1,
                    is_last_correct=is_corr,
                    last_attempt_at=now
                )
                db.session.add(q_stat)
            else:
                q_stat.attempts_count += 1
                if is_corr:
                    q_stat.correct_count += 1
                else:
                    q_stat.incorrect_count += 1
                q_stat.is_last_correct = is_corr
                q_stat.last_attempt_at = now

        # Foiz hisoblash
        percentage = round((correct_count / total_questions * 100.0), 2) if total_questions > 0 else 0.0
        is_passed = percentage >= float(session.test.passing_score)

        time_spent_secs = int((now - session.started_at).total_seconds())
        max_duration_secs = session.test.duration_minutes * 60
        completion_time = min(time_spent_secs, max_duration_secs)

        # Natija obyektini yaratish
        result = Result(
            session_id=session.id,
            user_id=session.user_id,
            test_id=session.test_id,
            total_questions=total_questions,
            correct_answers=correct_count,
            incorrect_answers=incorrect_count,
            unanswered=unanswered_count,
            score=total_score,
            percentage=percentage,
            is_passed=is_passed,
            completion_time_seconds=completion_time
        )
        db.session.add(result)
        db.session.flush()

        # ResultDetail va UserTopicStat larni yangilash
        for t_id, data in topic_stats_map.items():
            t_perc = round((data['correct'] / data['total'] * 100.0), 2) if data['total'] > 0 else 0.0
            detail = ResultDetail(
                result_id=result.id,
                subject_id=data['subject_id'],
                topic_id=t_id,
                total_topic_questions=data['total'],
                correct_topic_questions=data['correct'],
                topic_percentage=t_perc
            )
            db.session.add(detail)

            # UserTopicStat ni yangilash
            u_top_stat = UserTopicStat.query.filter_by(user_id=session.user_id, topic_id=t_id).first()
            if not u_top_stat:
                u_top_stat = UserTopicStat(
                    user_id=session.user_id,
                    topic_id=t_id,
                    total_answered=data['total'],
                    correct_answered=data['correct'],
                    accuracy_percentage=t_perc,
                    last_updated_at=now
                )
                db.session.add(u_top_stat)
            else:
                u_top_stat.total_answered += data['total']
                u_top_stat.correct_answered += data['correct']
                if u_top_stat.total_answered > 0:
                    u_top_stat.accuracy_percentage = round((u_top_stat.correct_answered / u_top_stat.total_answered * 100.0), 2)
                u_top_stat.last_updated_at = now

        # AI Tavsiyasini shakllantirish
        try:
            result.ai_recommendation = AIService.generate_recommendations(session.user_id, result.id)
        except Exception:
            result.ai_recommendation = "Natijalaringiz tahlil qilindi. Zaif mavzular bo'yicha ko'proq test ishlash tavsiya etiladi."

        db.session.commit()
        return result
