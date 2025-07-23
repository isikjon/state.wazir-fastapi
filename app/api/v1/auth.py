from datetime import timedelta
from typing import Any
import re

from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func

from app import models, schemas, services
from app.api import deps
from app.utils.security import create_access_token, verify_password, get_password_hash
# from app.utils.email import send_reset_password_email
from app.utils.token import generate_password_reset_token, verify_password_reset_token
from config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/login/access-token", response_model=schemas.Token)
def login_access_token(
    db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    # Сначала пытаемся точное совпадение
    user = db.query(models.User).filter(
        (models.User.email == form_data.username) |
        (models.User.phone == form_data.username)
    ).first()
    
    # Если не нашли и это похоже на телефон, пытаемся нормализованный поиск
    if not user and not '@' in form_data.username:
        phone_clean = re.sub(r'\D', '', form_data.username)
        if len(phone_clean) >= 10:  # Минимальная длина телефона
            user = db.query(models.User).filter(
                func.replace(
                    func.replace(
                        func.replace(
                            func.replace(
                                func.replace(models.User.phone, '+', ''), 
                                ' ', ''
                            ), 
                            '-', ''
                        ), 
                        '(', ''
                    ), 
                    ')', ''
                ) == phone_clean
            ).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email/телефон или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Аккаунт неактивен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.post("/register", response_model=schemas.User)
def register_user(
    *, db: Session = Depends(deps.get_db), user_in: schemas.UserCreate
) -> Any:
    # Сначала пытаемся точное совпадение
    user = db.query(models.User).filter(
        (models.User.email == user_in.email) |
        (models.User.phone == user_in.phone)
    ).first()
    
    # Если не нашли по точному совпадению и есть телефон, проверяем нормализованный поиск
    if not user and user_in.phone:
        phone_clean = re.sub(r'\D', '', user_in.phone)
        if len(phone_clean) >= 10:  # Минимальная длина телефона
            user = db.query(models.User).filter(
                func.replace(
                    func.replace(
                        func.replace(
                            func.replace(
                                func.replace(models.User.phone, '+', ''), 
                                ' ', ''
                            ), 
                            '-', ''
                        ), 
                        '(', ''
                    ), 
                    ')', ''
                ) == phone_clean
            ).first()
    
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с такой почтой или телефоном уже существует",
        )
    user = services.user.create(db, obj_in=user_in)
    return user


@router.post("/password-recovery/{email}", response_model=schemas.Msg)
def recover_password(email: str, db: Session = Depends(deps.get_db)) -> Any:
    user = services.user.get_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь с таким email не найден",
        )
    password_reset_token = generate_password_reset_token(email=email)
    
    # Вместо отправки письма, просто логируем токен
    logger.info(f"Токен для сброса пароля: {password_reset_token}")
    
    return {"msg": "Инструкции по восстановлению пароля отправлены на указанный email"}


@router.post("/reset-password/", response_model=schemas.Msg)
def reset_password(
    token: str = Body(...),
    new_password: str = Body(...),
    db: Session = Depends(deps.get_db),
) -> Any:
    email = verify_password_reset_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недействительный токен",
        )
    user = services.user.get_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неактивный пользователь",
        )
    hashed_password = get_password_hash(new_password)
    user.hashed_password = hashed_password
    db.add(user)
    db.commit()
    return {"msg": "Пароль успешно обновлен"} 