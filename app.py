from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
import json
import os

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

# Корневой маршрут - редирект на админку
@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/admin/dashboard")

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