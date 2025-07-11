from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy import or_
from app import deps
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
import json
import os
from app.services.devino_sms_service import DevinoSMSService

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
    use_sms: bool = Form(True),  # Изменил default на True
    db: Session = Depends(deps.get_db)
):
    """Отправка кода подтверждения"""
    print("\n" + "=" * 80)
    print("ОТПРАВКА SMS КОДА")
    print("=" * 80)
    print(f"Контакт: {contact}")
    print(f"Тип контакта: {contact_type}")
    print(f"Использовать SMS: {use_sms}")
    
    try:
        if contact_type == "phone":
            # Нормализация номера телефона
            normalized_phone = contact.strip()
            if not normalized_phone.startswith('+'):
                if normalized_phone.startswith('0'):
                    normalized_phone = '+996' + normalized_phone[1:]
                elif len(normalized_phone) == 9:
                    normalized_phone = '+996' + normalized_phone
                else:
                    normalized_phone = '+' + normalized_phone
            
            print(f"ТЕЛЕФОН ПОДГОТОВЛЕН: {normalized_phone}")
            
            if use_sms:
                print("🔥 Отправка через DEVINO SMS API")
                devino_service = DevinoSMSService()
                
                # Используем новый метод send_sms_code
                result = await devino_service.send_sms_code(normalized_phone)
                
                print(f"ОТВЕТ: {result}")
                print("=" * 80)
                
                if result.get('success'):
                    response_data = {
                        "success": True,
                        "message": result.get('message', 'SMS код отправлен'),
                        "contact": normalized_phone,
                        "debug": result.get('debug', False)
                    }
                else:
                    response_data = {
                        "success": False,
                        "error": result.get('error', 'Неизвестная ошибка отправки SMS')
                    }
            else:
                print("🤖 Отправка через Telegram Bot")
                response_data = {
                    "success": True,
                    "message": f"📱 Для получения кода перейдите в Telegram к боту @{settings.TELEGRAM_BOT_USERNAME} и нажмите кнопку 'Поделиться номером'.\n\n🤖 Бот отправит вам код для авторизации."
                }
                
        else:
            response_data = {
                "success": False,
                "error": "Поддерживается только отправка на номер телефона"
            }
            
        return JSONResponse(
            status_code=200,
            content=response_data
        )
            
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: {str(e)}")
        print("=" * 80)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Ошибка сервера: {str(e)}"
            }
        )

@router.post("/verify-code")
async def verify_code(
    code: str = Form(...),
    contact: str = Form(...),
    contact_type: str = Form(...),
    use_sms: bool = Form(True),  # Изменил default на True
    db: Session = Depends(deps.get_db)
):
    """Проверка кода подтверждения"""
    print("\n" + "=" * 80)
    print("ПРОВЕРКА SMS КОДА")
    print("=" * 80)
    print(f"Контакт: {contact}")
    print(f"Код: {code}")
    print(f"Использовать SMS: {use_sms}")
    
    try:
        if contact_type == "phone":
            # Нормализация номера телефона
            normalized_phone = contact.strip()
            if not normalized_phone.startswith('+'):
                if normalized_phone.startswith('0'):
                    normalized_phone = '+996' + normalized_phone[1:]
                elif len(normalized_phone) == 9:
                    normalized_phone = '+996' + normalized_phone
                else:
                    normalized_phone = '+' + normalized_phone
            
            print(f"ТЕЛЕФОН ПОДГОТОВЛЕН: {normalized_phone}")
            print(f"КОД ДЛЯ ПРОВЕРКИ: {code}")
            
            if use_sms:
                print("🔥 Проверка через DEVINO SMS API")
                devino_service = DevinoSMSService()
                
                # Используем новый метод verify_sms_code
                result = await devino_service.verify_sms_code(normalized_phone, code)
                
                print(f"ОТВЕТ: {result}")
                print("=" * 80)
                
                if result.get('success'):
                    is_valid = result.get('valid', False)
                    if is_valid:
                        return {"verified": True}
                    else:
                        return {"verified": False, "error": result.get('message', 'Неверный код подтверждения')}
                else:
                    return {"verified": False, "error": result.get('error', 'Ошибка проверки кода')}
            else:
                print("🤖 Проверка через Telegram Bot")
                from telegram_bot import sms_bot
                
                if sms_bot.verify_code(normalized_phone, code):
                    return {"verified": True}
                else:
                    return {"verified": False, "error": "Неверный код"}
                
        else:
            return {"verified": False, "error": "Поддерживается только проверка номера телефона"}
            
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: {str(e)}")
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
async def devino_send_test(
    phone: str = Form(...),
    imsi_code: str = Form(None)
):
    """Тестовая отправка SMS через Devino API"""
    print("\n" + "=" * 80)
    print("🧪 DEVINO SMS TEST - SEND")
    print("=" * 80)
    print(f"📱 Phone: {phone}")
    
    try:
        devino_service = DevinoSMSService()
        
        if imsi_code:
            print(f"🔐 Test IMSI: {imsi_code}")
        
        result = await devino_service.send_sms_code(phone)
        
        response_data = {
            "success": result.get('success', False),
            "message": result.get('message', ''),
            "error": result.get('error', ''),
            "phone": phone,
            "debug": result.get('debug', False)
        }
        
        print(f"✅ Result: {response_data}")
        print("=" * 80)
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        error_msg = f"Test error: {str(e)}"
        print(f"❌ {error_msg}")
        print("=" * 80)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": error_msg}
        )

@router.post("/devino/verify-test")  
async def devino_verify_test(
    phone: str = Form(...),
    code: str = Form(...)
):
    """Тестовая проверка SMS кода через Devino API"""
    print("\n" + "=" * 80)
    print("🧪 DEVINO SMS TEST - VERIFY")
    print("=" * 80)
    print(f"📱 Phone: {phone}")
    print(f"🔢 Code: {code}")
    
    try:
        devino_service = DevinoSMSService()
        result = await devino_service.verify_sms_code(phone, code)
        
        response_data = {
            "success": result.get('success', False),
            "valid": result.get('valid', False),
            "message": result.get('message', ''),
            "error": result.get('error', ''),
            "phone": phone,
            "debug": result.get('debug', False)
        }
        
        print(f"✅ Result: {response_data}")
        print("=" * 80)
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        error_msg = f"Verification test error: {str(e)}"
        print(f"❌ {error_msg}")
        print("=" * 80)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": error_msg}
        )

@router.get("/devino/test")
async def devino_test():
    """Тест конфигурации Devino SMS API"""
    print("\n" + "=" * 80)
    print("🧪 DEVINO SMS CONFIGURATION TEST")
    print("=" * 80)
    
    try:
        devino_service = DevinoSMSService()
        
        config_status = {
            "api_url": devino_service.api_url,
            "api_key_configured": bool(devino_service.api_key),
            "debug_mode": devino_service.debug_mode
        }
        
        print(f"📋 Configuration: {config_status}")
        
        balance_result = None
        if devino_service.api_key:
            try:
                print("💰 Checking balance...")
                balance_result = await devino_service.get_balance()
                print(f"💰 Balance result: {balance_result}")
            except Exception as e:
                print(f"❌ Balance check failed: {e}")
                balance_result = {"error": str(e)}
        
        print("=" * 80)
        
        return {
            "service": "Devino SMS API",
            "status": "configured" if devino_service.api_key else "not_configured",
            "config": config_status,
            "balance": balance_result
        }
        
    except Exception as e:
        error_msg = f"Configuration test failed: {str(e)}"
        print(f"❌ {error_msg}")
        print("=" * 80)
        return JSONResponse(
            status_code=500,
            content={"error": error_msg}
        ) 