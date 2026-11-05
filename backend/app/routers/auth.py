import os
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Token
from ..schemas import RegisterIn, LoginIn
from ..security import hash_password, verify_password, current_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _session(db, u):
    t = Token(token=secrets.token_urlsafe(32), user_id=u.id)
    db.add(t)
    db.commit()
    return {"token": t.token, "user": {"id": u.id, "name": u.name, "email": u.email, "role": u.role}}


@router.post("/register")
def register(p: RegisterIn, db: Session = Depends(get_db)):
    email = p.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "Email already registered")
    if p.role == "hr" and p.hr_code != os.getenv("HR_SIGNUP_CODE", "akshara-hr"):
        raise HTTPException(403, "Invalid HR signup code")
    u = User(name=p.name, email=email, phone=p.phone, role=p.role, password_hash=hash_password(p.password))
    db.add(u)
    db.commit()
    db.refresh(u)
    return _session(db, u)


@router.post("/login")
def login(p: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == p.email.lower()).first()
    if not u or not verify_password(p.password, u.password_hash):
        raise HTTPException(401, "Wrong email or password")
    return _session(db, u)


@router.get("/me")
def me(u: User = Depends(current_user)):
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role}