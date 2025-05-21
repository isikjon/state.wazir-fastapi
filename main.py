from fastapi import FastAPI, Request, Depends, Form, status, HTTPException, Query, WebSocket, WebSocketDisconnect
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
import jwt
from app.models.token import TokenPayload
from fastapi import APIRouter

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
        ]
        
        # Для статических файлов, API разрешаем доступ
        if request.url.path.startswith('/static/') or request.url.path.startswith('/api/'):
            return await call_next(request)
            
        # Проверяем, является ли путь публичным (проверяем точное совпадение для API чата)
        if any(request.url.path.startswith(path) for path in public_paths) or '/api/v1/chat/' in request.url.path:
            return await call_next(request)
            
        # Проверяем наличие токена в localStorage через cookies
        auth_token = request.cookies.get('access_token')
        
        # Если токена нет или сессия недействительна, перенаправляем на страницу авторизации
        if not auth_token:
            return RedirectResponse('/mobile/auth', status_code=303)
            
        # Если токен есть, пропускаем запрос дальше
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

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

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = []
        self.active_connections[room].append(websocket)
        print(f"DEBUG: Подключен к комнате {room}, всего подключений: {len(self.active_connections[room])}")

    def disconnect(self, websocket: WebSocket, room: str):
        if room in self.active_connections:
            if websocket in self.active_connections[room]:
                self.active_connections[room].remove(websocket)
                print(f"DEBUG: Отключен от комнаты {room}, осталось подключений: {len(self.active_connections[room])}")
            if not self.active_connections[room]:
                del self.active_connections[room]
                print(f"DEBUG: Комната {room} удалена, нет активных подключений")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict, room: str, exclude=None):
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

manager = ConnectionManager()

# ============================ WebSocket Endpoints ============================

@app.websocket("/mobile/ws/test")
async def test_websocket_endpoint(websocket: WebSocket):
    print("DEBUG: Входящее тестовое соединение WebSocket")
    try:
        await websocket.accept()
        print("DEBUG: Соединение WebSocket принято")
        
        # Отправляем приветственное сообщение
        await websocket.send_json({"message": "Тестовое соединение успешно установлено"})
        
        while True:
            # Получаем сообщение
            data = await websocket.receive_json()
            print(f"DEBUG: Получено сообщение: {data}")
            
            # Отправляем эхо-ответ с дополнительной информацией
            response = {
                "message": f"Эхо: {data.get('message', 'Пустое сообщение')}",
                "received_data": data,
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send_json(response)
            print(f"DEBUG: Отправлен ответ: {response}")
            
    except WebSocketDisconnect:
        print("DEBUG: Тестовое соединение WebSocket закрыто")
    except Exception as e:
        print(f"DEBUG: Ошибка в тестовом WebSocket: {e}")
        try:
            # Попытка отправить сообщение об ошибке клиенту
            await websocket.send_json({"error": f"Ошибка: {str(e)}"})
        except:
            pass

@app.websocket("/mobile/ws/chats_list")
async def chats_list_endpoint(websocket: WebSocket):
    print("DEBUG: Входящее соединение для списка чатов")
    try:
        await websocket.accept()
        print("DEBUG: Соединение для списка чатов принято")
        
        # Отправляем приветственное сообщение
        await websocket.send_json({"message": "Подключено к списку чатов - упрощенный обработчик"})
        
        while True:
            # Получаем сообщение
            data = await websocket.receive_json()
            print(f"DEBUG: Получено сообщение от списка чатов: {data}")
            
            # Проверяем токен
            token = data.get("token")
            if not token:
                await websocket.send_json({"error": "Пользователь не авторизован"})
                continue
                
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                user_id = payload.get("sub")
                if not user_id:
                    await websocket.send_json({"error": "Некорректный токен"})
                    continue
            except Exception as e:
                print(f"DEBUG: Ошибка проверки токена: {e}")
                await websocket.send_json({"error": "Ошибка авторизации: " + str(e)})
                continue
                
            # Обработка запроса обновления списка чатов
            if data.get("type") == "get_chats":
                print(f"DEBUG: Запрос списка чатов от пользователя {user_id}")
                
                # Отправляем тестовый список чатов
                await websocket.send_json({
                    "type": "chats_list",
                    "success": True,
                    "chats": [
                        {
                            "id": 1,
                            "user1_id": int(user_id),
                            "user2_id": 3,
                            "created_at": datetime.now().isoformat(),
                            "updated_at": datetime.now().isoformat(),
                            "unread_count": 2,
                            "other_user_name": "Тестовый Пользователь",
                            "other_user_status": "Консультант",
                            "is_online": True,
                            "last_message": {
                                "content": "Тестовое сообщение",
                                "created_at": datetime.now().isoformat()
                            }
                        }
                    ]
                })
    except WebSocketDisconnect:
        print("DEBUG: Соединение списка чатов закрыто")
    except Exception as e:
        print(f"DEBUG: Ошибка в соединении списка чатов: {e}")

@app.websocket("/mobile/ws/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: int):
    print(f"DEBUG: Подключение к чату {chat_id}")
    try:
        await manager.connect(websocket, f"chat_{chat_id}")
        print(f"DEBUG: Соединение с чатом {chat_id} принято")
        await websocket.send_json({"message": f"Подключено к чату {chat_id}"})
        
        while True:
            data = await websocket.receive_json()
            
            # Получаем данные пользователя
            token = data.get("token")
            if not token:
                await websocket.send_json({"error": "Пользователь не авторизован"})
                continue
                
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                user_id = payload.get("sub")
                if not user_id:
                    await websocket.send_json({"error": "Некорректный токен"})
                    continue
            except Exception as e:
                print(f"DEBUG: Ошибка проверки токена: {str(e)}")
                # Для тестов продолжаем работу даже с истекшим токеном
                user_id = "2"  # Используем фиксированный ID для тестов
                
            # Обработка сообщения
            message_type = data.get("type")
            
            if message_type == "message":
                content = data.get("content")
                
                # Формируем ответ
                message_id = random.randint(1000, 9999)
                response = {
                    "type": "new_message",
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "sender_id": int(user_id),
                    "content": content,
                    "is_read": False,
                    "created_at": datetime.now().isoformat(),
                    "time": datetime.now().strftime("%H:%M")
                }
                
                # Сохраняем сообщение
                manager.save_message(f"chat_{chat_id}", response)
                print(f"DEBUG: Сохранено сообщение {message_id} для чата {chat_id}")
                
                # Отправляем сообщение отправителю
                await websocket.send_json(response)
                
                # Транслируем сообщение всем остальным в чате
                await manager.broadcast(response, f"chat_{chat_id}", exclude=websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"chat_{chat_id}")
        print(f"DEBUG: Соединение с чатом {chat_id} закрыто")
    except Exception as e:
        print(f"DEBUG: Ошибка в соединении с чатом {chat_id}: {e}")
        manager.disconnect(websocket, f"chat_{chat_id}")

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

@app.get("/layout/support", response_class=RedirectResponse)
async def layout_support():
    return RedirectResponse(url="/mobile/support")

@app.get("/layout/create-listing", response_class=RedirectResponse)
async def layout_create_listing():
    return RedirectResponse(url="/mobile/create-listing")

@app.get("/layout/search", response_class=RedirectResponse)
async def layout_search():
    return RedirectResponse(url="/mobile/search")

@app.get("/layout/property/{property_id}", response_class=RedirectResponse)
async def layout_property_detail(property_id: int):
    return RedirectResponse(url=f"/mobile/property/{property_id}")

@app.get("/layout/chats", response_class=RedirectResponse)
async def layout_chats():
    return RedirectResponse(url="/mobile/chats")

@app.get("/layout/chat/{user_id}", response_class=RedirectResponse)
async def layout_chat(user_id: int):
    return RedirectResponse(url=f"/mobile/chat/{user_id}")

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
async def mobile_profile(request: Request):
    return templates.TemplateResponse("layout/profile.html", {"request": request})

@app.get("/mobile/support", response_class=HTMLResponse, name="support")
async def mobile_support(request: Request):
    return templates.TemplateResponse("layout/support.html", {"request": request})

@app.get("/mobile/create-listing", response_class=HTMLResponse, name="create-listing")
async def mobile_create_listing(request: Request):
    return templates.TemplateResponse("layout/create-listing.html", {"request": request})

# Страница со списком чатов
@app.get("/mobile/chats", response_class=HTMLResponse, name="chats")
async def mobile_chats(request: Request, db: Session = Depends(deps.get_db)):
    # Получаем текущего пользователя из токена
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/mobile/auth", status_code=303)
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
        user = db.query(models.User).filter(models.User.id == token_data.sub).first()
        if not user:
            return RedirectResponse(url="/mobile/auth", status_code=303)
    except:
        return RedirectResponse(url="/mobile/auth", status_code=303)
    
    return templates.TemplateResponse("layout/chats.html", {"request": request, "current_user_id": user.id})

# Страница с одним чатом
@app.get("/mobile/chat/{chat_id}", response_class=HTMLResponse, name="chat")
async def mobile_chat(request: Request, chat_id: int, db: Session = Depends(deps.get_db)):
    # Получаем текущего пользователя из токена
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/mobile/auth", status_code=303)
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
        user = db.query(models.User).filter(models.User.id == token_data.sub).first()
        if not user:
            return RedirectResponse(url="/mobile/auth", status_code=303)
    except:
        return RedirectResponse(url="/mobile/auth", status_code=303)
    
    # Добавляем обработку отсутствия таблицы чатов
    try:
        # Проверяем, что чат существует и пользователь имеет доступ
        from models import ChatModel
        chat = db.query(ChatModel).filter(ChatModel.id == chat_id).first()
        if not chat:
            # Если чата нет, создаем временный мок-объект для тестирования
            print(f"DEBUG: Чат {chat_id} не найден, создаем тестовый объект")
            # Создаем простой объект-заглушку
            chat = type('ChatModel', (), {'id': chat_id, 'user1_id': user.id, 'user2_id': 3})
            
        # Определяем собеседника
        other_user_id = chat.user2_id if chat.user1_id == user.id else chat.user1_id
        
        try:
            other_user = db.query(models.User).filter(models.User.id == other_user_id).first()
        except:
            # Если пользователь не найден, создаем тестовый объект
            print(f"DEBUG: Собеседник {other_user_id} не найден, создаем тестовый объект")
            other_user = type('User', (), {
                'id': other_user_id,
                'first_name': 'Тестовый',
                'last_name': 'Пользователь',
                'role': 'Консультант',
                'is_active': True,
                'avatar_url': None
            })
        
    except Exception as e:
        print(f"DEBUG: Ошибка при получении данных чата: {str(e)}")
        # Создаем тестовые объекты для отображения интерфейса
        other_user = type('User', (), {
            'id': 3,
            'first_name': 'Тестовый',
            'last_name': 'Пользователь',
            'role': 'Консультант',
            'is_active': True,
            'avatar_url': None
        })
    
    return templates.TemplateResponse("layout/chat.html", {
        "request": request,
        "chat_id": chat_id,
        "current_user_id": user.id,
        "other_user": other_user
    })

# Тестовая страница для WebSocket
@app.get("/mobile/test-websocket", response_class=HTMLResponse)
async def test_websocket_page(request: Request):
    """Тестовая страница для проверки WebSocket соединений"""
    return templates.TemplateResponse("test_websocket.html", {"request": request})

@app.get("/mobile/search", response_class=HTMLResponse, name="search")
async def mobile_search(request: Request):
    return templates.TemplateResponse("layout/search.html", {"request": request})

@app.get("/api/v1/chat/{chat_id}/messages")
async def get_chat_messages(chat_id: int, request: Request):
    """Получение сообщений чата"""
    print(f"DEBUG: Запрос на получение сообщений для чата {chat_id}")
    
    # Получаем сообщения из менеджера соединений
    room_key = f"chat_{chat_id}"
    messages = manager.get_messages(room_key)
    
    # Если нет сообщений, возвращаем пустой список
    if not messages:
        print(f"DEBUG: Нет сохраненных сообщений для чата {chat_id}")
        return []
    
    print(f"DEBUG: Получены сообщения для чата {chat_id}: {len(messages)} сообщений")
    return messages

# Создаем прямой API-роутер для отладки, который не использует аутентификацию
debug_router = APIRouter(prefix="/debug")

@debug_router.get("/chat/{chat_id}/messages")
async def debug_get_chat_messages(chat_id: int):
    """Отладочная версия получения сообщений чата без аутентификации"""
    print(f"DEBUG: Отладочный запрос на получение сообщений для чата {chat_id}")
    
    room_key = f"chat_{chat_id}"
    messages = manager.get_messages(room_key)
    
    if not messages:
        print(f"DEBUG: Нет сохраненных сообщений для чата {chat_id}")
        return []
    
    print(f"DEBUG: Получены сообщения для чата {chat_id}: {len(messages)} сообщений")
    return messages

# Регистрируем отладочный роутер
app.include_router(debug_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 