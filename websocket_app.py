from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from datetime import datetime
import jwt
from config import settings

# Создаем отдельное приложение ТОЛЬКО для WebSocket
# Без middleware и проверок безопасности
websocket_app = FastAPI(
    title="WebSocket API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

@websocket_app.websocket("/test")
async def test_websocket_endpoint(websocket: WebSocket):
    print("DEBUG PURE WEBSOCKET APP: Входящее тестовое соединение")
    try:
        await websocket.accept()
        print("DEBUG PURE WEBSOCKET APP: Соединение принято!")
        
        # Отправляем приветственное сообщение
        await websocket.send_json({"message": "Тестовое соединение успешно установлено (отдельное приложение)"})
        
        while True:
            # Получаем сообщение
            data = await websocket.receive_json()
            print(f"DEBUG PURE WEBSOCKET APP: Получено сообщение: {data}")
            
            # Отправляем эхо-ответ
            await websocket.send_json({"message": f"Эхо (отдельное приложение): {data.get('message', 'Пустое сообщение')}"})
            
    except WebSocketDisconnect:
        print("DEBUG PURE WEBSOCKET APP: Соединение закрыто")
    except Exception as e:
        print(f"DEBUG PURE WEBSOCKET APP: Ошибка в WebSocket: {e}")

@websocket_app.websocket("/chats_list")
async def chats_list_endpoint(websocket: WebSocket):
    print("DEBUG PURE WEBSOCKET APP: Входящее соединение для списка чатов")
    try:
        await websocket.accept()
        print("DEBUG PURE WEBSOCKET APP: Соединение для списка чатов принято!")
        
        # Отправляем приветственное сообщение
        await websocket.send_json({"message": "Соединение для списка чатов установлено (отдельное приложение)"})
        
        while True:
            # Получаем сообщение
            data = await websocket.receive_json()
            print(f"DEBUG PURE WEBSOCKET APP: Получено сообщение: {data}")
            
            # Проверяем токен
            token = data.get("token")
            if not token:
                await websocket.send_json({"error": "Отсутствует токен"})
                continue
                
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                user_id = payload.get("sub")
                if not user_id:
                    await websocket.send_json({"error": "Некорректный токен"})
                    continue
            except Exception as e:
                print(f"DEBUG PURE WEBSOCKET APP: Ошибка проверки токена: {e}")
                await websocket.send_json({"error": "Ошибка проверки токена"})
                continue
                
            # Обработка запроса обновления списка чатов
            if data.get("type") == "get_chats":
                print(f"DEBUG PURE WEBSOCKET APP: Запрос списка чатов от пользователя {user_id}")
                # Временно возвращаем тестовые данные
                await websocket.send_json({
                    "type": "chats_list",
                    "chats": [
                        {
                            "id": 1,
                            "user1_id": int(user_id),
                            "user2_id": 3,
                            "other_user_name": "Тестовый Пользователь",
                            "other_user_status": "online",
                            "unread_count": 2,
                            "last_message": {
                                "content": "Тестовое сообщение от отдельного приложения",
                                "created_at": datetime.now().isoformat()
                            }
                        }
                    ]
                })
    except WebSocketDisconnect:
        print("DEBUG PURE WEBSOCKET APP: Соединение для списка чатов закрыто")
    except Exception as e:
        print(f"DEBUG PURE WEBSOCKET APP: Ошибка в WebSocket списка чатов: {e}") 