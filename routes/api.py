from fastapi import APIRouter, Request, Response, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List, Union
from models.settings import Settings
from models.user import User
from models.subscription import PushSubscription
from database import get_db, Database
import json
import uuid
from datetime import datetime
import base64
import os
from pywebpush import webpush, WebPushException

# Создаем роутер для API
router = APIRouter(prefix="/api/v1")

# Генерируем VAPID ключи при первом запуске, если их нет
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY")
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY")
VAPID_CLAIMS = {
    "sub": "mailto:admin@wazir.ru"
}

# Хранилище подписок для демонстрации
# В реальном приложении нужно хранить в базе данных
subscriptions = []

# Эндпоинт для получения публичного VAPID ключа
@router.get("/push/vapid-key")
async def get_vapid_key():
    if not VAPID_PUBLIC_KEY:
        return JSONResponse(
            status_code=500, 
            content={"success": False, "message": "VAPID ключи не настроены на сервере"}
        )
    return {"publicKey": VAPID_PUBLIC_KEY}

# Эндпоинт для сохранения push-подписки
@router.post("/push/subscribe")
async def subscribe(request: Request):
    try:
        subscription_data = await request.json()
        
        # Проверяем наличие необходимых данных
        if not subscription_data or not subscription_data.get("endpoint"):
            return JSONResponse(
                status_code=400, 
                content={"success": False, "message": "Некорректные данные подписки"}
            )
        
        # Создаем объект подписки
        subscription = {
            "id": str(uuid.uuid4()),
            "user_id": "admin",  # В реальном приложении - ID пользователя из сессии
            "subscription": subscription_data,
            "created_at": datetime.now().isoformat()
        }
        
        # В реальном приложении сохраняем в базу данных
        # Для демонстрации сохраняем в список
        for idx, sub in enumerate(subscriptions):
            if sub.get("subscription", {}).get("endpoint") == subscription_data.get("endpoint"):
                subscriptions[idx] = subscription
                return {"success": True, "message": "Подписка обновлена"}
        
        subscriptions.append(subscription)
        return {"success": True, "message": "Успешно подписаны на уведомления"}
        
    except Exception as e:
        print(f"Ошибка при сохранении подписки: {e}")
        return JSONResponse(
            status_code=500, 
            content={"success": False, "message": str(e)}
        )

# Эндпоинт для отмены подписки
@router.post("/push/unsubscribe")
async def unsubscribe(request: Request):
    try:
        subscription_data = await request.json()
        
        if not subscription_data or not subscription_data.get("endpoint"):
            return JSONResponse(
                status_code=400, 
                content={"success": False, "message": "Некорректные данные подписки"}
            )
        
        # В реальном приложении удаляем из базы данных
        # Для демонстрации удаляем из списка
        endpoint = subscription_data.get("endpoint")
        for idx, sub in enumerate(subscriptions):
            if sub.get("subscription", {}).get("endpoint") == endpoint:
                del subscriptions[idx]
                return {"success": True, "message": "Подписка отменена"}
        
        return {"success": True, "message": "Подписка не найдена"}
        
    except Exception as e:
        print(f"Ошибка при отмене подписки: {e}")
        return JSONResponse(
            status_code=500, 
            content={"success": False, "message": str(e)}
        )

# Эндпоинт для отправки тестового уведомления
@router.post("/push/test")
async def send_test_push(request: Request, background_tasks: BackgroundTasks):
    try:
        if not subscriptions:
            return {"success": False, "message": "Нет активных подписок"}
        
        # Данные для тестового уведомления
        notification_data = {
            "title": "Тестовое уведомление Wazir",
            "body": "Это тестовое push-уведомление. Система уведомлений работает корректно!",
            "icon": "/static/layout/assets/img/logo_non.png",
            "url": "/admin/dashboard"
        }
        
        # Отправляем уведомление всем подписчикам в фоновой задаче
        background_tasks.add_task(send_push_notifications, notification_data)
        
        return {"success": True, "message": "Тестовое уведомление отправлено"}
        
    except Exception as e:
        print(f"Ошибка при отправке тестового уведомления: {e}")
        return JSONResponse(
            status_code=500, 
            content={"success": False, "message": str(e)}
        )

# Эндпоинт для сохранения настроек
@router.post("/settings")
async def update_settings(request: Request, db: Database = Depends(get_db)):
    try:
        settings_data = await request.json()
        
        # В реальном приложении сохраняем в базу данных
        # Для демонстрации просто возвращаем успех
        return {"success": True, "message": "Настройки успешно сохранены"}
        
    except Exception as e:
        print(f"Ошибка при сохранении настроек: {e}")
        return JSONResponse(
            status_code=500, 
            content={"success": False, "message": str(e)}
        )

# Эндпоинт для сброса настроек
@router.post("/settings/reset")
async def reset_settings(request: Request, db: Database = Depends(get_db)):
    try:
        # В реальном приложении сбрасываем настройки в базе данных
        # Для демонстрации просто возвращаем успех
        return {"success": True, "message": "Настройки успешно сброшены"}
        
    except Exception as e:
        print(f"Ошибка при сбросе настроек: {e}")
        return JSONResponse(
            status_code=500, 
            content={"success": False, "message": str(e)}
        )

# Фоновая функция для отправки уведомлений
async def send_push_notifications(notification_data: Dict[str, Any]):
    """Отправляет push-уведомления всем подписчикам."""
    if not VAPID_PRIVATE_KEY:
        print("VAPID ключи не настроены, отправка уведомлений невозможна")
        return
    
    for subscription in subscriptions:
        try:
            subscription_info = subscription.get("subscription")
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(notification_data),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS
            )
        except WebPushException as e:
            print(f"Ошибка при отправке уведомления: {e}")
            # Если ошибка связана с тем, что подписка больше не действительна, удаляем её
            if e.response and e.response.status_code == 410:
                for idx, sub in enumerate(subscriptions):
                    if sub.get("id") == subscription.get("id"):
                        del subscriptions[idx]
                        break
        except Exception as e:
            print(f"Неизвестная ошибка при отправке уведомления: {e}") 