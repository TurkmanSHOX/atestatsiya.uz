import re
import difflib
import pandas as pd
from docx import Document
from app.extensions import db
from app.models.question import Question, QuestionOption, Subject, Topic, SubjectSection, QuestionType, DifficultyLevel

class QuestionImportService:
    @staticmethod
    def parse_excel(file_path):
        """
        Excel faylni o'qish, ustunlarni validatsiya qilish va xatolarni aniqlash.
        Ustunlar: Fan, Bo'lim, Mavzu, Savol, A, B, C, D, To'g'ri javob, Qiyinlik, Izoh, Manba
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
            'q_image': next((c for c in df.columns if any(k in c for k in ['savol_rasm', 'savol rasmi', 'question_image', 'q_image', 'rasm'])), None),
            'opt_a': next((c for c in df.columns if any(k in c for k in ['variant a', 'opt_a']) or c == 'a'), None),
            'opt_a_img': next((c for c in df.columns if any(k in c for k in ['a_rasm', 'a rasm', 'opt_a_image', 'variant_a_rasm'])), None),
            'opt_b': next((c for c in df.columns if any(k in c for k in ['variant b', 'opt_b']) or c == 'b'), None),
            'opt_b_img': next((c for c in df.columns if any(k in c for k in ['b_rasm', 'b rasm', 'opt_b_image', 'variant_b_rasm'])), None),
            'opt_c': next((c for c in df.columns if any(k in c for k in ['variant c', 'opt_c']) or c == 'c'), None),
            'opt_c_img': next((c for c in df.columns if any(k in c for k in ['c_rasm', 'c rasm', 'opt_c_image', 'variant_c_rasm'])), None),
            'opt_d': next((c for c in df.columns if any(k in c for k in ['variant d', 'opt_d']) or c == 'd'), None),
            'opt_d_img': next((c for c in df.columns if any(k in c for k in ['d_rasm', 'd rasm', 'opt_d_image', 'variant_d_rasm'])), None),
            'correct': next((c for c in df.columns if any(k in c for k in ["to'g'ri", 'togri', 'correct', 'javob'])), None),
            'subject': next((c for c in df.columns if any(k in c for k in ['fan', 'subject'])), None),
            'section': next((c for c in df.columns if any(k in c for k in ["bo'lim", 'bolim', 'section'])), None),
            'topic': next((c for c in df.columns if any(k in c for k in ['mavzu', 'topic'])), None),
            'difficulty': next((c for c in df.columns if any(k in c for k in ['qiyinlik', 'daraja', 'difficulty'])), None),
            'explanation': next((c for c in df.columns if any(k in c for k in ['izoh', 'tushuntirish', 'explanation'])), None),
            'source': next((c for c in df.columns if any(k in c for k in ['manba', 'source'])), None)
        }

        if not col_map['text']:
            return {'success': False, 'message': "Excel jadvalida 'Savol' ustuni topilmadi.", 'errors': [], 'questions': []}

        for idx, row in df.iterrows():
            row_num = idx + 2
            q_text = str(row.get(col_map['text'], '')).strip()

            if not q_text or q_text.lower() == 'nan':
                errors.append(f"{row_num}-qator: Savol matni bo'sh.")
                continue

            # Savol rasmi
            q_img = str(row.get(col_map['q_image'], '')).strip() if col_map.get('q_image') else ''
            if q_img.lower() == 'nan':
                q_img = ''

            # Variantlar
            opt_a = str(row.get(col_map['opt_a'], '')).strip() if col_map.get('opt_a') else ''
            opt_b = str(row.get(col_map['opt_b'], '')).strip() if col_map.get('opt_b') else ''
            opt_c = str(row.get(col_map['opt_c'], '')).strip() if col_map.get('opt_c') else ''
            opt_d = str(row.get(col_map['opt_d'], '')).strip() if col_map.get('opt_d') else ''

            opt_a_img = str(row.get(col_map['opt_a_img'], '')).strip() if col_map.get('opt_a_img') else ''
            if opt_a_img.lower() == 'nan': opt_a_img = ''
            opt_b_img = str(row.get(col_map['opt_b_img'], '')).strip() if col_map.get('opt_b_img') else ''
            if opt_b_img.lower() == 'nan': opt_b_img = ''
            opt_c_img = str(row.get(col_map['opt_c_img'], '')).strip() if col_map.get('opt_c_img') else ''
            if opt_c_img.lower() == 'nan': opt_c_img = ''
            opt_d_img = str(row.get(col_map['opt_d_img'], '')).strip() if col_map.get('opt_d_img') else ''
            if opt_d_img.lower() == 'nan': opt_d_img = ''

            # Har bir variantda matn yoki rasm bo'lishi kerak
            has_a = (opt_a and opt_a.lower() != 'nan') or bool(opt_a_img)
            has_b = (opt_b and opt_b.lower() != 'nan') or bool(opt_b_img)

            if not has_a:
                errors.append(f"{row_num}-qator: A varianti matni yoki rasmi mavjud emas.")
                continue
            if not has_b:
                errors.append(f"{row_num}-qator: B varianti matni yoki rasmi mavjud emas.")
                continue

            raw_correct = str(row.get(col_map['correct'], '')).strip().upper() if col_map.get('correct') else ''
            correct_key = raw_correct[0] if raw_correct and raw_correct[0] in ['A', 'B', 'C', 'D'] else None

            if not correct_key:
                errors.append(f"{row_num}-qator: To'g'ri javob ko'rsatilmagan yoki noto'g'ri (A, B, C, D bo'lishi kerak).")
                continue

            # Duplicate tekshiruvi
            q_hash = Question.calculate_hash(q_text)
            existing_db = Question.query.filter_by(hash=q_hash).first()
            is_dup = existing_db is not None
            if is_dup:
                duplicates_count += 1

            subject_name = str(row.get(col_map['subject'], 'Umumiy')).strip() if col_map.get('subject') else 'Umumiy'
            section_name = str(row.get(col_map['section'], '')).strip() if col_map.get('section') else ''
            topic_name = str(row.get(col_map['topic'], 'Asosiy mavzu')).strip() if col_map.get('topic') else 'Asosiy mavzu'
            
            raw_diff = str(row.get(col_map['difficulty'], 'MEDIUM')).strip().upper() if col_map.get('difficulty') else 'MEDIUM'
            if 'OSON' in raw_diff or 'EASY' in raw_diff:
                diff = DifficultyLevel.EASY
            elif 'QIYIN' in raw_diff or 'HARD' in raw_diff:
                diff = DifficultyLevel.HARD
            else:
                diff = DifficultyLevel.MEDIUM

            explanation = str(row.get(col_map['explanation'], '')).strip() if col_map.get('explanation') else ''
            if explanation.lower() == 'nan':
                explanation = ''
            source = str(row.get(col_map['source'], '')).strip() if col_map.get('source') else ''
            if source.lower() == 'nan':
                source = ''

            clean_a = '' if opt_a.lower() == 'nan' else opt_a
            clean_b = '' if opt_b.lower() == 'nan' else opt_b
            clean_c = '' if opt_c.lower() == 'nan' else opt_c
            clean_d = '' if opt_d.lower() == 'nan' else opt_d

            options = [
                {'key': 'A', 'text': clean_a, 'image_url': opt_a_img, 'is_correct': (correct_key == 'A')},
                {'key': 'B', 'text': clean_b, 'image_url': opt_b_img, 'is_correct': (correct_key == 'B')}
            ]
            if clean_c or opt_c_img:
                options.append({'key': 'C', 'text': clean_c, 'image_url': opt_c_img, 'is_correct': (correct_key == 'C')})
            if clean_d or opt_d_img:
                options.append({'key': 'D', 'text': clean_d, 'image_url': opt_d_img, 'is_correct': (correct_key == 'D')})

            parsed_questions.append({
                'row_num': row_num,
                'text': q_text,
                'image_url': q_img,
                'subject': subject_name,
                'section': section_name,
                'topic': topic_name,
                'difficulty': diff,
                'explanation': explanation,
                'source': source,
                'options': options,
                'is_duplicate': is_dup,
                'hash': q_hash
            })

        return {
            'success': True,
            'total_rows': len(df),
            'valid_count': len(parsed_questions),
            'errors_count': len(errors),
            'duplicates_count': duplicates_count,
            'errors': errors,
            'questions': parsed_questions
        }

    @staticmethod
    def parse_word(file_path):
        """
        Word (.docx) fayldan savollarni ajratish.
        Format:
        1. Savol matni?
        A) Variant 1
        *B) To'g'ri variant
        C) Variant 3
        D) Variant 4
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
        line_idx = 0

        q_pattern = re.compile(r'^(?:savol\s*)?(\d+)[\.\)\-]\s*(.+)$', re.IGNORECASE)
        opt_pattern = re.compile(r'^(\*?)\s*([A-Da-d])[\.\)]\s*(.+)$')

        for para in paragraphs:
            line_idx += 1
            q_img_match = re.search(r'\[(?:rasm|image|img)\s*:\s*([^\]]+)\]', para, re.IGNORECASE)
            para_clean = re.sub(r'\[(?:rasm|image|img)\s*:\s*([^\]]+)\]', '', para, flags=re.IGNORECASE).strip()

            q_match = q_pattern.match(para_clean)
            opt_match = opt_pattern.match(para_clean)

            if q_match:
                if current_q:
                    # Oldingi savolni tekshirish
                    valid, err = QuestionImportService._validate_parsed_question(current_q, current_options)
                    if valid:
                        current_q['options'] = current_options
                        parsed_questions.append(current_q)
                    else:
                        errors.append(f"{current_q.get('num_str', '')}-savol: {err}")

                q_num = q_match.group(1)
                q_text = q_match.group(2).strip()
                q_hash = Question.calculate_hash(q_text)
                is_dup = Question.query.filter_by(hash=q_hash).first() is not None
                if is_dup:
                    duplicates_count += 1

                current_q = {
                    'num_str': q_num,
                    'text': q_text,
                    'image_url': q_img_match.group(1).strip() if q_img_match else '',
                    'subject': 'Umumiy',
                    'topic': 'Asosiy mavzu',
                    'difficulty': DifficultyLevel.MEDIUM,
                    'is_duplicate': is_dup,
                    'hash': q_hash
                }
                current_options = []

            elif opt_match and current_q:
                is_correct = bool(opt_match.group(1)) or ('*' in para)
                key = opt_match.group(2).upper()
                opt_text = opt_match.group(3).strip()
                # Agar matn ichida ham * bo'lsa tozalash
                opt_text = opt_text.replace('*', '').strip()
                opt_img = q_img_match.group(1).strip() if q_img_match else ''

                current_options.append({
                    'key': key,
                    'text': opt_text,
                    'image_url': opt_img,
                    'is_correct': is_correct
                })
            elif current_q and not opt_match:
                if q_img_match and not current_q.get('image_url'):
                    current_q['image_url'] = q_img_match.group(1).strip()
                current_q['text'] += " " + para_clean

        # Oxirgi savolni saqlash
        if current_q:
            valid, err = QuestionImportService._validate_parsed_question(current_q, current_options)
            if valid:
                current_q['options'] = current_options
                parsed_questions.append(current_q)
            else:
                errors.append(f"{current_q.get('num_str', '')}-savol: {err}")

        return {
            'success': True,
            'total_parsed': len(parsed_questions),
            'errors_count': len(errors),
            'duplicates_count': duplicates_count,
            'errors': errors,
            'questions': parsed_questions
        }

    @staticmethod
    def _validate_parsed_question(q_data, options):
        if len(options) < 2:
            return False, "Variantlar soni 2 tadan kam."
        
        correct_count = sum(1 for o in options if o['is_correct'])
        if correct_count == 0:
            return False, "To'g'ri javob ko'rsatilmagan (* belgisi topilmadi)."
        if correct_count > 1:
            return False, f"Bir nechta to'g'ri javob ({correct_count} ta) belgilangan."
        return True, ""

    @staticmethod
    def save_imported_questions(questions_list, default_subject_id=None, default_topic_id=None):
        """
        Admin tasdiqlagan savollarni bazaga saqlash.
        """
        from app.models.question import QuestionMedia, QuestionOptionMedia

        imported_count = 0
        skipped_count = 0

        for item in questions_list:
            q_text = item.get('text', '').strip()
            if not q_text:
                continue

            q_hash = item.get('hash') or Question.calculate_hash(q_text)
            
            # Agar mavjud bo'lsa, o'tkazib yuborish
            if Question.query.filter_by(hash=q_hash).first():
                skipped_count += 1
                continue

            # Fan va Mavzuni aniqlash
            subject_id = default_subject_id
            if not subject_id and item.get('subject'):
                subj = Subject.query.filter(Subject.name.ilike(item['subject'])).first()
                if not subj:
                    slug = re.sub(r'[^a-z0-9]+', '-', item['subject'].lower()).strip('-')
                    subj = Subject(name=item['subject'], slug=slug)
                    db.session.add(subj)
                    db.session.flush()
                subject_id = subj.id

            if not subject_id:
                subj = Subject.query.first()
                subject_id = subj.id if subj else 1

            topic_id = default_topic_id
            if not topic_id and item.get('topic'):
                top = Topic.query.filter_by(subject_id=subject_id).filter(Topic.name.ilike(item['topic'])).first()
                if not top:
                    top = Topic(subject_id=subject_id, name=item['topic'])
                    db.session.add(top)
                    db.session.flush()
                topic_id = top.id

            if not topic_id:
                top = Topic.query.filter_by(subject_id=subject_id).first()
                topic_id = top.id if top else 1

            q = Question(
                subject_id=subject_id,
                topic_id=topic_id,
                question_type=item.get('question_type', QuestionType.SINGLE_CHOICE),
                text=q_text,
                explanation=item.get('explanation', ''),
                difficulty=item.get('difficulty', DifficultyLevel.MEDIUM),
                source=item.get('source', ''),
                status='ACTIVE',
                is_approved=True,
                version=1,
                hash=q_hash
            )
            db.session.add(q)
            db.session.flush()

            # Savol rasmi
            q_img = item.get('image_url')
            if q_img:
                db.session.add(QuestionMedia(
                    question_id=q.id,
                    file_path=str(q_img),
                    file_url=str(q_img),
                    original_name='imported_question_image.png',
                    media_type='IMAGE'
                ))

            for opt in item.get('options', []):
                option = QuestionOption(
                    question_id=q.id,
                    key=opt.get('key', 'A'),
                    text=opt.get('text', '') or '',
                    is_correct=opt.get('is_correct', False)
                )
                db.session.add(option)
                db.session.flush()

                opt_img = opt.get('image_url')
                if opt_img:
                    db.session.add(QuestionOptionMedia(
                        option_id=option.id,
                        file_path=str(opt_img),
                        file_url=str(opt_img),
                        original_name=f"imported_opt_{opt.get('key')}.png",
                        media_type='IMAGE'
                    ))

            imported_count += 1

        db.session.commit()
        return {'imported': imported_count, 'skipped': skipped_count}
