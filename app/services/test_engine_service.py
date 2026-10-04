import random
from datetime import datetime, timedelta
from app.extensions import db
from app.models.attestation import AttestationRegistration, RegistrationStep
from app.models.test import Test, TestBlueprint, TestBlueprintRule
from app.models.question import Question, QuestionOption, QuestionType
from app.models.session import TestSession, SessionStatus, TestAnswer
from app.models.result import Result, ResultDetail
from app.services.certificate_service import CertificateService

class TestEngineService:
    @staticmethod
    def validate_test(test_id: int):
        """
        Testni ACTIVE qilishdan oldin yetarli savollar va blueprint to'liqligini tekshirish.
        """
        test = Test.query.get(test_id)
        if not test:
            return {'valid': False, 'reasons': ["Test topilmadi."]}

        reasons = []
        if not test.blueprint or not test.blueprint.rules:
            reasons.append("Test uchun blueprint yoki qoidalar belgilanmagan.")
            return {'valid': False, 'reasons': reasons}

        total_needed = test.blueprint.total_questions
        rules_total = sum(r.questions_count for r in test.blueprint.rules)
        if rules_total != total_needed:
            reasons.append(f"Blueprint qoidalari yig'indisi ({rules_total}) umumiy savollar soniga ({total_needed}) mos kelmaydi.")

        for rule in test.blueprint.rules:
            query = Question.query.filter_by(subject_id=rule.subject_id, status='ACTIVE')
            if rule.topic_id:
                query = query.filter_by(topic_id=rule.topic_id)
            if rule.difficulty and rule.difficulty != 'ANY':
                query = query.filter_by(difficulty=rule.difficulty)
            
            available_count = query.count()
            if available_count < rule.questions_count:
                subj_name = rule.subject.name if rule.subject else f"Fan ID {rule.subject_id}"
                top_name = f", Mavzu: {rule.topic.name}" if rule.topic else ""
                diff_name = f", Qiyinlik: {rule.difficulty}" if rule.difficulty != 'ANY' else ""
                reasons.append(f"Yetarli savollar mavjud emas ({subj_name}{top_name}{diff_name}): Kerak: {rule.questions_count}, Mavjud: {available_count}.")

        return {
            'valid': len(reasons) == 0,
            'reasons': reasons
        }

    @staticmethod
    def start_session(user_id: int, registration_id: int, ip_address: str, user_agent: str, device_fingerprint: str = None):
        """
        Imtihon sessiyasini boshlash, savollarni aralashtirish va sessiyani saqlash.
        """
        reg = AttestationRegistration.query.get(registration_id)
        if not reg or reg.user_id != user_id:
            raise ValueError("Attestatsiya arizasi topilmadi yoki sizga tegishli emas.")

        # Tekshiruvlar: ruxsat berilganmi?
        if reg.step not in [RegistrationStep.APPROVED, RegistrationStep.EXAM_READY]:
            raise ValueError("Ushbu attestatsiyaga kirishga hali ruxsat berilmagan yoki to'lov tasdiqlanmagan.")

        attestation = reg.attestation
        test = Test.query.filter_by(attestation_id=attestation.id, status='ACTIVE').first()
        if not test:
            raise ValueError("Ushbu attestatsiya uchun faol imtihon testi topilmadi.")

        # Urinishlar sonini tekshirish
        completed_sessions = TestSession.query.filter_by(
            registration_id=reg.id,
            status=SessionStatus.SUBMITTED
        ).count()

        if completed_sessions >= attestation.max_attempts:
            raise ValueError(f"Siz uchun belgilangan maksimal urinishlar soni ({attestation.max_attempts}) tugagan.")

        # Agar allaqachon faol sessiya bo'lsa va muddati o'tmagan bo'lsa — o'shani qaytarish (Sessiyani tiklash)
        existing_session = TestSession.query.filter_by(
            registration_id=reg.id,
            status=SessionStatus.IN_PROGRESS
        ).order_by(TestSession.started_at.desc()).first()

        if existing_session:
            if not existing_session.is_expired:
                # Sessiyani davom ettirish
                existing_session.last_heartbeat_at = datetime.utcnow()
                db.session.commit()
                return existing_session
            else:
                # Muddat tugagan bo'lsa uni yakunlash
                TestEngineService.finish_session(existing_session.id, auto_expire=True)

        # Yangi sessiya yaratish
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=test.duration_minutes)

        session = TestSession(
            user_id=user_id,
            test_id=test.id,
            registration_id=reg.id,
            started_at=now,
            expires_at=expires_at,
            status=SessionStatus.IN_PROGRESS,
            ip_address=ip_address,
            user_agent=user_agent,
            device_fingerprint=device_fingerprint,
            last_heartbeat_at=now
        )
        db.session.add(session)
        db.session.flush()

        # Blueprint bo'yicha savollarni tanlash
        selected_question_ids = []
        if test.blueprint and test.blueprint.rules:
            for rule in test.blueprint.rules:
                q_query = Question.query.filter_by(subject_id=rule.subject_id, status='ACTIVE')
                if rule.topic_id:
                    q_query = q_query.filter_by(topic_id=rule.topic_id)
                if rule.difficulty and rule.difficulty != 'ANY':
                    q_query = q_query.filter_by(difficulty=rule.difficulty)

                rule_pool = [q.id for q in q_query.all() if q.id not in selected_question_ids]
                if len(rule_pool) < rule.questions_count:
                    # Agar aniq topicda yetishmasa shu fanning ixtiyoriy faol savollaridan to'ldirish
                    fallback_pool = [q.id for q in Question.query.filter_by(subject_id=rule.subject_id, status='ACTIVE').all() if q.id not in selected_question_ids]
                    sampled = random.sample(fallback_pool, min(rule.questions_count, len(fallback_pool)))
                else:
                    sampled = random.sample(rule_pool, rule.questions_count)
                selected_question_ids.extend(sampled)

        # Agar blueprint bo'yicha savollar kam bo'lsa yoki bo'sh bo'lsa:
        if len(selected_question_ids) < test.duration_minutes:
            all_q_ids = [q.id for q in Question.query.filter_by(status='ACTIVE').all() if q.id not in selected_question_ids]
            needed = (test.blueprint.total_questions if test.blueprint else 40) - len(selected_question_ids)
            if needed > 0 and all_q_ids:
                selected_question_ids.extend(random.sample(all_q_ids, min(needed, len(all_q_ids))))

        # Randomize order if shuffle_questions
        if test.shuffle_questions:
            random.shuffle(selected_question_ids)

        # TestAnswer placeholderlarini yaratish
        for q_id in selected_question_ids:
            answer = TestAnswer(
                session_id=session.id,
                question_id=q_id,
                selected_option_ids=[],
                is_flagged=False
            )
            db.session.add(answer)

        reg.step = RegistrationStep.EXAM_READY
        db.session.commit()
        return session

    @staticmethod
    def get_session_payload(session_id: str):
        """
        Test oynasi uchun barcha savollar va holatni xavfsiz JSON shaklida tayyorlash.
        To'g'ri javoblar mijozga HECH QACHON yuborilmaydi!
        """
        session = TestSession.query.get(session_id)
        if not session:
            return None

        # Expire tekshiruvi
        if session.is_expired:
            TestEngineService.finish_session(session.id, auto_expire=True)
            return {'status': 'EXPIRED', 'session_id': session.id}

        test = session.test
        answers = TestAnswer.query.filter_by(session_id=session.id).order_by(TestAnswer.id.asc()).all()

        questions_payload = []
        for idx, ans in enumerate(answers):
            q = ans.question
            options = []
            opts_list = list(q.options)
            if test.shuffle_options:
                # Variantlarni aralashtirish
                random.seed(int(session.user_id) + q.id)
                random.shuffle(opts_list)

            for opt in opts_list:
                options.append({
                    'id': opt.id,
                    'key': opt.option_key,
                    'text': opt.text,
                    'match_key': opt.match_key
                })

            questions_payload.append({
                'number': idx + 1,
                'question_id': q.id,
                'type': q.question_type,
                'text': q.text,
                'points': float(q.points),
                'options': options,
                'media': [m.to_dict() for m in q.media],
                'selected_option_ids': ans.selected_option_ids or [],
                'text_answer': ans.text_answer or '',
                'is_flagged': ans.is_flagged,
                'is_answered': bool(ans.selected_option_ids or ans.text_answer)
            })

        return {
            'status': session.status,
            'session_id': session.id,
            'attestation_title': session.registration.attestation.title,
            'remaining_seconds': session.remaining_seconds,
            'total_questions': len(questions_payload),
            'questions': questions_payload
        }

    @staticmethod
    def save_answer(session_id: str, question_id: int, selected_option_ids: list = None, text_answer: str = None, is_flagged: bool = False, time_spent: int = 0):
        """
        Real-time javobni xavfsiz saqlash.
        """
        session = TestSession.query.get(session_id)
        if not session or session.status != SessionStatus.IN_PROGRESS:
            return {'success': False, 'message': "Imtihon faol emas yoki yakunlangan."}

        if session.is_expired:
            TestEngineService.finish_session(session_id, auto_expire=True)
            return {'success': False, 'message': "Imtihon vaqti tugagan.", 'expired': True}

        answer = TestAnswer.query.filter_by(session_id=session.id, question_id=question_id).first()
        if not answer:
            return {'success': False, 'message': "Savol topilmadi."}

        answer.selected_option_ids = selected_option_ids or []
        answer.text_answer = text_answer
        answer.is_flagged = bool(is_flagged)
        answer.answered_at = datetime.utcnow()
        answer.time_spent_seconds += time_spent

        session.last_heartbeat_at = datetime.utcnow()
        db.session.commit()
        return {'success': True, 'remaining_seconds': session.remaining_seconds}

    @staticmethod
    def finish_session(session_id: str, auto_expire: bool = False):
        """
        Testni yakunlash va to'liq avtomatik baholash.
        """
        session = TestSession.query.get(session_id)
        if not session:
            return None

        if session.status in [SessionStatus.SUBMITTED, SessionStatus.TERMINATED]:
            return session.result

        test = session.test
        reg = session.registration
        attestation = reg.attestation

        answers = TestAnswer.query.filter_by(session_id=session.id).all()
        total_questions = len(answers)
        correct_count = 0
        incorrect_count = 0
        unanswered_count = 0
        total_score = 0.0
        max_possible_score = sum(float(ans.question.points) for ans in answers) or 1.0

        topic_stats = {}  # {topic_id: {'total': 0, 'correct': 0, 'subject_id': 0}}

        for ans in answers:
            q = ans.question
            top_id = q.topic_id
            subj_id = q.subject_id

            if top_id not in topic_stats:
                topic_stats[top_id] = {'total': 0, 'correct': 0, 'subject_id': subj_id}
            topic_stats[top_id]['total'] += 1

            selected = ans.selected_option_ids or []
            correct_opts = [opt.id for opt in q.options if opt.is_correct]

            if not selected and not ans.text_answer:
                unanswered_count += 1
                ans.is_correct = False
                ans.awarded_points = 0.0
                continue

            # Baholash mantiqi
            is_q_correct = False
            points_awarded = 0.0

            if q.question_type in [QuestionType.SINGLE_CHOICE, QuestionType.TRUE_FALSE, QuestionType.IMAGE_BASED, QuestionType.TABLE_BASED, QuestionType.FORMULA_BASED, QuestionType.AUDIO_BASED, QuestionType.VIDEO_BASED]:
                if len(selected) == 1 and selected[0] in correct_opts:
                    is_q_correct = True
                    points_awarded = float(q.points)
            elif q.question_type == QuestionType.MULTIPLE_CHOICE:
                correct_selected = len(set(selected).intersection(set(correct_opts)))
                wrong_selected = len(set(selected).difference(set(correct_opts)))
                if len(correct_opts) > 0:
                    fraction = max(0.0, (correct_selected - wrong_selected) / len(correct_opts))
                    points_awarded = fraction * float(q.points)
                    is_q_correct = (fraction >= 0.99)
            elif q.question_type == QuestionType.FILL_BLANK:
                # Text answer matching with correct option texts
                user_text = (ans.text_answer or '').strip().lower()
                correct_texts = [opt.text.strip().lower() for opt in q.options if opt.is_correct]
                if user_text in correct_texts:
                    is_q_correct = True
                    points_awarded = float(q.points)
            else:
                # Matching / Ordering: proportional match
                if set(selected) == set(correct_opts):
                    is_q_correct = True
                    points_awarded = float(q.points)

            ans.is_correct = is_q_correct
            ans.awarded_points = points_awarded

            if is_q_correct:
                correct_count += 1
                topic_stats[top_id]['correct'] += 1
            else:
                incorrect_count += 1

            total_score += points_awarded

        # Foizni hisoblash
        percentage = round((total_score / max_possible_score) * 100, 2) if max_possible_score > 0 else 0.0
        is_passed = percentage >= float(test.passing_score)

        # Sessiya holatini o'zgartirish
        session.finished_at = datetime.utcnow()
        session.status = SessionStatus.EXPIRED if auto_expire else SessionStatus.SUBMITTED
        reg.step = RegistrationStep.COMPLETED

        total_time_seconds = int((session.finished_at - session.started_at).total_seconds())

        # Result obyekti
        result = Result(
            session_id=session.id,
            user_id=session.user_id,
            attestation_id=attestation.id,
            total_questions=total_questions,
            correct_answers=correct_count,
            incorrect_answers=incorrect_count,
            unanswered=unanswered_count,
            score=round(total_score, 2),
            percentage=percentage,
            is_passed=is_passed,
            completion_time_seconds=max(1, total_time_seconds)
        )
        db.session.add(result)
        db.session.flush()

        # Result details
        for top_id, stats in topic_stats.items():
            top_pct = round((stats['correct'] / stats['total']) * 100, 2) if stats['total'] > 0 else 0.0
            detail = ResultDetail(
                result_id=result.id,
                subject_id=stats['subject_id'],
                topic_id=top_id,
                total_topic_questions=stats['total'],
                correct_topic_questions=stats['correct'],
                topic_percentage=top_pct
            )
            db.session.add(detail)

        db.session.commit()

        # Agar imtihondan o'tgan bo'lsa va sertifikat beriladigan bo'lsa:
        if is_passed and attestation.issue_certificate:
            try:
                CertificateService.generate_certificate(result.id)
            except Exception as e:
                print(f"[Certificate Generation Error]: {e}")

        return result
