from datetime import datetime
from app.extensions import db
from app.models.user import User
from app.models.result import Result, UserQuestionStat, UserTopicStat
from app.models.question import Topic, Subject

class AnalyticsService:
    @staticmethod
    def get_user_dashboard_stats(user_id: int):
        user = User.query.get(user_id)
        if not user:
            return {}

        results = Result.query.filter_by(user_id=user.id).order_by(Result.created_at.desc()).all()
        total_tests = len(results)
        
        avg_score = 0
        if total_tests > 0:
            avg_score = round(sum(float(r.percentage) for r in results) / total_tests, 1)

        # Zaif mavzular (aniqlik < 60%)
        weak_topics = UserTopicStat.query.filter_by(user_id=user.id)\
            .filter(UserTopicStat.total_answered >= 2)\
            .filter(UserTopicStat.accuracy_percentage < 60.0)\
            .order_by(UserTopicStat.accuracy_percentage.asc())\
            .limit(5).all()

        weak_list = []
        for wt in weak_topics:
            topic = wt.topic
            subj_name = topic.subject.name if topic and topic.subject else "Fan"
            weak_list.append({
                'topic_id': wt.topic_id,
                'topic_name': topic.name if topic else "Mavzu",
                'subject_name': subj_name,
                'accuracy': float(wt.accuracy_percentage),
                'answered': wt.total_answered
            })

        # Xatolar soni
        mistakes_count = UserQuestionStat.query.filter_by(user_id=user.id, is_last_correct=False).count()

        # Faol paket va qolgan kunlar
        entitlement = user.get_active_entitlement()
        package_info = None
        if entitlement:
            package_info = {
                'name': entitlement.package.name,
                'remaining_days': entitlement.remaining_days,
                'expires_at': entitlement.expires_at.strftime('%Y-%m-%d')
            }

        return {
            'readiness_score': user.get_readiness_score(),
            'total_tests': total_tests,
            'average_accuracy': avg_score,
            'weak_topics_count': len(weak_list),
            'weak_topics': weak_list,
            'mistakes_count': mistakes_count,
            'package_info': package_info,
            'has_active_package': user.has_active_package(),
            'recent_results': results[:5]
        }

    @staticmethod
    def get_weak_topics(user_id: int):
        """Foydalanuvchining barcha zaif mavzulari ro'yxati"""
        stats = UserTopicStat.query.filter_by(user_id=user_id)\
            .filter(UserTopicStat.total_answered >= 2)\
            .filter(UserTopicStat.accuracy_percentage < 60.0)\
            .order_by(UserTopicStat.accuracy_percentage.asc()).all()

        result = []
        for s in stats:
            t = s.topic
            if t:
                result.append({
                    'topic_id': t.id,
                    'topic_name': t.name,
                    'subject_id': t.subject_id,
                    'subject_name': t.subject.name if t.subject else "",
                    'accuracy': float(s.accuracy_percentage),
                    'total_answered': s.total_answered,
                    'correct_answered': s.correct_answered
                })
        return result

    @staticmethod
    def get_user_readiness_score(user_id: int):
        user = User.query.get(user_id)
        if not user:
            return 0.0
        return user.get_readiness_score()

