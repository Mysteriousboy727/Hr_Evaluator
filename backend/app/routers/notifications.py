from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Notification, User
from ..security import current_user

router = APIRouter(tags=["notifications"])


@router.get("/notifications")
def list_notifications(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = (db.query(Notification).filter(Notification.user_id == user.id)
            .order_by(Notification.id.desc()).limit(50).all())
    return {"unread": sum(1 for n in rows if not n.read),
            "items": [{"id": n.id, "title": n.title, "body": n.body, "read": n.read,
                       "created_at": n.created_at.isoformat(timespec="minutes")} for n in rows]}


@router.post("/notifications/read")
def mark_read(db: Session = Depends(get_db), user: User = Depends(current_user)):
    db.query(Notification).filter(Notification.user_id == user.id, Notification.read.is_(False)).update({"read": True})
    db.commit()
    return {"ok": True}