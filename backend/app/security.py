import hashlib
import secrets
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from .database import get_db
from .models import User, Token


def hash_password(pw: str, salt: str = None) -> str:
    salt = salt or secrets.token_hex(8)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${h}"


def verify_password(pw: str, stored: str) -> bool:
    salt = stored.split("$")[0]
    return secrets.compare_digest(hash_password(pw, salt), stored)


def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    token = authorization.replace("Bearer ", "").strip()
    t = db.get(Token, token) if token else None
    if not t:
        raise HTTPException(401, "Not authenticated")
    return db.get(User, t.user_id)


def require_role(role: str):
    def dep(u: User = Depends(current_user)) -> User:
        if u.role != role:
            raise HTTPException(403, f"{role} access only")
        return u
    return dep