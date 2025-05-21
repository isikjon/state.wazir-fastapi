from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import Mount
from starlette.applications import Starlette

from main import app as main_app
from websocket_app import websocket_app
from config import settings

# Применяем CORS для обоих приложений, чтобы обеспечить работу WebSocket
websocket_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создаем комбинированное ASGI приложение
routes = [
    Mount("/ws", app=websocket_app),  # WebSocket приложение монтируется по пути /ws
    Mount("/", app=main_app)  # Основное приложение монтируется в корне
]

app = Starlette(routes=routes)

# Для запуска через uvicorn: uvicorn asgi:app --reload --host 0.0.0.0 --port 8000 --log-level debug 