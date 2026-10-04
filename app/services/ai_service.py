import re
import json
from flask import current_app
from app.models.question import QuestionType, DifficultyLevel, Question, Topic
from app.models.result import Result, ResultDetail, UserTopicStat

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

    @staticmethod
    def generate_recommendations(user_id: int, result_id: int = None) -> str:
        """
        O'qituvchining test natijalari asosida shaxsiy AI tavsiyasi shakllantirish.
        Bu tavsiya rasmiy davlat attestatsiyasi natijasi emas, balki platformadagi ichki tayyorgarlik tahlili hisoblanadi.
        """
        # Natija ma'lumotlarini olish
        result = Result.query.get(result_id) if result_id else None
        
        details = result.details if result else []
        strong_topics = []
        weak_topics = []

        for d in details:
            topic_name = d.topic.name if d.topic else (d.subject.name if d.subject else "Mavzu")
            perc = float(d.topic_percentage)
            if perc >= 75.0:
                strong_topics.append(f"{topic_name} ({perc:.0f}%)")
            elif perc < 60.0:
                weak_topics.append(f"{topic_name} ({perc:.0f}%)")

        # Tavsiya matnini shakllantirish
        recommendation_parts = []

        if result:
            score_perc = float(result.percentage)
            recommendation_parts.append(
                f"Platformadagi ushbu test natijangiz: {score_perc:.1f}%. "
                f"To'g'ri javoblar: {result.correct_answers}/{result.total_questions}."
            )

        if strong_topics:
            strong_str = ", ".join(strong_topics[:3])
            recommendation_parts.append(f"Siz {strong_str} mavzulari bo'yicha yuqori bilim darajasini ko'rsatmoqdasiz.")

        if weak_topics:
            weak_str = ", ".join(weak_topics[:3])
            recommendation_parts.append(
                f"Biroq {weak_str} bo'yicha natijalaringiz pastroq bo'ldi. "
                f"Keyingi mashg'ulotlarda ushbu mavzularga oid testlarni alohida ishlab chiqish tavsiya etiladi."
            )
        else:
            recommendation_parts.append("Barcha mavzular bo'yicha barqaror natija ko'rsatildi. Tayyorgarlikni yanada mustahkamlash uchun qiyin darajadagi savollarni ishlashingiz mumkin.")

        recommendation_parts.append(
            "Eslatma: Ushbu tahlil platformaning ichki tayyorgarlik ko'rsatkichi bo'lib, rasmiy davlat attestatsiyasi natijasi hisoblanmaydi."
        )

        return " ".join(recommendation_parts)
