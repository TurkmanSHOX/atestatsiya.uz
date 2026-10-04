import re
import pandas as pd
from docx import Document
from app.extensions import db
from app.models.question import Question, QuestionOption, Subject, Topic, QuestionType, DifficultyLevel

class QuestionImportService:
    @staticmethod
    def parse_excel(file_path):
        """
        Excel faylni o'qish, ustunlarni validatsiya qilish va xatolarni aniqlash.
        Kutiladigan ustunlar: Savol matni, Variant A, Variant B, Variant C, Variant D, To'g'ri javob, Fan, Mavzu, Qiyinlik, Ball
        """
        errors = []
        parsed_questions = []
        duplicates_count = 0

        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            return {'success': False, 'message': f"Excel faylini o'qib bo'lmadi: {str(e)}", 'errors': [], 'questions': []}

        # Normalize column names
        df.columns = [str(c).strip().lower() for c in df.columns]

        # Kerakli ustunlar xaritasi
        col_map = {
            'text': next((c for c in df.columns if any(k in c for k in ['savol', 'question', 'text'])), None),
            'opt_a': next((c for c in df.columns if any(k in c for k in ['a', 'variant a', 'opt_a'])), None),
            'opt_b': next((c for c in df.columns if any(k in c for k in ['b', 'variant b', 'opt_b'])), None),
            'opt_c': next((c for c in df.columns if any(k in c for k in ['c', 'variant c', 'opt_c'])), None),
            'opt_d': next((c for c in df.columns if any(k in c for k in ['d', 'variant d', 'opt_d'])), None),
            'correct': next((c for c in df.columns if any(k in c for k in ["to'g'ri", 'togri', 'correct', 'javob'])), None),
            'subject': next((c for c in df.columns if any(k in c for k in ['fan', 'subject'])), None),
            'topic': next((c for c in df.columns if any(k in c for k in ['mavzu', 'topic'])), None),
            'difficulty': next((c for c in df.columns if any(k in c for k in ['qiyinlik', 'daraja', 'difficulty'])), None),
            'points': next((c for c in df.columns if any(k in c for k in ['ball', 'points', 'score'])), None)
        }

        if not col_map['text']:
            return {'success': False, 'message': "Excel jadvalida 'Savol' ustuni topilmadi.", 'errors': [], 'questions': []}

        for idx, row in df.iterrows():
            row_num = idx + 2  # Excel 1-based + 1 for header
            q_text = str(row.get(col_map['text'], '')).strip()

            if not q_text or q_text.lower() == 'nan':
                errors.append(f"{row_num}-qator: Savol matni bo'sh.")
                continue

            # Variantlar
            opt_a = str(row.get(col_map['opt_a'], '')).strip() if col_map['opt_a'] else ''
            opt_b = str(row.get(col_map['opt_b'], '')).strip() if col_map['opt_b'] else ''
            opt_c = str(row.get(col_map['opt_c'], '')).strip() if col_map['opt_c'] else ''
            opt_d = str(row.get(col_map['opt_d'], '')).strip() if col_map['opt_d'] else ''

            if not opt_a or opt_a.lower() == 'nan':
                errors.append(f"{row_num}-qator: A varianti mavjud emas.")
                continue
            if not opt_b or opt_b.lower() == 'nan':
                errors.append(f"{row_num}-qator: B varianti mavjud emas.")
                continue

            raw_correct = str(row.get(col_map['correct'], '')).strip().upper() if col_map['correct'] else ''
            correct_key = raw_correct[0] if raw_correct and raw_correct[0] in ['A', 'B', 'C', 'D'] else None

            if not correct_key:
                errors.append(f"{row_num}-qator: To'g'ri javob ko'rsatilmagan yoki noto'g'ri (A, B, C, D bo'lishi kerak).")
                continue

            # Duplicate tekshiruvi (hash orqali)
            q_hash = Question.calculate_hash(q_text)
            existing_db = Question.query.filter_by(hash=q_hash).first()
            is_dup = existing_db is not None
            if is_dup:
                duplicates_count += 1

            subject_name = str(row.get(col_map['subject'], 'Umumiy')).strip() if col_map['subject'] else 'Umumiy'
            topic_name = str(row.get(col_map['topic'], 'Asosiy')).strip() if col_map['topic'] else 'Asosiy'
            
            raw_diff = str(row.get(col_map['difficulty'], 'MEDIUM')).strip().upper()
            if 'OSON' in raw_diff or 'EASY' in raw_diff:
                diff = DifficultyLevel.EASY
            elif 'QIYIN' in raw_diff or 'HARD' in raw_diff:
                diff = DifficultyLevel.HARD
            else:
                diff = DifficultyLevel.MEDIUM

            try:
                pts = float(row.get(col_map['points'], 1.0)) if col_map['points'] else 1.0
            except Exception:
                pts = 1.0

            options = [
                {'key': 'A', 'text': opt_a, 'is_correct': (correct_key == 'A')},
                {'key': 'B', 'text': opt_b, 'is_correct': (correct_key == 'B')}
            ]
            if opt_c and opt_c.lower() != 'nan':
                options.append({'key': 'C', 'text': opt_c, 'is_correct': (correct_key == 'C')})
            if opt_d and opt_d.lower() != 'nan':
                options.append({'key': 'D', 'text': opt_d, 'is_correct': (correct_key == 'D')})

            parsed_questions.append({
                'row_num': row_num,
                'text': q_text,
                'subject': subject_name,
                'topic': topic_name,
                'difficulty': diff,
                'points': pts,
                'question_type': QuestionType.SINGLE_CHOICE,
                'options': options,
                'is_duplicate': is_dup,
                'hash': q_hash
            })

        return {
            'success': True,
            'total_rows': len(df),
            'valid_count': len(parsed_questions),
            'errors': errors,
            'duplicates_count': duplicates_count,
            'questions': parsed_questions
        }

    @staticmethod
    def parse_word(file_path):
        """
        Word (.docx) faylidan savollarni ajratish.
        Format:
        1. Savol matni?
        A) Variant
        *B) To'g'ri javob
        C) Variant
        D) Variant
        """
        errors = []
        parsed_questions = []
        duplicates_count = 0

        try:
            doc = Document(file_path)
        except Exception as e:
            return {'success': False, 'message': f"Word faylini ochib bo'lmadi: {str(e)}", 'errors': [], 'questions': []}

        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        current_q = None
        current_options = []
        q_counter = 0

        # Pattern for question start: "1.", "1)", "1 - "
        q_start_regex = re.compile(r'^\s*(\d+)[\.\)\-]\s*(.+)$')
        # Pattern for options: "A)", "*B)", "A.", "a)"
        opt_regex = re.compile(r'^\s*(\*?)\s*([A-Da-d])[\.\)]\s*(.+)$')

        for line in paragraphs:
            q_match = q_start_regex.match(line)
            opt_match = opt_regex.match(line)

            if q_match:
                # Save previous question if valid
                if current_q and current_options:
                    has_correct = any(opt['is_correct'] for opt in current_options)
                    if has_correct and len(current_options) >= 2:
                        q_hash = Question.calculate_hash(current_q['text'])
                        is_dup = Question.query.filter_by(hash=q_hash).first() is not None
                        if is_dup:
                            duplicates_count += 1
                        current_q['options'] = current_options
                        current_q['is_duplicate'] = is_dup
                        current_q['hash'] = q_hash
                        parsed_questions.append(current_q)
                    else:
                        errors.append(f"Savol '{current_q['number']}': To'g'ri javob belgilanmagan ('*' belgisi topilmadi) yoki variantlar yetarli emas.")

                q_counter += 1
                q_num = q_match.group(1)
                q_text = q_match.group(2).strip()
                current_q = {
                    'number': q_num,
                    'text': q_text,
                    'subject': 'Umumiy',
                    'topic': 'Asosiy',
                    'difficulty': DifficultyLevel.MEDIUM,
                    'points': 1.0,
                    'question_type': QuestionType.SINGLE_CHOICE
                }
                current_options = []
            elif opt_match and current_q:
                is_correct = bool(opt_match.group(1)) or ('*' in line)
                opt_key = opt_match.group(2).upper()
                opt_text = opt_match.group(3).strip()
                current_options.append({
                    'key': opt_key,
                    'text': opt_text,
                    'is_correct': is_correct
                })
            elif current_q and not opt_match:
                # Qo'shimcha matn / savol davomi
                current_q['text'] += " " + line

        # Oxirgi savolni saqlash
        if current_q and current_options:
            has_correct = any(opt['is_correct'] for opt in current_options)
            if has_correct and len(current_options) >= 2:
                q_hash = Question.calculate_hash(current_q['text'])
                is_dup = Question.query.filter_by(hash=q_hash).first() is not None
                if is_dup:
                    duplicates_count += 1
                current_q['options'] = current_options
                current_q['is_duplicate'] = is_dup
                current_q['hash'] = q_hash
                parsed_questions.append(current_q)
            else:
                errors.append(f"Savol '{current_q['number']}': To'g'ri javob belgilanmagan ('*' belgisi topilmadi).")

        return {
            'success': True,
            'total_parsed': len(parsed_questions),
            'errors': errors,
            'duplicates_count': duplicates_count,
            'questions': parsed_questions
        }

    @staticmethod
    def commit_questions(questions_data, default_subject_id=None, default_topic_id=None):
        """
        Tasdiqlangan savollar ro'yxatini bazaga saqlash.
        """
        imported_count = 0
        skipped_duplicates = 0

        # Agar fan/mavzu ko'rsatilmagan bo'lsa standartlarini topish/yaratish
        if not default_subject_id:
            subj = Subject.query.filter_by(name='Umumiy').first()
            if not subj:
                subj = Subject(name='Umumiy', code='GEN', description='Umumiy fanlar')
                db.session.add(subj)
                db.session.flush()
            default_subject_id = subj.id

        if not default_topic_id:
            top = Topic.query.filter_by(subject_id=default_subject_id, name='Asosiy').first()
            if not top:
                top = Topic(subject_id=default_subject_id, name='Asosiy', code='MAIN')
                db.session.add(top)
                db.session.flush()
            default_topic_id = top.id

        for q_item in questions_data:
            q_text = q_item['text'].strip()
            q_hash = q_item.get('hash') or Question.calculate_hash(q_text)

            # Takroriylik tekshiruvi
            if Question.query.filter_by(hash=q_hash).first():
                skipped_duplicates += 1
                continue

            subj_id = default_subject_id
            top_id = default_topic_id

            # Agar savolda mavzu/fan nomi kelsa:
            if 'subject' in q_item and q_item['subject']:
                s = Subject.query.filter_by(name=q_item['subject']).first()
                if not s:
                    s = Subject(name=q_item['subject'])
                    db.session.add(s)
                    db.session.flush()
                subj_id = s.id

                if 'topic' in q_item and q_item['topic']:
                    t = Topic.query.filter_by(subject_id=subj_id, name=q_item['topic']).first()
                    if not t:
                        t = Topic(subject_id=subj_id, name=q_item['topic'])
                        db.session.add(t)
                        db.session.flush()
                    top_id = t.id

            q = Question(
                subject_id=subj_id,
                topic_id=top_id,
                question_type=q_item.get('question_type', QuestionType.SINGLE_CHOICE),
                text=q_text,
                explanation=q_item.get('explanation', ''),
                difficulty=q_item.get('difficulty', DifficultyLevel.MEDIUM),
                points=float(q_item.get('points', 1.0)),
                status='ACTIVE',
                hash=q_hash
            )
            db.session.add(q)
            db.session.flush()

            for idx, opt in enumerate(q_item.get('options', [])):
                o = QuestionOption(
                    question_id=q,
                    option_key=opt.get('key', chr(65 + idx)),
                    text=opt.get('text', ''),
                    is_correct=bool(opt.get('is_correct', False)),
                    order_index=idx
                )
                db.session.add(o)

            imported_count += 1

        db.session.commit()
        return {'success': True, 'imported_count': imported_count, 'skipped_duplicates': skipped_duplicates}
