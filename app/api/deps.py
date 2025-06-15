from typing import Generator, Optional
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jose import JWTError, jwt

from database import SessionLocal
from config import settings

security = HTTPBearer()

def get_db() -> Generator:
    """Получение сессии базы данных"""
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_current_user_optional(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(security)
) -> Optional[dict]:
    """Получение текущего пользователя (опционально)"""
    if not token:
        return None
    
    try:
        payload = jwt.decode(
            token.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    
    # Здесь должен быть запрос к БД для получения пользователя
    # Пока возвращаем mock данные
    return {
        "id": int(user_id),
        "email": f"user{user_id}@example.com",
        "full_name": f"User {user_id}",
        "is_active": True,
        "role": "user"
    }

def get_current_user(
    current_user: Optional[dict] = Depends(get_current_user_optional)
) -> dict:
    """Получение текущего пользователя (обязательно)"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return current_user

def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Получение активного пользователя"""
    if not current_user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

def get_current_active_admin(
    current_user: dict = Depends(get_current_active_user)
) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав"
        )
    return current_user 