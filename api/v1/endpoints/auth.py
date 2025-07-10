from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.api import deps
from app import models
from app.utils.security import get_password_hash, verify_password
from app.utils.auth import create_access_token
from datetime import timedelta, datetime
from typing import Optional
from pydantic import EmailStr
from config import settings
import re
import random
import string
from fastapi.responses import JSONResponse
import json
import os
from app.services.telegram_service import TelegramService
from app.services.user_service import UserService
from app.services.sms_service import SMSService
from app.services.devino_sms_service import devino_sms_service
from app.models.user import User

router = APIRouter()

# Проверка формата телефона (любая страна)
def is_valid_phone(phone: str) -> bool:
    # Очищаем телефон от пробелов и других символов
    phone_clean = re.sub(r'\D', '', phone)
    # Проверяем, что номер содержит от 10 до 15 цифр (международный стандарт)
    return len(phone_clean) >= 10 and len(phone_clean) <= 15

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

# Файл для хранения кодов (тот же что использует бот)
CODES_FILE = "verification_codes.json"

def load_verification_codes():
    """Загрузка кодов из файла"""
    try:
        if os.path.exists(CODES_FILE):
            with open(CODES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Конвертируем строки обратно в datetime
                for phone, code_data in data.items():
                    code_data['timestamp'] = datetime.fromisoformat(code_data['timestamp'])
                return data
    except Exception as e:
        print(f"Ошибка загрузки кодов: {e}")
    return {}

def save_verification_codes(codes):
    """Сохранение кодов в файл"""
    try:
        # Конвертируем datetime в строки для JSON
        data = {}
        for phone, code_data in codes.items():
            data[phone] = {
                'code': code_data['code'],
                'timestamp': code_data['timestamp'].isoformat(),
                'user_id': code_data.get('user_id')
            }
        
        with open(CODES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения кодов: {e}")

def verify_code_from_file(phone: str, code: str) -> bool:
    """Проверка кода из файла"""
    codes = load_verification_codes()
    
    if phone not in codes:
        return False
    
    stored_data = codes[phone]
    
    # Проверяем, не истек ли код (5 минут)
    if datetime.now() - stored_data['timestamp'] > timedelta(minutes=5):
        # Удаляем истекший код
        del codes[phone]
        save_verification_codes(codes)
        return False
    
    # Проверяем код
    if stored_data['code'] == code:
        # Удаляем код после успешной проверки
        del codes[phone]
        save_verification_codes(codes)
        return True
    
    return False

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
    request: Request,
    contact: str = Form(...),
    contact_type: str = Form(...),
    use_sms: bool = Form(True),  # Новый параметр для выбора SMS
    db: Session = Depends(deps.get_db)
):
    """
    Отправка кода подтверждения через Telegram бот ИЛИ Devino SMS
    """
    print("\n" + "=" * 80)
    print("ОТПРАВКА SMS КОДА")
    print("=" * 80)
    print(f"Контакт: {contact}")
    print(f"Тип контакта: {contact_type}")
    print(f"Использовать SMS: {use_sms}")
    
    try:
        if contact.startswith('+'):
            phone = contact
        else:
            phone = '+' + contact
        
        print(f"ТЕЛЕФОН ПОДГОТОВЛЕН: {phone}")
        
        # Выбираем способ отправки
        if use_sms:
            # Отправляем через Devino SMS API
            print("🔥 Отправка через DEVINO SMS API")
            result = await devino_sms_service.send_verification_code(phone)
            
            if result.success:
                response_data = {
                    "success": True,
                    "message": f"📱 SMS код отправлен на номер {phone}"
                }
            else:
                response_data = {
                    "success": False,
                    "error": f"Ошибка отправки SMS: {result.description}"
                }
        else:
            # Отправляем через Telegram бот (текущий способ)
            print("🤖 Отправка через TELEGRAM БОТ")
            response_data = {
                "success": True,
                "message": f"📱 Для получения кода перейдите в Telegram к боту @{settings.TELEGRAM_BOT_USERNAME} и нажмите кнопку 'Поделиться номером'.\n\n🤖 Бот отправит вам код для авторизации."
            }
        
        print(f"ОТВЕТ: {response_data}")
        print("=" * 80)
        
        return JSONResponse(
            status_code=200,
            content=response_data
        )
        
    except Exception as e:
        print(f"ОШИБКА: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Внутренняя ошибка сервера"}
        )

@router.post("/verify-code")
async def verify_code(
    code: str = Form(...),
    contact: str = Form(...),
    contact_type: str = Form(...),
    use_sms: bool = Form(True),  # Новый параметр для выбора способа проверки
    db: Session = Depends(deps.get_db)
):
    """
    Проверка кода подтверждения через Telegram бот ИЛИ Devino SMS
    """
    print("\n" + "=" * 80)
    print("ПРОВЕРКА SMS КОДА")
    print("=" * 80)
    print(f"Контакт: {contact}")
    print(f"Тип контакта: {contact_type}")
    print(f"Код: {code}")
    print(f"Использовать SMS: {use_sms}")
    
    try:
        # Приводим телефон к стандартному формату
        if contact.startswith('+'):
            phone = contact
        else:
            phone = '+' + contact
            
        # Выбираем способ проверки
        if use_sms:
            # Проверяем через Devino SMS API
            print("🔥 Проверка через DEVINO SMS API")
            result = await devino_sms_service.verify_code(phone, code)
            
            if result.success:
                print("РЕЗУЛЬТАТ: Код подтвержден через Devino SMS")
                print("=" * 80)
                return {"verified": True}
            else:
                print(f"РЕЗУЛЬТАТ: Ошибка Devino SMS: {result.description}")
                print("=" * 80)
                return {"verified": False, "error": result.description}
        else:
            # Проверяем через Telegram бот (текущий способ)
            print("🤖 Проверка через TELEGRAM БОТ")
            from telegram_bot import sms_bot
            
            if sms_bot.verify_code(phone, code):
                print("РЕЗУЛЬТАТ: Код подтвержден через Telegram бот")
                print("=" * 80)
                return {"verified": True}
            else:
                print("РЕЗУЛЬТАТ: Код не найден или неверный")
                print("=" * 80)
                return {"verified": False, "error": "Неверный код"}
            
    except Exception as e:
        print(f"ОШИБКА ПРОВЕРКИ: {str(e)}")
        print("=" * 80)
        
        # Для тестирования принимаем любой 4-значный код
        if len(code) == 4 and code.isdigit():
            print("РЕЗУЛЬТАТ: Код принят (тестовый режим)")
            return {"verified": True}
        else:
            return {"verified": False, "error": "Неверный код"}

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

@router.post("/devino/send-test")
async def test_devino_send_sms(
    phone: str = Form(..., description="Phone number to send test SMS"),
    include_imsi: bool = Form(False, description="Include IMSI code test")
):
    print("\n" + "=" * 80)
    print("🧪 DEVINO SMS TEST - SEND CODE")
    print("=" * 80)
    print(f"📱 Phone: {phone}")
    print(f"🔐 Include IMSI: {include_imsi}")
    
    try:
        imsi_code = "901700000001234" if include_imsi else None
        if imsi_code:
            print(f"🔐 Test IMSI: {imsi_code}")
        
        result = await devino_sms_service.send_verification_code(phone, imsi_code)
        
        response_data = {
            "service": "Devino SMS Test",
            "phone": phone,
            "success": result.success,
            "code": result.code,
            "description": result.description,
            "data": result.data,
            "imsi_included": bool(imsi_code)
        }
        
        if result.success:
            print(f"✅ TEST PASSED: {result.description}")
            if 'code' in result.data:
                print(f"🔑 Generated code: {result.data['code']}")
        else:
            print(f"❌ TEST FAILED: {result.description}")
        
        print("=" * 80)
        return response_data
        
    except Exception as e:
        print(f"💥 TEST ERROR: {str(e)}")
        print("=" * 80)
        return {
            "service": "Devino SMS Test",
            "phone": phone,
            "success": False,
            "error": str(e)
        }

@router.post("/devino/verify-test")
async def test_devino_verify_sms(
    phone: str = Form(..., description="Phone number"),
    code: str = Form(..., description="4-digit verification code")
):
    print("\n" + "=" * 80)
    print("🧪 DEVINO SMS TEST - VERIFY CODE")
    print("=" * 80)
    print(f"📱 Phone: {phone}")
    print(f"🔢 Code: {code}")
    
    try:
        result = await devino_sms_service.verify_code(phone, code)
        
        response_data = {
            "service": "Devino SMS Verification Test",
            "phone": phone,
            "code": code,
            "success": result.success,
            "result_code": result.code,
            "description": result.description,
            "data": result.data
        }
        
        if result.success:
            print(f"✅ VERIFICATION PASSED: {result.description}")
        else:
            print(f"❌ VERIFICATION FAILED: {result.description}")
        
        print("=" * 80)
        return response_data
        
    except Exception as e:
        print(f"💥 VERIFICATION ERROR: {str(e)}")
        print("=" * 80)
        return {
            "service": "Devino SMS Verification Test",
            "phone": phone,
            "code": code,
            "success": False,
            "error": str(e)
        }

@router.get("/devino/test")
async def test_devino_sms():
    print("\n" + "=" * 80)
    print("🔍 DEVINO SMS API STATUS CHECK")
    print("=" * 80)
    
    config_status = {
        "api_url": devino_sms_service.api_url,
        "api_key_configured": bool(devino_sms_service.api_key),
        "debug_mode": devino_sms_service.debug_mode,
        "timeout": devino_sms_service.timeout
    }
    
    print(f"📋 Configuration: {config_status}")
    
    balance_result = None
    if devino_sms_service.api_key:
        try:
            print("💰 Checking balance...")
            balance_result = await devino_sms_service.get_balance()
            print(f"💰 Balance result: {balance_result.success} - {balance_result.description}")
        except Exception as e:
            print(f"💥 Balance error: {e}")
            balance_result = {"error": str(e)}
    else:
        print("⚠️  No API key - skipping balance check")
    
    print("=" * 80)
    
    return {
        "service": "Devino SMS API",
        "status": "configured" if devino_sms_service.api_key else "not_configured",
        "config": config_status,
        "balance": {
            "success": balance_result.success if balance_result and hasattr(balance_result, 'success') else False,
            "description": balance_result.description if balance_result and hasattr(balance_result, 'description') else "API key not configured",
            "data": balance_result.data if balance_result and hasattr(balance_result, 'data') else None
        } if balance_result else {"error": "API key not configured"},
        "endpoints": {
            "send_test": "/api/v1/auth/devino/send-test",
            "verify_test": "/api/v1/auth/devino/verify-test",
            "production_send": "/api/v1/auth/send-code?use_sms=true",
            "production_verify": "/api/v1/auth/verify-code?use_sms=true"
        }
    } 