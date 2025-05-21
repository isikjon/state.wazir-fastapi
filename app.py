from fastapi import FastAPI, Request, Response, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
import json
import os
from typing import Dict, List

# Создаем экземпляр FastAPI приложения
app = FastAPI(
    title="Wazir Admin Panel",
    description="Административная панель Wazir",
    version="1.0.0"
)

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# Шаблоны
templates = Jinja2Templates(directory="templates")

# Корневой маршрут - редирект на мобильную версию@app.get("/", response_class=HTMLResponse)async def root():    return RedirectResponse(url="/mobile")

# Эндпоинт для обслуживания сервис-воркера
@app.get("/service-worker.js", response_class=FileResponse)
async def get_service_worker():
    return FileResponse(
        "static/js/service-worker.js",
        media_type="application/javascript"
    )

# Генерация VAPID ключей при запуске, если их нет
if not os.environ.get("VAPID_PUBLIC_KEY") or not os.environ.get("VAPID_PRIVATE_KEY"):
    try:
        # Пробуем сгенерировать ключи с помощью py-vapid
        try:
            # Используем Web Push библиотеку для генерации ключей
            from pywebpush import webpush, WebPushException
            from py_vapid import Vapid
            
            print("Генерация новых VAPID ключей...")
            # Создаем временный файл для ключей
            vapid_private_key_file = "private_key.pem"
            vapid_public_key_file = "public_key.pem"
            
            # Генерируем и сохраняем ключи вручную
            with open("vapid-keys.json", "w") as vapid_file:
                vapid_file.write('{"privateKey": "MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQggn5eRCm5FLWVgdjF9d5v3YxwEUaddoO1VvypKa+eXcShRANCAAQrfYoK9+wmi12XGKDtiKXU4ys1CHgsXEOyuQgcF6YRrPbi1GHDKPUcGdEU8JF+FaJUhH9PRtqCnG5En75dJYEm", "publicKey": "BAlZprGlNSMvnumbIyuxGvf5bKma7YbPvzvktzCJZ0YMxBTYpp_b_yZALcc1PG7nCvaoPgP-Ochc1RvHwRvFH_o"}')
            
            # Загружаем ключи
            with open("vapid-keys.json") as vapid_file:
                vapid_data = json.load(vapid_file)
                
            # Сохраняем ключи в переменные окружения
            os.environ["VAPID_PRIVATE_KEY"] = vapid_data["privateKey"]
            os.environ["VAPID_PUBLIC_KEY"] = vapid_data["publicKey"]
            
            print("VAPID ключи успешно установлены")
            
        except ImportError:
            print("Библиотека py-vapid не установлена")
        except Exception as e:
            print(f"Ошибка при генерации VAPID ключей: {e}")
    except Exception as e:
        print(f"Общая ошибка при работе с VAPID ключами: {e}")
else:
    print("VAPID ключи уже настроены")

# Обработка событий запуска/завершения приложения
@app.on_event("startup")
async def startup_event():
    # Загружаем VAPID ключи из файла, если они есть
    try:
        if not os.environ.get("VAPID_PUBLIC_KEY") or not os.environ.get("VAPID_PRIVATE_KEY"):
            if os.path.exists("vapid-keys.json"):
                with open("vapid-keys.json", "r") as f:
                    vapid_data = json.load(f)
                    os.environ["VAPID_PRIVATE_KEY"] = vapid_data["privateKey"]
                    os.environ["VAPID_PUBLIC_KEY"] = vapid_data["publicKey"]
                    print("VAPID ключи загружены из файла")
    except Exception as e:
        print(f"Ошибка при загрузке VAPID ключей: {e}")
    
    print("Приложение запущено")

@app.on_event("shutdown")
async def shutdown_event():
    print("Приложение завершает работу")

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.chat_messages: Dict[str, List[dict]] = {}

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = []
        self.active_connections[room].append(websocket)

    def disconnect(self, websocket: WebSocket, room: str):
        if room in self.active_connections:
            self.active_connections[room].remove(websocket)
            if not self.active_connections[room]:
                del self.active_connections[room]

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

    def get_messages(self, room: str):
        return self.chat_messages.get(room, [])

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("layout/dashboard.html", {"request": request})

@app.get("/search", response_class=HTMLResponse)
async def search(request: Request):
    return templates.TemplateResponse("layout/search.html", {"request": request})

@app.get("/chats", response_class=HTMLResponse)
async def chats(request: Request):
    return templates.TemplateResponse("layout/chats.html", {"request": request})

@app.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    return templates.TemplateResponse("layout/chat.html", {"request": request})

@app.get("/support", response_class=HTMLResponse)
async def support(request: Request):
    return templates.TemplateResponse("layout/support.html", {"request": request})

@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request):
    return templates.TemplateResponse("layout/profile.html", {"request": request})

@app.websocket("/ws/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: str):
    await manager.connect(websocket, chat_id)
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "load_history":
                messages = manager.get_messages(chat_id)
                await manager.send_personal_message({"type": "chat_history", "messages": messages}, websocket)
            
            elif data.get("type") == "message":
                message = {
                    "text": data.get("text", ""),
                    "sender": data.get("sender", "unknown"),
                    "time": data.get("time", ""),
                    "type": "message"
                }
                
                manager.save_message(chat_id, message)
                
                await manager.broadcast(message, chat_id, exclude=websocket)
                
                notification = {
                    "type": "new_message",
                    "chatId": chat_id,
                    "text": data.get("text", ""),
                    "time": data.get("time", "")
                }
                
                for room in manager.active_connections:
                    if room != chat_id:
                        await manager.broadcast(notification, room)
            
            elif data.get("type") == "status_change":
                status_data = {
                    "type": "status_change",
                    "userId": data.get("userId", ""),
                    "status": data.get("status", "")
                }
                
                for room in manager.active_connections:
                    await manager.broadcast(status_data, room)
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket, chat_id)

@app.websocket("/ws/chats_list")
async def chats_list_endpoint(websocket: WebSocket):
    await manager.connect(websocket, "chats_list")
    try:
        while True:
            await websocket.receive_json()
    except WebSocketDisconnect:
        manager.disconnect(websocket, "chats_list")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 