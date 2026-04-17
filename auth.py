from jose import jwt, JWTError
import bcrypt
from datetime import datetime, timedelta
from fastapi import Request
from sqlalchemy.orm import Session
import models

SECRET_KEY = "sigma-energia-2026-proyectos-secret"
ALGORITHM = "HS256"
EXPIRE_DAYS = 7


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def create_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(days=EXPIRE_DAYS)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(request: Request, db: Session) -> models.Usuario | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        return None
    return db.query(models.Usuario).filter(
        models.Usuario.id == user_id,
        models.Usuario.activo == True
    ).first()
