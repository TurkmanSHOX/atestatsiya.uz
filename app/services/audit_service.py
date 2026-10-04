from datetime import datetime
from flask import request
from app.extensions import db
from app.models.system import AuditLog

class AuditService:
    @staticmethod
    def log_action(user_id, action, entity, entity_id=None, old_values=None, new_values=None, ip_address=None):
        try:
            if not ip_address:
                try:
                    ip_address = request.remote_addr
                except Exception:
                    ip_address = '127.0.0.1'

            log = AuditLog(
                user_id=user_id,
                action=action,
                entity=entity,
                entity_id=str(entity_id) if entity_id is not None else None,
                old_values=old_values,
                new_values=new_values,
                ip_address=ip_address,
                created_at=datetime.utcnow()
            )
            db.session.add(log)
            db.session.commit()
            return log
        except Exception as e:
            db.session.rollback()
            print(f"[AuditService Error]: {e}")
            return None
