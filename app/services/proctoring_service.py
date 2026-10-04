from datetime import datetime
from app.extensions import db
from app.models.session import ProctoringEvent, TestSession

class ProctoringService:
    @staticmethod
    def log_event(session_id: str, user_id: int, event_type: str, severity: str = 'LOW', details: dict = None):
        try:
            event = ProctoringEvent(
                session_id=session_id,
                user_id=user_id,
                event_type=event_type,
                severity=severity,
                details=details or {},
                created_at=datetime.utcnow()
            )
            db.session.add(event)
            db.session.commit()
            return event
        except Exception as e:
            db.session.rollback()
            print(f"[ProctoringService Error]: {e}")
            return None

    @staticmethod
    def get_session_summary(session_id: str):
        events = ProctoringEvent.query.filter_by(session_id=session_id).order_by(ProctoringEvent.created_at.asc()).all()
        
        counts = {
            'TAB_SWITCH': 0,
            'FULLSCREEN_EXIT': 0,
            'SUSPICIOUS_PASTE': 0,
            'DEVTOOLS_OPEN': 0,
            'OTHER': 0
        }
        high_severity_count = 0

        for ev in events:
            if ev.event_type in counts:
                counts[ev.event_type] += 1
            else:
                counts['OTHER'] += 1

            if ev.severity == 'HIGH':
                high_severity_count += 1

        total_violations = len(events)
        # Risk darajasi: 0 - 100%
        risk_score = min(100, (counts['TAB_SWITCH'] * 15) + (counts['FULLSCREEN_EXIT'] * 20) + (counts['DEVTOOLS_OPEN'] * 40) + (counts['SUSPICIOUS_PASTE'] * 20))

        risk_level = 'PAST'
        if risk_score >= 60:
            risk_level = 'YUQORI'
        elif risk_score >= 30:
            risk_level = "O'RTA"

        return {
            'total_events': total_violations,
            'high_severity': high_severity_count,
            'event_breakdown': counts,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'events': [{
                'type': ev.event_type,
                'severity': ev.severity,
                'time': ev.created_at.strftime('%H:%M:%S'),
                'details': ev.details
            } for ev in events]
        }
