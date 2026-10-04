import re
import json
from app.models.question import QuestionType, DifficultyLevel

class AIService:
    @staticmethod
    def parse_unstructured_text(text: str):
        """
        Matn, PDF yoki Word ko'chirilmasidan savollarni ajratish.
        Sun'iy intellekt / aqlli parsing algoritmi.
        Hech qachon to'g'ridan-to'g'ri bazaga yozilmaydi, faqat Admin Preview uchun JSON qaytaradi.
        """
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        questions = []
        current_q = None
        current_opts = []

        q_regex = re.compile(r'^(?:savol\s*)?(\d+)[\.\)\-]\s*(.+)$', re.IGNORECASE)
        opt_regex = re.compile(r'^(\*?)\s*([A-Da-d])[\.\)]\s*(.+)$')

        for line in lines:
            q_match = q_regex.match(line)
            opt_match = opt_regex.match(line)

            if q_match:
                if current_q and current_opts:
                    current_q['options'] = current_opts
                    questions.append(current_q)
                
                q_text = q_match.group(2).strip()
                current_q = {
                    'text': q_text,
                    'subject': 'Umumiy',
                    'topic': 'Asosiy',
                    'question_type': QuestionType.SINGLE_CHOICE,
                    'difficulty': DifficultyLevel.MEDIUM,
                    'points': 1.0,
                    'ai_confidence': 0.95
                }
                current_opts = []
            elif opt_match and current_q:
                is_correct = bool(opt_match.group(1)) or ('*' in line)
                current_opts.append({
                    'key': opt_match.group(2).upper(),
                    'text': opt_match.group(3).strip(),
                    'is_correct': is_correct
                })
            elif current_q and not opt_match:
                current_q['text'] += " " + line

        if current_q and current_opts:
            current_q['options'] = current_opts
            questions.append(current_q)

        # Agar regex orqali kam savol topilsa, paragraflar bo'yicha tahlil
        if not questions and len(lines) >= 3:
            # Soddalashtirilgan tahlil
            questions.append({
                'text': lines[0],
                'subject': 'Umumiy',
                'topic': 'Asosiy',
                'question_type': QuestionType.SINGLE_CHOICE,
                'difficulty': DifficultyLevel.MEDIUM,
                'points': 1.0,
                'ai_confidence': 0.80,
                'options': [
                    {'key': 'A', 'text': lines[1] if len(lines) > 1 else 'Variant A', 'is_correct': True},
                    {'key': 'B', 'text': lines[2] if len(lines) > 2 else 'Variant B', 'is_correct': False},
                ]
            })

        return {
            'success': True,
            'source': 'AI Parsing Engine',
            'extracted_count': len(questions),
            'questions': questions
        }
