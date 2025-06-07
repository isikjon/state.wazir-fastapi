from fastapi import FastAPI, Request, Depends, Form, status, HTTPException, Query, WebSocket, WebSocketDisconnect, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from config import settings
from api.v1.api import api_router
from sqlalchemy.orm import Session, joinedload
from app.api import deps
from app.utils.security import verify_password
from app import models
from app.models.user import User
from sqlalchemy import func, desc, or_, and_
from datetime import datetime, timedelta
from sqlalchemy.types import String
import pandas as pd
import os
from uuid import uuid4
import json
from flask import jsonify
import random
from starlette.middleware.sessions import SessionMiddleware
from typing import Dict, Any, Optional, List
from starlette.middleware.base import BaseHTTPMiddleware
from jose import jwt as pyjwt
from app.models.token import TokenPayload
from fastapi import APIRouter
from app.models.chat import AppChatModel, AppChatMessageModel
from app.models.chat_message import ChatMessage
from app.websockets.chat_manager import ConnectionManager as WebSocketManager
from app.utils.image_helper import get_valid_image_url
from app.models.property import PropertyCategory

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = pyjwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# Класс для аутентификации HTTP запросов (но не WebSocket)
class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Проверяем, является ли запрос WebSocket
        if request.scope.get("type") == "websocket":
            # Для WebSocket запросов пропускаем проверку
            return await call_next(request)
        
        # Пути, доступные без авторизации
        public_paths = [
            '/mobile/auth',
            '/mobile/register',
            '/mobile/register/verify',
            '/mobile/register/profile',
            '/mobile/reset',
            '/mobile/reset/verify',
            '/mobile/reset/password',
            '/api/v1/auth/login',
            '/api/v1/auth/check-exists',
            '/api/v1/auth/send-code',
            '/api/v1/auth/verify-code',
            '/api/v1/auth/register',
            '/api/v1/auth/reset-password',
            '/static/',
            '/favicon.ico',
            '/mobile/test-websocket',
            '/mobile/ws/',
            '/api/v1/chat/',  # Chat API general path
            '/admin/login',   # Admin login page
        ]
        
        # Для статических файлов, API разрешаем доступ
        if request.url.path.startswith('/static/'):
            return await call_next(request)
            
        # Для API запросов проверяем токен в заголовке Authorization
        if request.url.path.startswith('/api/'):
            # Разрешаем доступ к эндпоинтам авторизации без токена
            if any(request.url.path.endswith(path) for path in [
                '/login',
                '/register',
                '/check-exists',
                '/send-code',
                '/verify-code',
                '/reset-password'
            ]):
                return await call_next(request)
                
            auth_token = None
            auth_header = request.headers.get('Authorization')
            
            if auth_header and auth_header.startswith('Bearer '):
                auth_token = auth_header.split(' ')[1]
            
            if not auth_token:
                auth_token = request.cookies.get('access_token')
                print(f"DEBUG: Используем токен из cookie: {auth_token is not None}")
            
            if auth_token:
                try:
                    payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                    if datetime.fromtimestamp(payload["exp"]) < datetime.utcnow():
                        print(f"DEBUG: Token expired: {payload}")
                        return JSONResponse(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            content={"detail": "Токен истек"}
                        )
                    
                    if not auth_header:
                        request.headers.__dict__["_list"].append((b"authorization", f"Bearer {auth_token}".encode()))
                        print("DEBUG: Добавлен заголовок Authorization из cookie")
                    
                    return await call_next(request)
                except Exception as e:
                    print(f"DEBUG: Token validation error: {str(e)}")
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": f"Недействительный токен: {str(e)}"}
                    )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Требуется авторизация"}
            )
            
        if any(request.url.path.startswith(path) for path in public_paths) or '/api/v1/chat/' in request.url.path:
            return await call_next(request)
            
        auth_token = request.cookies.get('access_token')
        auth_header = request.headers.get('Authorization')
        
        print(f"DEBUG: Checking auth for path: {request.url.path}")
        print(f"DEBUG: Cookie token: {auth_token}")
        print(f"DEBUG: Auth header: {auth_header}")
        
        if auth_header and auth_header.startswith('Bearer '):
            auth_token = auth_header.split(' ')[1]
            print(f"DEBUG: Using token from header: {auth_token}")
        
        if not auth_token:
            print("DEBUG: No token found")
            if request.url.path.startswith('/admin/'):
                return RedirectResponse('/admin/login', status_code=303)
            # Для остальных маршрутов перенаправляем на страницу авторизации
            return RedirectResponse('/mobile/auth', status_code=303)
            
        # Проверяем валидность токена
        try:
            payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            print(f"DEBUG: Token payload: {payload}")
            if datetime.fromtimestamp(payload["exp"]) < datetime.utcnow():
                print("DEBUG: Token expired")
                if request.url.path.startswith('/admin/'):
                    return RedirectResponse('/admin/login', status_code=303)
                return RedirectResponse('/mobile/auth', status_code=303)
                
            # Для админ-маршрутов проверяем, что пользователь является администратором
            if request.url.path.startswith('/admin/') and not payload.get("is_admin"):
                print("DEBUG: Non-admin user trying to access admin area")
                return RedirectResponse('/admin/login', status_code=303)
                
        except Exception as e:
            print(f"DEBUG: Token validation error (cookie): {str(e)}")
            if request.url.path.startswith('/admin/'):
                return RedirectResponse('/admin/login', status_code=303)
            return RedirectResponse('/mobile/auth', status_code=303)
            
        # Если токен валиден, пропускаем запрос дальше
        return await call_next(request)

# Кастомный JSON-энкодер для обработки datetime и других неподдерживаемых типов
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        return super().default(obj)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="static", html=True, check_dir=True), name="static")

# Используем импортированный chat_manager вместо создания нового экземпляра

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "Set-Cookie"],
)

app.add_middleware(SessionMiddleware, secret_key="wazir_super_secret_key")

# Функция для сериализации объектов в JSON, используя CustomJSONEncoder
def json_serialize(obj):
    return json.dumps(obj, cls=CustomJSONEncoder)

@app.exception_handler(TypeError)
async def type_error_handler(request, exc):
    if "not JSON serializable" in str(exc):
        return JSONResponse(
            status_code=500,
            content={"detail": "Error serializing the response"},
        )
    raise exc

# Монтируем директорию media
app.mount("/media", StaticFiles(directory="media", check_dir=True), name="media")

templates = Jinja2Templates(directory="templates")

# Регистрация API роутеров
app.include_router(api_router, prefix=settings.API_V1_STR)

# Добавляем мидлвар для проверки авторизации
app.add_middleware(AuthenticationMiddleware)

# WebSocket Manager class
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.chat_messages: Dict[str, List[dict]] = {}
        # Загружаем сохраненные сообщения, если файл существует
        try:
            if os.path.exists("chat_messages.json"):
                with open("chat_messages.json", "r", encoding="utf-8") as f:
                    data = f.read()
                    if data.strip():  # проверяем, что файл не пустой
                        self.chat_messages = json.loads(data)
                        print(f"DEBUG: Загружены сохраненные сообщения чатов. Доступные комнаты: {list(self.chat_messages.keys())}")
                        for room, messages in self.chat_messages.items():
                            print(f"DEBUG: Комната {room}: {len(messages)} сообщений")
                            # Выводим первое и последнее сообщение для отладки
                            if messages:
                                print(f"DEBUG: Первое сообщение: {messages[0].get('content', 'Нет контента')}")
                                print(f"DEBUG: Последнее сообщение: {messages[-1].get('content', 'Нет контента')}")
                    else:
                        print("DEBUG: Файл с сообщениями пуст, создаем новый")
                        with open("chat_messages.json", "w", encoding="utf-8") as f:
                            json.dump({}, f, ensure_ascii=False, indent=2)
            else:
                print("DEBUG: Файл с сообщениями не найден, создаем новый")
                with open("chat_messages.json", "w", encoding="utf-8") as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"DEBUG: Ошибка при загрузке сообщений: {e}")
            # Создаем пустой файл в случае ошибки
            try:
                with open("chat_messages.json", "w", encoding="utf-8") as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
            except Exception as e2:
                print(f"DEBUG: Не удалось создать пустой файл: {e2}")

    async def connect(self, websocket: WebSocket, room: str, accept_connection: bool = True):
        if accept_connection:
            await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = []
        if websocket not in self.active_connections[room]:
            self.active_connections[room].append(websocket)
            print(f"DEBUG: Подключен к комнате {room}, всего подключений: {len(self.active_connections[room])}")
        else:
            print(f"DEBUG: Соединение уже подключено к комнате {room}")

    def disconnect(self, websocket: WebSocket, room: str):
        try:
            if room in self.active_connections:
                if websocket in self.active_connections[room]:
                    self.active_connections[room].remove(websocket)
                    print(f"DEBUG: Отключен от комнаты {room}, осталось подключений: {len(self.active_connections[room])}")
                if not self.active_connections[room]:
                    del self.active_connections[room]
                    print(f"DEBUG: Комната {room} удалена, нет активных подключений")
        except Exception as e:
            print(f"DEBUG: Ошибка при отключении от комнаты {room}: {e}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    # Метод для сохранения сообщений в файл
    def save_messages_to_file(self):
        try:
            with open("chat_messages.json", "w", encoding="utf-8") as f:
                json.dump(self.chat_messages, f, ensure_ascii=False, indent=2)
            print(f"DEBUG: Сообщения сохранены в файл. Всего комнат: {len(self.chat_messages)}")
        except Exception as e:
            print(f"ERROR: Ошибка при сохранении сообщений в файл: {e}")
    
    # Метод для добавления сообщения в память и сохранения в файл
    def add_message_to_memory(self, chat_id: str, message: dict):
        if chat_id not in self.chat_messages:
            self.chat_messages[chat_id] = []
        
        # Добавляем сообщение в память
        self.chat_messages[chat_id].append(message)
        
        # Сохраняем в файл после добавления нового сообщения
        self.save_messages_to_file()
    
    async def broadcast(self, message: dict, room: str, exclude=None):
        # Если это сообщение чата, сохраняем его в памяти
        if message.get("type") in ["message", "message_sent", "new_message"] and "message" in message:
            chat_id = str(message["message"].get("chat_id", room))
            self.add_message_to_memory(chat_id, message["message"])
        
        # Отправляем сообщение всем активным соединениям в комнате
        if room in self.active_connections:
            for connection in self.active_connections[room]:
                if connection != exclude:
                    await connection.send_json(message)

    def save_message(self, room: str, message: dict):
        if room not in self.chat_messages:
            self.chat_messages[room] = []
        self.chat_messages[room].append(message)
        # Сохраняем сообщения в файл для персистентности
        try:
            # Преобразуем datetime в строку для сериализации
            serializable_messages = {}
            for room_key, messages in self.chat_messages.items():
                serializable_messages[room_key] = []
                for msg in messages:
                    # Копируем сообщение и обрабатываем timestamp, если нужно
                    if isinstance(msg, dict):
                        serializable_messages[room_key].append(msg)
                    else:
                        # Если сообщение не словарь, преобразуем его в строку
                        serializable_messages[room_key].append(str(msg))
            
            with open("chat_messages.json", "w", encoding="utf-8") as f:
                json.dump(serializable_messages, f, ensure_ascii=False, indent=2)
                
            print(f"DEBUG: Сохранено сообщение в комнату {room}, всего сообщений: {len(self.chat_messages[room])}")
        except Exception as e:
            print(f"DEBUG: Ошибка при сохранении сообщений: {e}")

    def get_messages(self, room: str) -> List[dict]:
        """Получить все сообщения для указанной комнаты"""
        return self.chat_messages.get(room, [])
        
    async def save_message_to_db(self, message_data: dict, db: Session) -> dict:
        """Сохраняет сообщение в базу данных и возвращает его с дополнительными полями"""
        try:
            # Создаем полную копию данных сообщения
            saved_message = message_data.copy()
            
            # Добавляем timestamp если его нет
            current_time = datetime.now()
            saved_message["timestamp"] = current_time.isoformat()
            saved_message["is_read"] = False
            # Используем целочисленный ID вместо UUID для совместимости с предложенной структурой БД
            saved_message["id"] = random.randint(100, 10000)
            
            # Определяем комнату для сообщения (всегда используем меньший ID первым)
            sender_id = int(saved_message["sender_id"])
            receiver_id = int(saved_message["receiver_id"])
            room = f"{min(sender_id, receiver_id)}_{max(sender_id, receiver_id)}"
            
            # Сохраняем сообщение
            self.save_message(room, saved_message)
            
            print(f"DEBUG: Сообщение сохранено: {saved_message}")
            return saved_message
        except Exception as e:
            print(f"ERROR: Ошибка при сохранении сообщения: {e}")
            # Возвращаем базовое сообщение с временной меткой в случае ошибки
            basic_message = message_data.copy()
            basic_message["timestamp"] = datetime.now().isoformat()
            basic_message["is_read"] = False
            basic_message["id"] = str(uuid4())
            return basic_message

manager = ConnectionManager()

# ============================ WebSocket Endpoints ============================
from sqlalchemy.orm import Session
from app.api import deps
from app.websockets.chat_manager import manager as chat_manager
from jose import jwt as pyjwt

@app.websocket("/mobile/ws/chat/{token}")
async def chat_websocket_endpoint(websocket: WebSocket, token: str):
    try:
        payload = pyjwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=1008)
            return
    except Exception as e:
        print(f"WebSocket auth error: {e}")
        await websocket.close(code=1008)
        return
        
    await chat_manager.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "message":
                db = next(deps.get_db())
                message_data = {
                    "sender_id": int(user_id),
                    "receiver_id": data["receiver_id"],
                    "content": data["content"]
                }
                
                saved_message = await chat_manager.save_message_to_db(message_data, db)
                
                await websocket.send_json({
                    "type": "message_sent",
                    "message": saved_message
                })
                
                # Добавляем получателя в данные для отправки
                broadcast_message = {
                    "type": "new_message",
                    "message": saved_message,
                    "receiver_id": data["receiver_id"]
                }
                await chat_manager.broadcast(broadcast_message)
    except WebSocketDisconnect:
        chat_manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        chat_manager.disconnect(websocket, user_id)

@app.websocket("/mobile/ws/test")
async def websocket_test_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Server received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await websocket.close()
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)
        await websocket.close()

# Корневой маршрут - перенаправление на мобильную версию
@app.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(url="/mobile")

# Добавляем маршруты для доступа через /layout
@app.get("/layout", response_class=RedirectResponse)
async def layout_root():
    return RedirectResponse(url="/mobile")

@app.get("/layout/dashboard", response_class=RedirectResponse)
async def layout_dashboard():
    return RedirectResponse(url="/mobile")

@app.get("/layout/auth", response_class=RedirectResponse)
async def layout_auth():
    return RedirectResponse(url="/mobile/auth")

@app.get("/layout/profile", response_class=RedirectResponse)
async def layout_profile():
    return RedirectResponse(url="/mobile/profile")

@app.get("/layout/create-listing", response_class=RedirectResponse)
async def layout_create_listing():
    return RedirectResponse(url="/mobile/create-listing")

@app.get("/layout/search", response_class=RedirectResponse)
async def layout_search():
    return RedirectResponse(url="/mobile/search")

@app.get("/layout/property/{property_id}", response_class=RedirectResponse)
async def layout_property_detail(property_id: int):
    return RedirectResponse(url=f"/mobile/property/{property_id}")

# Новые страницы для аутентификации
@app.get("/register", response_class=RedirectResponse)
async def redirect_register():
    return RedirectResponse(url="/mobile/register")

@app.get("/reset", response_class=RedirectResponse)
async def redirect_reset():
    return RedirectResponse(url="/mobile/reset")

@app.get("/mobile/register", response_class=HTMLResponse, name="mobile_register")
async def mobile_register(request: Request):
    return templates.TemplateResponse("layout/register.html", {"request": request})

@app.get("/mobile/register/verify", response_class=HTMLResponse, name="mobile_register_verify")
async def mobile_register_verify(request: Request):
    return templates.TemplateResponse("layout/verify.html", {"request": request})

@app.get("/mobile/register/profile", response_class=HTMLResponse, name="mobile_profile_create")
async def mobile_profile_create(request: Request):
    return templates.TemplateResponse("layout/profile_create.html", {"request": request})

@app.get("/mobile/reset", response_class=HTMLResponse, name="mobile_reset")
async def mobile_reset(request: Request):
    return templates.TemplateResponse("layout/reset.html", {"request": request})

@app.get("/mobile/reset/verify", response_class=HTMLResponse, name="mobile_reset_verify")
async def mobile_reset_verify(request: Request):
    return templates.TemplateResponse("layout/reset_verify.html", {"request": request})

@app.get("/mobile/reset/password", response_class=HTMLResponse, name="mobile_reset_password")
async def mobile_reset_password(request: Request):
    return templates.TemplateResponse("layout/reset_password.html", {"request": request})

# Мобильные (клиентские) маршруты
@app.get("/mobile", response_class=HTMLResponse, name="dashboard")
async def mobile_root(request: Request):
    return templates.TemplateResponse("layout/dashboard.html", {"request": request})

@app.get("/mobile/auth", response_class=HTMLResponse, name="mobile_auth")
async def mobile_auth(request: Request):
    return templates.TemplateResponse("layout/auth.html", {"request": request})

@app.get("/mobile/profile", response_class=HTMLResponse, name="profile")
async def mobile_profile(request: Request, tab: str = None, db: Session = Depends(deps.get_db)):
    # Получаем текущего пользователя
    user = None
    formatted_user_listings = []
    formatted_saved_listings = []
    
    # Получаем токен из cookie
    auth_token = request.cookies.get('access_token')
    auth_header = request.headers.get('Authorization')
    
    if auth_header and auth_header.startswith('Bearer '):
        auth_token = auth_header.split(' ')[1]
    
    # Получаем погоду и курс валюты для отображения в шапке
    weather = {"temperature": "+20°"}
    currency = {"value": "69.8"}
    
    if auth_token:
        try:
            # Декодируем токен
            payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            
            if user_id:
                # Получаем данные пользователя из БД
                user = db.query(models.User).filter(models.User.id == user_id).first()
                
                if user:
                    # Получаем объявления пользователя с изображениями
                    try:
                        user_listings = db.query(models.Property).options(
                            joinedload(models.Property.images)
                        ).filter(models.Property.owner_id == user_id).all()
                        
                        # Форматируем объявления пользователя для шаблона
                        for prop in user_listings:
                            # Находим главное изображение или первое доступное
                            main_image = next((img for img in prop.images if img.is_main), None) or \
                                       (prop.images[0] if prop.images else None)
                            
                            formatted_user_listings.append({
                                "id": prop.id,
                                "title": prop.title,
                                "price": prop.price,
                                "address": prop.address,
                                "rooms": prop.rooms,
                                "area": prop.area,
                                "status": prop.status,
                                "notes": prop.notes,  # Дата съемки 360
                                "tour_360_url": prop.tour_360_url,
                                "has_tour": bool(prop.tour_360_url),
                                "image_url": get_valid_image_url(main_image.url if main_image else None)
                            })
                        
                    except Exception as e:
                        print(f"DEBUG: Ошибка при получении объявлений пользователя: {e}")
                    
                    # Получаем сохраненные объявления пользователя
                    try:
                        # Получаем идентификаторы сохраненных объявлений
                        favorites_query = db.query(models.Favorite).filter(models.Favorite.user_id == user_id).all()
                        saved_property_ids = [fav.property_id for fav in favorites_query]
                        
                        # Получаем сами объявления по ID с изображениями
                        if saved_property_ids:
                            saved_listings = db.query(models.Property).options(
                                joinedload(models.Property.images)
                            ).filter(
                                models.Property.id.in_(saved_property_ids)
                            ).all()
                            
                            # Форматируем сохраненные объявления для шаблона
                            for prop in saved_listings:
                                # Находим главное изображение или первое доступное
                                main_image = next((img for img in prop.images if img.is_main), None) or \
                                           (prop.images[0] if prop.images else None)
                                
                                formatted_saved_listings.append({
                                    "id": prop.id,
                                    "title": prop.title,
                                    "price": prop.price,
                                    "address": prop.address,
                                    "rooms": prop.rooms,
                                    "area": prop.area,
                                    "status": prop.status,
                                    "tour_360_url": prop.tour_360_url,
                                    "has_tour": bool(prop.tour_360_url),
                                    "image_url": get_valid_image_url(main_image.url if main_image else None)
                                })
                            
                            print(f"DEBUG: Найдено {len(saved_listings)} сохраненных объявлений")
                        else:
                            print("DEBUG: У пользователя нет избранных объявлений")
                    except Exception as e:
                        print(f"DEBUG: Ошибка при получении сохраненных объявлений: {e}")
        except Exception as e:
            print(f"DEBUG: Ошибка декодирования токена: {e}")
    
    # Если не удалось получить пользователя, перенаправляем на страницу авторизации
    if not user:
        return RedirectResponse('/mobile/auth', status_code=303)
    
    return templates.TemplateResponse(
        "layout/profile.html", 
        {
            "request": request, 
            "user": user, 
            "user_listings": formatted_user_listings, 
            "saved_listings": formatted_saved_listings,
            "active_tab": tab or "listings",
            "weather": weather,
            "currency": currency
        }
    )

@app.get("/mobile/create-listing", response_class=HTMLResponse, name="create_listing")
async def mobile_create_listing(request: Request, db: Session = Depends(deps.get_db)):
    # Получаем текущего пользователя
    user = None
    
    # Получаем токен из cookie
    auth_token = request.cookies.get('access_token')
    auth_header = request.headers.get('Authorization')
    
    if auth_header and auth_header.startswith('Bearer '):
        auth_token = auth_header.split(' ')[1]
    
    if auth_token:
        try:
            # Декодируем токен
            payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            
            if user_id:
                # Получаем данные пользователя из БД
                user = db.query(models.User).filter(models.User.id == user_id).first()
        except Exception as e:
            print(f"DEBUG: Ошибка при проверке токена: {e}")
    
    # Проверяем, авторизован ли пользователь
    if not user:
        return RedirectResponse(url="/mobile/login")
    
    return templates.TemplateResponse(
        "layout/create-listing.html",
        {
            "request": request,
            "user": user
        }
    )

@app.get("/mobile/search", response_class=HTMLResponse, name="search")
async def mobile_search(
    request: Request, 
    category: str = None, 
    price_min: int = None, 
    price_max: int = None, 
    min_area: float = None, 
    max_area: float = None,
    rooms: int = None,
    min_floor: int = None,
    max_floor: int = None,
    balcony: bool = None,
    furniture: bool = None,
    renovation: bool = None,
    parking: bool = None,
    q: str = None,
    db: Session = Depends(deps.get_db)
):
    print("\n===================================================")
    print("DEBUG: Параметры запроса:")
    print(f"  URL: {request.url}")
    print(f"  Поисковый запрос: {q}")
    print(f"  Категория: {category}")
    print(f"  Цена: {price_min} - {price_max}")
    print(f"  Площадь: {min_area} - {max_area}")
    print(f"  Комнаты: {rooms}")
    print(f"  Этаж: {min_floor} - {max_floor}")
    print(f"  Балкон: {balcony}, Мебель: {furniture}, Ремонт: {renovation}, Паркинг: {parking}")
    print("===================================================")
    
    # Формируем базовый запрос для получения активных объявлений
    query = db.query(models.Property).filter(models.Property.status == 'active')
    
    # Получаем все категории для выпадающего списка
    categories = db.query(models.Category).all()
    print(f"DEBUG: Загружены категории: {[cat.name for cat in categories]}")
    
    # Применяем фильтры, если они указаны
    if category:
        print(f"DEBUG: Применяем фильтр по категории: {category}")
        query = query.join(models.Property.categories).filter(models.Category.name == category)
    
    # Поиск по ключевому слову в названии или адресе
    if q:
        search_term = f"%{q}%"
        query = query.filter(or_(
            models.Property.title.ilike(search_term),
            models.Property.address.ilike(search_term),
            models.Property.description.ilike(search_term)
        ))
    
    # Фильтры по цене
    if price_min is not None:
        query = query.filter(models.Property.price >= price_min)
    
    if price_max is not None:
        query = query.filter(models.Property.price <= price_max)
    
    # Фильтры по площади
    if min_area is not None:
        query = query.filter(models.Property.area >= min_area)
    
    if max_area is not None:
        query = query.filter(models.Property.area <= max_area)
    
    # Фильтр по количеству комнат
    if rooms is not None:
        query = query.filter(models.Property.rooms == rooms)
    
    # Фильтры по этажу
    if min_floor is not None:
        query = query.filter(models.Property.floor >= min_floor)
    
    if max_floor is not None:
        query = query.filter(models.Property.floor <= max_floor)
    
    # Дополнительные фильтры
    if balcony is not None and balcony:
        query = query.filter(models.Property.has_balcony == True)
    
    if furniture is not None and furniture:
        query = query.filter(models.Property.has_furniture == True)
    
    if renovation is not None and renovation:
        query = query.filter(models.Property.has_renovation == True)
    
    if parking is not None and parking:
        query = query.filter(models.Property.has_parking == True)
    
    # Получаем объявления с загрузкой изображений
    properties_db = query.options(joinedload(models.Property.images)).all()
    
    # Форматируем данные для шаблона
    properties = []
    for prop in properties_db:
        # Находим главное изображение
        main_image = next((img for img in prop.images if img.is_main), None) or \
                   (prop.images[0] if prop.images else None)
        
        # Формируем массив URL изображений
        images = [get_valid_image_url(img.url) for img in prop.images] if prop.images else []
        
        properties.append({
            "id": prop.id,
            "title": prop.title,
            "price": prop.price,
            "address": prop.address,
            "rooms": prop.rooms,
            "area": prop.area,
            "floor": prop.floor,
            "has_tour": bool(prop.tour_360_url),
            "tour_360_url": prop.tour_360_url,  # Добавляем URL для 360° тура
            "has_balcony": prop.has_balcony,
            "has_furniture": prop.has_furniture,
            "has_renovation": prop.has_renovation,
            "has_parking": prop.has_parking,
            "image_url": get_valid_image_url(main_image.url if main_image else None),
            "images": images,
            "images_count": len(images)
        })
    
    # Получаем погоду и курс валюты для отображения в шапке
    weather = None
    currency = None
    try:
        # Здесь можно добавить вызов API для получения погоды и курса валюты
        # Для простоты используем заглушки
        weather = {"temperature": "+15°"}
        currency = {"value": "87.5"}
    except Exception as e:
        print(f"DEBUG: Ошибка при получении погоды или курса валюты: {e}")
    
    return templates.TemplateResponse("layout/search.html", {
        "request": request, 
        "properties": properties,
        "weather": weather,
        "currency": currency,
        "categories": categories,  # Передаем список категорий в шаблон
        "selected_category": category,  # Выбранная категория
        "q": q,  # Поисковый запрос
        "filter": {
            "category": category,
            "price_min": price_min,
            "price_max": price_max,
            "min_area": min_area,
            "max_area": max_area,
            "rooms": rooms,
            "min_floor": min_floor,
            "max_floor": max_floor,
            "balcony": balcony,
            "furniture": furniture,
            "renovation": renovation,
            "parking": parking
        }
    })

@app.get("/mobile/chats", response_class=HTMLResponse, name="chats")
async def mobile_chats(request: Request):
    return templates.TemplateResponse("mobile/chats.html", {"request": request})

@app.get("/mobile/support", response_class=HTMLResponse, name="support")
async def mobile_support(request: Request):
    return templates.TemplateResponse("mobile/support.html", {"request": request})

@app.get("/mobile/property/{property_id}", response_class=HTMLResponse, name="property")
async def mobile_property_detail(request: Request, property_id: int, db: Session = Depends(deps.get_db)):
    # Получаем текущего пользователя, если он авторизован
    current_user = None
    token = request.cookies.get('access_token')
    
    if token:
        try:
            payload = pyjwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = int(payload.get("sub"))
            current_user = db.query(models.User).filter(models.User.id == user_id).first()
        except Exception as e:
            print(f"DEBUG: Ошибка при получении пользователя: {e}")
    
    # Получаем объявление из БД
    property = db.query(models.Property).options(
        joinedload(models.Property.owner),
        joinedload(models.Property.images),
        joinedload(models.Property.categories)
    ).filter(models.Property.id == property_id).first()
    
    if not property:
        return templates.TemplateResponse("404.html", {"request": request})
    
    # Проверяем, добавлено ли объявление в избранное
    is_favorite = False
    if current_user:
        favorite = db.query(models.Favorite).filter(
            models.Favorite.user_id == current_user.id,
            models.Favorite.property_id == property.id
        ).first()
        is_favorite = favorite is not None
    
    # Получаем похожие объявления (того же типа, в том же городе)
    similar_properties = db.query(models.Property).options(
        joinedload(models.Property.images)
    ).filter(
        models.Property.id != property.id,
        models.Property.type == property.type,
        models.Property.city == property.city,
        models.Property.status == 'ACTIVE'
    ).limit(5).all()
    
    # Форматируем данные для шаблона
    property_data = {
        "id": property.id,
        "title": property.title,
        "description": property.description,
        "price": property.price,
        "address": property.address,
        "city": property.city,
        "area": property.area,
        "status": property.status,
        "is_featured": property.is_featured,
        "tour_360_url": property.tour_360_url,
        "type": property.type,
        "rooms": property.rooms,
        "floor": property.floor,
        "building_floors": property.building_floors,
        "has_balcony": property.has_balcony,
        "has_furniture": property.has_furniture,
        "has_renovation": property.has_renovation,
        "has_parking": property.has_parking,
        "notes": property.notes,  # Дата съемки 360
        "created_at": property.created_at,
        "updated_at": property.updated_at,
        "views_count": getattr(property, 'views_count', 0),  # Безопасное получение значения
        "owner": {
            "id": property.owner.id,
            "full_name": property.owner.full_name,
            "email": property.owner.email,
            "phone": property.owner.phone
        },
        "images": [{
            "id": image.id,
            "url": get_valid_image_url(image.url),
            "is_main": image.is_main
        } for image in property.images],
        "is_favorite": is_favorite,
        "is_owner": current_user and current_user.id == property.owner_id
    }
    
    # Форматируем похожие объявления
    similar_properties_data = []
    for prop in similar_properties:
        # Находим главное изображение или берем первое доступное
        main_image = next((img for img in prop.images if img.is_main), None) or \
                    (prop.images[0] if prop.images else None)
        
        similar_properties_data.append({
            "id": prop.id,
            "title": prop.title,
            "price": prop.price,
            "address": prop.address,
            "rooms": prop.rooms,
            "area": prop.area,
            "image_url": main_image.url if main_image else "/static/layout/assets/img/property-placeholder.jpg"
        })
    
    # Получаем погоду и курс валюты для отображения в шапке
    weather = None
    currency = None
    try:
        # Здесь можно добавить вызов API для получения погоды и курса валюты
        # Для простоты используем заглушки
        weather = {"temperature": "+20°"}
        currency = {"value": "69.8"}
    except Exception as e:
        print(f"DEBUG: Ошибка при получении погоды или курса валюты: {e}")
    
    return templates.TemplateResponse("layout/property.html", {
        "request": request,
        "property": property_data,
        "similar_properties": similar_properties_data,
        "weather": weather,
        "currency": currency,
        "user": current_user
    })

@app.get("/mobile/chat/{user_id}", response_class=HTMLResponse, name="chat")
async def mobile_chat(request: Request, user_id: int, db: Session = Depends(deps.get_db)):
    # Получаем property_id из query-параметров
    property_id = request.query_params.get("property_id")
    context = {"request": request, "user_id": user_id}
    
    if property_id:
        try:
            property_id = int(property_id)  # Преобразуем в число
            # Получаем информацию о объявлении, если указан property_id
            property_item = db.query(models.Property).filter(models.Property.id == property_id).first()
            if property_item:
                context["property"] = {
                    "id": property_item.id,
                    "title": property_item.title,
                    "price": property_item.price
                }
        except ValueError:
            # Обработка случая, когда property_id не является числом
            pass
    
    return templates.TemplateResponse("mobile/chat.html", context)

# Тестовая страница для WebSocket
@app.get("/mobile/test-websocket", response_class=HTMLResponse)
async def test_websocket_page(request: Request):
    """Тестовая страница для проверки WebSocket соединений"""
    return templates.TemplateResponse("test_websocket.html", {"request": request})

# Создаем прямой API-роутер для отладки, который не использует аутентификацию
debug_router = APIRouter(prefix="/debug")

# Добавляем debug_router в приложение
app.include_router(debug_router)

# Добавляем маршруты отладки
@debug_router.get("/")
async def get_debug_info():
    return {
        "status": "ok",
        "message": "Отладочный API доступен"
    }

# API для чата
from pydantic import BaseModel

from app.models.chat import AppChatMessageModel
from typing import List, Optional, Dict, Any

class MessageReadRequest(BaseModel):
    message_id: int

@app.post("/api/v1/chat/messages/read")
async def mark_message_as_read(request: MessageReadRequest, db: Session = Depends(deps.get_db)):
    """ Маркировать сообщение как прочитанное """
    try:
        # В реальном приложении здесь был бы код для обновления сообщения в базе данных
        # Например: message = db.query(AppChatMessageModel).filter(AppChatMessageModel.id == request.message_id).first()
        # if message:
        #    message.is_read = True
        #    db.commit()
        print(f"DEBUG: Сообщение {request.message_id} отмечено как прочитанное")
        return {"status": "success", "message": f"Сообщение {request.message_id} отмечено как прочитанное"}
    except Exception as e:
        print(f"ERROR: Ошибка при маркировке сообщения как прочитанное: {e}")
        return {"status": "error", "message": f"Ошибка при маркировке сообщения: {str(e)}"}

# API для получения пользователя по ID
@app.get("/api/v1/users/{user_id}")
async def get_user(user_id: int, db: Session = Depends(deps.get_db)):
    """Получить информацию о пользователе по ID"""
    try:
        print(f"DEBUG: Запрос данных пользователя с ID {user_id}")
        
        # Получаем пользователя из базы данных
        user = db.query(models.User).filter(models.User.id == user_id).first()
        
        # Если пользователь найден, формируем ответ с его данными
        if user:
            print(f"DEBUG: Пользователь найден в БД: {user.email}, {user.full_name}")
            return {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "avatar": user.avatar if user.avatar else f"/static/img/avatar{user_id}.png",
                "status": "Онлайн" if user.is_active else "Не в сети",
                "is_active": user.is_active
            }
        else:
            print(f"DEBUG: Пользователь с ID {user_id} не найден в БД")
            # Если пользователь не найден, возвращаем стандартные данные
            return {
                "id": user_id,
                "email": f"user{user_id}@example.com",
                "full_name": f"User {user_id}",
                "avatar": f"/static/img/avatar{user_id}.png",
                "status": "Пользователь",
                "is_active": False
            }
    except Exception as e:
        print(f"ERROR: Ошибка при получении пользователя: {e}")
        # В случае ошибки возвращаем базовые данные
        return {
            "id": user_id,
            "email": f"user{user_id}@example.com",
            "full_name": f"User {user_id}",
            "avatar": f"/static/img/avatar{user_id}.png",
            "status": "Пользователь",
            "is_active": True
        }

# API для получения сообщений чата
@app.get("/api/v1/chat/messages/{user_id}")
async def get_chat_messages(user_id: int, current_user: dict = Depends(deps.get_current_user_optional), db: Session = Depends(deps.get_db)):
    """Получить сообщения чата с пользователем"""
    try:
        # Получаем ID текущего пользователя из токена
        current_user_id = int(current_user.get("sub", 0)) if current_user else 0
        if current_user_id == 0:
            print("DEBUG: Не удалось определить текущего пользователя")
            return []
        
        # Используем импортированный chat_manager для доступа к сообщениям
        from app.websockets.chat_manager import manager as chat_manager
        
        # Формируем уникальный ID чата на основе идентификаторов пользователей
        chat_id = chat_manager.get_chat_id(current_user_id, user_id)
        print(f"DEBUG: Сформированный chat_id: {chat_id} для пользователей {current_user_id} и {user_id}")
        
        # Получаем сообщения из памяти chat_manager
        messages = chat_manager.chat_messages.get(chat_id, [])
        
        # Если сообщений нет в памяти, пробуем загрузить их из файла
        if not messages and os.path.exists("chat_messages.json"):
            try:
                with open("chat_messages.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # Сначала пробуем найти сообщения по новому chat_id
                    messages = data.get(chat_id, [])
                    
                    if not messages:
                        # Если сообщений нет, пробуем найти сообщения по старому chat_id="4"
                        # Это нужно для обратной совместимости со старыми сообщениями
                        old_messages = data.get("4", [])
                        
                        # Фильтруем сообщения, относящиеся к этим пользователям
                        filtered_messages = []
                        for msg in old_messages:
                            if (str(msg.get("sender_id")) == str(current_user_id) and str(msg.get("receiver_id")) == str(user_id)) or \
                               (str(msg.get("sender_id")) == str(user_id) and str(msg.get("receiver_id")) == str(current_user_id)):
                                # Обновляем chat_id для совместимости с новой системой
                                msg["chat_id"] = chat_id
                                filtered_messages.append(msg)
                        
                        # Используем отфильтрованные сообщения
                        messages = filtered_messages
                        
                        # Сохраняем обновленные сообщения в памяти chat_manager
                        if messages:
                            for msg in messages:
                                chat_manager.add_message_to_memory(chat_id, msg)
                    
                    print(f"DEBUG: Загружено {len(messages)} сообщений для чата {chat_id}")
                    # В случае, если мы мигрировали сообщения, сохраняем их в файл
                    chat_manager.save_messages_to_file()
            except Exception as e:
                print(f"DEBUG: Ошибка при загрузке сообщений из файла: {e}")
        
        print(f"DEBUG: Возвращаем {len(messages)} сообщений для чата с пользователем {user_id}")
        return messages
    except Exception as e:
        print(f"ERROR: Ошибка при получении сообщений чата: {e}")
        # Возвращаем пустой список, чтобы приложение продолжало работать
        return []

@app.get("/admin/login")
async def admin_login_get(request: Request):
    return templates.TemplateResponse("admin/index.html", {"request": request})

@app.post("/admin/login")
async def admin_login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    # Проверяем учетные данные администратора
    admin = db.query(models.User).filter(
        models.User.email == username,
        models.User.role == models.UserRole.ADMIN
    ).first()
    
    if not admin or not verify_password(password, admin.hashed_password):
        return templates.TemplateResponse(
            "admin/index.html",
            {"request": request, "error": "Неверный email или пароль"}
        )
    
    # Создаем токен для администратора
    access_token = create_access_token(
        data={"sub": str(admin.id), "is_admin": True}
    )
    
    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=False,  # Позволяем JavaScript получить доступ к токену
        max_age=3600 * 24,  # Увеличиваем время жизни до 24 часов
        samesite="lax",
        path="/"  # Устанавливаем для всех путей
    )
    
    # Для отладки добавляем токен в URL первый раз
    return response

@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем токен администратора
    auth_token = request.cookies.get('access_token')
    if not auth_token:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if not payload.get("is_admin"):
            return RedirectResponse(url="/admin/login", status_code=303)
    except:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Получаем реальную статистику из БД
    total_users = db.query(models.User).count()
    
    # Общее количество объектов недвижимости
    total_properties = db.query(models.Property).count()
    
    # Количество объектов на модерации (заявки)
    pending_properties = db.query(models.Property).filter(models.Property.status == "pending").count()
    
    # Количество чатов
    total_chats = db.query(AppChatModel).count()
    
    # Для тикетов (обращений в техподдержку) используем примерное значение
    # В реальном приложении эти данные были бы получены из БД
    total_tickets = 13
    
    # Получаем последние 5 объектов недвижимости
    latest_properties_query = db.query(models.Property).options(
        joinedload(models.Property.owner),
        joinedload(models.Property.images)
    ).order_by(models.Property.created_at.desc()).limit(5).all()
    
    # Подготавливаем форматированные данные для отображения
    latest_properties = []
    
    status_display = {
        "draft": "Черновик",
        "pending": "На модерации",
        "active": "Активно",
        "rejected": "Отклонено",
        "sold": "Продано"
    }
    
    for prop in latest_properties_query:
        # Форматируем цену
        price = prop.price or 0
        
        # Определяем статус для отображения
        status_value = prop.status.value if prop.status else "draft"
        status = status_display.get(status_value, "Неизвестно")
        
        # Определяем тип объекта
        property_type = "sale"
        if hasattr(prop, 'property_type') and prop.property_type:
            property_type = prop.property_type.value
        
        property_type_display = {
            "sale": "Продажа",
            "rent": "Аренда"
        }.get(property_type, property_type)
        
        # Добавляем данные в массив
        latest_properties.append({
            "id": prop.id,
            "title": prop.title or f"Объект #{prop.id}",
            "price": price,
            "status": status_value,
            "status_display": status,
            "property_type": property_type,
            "property_type_display": property_type_display,
            "created_at": prop.created_at
        })
    
    # Рассчитываем динамические проценты изменений на основе имеющихся данных
    # В реальном приложении это можно было бы рассчитать сравнивая с предыдущим месяцем
    # Для примера используем ID как показатель роста
    
    # Делаем рост пользователей на основе ID последнего пользователя
    last_user_id = db.query(models.User.id).order_by(models.User.id.desc()).first()
    last_user_id = last_user_id[0] if last_user_id else 0
    users_change = round((last_user_id - total_users) / max(total_users, 1) * 100) if total_users > 0 else 0
    users_change = min(max(users_change, -99), 99)  # Ограничиваем диапазоном -99 до 99
    
    # Делаем рост объектов на основе ID последнего объекта
    last_property_id = db.query(models.Property.id).order_by(models.Property.id.desc()).first()
    last_property_id = last_property_id[0] if last_property_id else 0
    properties_change = round((last_property_id - total_properties) / max(total_properties, 1) * 100) if total_properties > 0 else 0
    properties_change = min(max(properties_change, -99), 99)  # Ограничиваем диапазоном -99 до 99
    
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "total_users": total_users,
            "users_count": total_users,
            "users_change": users_change,
            "total_properties": total_properties,
            "properties_count": total_properties,
            "properties_change": properties_change,
            "total_chats": total_chats,
            "chats_change": total_chats,  # Используем количество чатов как динамический процент
            "requests_count": pending_properties,  # Заявки = объекты на модерации
            "requests_change": pending_properties,  # Используем количество заявок как динамический процент
            "tickets_count": total_tickets,  # Количество тикетов в техподдержку
            "tickets_change": -5,  # Примерное значение изменения
            "last_properties": latest_properties,
            "last_tickets": [],  # В данной версии не реализовано
        }
    )

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request, db: Session = Depends(deps.get_db)):
    auth_token = request.cookies.get('access_token')
    if not auth_token:
        return RedirectResponse(url="/admin/login", status_code=303)
    try:
        payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if not payload.get("is_admin"):
            return RedirectResponse(url="/admin/login", status_code=303)
    except:
        return RedirectResponse(url="/admin/login", status_code=303)
        
    # Получаем всех пользователей
    users = db.query(models.User).all()
    
    # Подготавливаем данные для отображения
    enhanced_users = []
    
    for user in users:
        # Получаем количество объявлений пользователя
        properties_count = db.query(models.Property).filter(models.Property.owner_id == user.id).count()
        
        # Получаем количество объявлений с 360-турами
        # В данном случае будем считать, что объявление имеет 360-тур, если у него есть непустое поле tour_360_url
        tours_count = db.query(models.Property).filter(
            models.Property.owner_id == user.id,
            models.Property.tour_360_url.isnot(None),
            models.Property.tour_360_url != ""
        ).count()
        
        # Форматируем дату регистрации
        registered_at = "Нет данных"
        if hasattr(user, 'created_at') and user.created_at:
            registered_at = user.created_at.strftime("%Y-%m-%d %H:%M:%S")
        
        # Добавляем данные в массив
        enhanced_users.append({
            "id": user.id,
            "full_name": user.full_name if hasattr(user, 'full_name') and user.full_name else f"Пользователь {user.id}",
            "phone": user.phone if hasattr(user, 'phone') and user.phone else "Нет данных",
            "email": user.email if hasattr(user, 'email') and user.email else "Нет данных",
            "is_active": user.is_active if hasattr(user, 'is_active') else True,
            "properties_count": properties_count,
            "tours_count": tours_count,
            "registered_at": registered_at,
            "avatar_url": user.avatar_url if hasattr(user, 'avatar_url') and user.avatar_url else None,
        })
    
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "users": enhanced_users,
            "start_item": 1,
            "end_item": len(enhanced_users),
            "total_users": len(enhanced_users),
            "search_query": "",
            "status": None,
            "current_page": 1,
            "total_pages": 1,
            "pages": [1],
            "show_ellipsis": False,
        }
    )

@app.get("/admin/properties", response_class=HTMLResponse)
async def admin_properties(
    request: Request, 
    status: str = Query(None), 
    property_type: str = Query(None),
    search: str = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(deps.get_db)
):
    auth_token = request.cookies.get('access_token')
    if not auth_token:
        return RedirectResponse(url="/admin/login", status_code=303)
    try:
        payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if not payload.get("is_admin"):
            return RedirectResponse(url="/admin/login", status_code=303)
    except:
        return RedirectResponse(url="/admin/login", status_code=303)
        
    # Получаем категории для фильтра
    categories = db.query(models.Category).all()
    
    # Создаем базовый запрос к объектам недвижимости
    properties_query = db.query(models.Property).options(
        joinedload(models.Property.owner),
        joinedload(models.Property.images)
    )
    
    # Применяем фильтры
    if status:
        properties_query = properties_query.filter(models.Property.status == status)
    
    if property_type:
        try:
            property_type_id = int(property_type)
            # Фильтруем по категории (связь с таблицей categories через PropertyCategory)
            properties_query = properties_query.join(models.PropertyCategory).filter(
                models.PropertyCategory.category_id == property_type_id
            )
        except (ValueError, TypeError):
            # Если не удалось преобразовать в число, игнорируем фильтр
            pass
            
    if search:
        search_term = f"%{search}%"
        properties_query = properties_query.filter(
            or_(
                models.Property.title.ilike(search_term),
                models.Property.description.ilike(search_term),
                models.Property.address.ilike(search_term)
            )
        )
    
    # Получаем общее количество записей после применения фильтров
    total_items = properties_query.count()
    
    # Настройка пагинации
    items_per_page = 10
    total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
    
    # Проверка корректности номера страницы
    if page > total_pages and total_pages > 0:
        page = total_pages
        
    # Получаем данные с пагинацией
    start_idx = (page - 1) * items_per_page
    properties_query = properties_query.order_by(desc(models.Property.created_at)).offset(start_idx).limit(items_per_page)
    
    # Получаем результаты запроса
    properties_results = properties_query.all()
    
    # Подготавливаем данные для отображения в шаблоне
    enhanced_properties = []
    
    for prop in properties_results:
        # Находим главное изображение или используем заглушку
        image_url = "/static/layout/assets/img/property-placeholder.jpg"
        if prop.images:
            main_images = [img for img in prop.images if img.is_main]
            if main_images:
                image_url = main_images[0].url
            else:
                image_url = prop.images[0].url if prop.images else image_url
        
        # Форматируем цену
        price_formatted = f"{prop.price:,.0f} KGZ" if prop.price else "Цена не указана"
        
        # Определяем понятный статус для отображения
        status_map = {
            "draft": "Черновик",
            "pending": "На проверке",
            "active": "Активно",
            "rejected": "Отклонено",
            "sold": "Продано"
        }
        
        status_val = prop.status.value if prop.status else "draft"
        status_display = status_map.get(status_val, "Неизвестно")
        
        # Проверяем наличие 360° тура
        has_tour = bool(prop.tour_360_url) if hasattr(prop, 'tour_360_url') and prop.tour_360_url else False
        
        # Количество просмотров для объектов на модерации - 0
        views = 0 if status_val == "pending" else prop.views if hasattr(prop, 'views') and prop.views else 0
        
        # Добавляем данные в массив
        enhanced_properties.append({
            "id": prop.id,
            "title": prop.title or f"Объект #{prop.id}",
            "description": prop.description,
            "price": prop.price,
            "price_formatted": price_formatted,
            "address": prop.address or "Адрес не указан",
            "city": prop.city,
            "area": prop.area,
            "status": status_val,
            "status_display": status_display,
            "owner_id": prop.owner_id,
            "owner_name": prop.owner.full_name if prop.owner else "Нет данных",
            "image_url": image_url,
            "created_at": prop.created_at.strftime("%Y-%m-%d %H:%M:%S") if prop.created_at else "Нет данных",
            "views": views,
            "has_tour": has_tour,
            "rooms": prop.rooms,
            "floor": prop.floor,
            "building_floors": prop.building_floors,
            "has_balcony": prop.has_balcony,
            "has_furniture": prop.has_furniture,
            "has_renovation": prop.has_renovation,
            "has_parking": prop.has_parking
        })
    
    # Вычисляем начальный и конечный индексы для пагинации
    start_item = start_idx + 1 if total_items > 0 else 0
    end_item = min(start_idx + len(enhanced_properties), total_items)
    
    # Формируем параметры запроса для пагинации
    query_params = ""
    if status:
        query_params += f"&status={status}"
    if property_type:
        query_params += f"&property_type={property_type}"
    if search:
        query_params += f"&search={search}"
    
    # Генерируем список страниц для навигации
    page_range = range(max(1, page - 2), min(total_pages + 1, page + 3))
    
    return templates.TemplateResponse(
        "admin/properties.html",
        {
            "request": request,
            "properties": enhanced_properties,
            "total_pages": total_pages,
            "current_page": page,
            "pages": page_range,
            "show_ellipsis": total_pages > 5,
            "start_item": start_item,
            "end_item": end_item,
            "total_properties": total_items,
            "search_query": search or "",
            "status": status,
            "property_type": property_type,
            "categories": categories,  # Передаем категории для выпадающего списка
        }
    )

# Функция для проверки доступа администратора
async def check_admin_access(request: Request, db: Session):
    auth_token = request.cookies.get('access_token')
    if not auth_token:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if datetime.fromtimestamp(payload["exp"]) < datetime.utcnow():
            return RedirectResponse(url="/admin/login", status_code=303)
            
        # Проверяем, что пользователь является администратором
        if not payload.get("is_admin"):
            return RedirectResponse(url="/admin/login", status_code=303)
            
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return RedirectResponse(url="/admin/login", status_code=303)
            
        return user
    except Exception as e:
        print(f"DEBUG: Token validation error: {str(e)}")
        return RedirectResponse(url="/admin/login", status_code=303)

@app.get("/admin/requests", response_class=HTMLResponse, name="admin_requests")
async def admin_requests(request: Request, tab: str = Query('listings'), status: str = Query(None), 
                    property_type: str = Query(None), search: str = Query(None), 
                    page: int = Query(1, ge=1), db: Session = Depends(deps.get_db)):
    # Проверяем авторизацию и доступ администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
        
    # Получаем количество объявлений по типам
    try:
        # Для таба tours будем считать объявления с запросом на съемку 360
        tour_requests_count = db.query(models.Property).filter(
            models.Property.tour_360_url.like('%example.com%')
        ).count()
        
        # Для таба listings будем считать только объявления со статусом PENDING
        listing_requests_count = db.query(models.Property).filter(
            models.Property.status == 'PENDING'
        ).count()
    except Exception as e:
        print(f"Error counting properties: {e}")
        tour_requests_count = 0
        listing_requests_count = 0
        
    # Получаем список объявлений из БД
    try:
        # Создаем базовый запрос к таблице properties
        query = db.query(models.Property)\
            .join(models.User, models.Property.owner_id == models.User.id, isouter=True)\
            .options(
                joinedload(models.Property.owner)
            )
            
        # Фильтрация по типу объявления
        if tab == 'tours':
            # Для таба tours берем только принятые объявления с запросом на съемку 360
            # Фильтруем по статусу ACTIVE и наличию URL с 'example.com'
            query = query.filter(
                models.Property.tour_360_url.like('%example.com%'),
                models.Property.status.in_(['ACTIVE', 'PROCESSING'])
            )
        elif tab == 'listings':
            # Для таба listings берем все объявления со статусом PENDING (на модерации)
            query = query.filter(
                models.Property.status == 'PENDING'
            )
            
        # Фильтрация по статусу, если указан
        if status:
            if status == 'new':
                query = query.filter(models.Property.status.in_(['NEW', 'PENDING']))
            else:
                status_map = {
                    'in_progress': 'PROCESSING',
                    'completed': 'ACTIVE',
                    'rejected': 'REJECTED'
                }
                if status in status_map:
                    query = query.filter(models.Property.status == status_map[status])
        
        # Фильтрация по типу недвижимости, если указан
        if property_type:
            # Преобразуем property_type в int, если это возможно
            try:
                property_type_id = int(property_type)
                # Фильтруем по категории (связь с таблицей categories)
                query = query.join(models.PropertyCategory).filter(
                    models.PropertyCategory.category_id == property_type_id
                )
            except (ValueError, TypeError):
                # Если property_type не является числом, фильтруем по типу как обычно
                query = query.filter(models.Property.type == property_type)
        
        # Поиск
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    models.Property.title.ilike(search_term),
                    models.Property.description.ilike(search_term),
                    models.Property.address.ilike(search_term),
                    models.User.full_name.ilike(search_term)
                )
            )
            
        # Подсчитываем общее количество записей
        total_items = query.count()
        
        # Пагинация
        items_per_page = 10
        total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
        
        # Проверяем корректность номера страницы
        if page > total_pages and total_pages > 0:
            page = total_pages
            
        # Получаем данные с пагинацией
        start_idx = (page - 1) * items_per_page
        query = query.order_by(desc(models.Property.created_at)).offset(start_idx).limit(items_per_page)
        
        # Получаем объекты недвижимости
        properties = query.all()
        
        # Преобразуем в формат для шаблона
        requests_data = []
        
        # Маппинг статусов из БД в формат для шаблона
        status_map_reverse = {
            'NEW': 'new',
            'PENDING': 'new',
            'PROCESSING': 'in_progress',
            'ACTIVE': 'completed',     # Активные объявления считаем завершенными
            'REJECTED': 'rejected',
            'INACTIVE': 'rejected'
        }
        
        for prop in properties:
            # Форматируем цену корректно
            if prop.price:
                if prop.price >= 1000000:
                    # Если цена больше миллиона, форматируем в миллионах
                    millions = prop.price / 1000000
                    price_formatted = f"{millions:.1f} млн KGZ".replace('.0', '')
                else:
                    # Иначе форматируем в тысячах
                    thousands = prop.price / 1000
                    price_formatted = f"{thousands:.1f} тыс KGZ".replace('.0', '')
            else:
                price_formatted = "Цена не указана"
            
            # Определяем статус для отображения
            display_status = status_map_reverse.get(prop.status, 'new') if prop.status else 'new'
            
            # Берем дату съемки напрямую из поля notes
            scheduled_date = prop.notes
            
            # Очищаем описание от повторяющихся дат съемки
            if prop.description and "Дата съемки 360:" in prop.description:
                try:
                    # Берем только первую часть описания до первого упоминания даты
                    clean_description = prop.description.split("\n\nДата съемки 360:")[0]
                    # Обновляем описание, чтобы убрать все повторяющиеся даты
                    prop.description = clean_description
                    db.commit()
                    print(f"DEBUG: Очищено описание для объявления ID={prop.id}")
                except Exception as e:
                    print(f"DEBUG: Ошибка при очистке описания: {e}")
                    pass
            
            # Получаем информацию о владельце
            owner_data = {
                'id': prop.owner.id if prop.owner else None,
                'name': prop.owner.full_name if prop.owner and prop.owner.full_name else "Пользователь",
                'email': prop.owner.email if prop.owner and prop.owner.email else ""
            }
            
            # Добавляем объект в список
            requests_data.append({
                'id': prop.id,
                'status': display_status,
                'created_at': prop.created_at.strftime("%d.%m.%Y %H:%M") if prop.created_at else "",
                'scheduled_date': prop.notes,  # Берем дату съемки из поля notes
                'property': {
                    'id': prop.id,
                    'title': prop.title or f"Объект №{prop.id}",
                    'address': prop.address or "Адрес не указан",
                    'price': prop.price or 0,
                    'price_formatted': price_formatted,
                    'type': prop.type or "apartment",
                    'image_url': prop.tour_360_url if tab == 'tours' and prop.tour_360_url else f"/static/img/property/property-{prop.id % 5 + 1}.jpg"
                },
                'user': owner_data
            })
            
        # Вычисляем начальный и конечный индексы для пагинации
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + len(requests_data), total_items)
    except Exception as e:
        print(f"Error getting requests: {e}")
        requests_data = []
    
    # Пагинация
    items_per_page = 10
    total_items = len(requests_data)
    total_pages = (total_items + items_per_page - 1) // items_per_page
    
    # Проверяем корректность номера страницы
    if page > total_pages and total_pages > 0:
        page = total_pages
    
    # Получаем элементы для текущей страницы
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    page_items = requests_data[start_idx:end_idx] if total_items > 0 else []
    
    # Вычисляем метрики для отображения
    try:
        # Подготовим базовый запрос для метрик
        metrics_query = db.query(models.Property)
        
        # Фильтрация по типу объявления
        if tab == 'tours':
            metrics_query = metrics_query.filter(
                models.Property.tour_360_url.isnot(None),
                models.Property.tour_360_url != ''
            )
        elif tab == 'listings':
            metrics_query = metrics_query.filter(
                or_(models.Property.tour_360_url.is_(None),
                   models.Property.tour_360_url == '')
            )
        
        # Количество принятых/активных объявлений
        accepted_count = metrics_query.filter(models.Property.status == 'ACTIVE').count()
        
        # Количество отклоненных объявлений
        rejected_count = metrics_query.filter(models.Property.status.in_(['REJECTED', 'INACTIVE'])).count()
        
        # Количество ожидающих объявлений
        pending_count = metrics_query.filter(
            models.Property.status.in_(['NEW', 'PENDING', 'PROCESSING'])
        ).count()
        
        # Расчет среднего времени обработки
        # Вычисляем разницу между датой создания и обновления для активных объявлений
        active_properties = db.query(models.Property).filter(
            models.Property.status == 'ACTIVE'
        ).all()
        
        total_processing_days = 0
        properties_with_times = 0
        
        for prop in active_properties:
            if prop.created_at and prop.updated_at and prop.updated_at > prop.created_at:
                days_diff = (prop.updated_at - prop.created_at).days
                if days_diff >= 0:
                    total_processing_days += days_diff
                    properties_with_times += 1
        
        # Вычисляем среднее время обработки
        avg_processing_days = total_processing_days / properties_with_times if properties_with_times > 0 else 0
        avg_time_formatted = f"{avg_processing_days:.1f} дня" if avg_processing_days != 1 else "1 день"
        
        # Формируем метрики
        metrics = {
            'accepted': accepted_count,
            'rejected': rejected_count,
            'pending': pending_count,
            'avg_time': avg_time_formatted
        }
    except Exception as e:
        print(f"Error calculating metrics: {e}")
        # Если произошла ошибка, показываем нулевые значения
        metrics = {
            'accepted': 0,
            'rejected': 0,
            'pending': 0,
            'avg_time': "0 дней"
        }

    # Формируем строку параметров запроса для пагинации
    query_params = ""
    if status:
        query_params += f"&status={status}"
    if property_type:
        query_params += f"&property_type={property_type}"
    if search:
        query_params += f"&search={search}"
        
    # Генерируем список страниц для навигации
    page_range = range(max(1, page - 2), min(total_pages + 1, page + 3))
    
    # Получаем все категории для фильтра
    categories = db.query(models.Category).all()
    
    # Логируем выбранные фильтры
    print(f"[DEBUG] admin_requests: status={status}, property_type={property_type}, tab={tab}")
    # Логируем все связи property_category
    property_category_rows = db.query(PropertyCategory).all()
    print(f"[DEBUG] property_category rows: {[{'property_id': r.property_id, 'category_id': r.category_id} for r in property_category_rows]}")
    # Логируем количество объявлений до фильтрации
    all_props_count = db.query(models.Property).count()
    print(f"[DEBUG] Всего объявлений в базе: {all_props_count}")
    
    return templates.TemplateResponse("admin/requests.html", {
        "request": request,
        "user": user,
        "tab": tab,
        "status": status,
        "property_type": property_type,
        "search": search,
        "requests": page_items,
        "tour_requests_count": tour_requests_count,
        "listing_requests_count": listing_requests_count,
        "metrics": metrics,
        "page": page,
        "total_pages": total_pages,
        "total_requests": total_items,
        "items_per_page": items_per_page,
        "start_item": start_idx + 1 if total_items > 0 else 0,
        "end_item": end_idx,
        "pages": page_range,
        "query_params": query_params,
        "categories": categories,
    })

@app.get("/admin/settings", response_class=HTMLResponse, name="admin_settings")
async def admin_settings(request: Request, db: Session = Depends(deps.get_db)):
    auth_token = request.cookies.get('access_token')
    if not auth_token:
        return RedirectResponse(url="/admin/login", status_code=303)
    try:
        payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if not payload.get("is_admin"):
            return RedirectResponse(url="/admin/login", status_code=303)
    except:
        return RedirectResponse(url="/admin/login", status_code=303)
    class DummySettings:
        email_new_properties = False
        email_new_users = False
        push_notifications = False
        digest_frequency = 'never'
        color_scheme = 'orange'
        theme = 'light'
        compact_mode = False
        animations_enabled = True
    dummy_settings = DummySettings()
    return templates.TemplateResponse(
        "admin/settings.html",
        {"request": request, "settings": dummy_settings}
    )

# API для управления объявлениями и заявками
class PropertyActionRequest(BaseModel):
    # Убираем property_id, так как он уже передается в URL
    scheduled_date: Optional[str] = None

# Одобрение объявления
@app.post("/api/v1/properties/{property_id}/approve")
async def approve_property(property_id: int, request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем авторизацию администратора
    # Получаем токен из куки или заголовка
    auth_token = request.cookies.get('access_token') or request.headers.get('Authorization', '').replace('Bearer ', '')
    if not auth_token:
        return JSONResponse(status_code=401, content={"detail": "Требуется авторизация администратора"})
    
    try:
        payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # Проверяем, что пользователь является администратором
        if not payload.get("is_admin"):
            return JSONResponse(status_code=403, content={"detail": "Требуются права администратора"})
            
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return JSONResponse(status_code=401, content={"detail": "Пользователь не найден"})
    except Exception as e:
        return JSONResponse(status_code=401, content={"detail": f"Ошибка аутентификации: {str(e)}"})
        
    
    try:
        # Получаем объявление по ID
        property = db.query(models.Property).filter(models.Property.id == property_id).first()
        
        if not property:
            return JSONResponse(status_code=404, content={"detail": "Объявление не найдено"})
        
        # Меняем статус на ACTIVE
        property.status = "ACTIVE"
        property.updated_at = datetime.now()
        
        # Сохраняем изменения
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "detail": "Объявление успешно одобрено"
        })
    except Exception as e:
        db.rollback()
        print(f"Error approving property: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Ошибка при одобрении объявления: {str(e)}"})

# Отклонение объявления
@app.post("/api/v1/properties/{property_id}/reject")
async def reject_property(property_id: int, request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем авторизацию администратора
    # Получаем токен из куки или заголовка
    auth_token = request.cookies.get('access_token') or request.headers.get('Authorization', '').replace('Bearer ', '')
    if not auth_token:
        return JSONResponse(status_code=401, content={"detail": "Требуется авторизация администратора"})
    
    try:
        payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # Проверяем, что пользователь является администратором
        if not payload.get("is_admin"):
            return JSONResponse(status_code=403, content={"detail": "Требуются права администратора"})
            
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return JSONResponse(status_code=401, content={"detail": "Пользователь не найден"})
    except Exception as e:
        return JSONResponse(status_code=401, content={"detail": f"Ошибка аутентификации: {str(e)}"})
        
    
    try:
        # Получаем объявление по ID
        property = db.query(models.Property).filter(models.Property.id == property_id).first()
        
        if not property:
            return JSONResponse(status_code=404, content={"detail": "Объявление не найдено"})
        
        # Меняем статус на REJECTED
        property.status = "REJECTED"
        property.updated_at = datetime.now()
        
        # Сохраняем изменения
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "detail": "Объявление отклонено"
        })
    except Exception as e:
        db.rollback()
        print(f"Error rejecting property: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Ошибка при отклонении объявления: {str(e)}"})

# Назначение даты съемки 360
@app.post("/api/v1/properties/{property_id}/schedule")
async def schedule_tour(property_id: int, request_data: PropertyActionRequest, request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем авторизацию администратора
    # Получаем токен из куки или заголовка
    auth_token = request.cookies.get('access_token') or request.headers.get('Authorization', '').replace('Bearer ', '')
    if not auth_token:
        return JSONResponse(status_code=401, content={"detail": "Требуется авторизация администратора"})
    
    try:
        payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # Проверяем, что пользователь является администратором
        if not payload.get("is_admin"):
            return JSONResponse(status_code=403, content={"detail": "Требуются права администратора"})
            
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return JSONResponse(status_code=401, content={"detail": "Пользователь не найден"})
    except Exception as e:
        return JSONResponse(status_code=401, content={"detail": f"Ошибка аутентификации: {str(e)}"})
        
    
    if not request_data.scheduled_date:
        return JSONResponse(status_code=400, content={"detail": "Необходимо указать дату съемки"})
    
    try:
        # Получаем объявление по ID
        property = db.query(models.Property).filter(models.Property.id == property_id).first()
        
        if not property:
            return JSONResponse(status_code=404, content={"detail": "Объявление не найдено"})
        
        # Проверку на съемку 360 сделаем опциональной, чтобы можно было назначить дату для любого объявления
        # Если нет URL, создаем дефолтный
        if not property.tour_360_url:
            property.tour_360_url = 'https://example.com/tour/pending'
        
        # Не меняем статус, просто обновляем дату
        property.updated_at = datetime.now()
        
        # Сохраняем дату съемки в дополнительное поле
        # Создаем отдельное поле для даты съемки
        property.notes = request_data.scheduled_date
        print(f"DEBUG: Установлена дата съемки: {request_data.scheduled_date} для объявления ID={property_id}")
        
        # Сохраняем изменения
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "detail": "Дата съемки 360 успешно назначена"
        })
    except Exception as e:
        db.rollback()
        print(f"Error scheduling tour: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Ошибка при назначении даты съемки: {str(e)}"})

# Завершение съемки 360 - меняем URL на реальный и активируем объявление
@app.post("/api/v1/properties/{property_id}/complete-tour")
async def complete_tour(property_id: int, request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем авторизацию администратора
    # Получаем токен из куки или заголовка
    auth_token = request.cookies.get('access_token') or request.headers.get('Authorization', '').replace('Bearer ', '')
    if not auth_token:
        return JSONResponse(status_code=401, content={"detail": "Требуется авторизация администратора"})
    
    try:
        payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # Проверяем, что пользователь является администратором
        if not payload.get("is_admin"):
            return JSONResponse(status_code=403, content={"detail": "Требуются права администратора"})
            
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return JSONResponse(status_code=401, content={"detail": "Пользователь не найден"})
    except Exception as e:
        return JSONResponse(status_code=401, content={"detail": f"Ошибка аутентификации: {str(e)}"})
        
    
    try:
        # Получаем объявление по ID
        property = db.query(models.Property).filter(models.Property.id == property_id).first()
        
        if not property:
            return JSONResponse(status_code=404, content={"detail": "Объявление не найдено"})
        
        # Проверяем, что это запрос на съемку 360 и он в процессе
        if not property.tour_360_url or 'example.com' not in property.tour_360_url or property.status != "PROCESSING":
            return JSONResponse(status_code=400, content={"detail": "Это не запрос на съемку 360 или он не в процессе"})
        
        # Меняем URL на реальный (в данном случае просто заменяем example.com на real-tour.com)
        property.tour_360_url = property.tour_360_url.replace('example.com', 'real-tour.com')
        
        # Меняем статус на ACTIVE
        property.status = "ACTIVE"
        property.updated_at = datetime.now()
        
        # Сохраняем изменения
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "detail": "Съемка 360 завершена, объявление активировано"
        })
    except Exception as e:
        db.rollback()
        print(f"Error completing tour: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Ошибка при завершении съемки: {str(e)}"})
    
# API для управления пользователями (блокировка, активация, удаление)
class UserActionRequest(BaseModel):
    user_id: str

@app.post("/admin/users/{user_id}/ban")
async def ban_user(user_id: int, request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем, что запрос от администратора
    check_result = await check_admin_access(request, db)
    if isinstance(check_result, RedirectResponse):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JSONResponse(content={"success": False, "error": "Требуется авторизация администратора"}, status_code=401)
        return check_result
    
    try:
        # Получаем пользователя по ID
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JSONResponse(content={"success": False, "error": "Пользователь не найден"}, status_code=404)
            return RedirectResponse(url="/admin/users", status_code=303)
        
        # Блокируем пользователя
        user.is_active = False
        db.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JSONResponse(content={
                "success": True, 
                "message": f"Пользователь {user.full_name} успешно заблокирован"
            })
        return RedirectResponse(url="/admin/users", status_code=303)
    except Exception as e:
        db.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JSONResponse(content={"success": False, "error": f"Ошибка при блокировке пользователя: {str(e)}"}, status_code=500)
        return RedirectResponse(url="/admin/users", status_code=303)

@app.post("/admin/users/{user_id}/activate")
async def activate_user(user_id: int, request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем, что запрос от администратора
    check_result = await check_admin_access(request, db)
    if isinstance(check_result, RedirectResponse):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JSONResponse(content={"success": False, "error": "Требуется авторизация администратора"}, status_code=401)
        return check_result
    
    try:
        # Получаем пользователя по ID
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JSONResponse(content={"success": False, "error": "Пользователь не найден"}, status_code=404)
            return RedirectResponse(url="/admin/users", status_code=303)
        
        # Активируем пользователя
        user.is_active = True
        db.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JSONResponse(content={
                "success": True, 
                "message": f"Пользователь {user.full_name} успешно активирован"
            })
        return RedirectResponse(url="/admin/users", status_code=303)
    except Exception as e:
        db.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JSONResponse(content={"success": False, "error": f"Ошибка при активации пользователя: {str(e)}"}, status_code=500)
        return RedirectResponse(url="/admin/users", status_code=303)

@app.post("/admin/users/{user_id}/delete")
async def delete_user(user_id: int, request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем, что запрос от администратора
    check_result = await check_admin_access(request, db)
    if isinstance(check_result, RedirectResponse):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JSONResponse(content={"success": False, "error": "Требуется авторизация администратора"}, status_code=401)
        return check_result
    
    try:
        from sqlalchemy import text
        
        # Проверяем, что пользователь существует
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JSONResponse(content={"success": False, "error": "Пользователь не найден"}, status_code=404)
            return RedirectResponse(url="/admin/users", status_code=303)
        
        # В SQLite надо включить режим игнорирования foreign keys
        # Это работает в SQLite, но может не работать в других БД
        try:
            db.execute(text("PRAGMA foreign_keys = OFF"))
        except Exception:
            # Просто игнорируем ошибку, если это не SQLite
            pass
        
        try:
            # Сначала удалим объявления, чтобы освободить внешние ключи
            # Сначала удаляем изображения объявлений
            property_ids = [p.id for p in db.query(models.Property).filter(models.Property.owner_id == user_id).all()]
            if property_ids:
                db.query(models.PropertyImage).filter(models.PropertyImage.property_id.in_(property_ids)).delete(synchronize_session=False)
            
            # Удаляем все объявления пользователя
            db.query(models.Property).filter(models.Property.owner_id == user_id).delete(synchronize_session=False)
            
            # Теперь прямое удаление пользователя, минуя ORM
            db.execute(text(f'DELETE FROM "user" WHERE id = {user_id}'))
            
            # Фиксируем изменения
            db.commit()
            
        finally:
            # Включаем обратно проверку внешних ключей
            try:
                db.execute(text("PRAGMA foreign_keys = ON"))
            except Exception:
                # Просто игнорируем ошибку, если это не SQLite
                pass
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JSONResponse(content={
                "success": True, 
                "message": f"Пользователь с ID {user_id} успешно удален"
            })
        return RedirectResponse(url="/admin/users", status_code=303)
    except Exception as e:
        db.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JSONResponse(content={"success": False, "error": f"Ошибка при удалении пользователя: {str(e)}"}, status_code=500)
        return RedirectResponse(url="/admin/users", status_code=303)

# API для экспорта пользователей
@app.get("/admin/users/export")
async def export_users(request: Request, search: str = None, db: Session = Depends(deps.get_db)):
    # Проверяем, что запрос от администратора
    check_result = await check_admin_access(request, db)
    if isinstance(check_result, RedirectResponse):
        return check_result
    
    try:
        # Импортируем xlsxwriter для создания Excel файла
        import io
        import xlsxwriter
        from datetime import datetime
        
        # Получаем всех пользователей
        users_query = db.query(models.User)
        
        # Применяем фильтр поиска
        if search:
            search_term = f"%{search}%"
            users_query = users_query.filter(or_(
                models.User.full_name.ilike(search_term),
                models.User.email.ilike(search_term),
                models.User.phone.ilike(search_term),
                cast(models.User.id, String).ilike(search_term)
            ))
        
        users = users_query.all()
        
        # Создаем ин-мемори буфер для Excel файла
        output = io.BytesIO()
        
        # Создаем новую книгу Excel
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet("Пользователи")
        
        # Создаем стили для форматирования
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#0f172a',
            'color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        cell_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        # Стиль для активных пользователей
        active_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#dcfce7',
            'color': '#166534'
        })
        
        # Стиль для заблокированных пользователей
        inactive_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#fee2e2',
            'color': '#b91c1c'
        })
        
        # Заголовки таблицы
        headers = [
            'ID', 'Имя', 'Телефон', 'Email', 'Статус', 
            'Кол-во объявлений', '360-туры', 'Дата регистрации'
        ]
        
        # Устанавливаем ширину столбцов
        column_widths = [5, 25, 20, 25, 15, 20, 10, 25]
        for i, width in enumerate(column_widths):
            worksheet.set_column(i, i, width)
        
        # Записываем заголовки
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Добавляем данные пользователей
        row = 1
        for user in users:
            # Получаем количество объявлений пользователя
            properties_count = db.query(models.Property).filter(models.Property.owner_id == user.id).count()
            
            # Получаем количество объявлений с 360-турами
            tours_count = db.query(models.Property).filter(
                models.Property.owner_id == user.id,
                models.Property.tour_360_url.isnot(None),
                models.Property.tour_360_url != ""
            ).count()
            
            # Форматируем дату регистрации
            registered_at = "Нет данных"
            if hasattr(user, 'created_at') and user.created_at:
                registered_at = user.created_at.strftime("%Y-%m-%d %H:%M:%S")
            
            # Статус пользователя
            is_active = hasattr(user, 'is_active') and user.is_active
            status = "Активен" if is_active else "Заблокирован"
            status_format = active_format if is_active else inactive_format
            
            # Заполняем строку данными
            data = [
                user.id,
                user.full_name if hasattr(user, 'full_name') and user.full_name else f"Пользователь {user.id}",
                user.phone if hasattr(user, 'phone') and user.phone else "Нет данных",
                user.email if hasattr(user, 'email') and user.email else "Нет данных",
                status,  # Статус с особым форматированием
                properties_count,
                tours_count,
                registered_at
            ]
            
            # Записываем данные в ячейки, статус с особым форматированием
            for col, value in enumerate(data):
                if col == 4:  # Столбец со статусом
                    worksheet.write(row, col, value, status_format)
                else:
                    worksheet.write(row, col, value, cell_format)
            
            row += 1
        
        # Финализируем книгу Excel
        workbook.close()
        
        # Сбрасываем указатель на начало файла
        output.seek(0)
        
        # Создаем имя файла с текущей датой и временем
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"wazir_users_{current_time}.xlsx"
        
        # Создаем ответ с файлом Excel
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }
        
        return Response(content=output.getvalue(), headers=headers)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JSONResponse(content={"error": str(e)}, status_code=500)

# API для настроек
class SettingsModel(BaseModel):
    email_new_properties: Optional[bool] = True
    email_new_users: Optional[bool] = True
    push_notifications: Optional[bool] = False
    digest_frequency: Optional[str] = "daily"
    color_scheme: Optional[str] = "orange"
    theme: Optional[str] = "light"
    compact_mode: Optional[bool] = False
    animations_enabled: Optional[bool] = True

@app.post("/api/v1/settings")
async def save_settings(settings: SettingsModel, request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем авторизацию, но для этого API допускаем любого авторизованного пользователя
    auth_token = request.cookies.get('access_token')
    auth_header = request.headers.get('Authorization')
    
    if auth_header and auth_header.startswith('Bearer '):
        auth_token = auth_header.split(' ')[1]
    
    if not auth_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Требуется авторизация"})
    
    try:
        # Проверяем валидность токена
        payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if datetime.fromtimestamp(payload["exp"]) < datetime.utcnow():
            return JSONResponse(status_code=401, content={"success": False, "error": "Токен истек"})
        
        # В реальном приложении здесь бы сохраняли настройки в БД
        # Для демонстрации просто возвращаем успех
        return {"success": True, "message": "Настройки сохранены успешно"}
    except Exception as e:
        print(f"DEBUG: Ошибка при сохранении настроек: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"Ошибка сервера: {str(e)}"})

# Сброс настроек
@app.post("/api/v1/settings/reset")
async def reset_settings(request: Request, db: Session = Depends(deps.get_db)):
    # Проверяем авторизацию
    auth_token = request.cookies.get('access_token')
    auth_header = request.headers.get('Authorization')
    
    if auth_header and auth_header.startswith('Bearer '):
        auth_token = auth_header.split(' ')[1]
    
    if not auth_token:
        return JSONResponse(status_code=401, content={"success": False, "error": "Требуется авторизация"})
    
    try:
        # Проверяем валидность токена
        payload = pyjwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if datetime.fromtimestamp(payload["exp"]) < datetime.utcnow():
            return JSONResponse(status_code=401, content={"success": False, "error": "Токен истек"})
        
        # В реальном приложении здесь бы сбрасывали настройки к значениям по умолчанию
        # Для демонстрации просто возвращаем успех
        return {"success": True, "message": "Настройки сброшены к значениям по умолчанию"}
    except Exception as e:
        print(f"DEBUG: Ошибка при сбросе настроек: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"Ошибка сервера: {str(e)}"})

if __name__ == "__main__":
    # Исправляем изображения при старте
    from fix_images import fix_missing_images
    fix_missing_images()
    
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
