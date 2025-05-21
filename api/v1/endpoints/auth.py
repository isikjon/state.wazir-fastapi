from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.api import deps
from app import models
from app.utils.security import get_password_hash, verify_password
from app.utils.auth import create_access_token
from datetime import timedelta
from typing import Optional
from pydantic import EmailStr
from config import settings
import re
import random
import string

router = APIRouter()

# Проверка формата телефона (для Кыргызстана)
def is_valid_phone(phone: str) -> bool:
    # Очищаем телефон от пробелов и других символов
    phone_clean = re.sub(r'\D', '', phone)
    # Проверяем, что начинается с 996 и содержит всего 12 цифр
    return phone_clean.startswith('996') and len(phone_clean) == 12

# Проверка, существует ли пользователь с указанными контактами
def user_exists(db: Session, contact: str, contact_type: str) -> bool:
    if contact_type == "email":
        user = db.query(models.User).filter(models.User.email == contact).first()
    else:  # телефон
        # Очищаем телефон от пробелов и других символов для сравнения
        phone_clean = re.sub(r'\D', '', contact)
        
        # Сначала проверяем точное совпадение
        user = db.query(models.User).filter(models.User.phone == contact).first()
        if user:
            return True
            
        # Если не нашли, ищем по очищенному номеру с любыми разделителями
        user = db.query(models.User).filter(
            models.User.phone.ilike(f"%{phone_clean}%") |
            models.User.phone == phone_clean
        ).first()
    
    return user is not None

# Получение пользователя по контакту
def get_user_by_contact(db: Session, contact: str, contact_type: str):
    if contact_type == "email":
        return db.query(models.User).filter(models.User.email == contact).first()
    else:  # телефон
        # Очищаем телефон от пробелов и других символов для сравнения
        phone_clean = re.sub(r'\D', '', contact)
        
        # Сначала поробуем точное совпадение
        user = db.query(models.User).filter(models.User.phone == contact).first()
        if user:
            return user
            
        # Если не нашли, ищем по очищенному номеру с любыми разделителями
        return db.query(models.User).filter(
            models.User.phone.ilike(f"%{phone_clean}%") | 
            models.User.phone == phone_clean
        ).first()

# Генерация случайного кода подтверждения
def generate_confirmation_code() -> str:
    # В реальном проекте здесь будет отправка SMS или Email
    # Для тестирования используем код 1111
    return "1111"

@router.post("/login")
async def login(
    contact: str = Form(...),
    password: str = Form(...),
    contact_type: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    """
    Авторизация пользователя по телефону или email
    """
    # Базовая валидация
    if contact_type == "email":
        # Простая проверка формата email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", contact):
            return {"success": False, "error": "Некорректный формат email"}
    else:  # телефон
        if not is_valid_phone(contact):
            return {"success": False, "error": "Некорректный формат телефона"}
    
    # Получаем пользователя
    user = get_user_by_contact(db, contact, contact_type)
    
    if not user:
        return {"success": False, "error": f"Пользователь с таким {contact_type} не найден"}
    
    if not verify_password(password, user.hashed_password):
        return {"success": False, "error": "Неверный пароль"}
    
    if not user.is_active:
        return {"success": False, "error": "Аккаунт неактивен"}
    
    # Создаем JWT токен
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "full_name": user.full_name
    }

@router.post("/check-exists")
async def check_exists(
    contact: str = Form(...),
    contact_type: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    """
    Проверка существования пользователя с указанным контактом
    """
    # Базовая валидация
    if contact_type == "email":
        # Простая проверка формата email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", contact):
            return {"exists": False, "error": "Некорректный формат email"}
    else:  # телефон
        if not is_valid_phone(contact):
            return {"exists": False, "error": "Некорректный формат телефона"}
    
    exists = user_exists(db, contact, contact_type)
    
    return {"exists": exists}

@router.post("/send-code")
async def send_code(
    contact: str = Form(...),
    contact_type: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    """
    Отправка кода подтверждения на указанный контакт
    """
    # Базовая валидация
    if contact_type == "email":
        # Простая проверка формата email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", contact):
            return {"success": False, "error": "Некорректный формат email"}
    else:  # телефон
        if not is_valid_phone(contact):
            return {"success": False, "error": "Некорректный формат телефона"}
    
    # Генерируем код подтверждения (в реальном приложении отправили бы его по SMS или email)
    code = generate_confirmation_code()
    
    # В реальном проекте здесь будет сохранение кода в базу данных или отправка через SMS/Email сервис
    # Для тестирования просто возвращаем успех
    
    return {"success": True, "message": "Код подтверждения отправлен"}

@router.post("/verify-code")
async def verify_code(
    code: str = Form(...),
    contact: str = Form(...),
    contact_type: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    """
    Проверка кода подтверждения
    """
    # В реальном проекте здесь будет проверка кода из базы данных
    # Для тестирования просто проверяем, что код равен 1111
    if code != "1111":
        return {"verified": False, "error": "Неверный код подтверждения"}
    
    return {"verified": True}

@router.post("/register")
async def register(
    first_name: str = Form(...),
    last_name: str = Form(...),
    contact: str = Form(...),
    contact_type: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    """
    Регистрация нового пользователя
    """
    # Базовая валидация
    if not first_name or not last_name:
        return {"success": False, "error": "Имя и фамилия обязательны"}
    
    if len(password) < 6:
        return {"success": False, "error": "Пароль должен содержать минимум 6 символов"}
    
    # Проверяем, что пользователя с таким контактом не существует
    if user_exists(db, contact, contact_type):
        return {"success": False, "error": f"Пользователь с таким {contact_type} уже существует"}
    
    # Создаем нового пользователя
    user = models.User(
        full_name=f"{first_name} {last_name}",
        hashed_password=get_password_hash(password),
        is_active=True,
        status=models.UserStatus.ACTIVE
    )
    
    if contact_type == "email":
        user.email = contact
    else:  # телефон
        user.phone = contact
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Создаем JWT токен
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "full_name": user.full_name
    }

@router.post("/reset-password")
async def reset_password(
    contact: str = Form(...),
    contact_type: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    """
    Сброс пароля
    """
    # Базовая валидация
    if len(password) < 6:
        return {"success": False, "error": "Пароль должен содержать минимум 6 символов"}
    
    # Получаем пользователя
    user = get_user_by_contact(db, contact, contact_type)
    
    if not user:
        return {"success": False, "error": f"Пользователь с таким {contact_type} не найден"}
    
    # Обновляем пароль
    user.hashed_password = get_password_hash(password)
    db.commit()
    
    return {"success": True} 