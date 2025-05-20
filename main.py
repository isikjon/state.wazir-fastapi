from fastapi import FastAPI, Request, Depends, Form, status, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from config import settings
from app.api.v1 import api_router
from sqlalchemy.orm import Session, joinedload
from app.api import deps
from app.utils.security import verify_password
from app import models
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from sqlalchemy.types import String
import pandas as pd
import os
from uuid import uuid4
import json
from flask import jsonify
import random
from starlette.middleware.sessions import SessionMiddleware
from typing import Dict, Any, Optional

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

# Корневой маршрут - перенаправление на админ-панель
@app.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(url="/admin")

# Мобильные (клиентские) маршруты
@app.get("/mobile", response_class=HTMLResponse)
async def mobile_root(request: Request):
    return templates.TemplateResponse("layout/dashboard.html", {"request": request})

@app.get("/mobile/auth", response_class=HTMLResponse)
async def mobile_auth(request: Request):
    return templates.TemplateResponse("layout/auth.html", {"request": request})

@app.get("/mobile/profile", response_class=HTMLResponse)
async def mobile_profile(request: Request):
    return templates.TemplateResponse("layout/profile.html", {"request": request})

@app.get("/mobile/support", response_class=HTMLResponse)
async def mobile_support(request: Request):
    return templates.TemplateResponse("layout/support.html", {"request": request})

@app.get("/mobile/create-listing", response_class=HTMLResponse)
async def mobile_create_listing(request: Request):
    return templates.TemplateResponse("layout/create-listing.html", {"request": request})

@app.get("/mobile/search", response_class=HTMLResponse)
async def mobile_search(request: Request):
    return templates.TemplateResponse("layout/search.html", {"request": request})

@app.get("/mobile/property/{property_id}", response_class=HTMLResponse)
async def mobile_property_detail(request: Request, property_id: int):
    return templates.TemplateResponse("layout/property.html", {"request": request, "property_id": property_id})

@app.get("/mobile/chats", response_class=HTMLResponse)
async def mobile_chats(request: Request):
    return templates.TemplateResponse("layout/chats.html", {"request": request})

@app.get("/mobile/chat/{user_id}", response_class=HTMLResponse)
async def mobile_chat(request: Request, user_id: int):
    return templates.TemplateResponse("layout/chat.html", {"request": request, "user_id": user_id})

# Админские маршруты
@app.get("/admin", response_class=HTMLResponse)
async def admin_index(request: Request):
    return templates.TemplateResponse("admin/index.html", {"request": request})

@app.post("/admin/login", response_class=RedirectResponse)
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    user = db.query(models.User).filter(
        (models.User.email == username) | 
        (models.User.phone == username)
    ).first()
    
    if not user or not verify_password(password, user.hashed_password) or user.role != "admin":
        return templates.TemplateResponse(
            "admin/index.html", 
            {"request": request, "error": "Неверные учетные данные или недостаточно прав"}
        )
    
    response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return response

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(deps.get_db)):
    # Получаем статистику
    properties_count = db.query(func.count(models.Property.id)).scalar() or 0
    users_count = db.query(func.count(models.User.id)).scalar() or 0
    
    # Получение количества заявок
    requests_count = db.query(func.count(models.Request.id)).scalar() or 0
    
    # Получение количества тикетов
    tickets_count = db.query(func.count(models.SupportTicket.id)).scalar() or 0
    
    # Получаем последние объекты
    last_properties = db.query(models.Property).order_by(desc(models.Property.created_at)).limit(4).all()
    
    # Получаем последние заявки
    last_requests = db.query(models.Request).order_by(desc(models.Request.created_at)).limit(3).all()
    
    # Получаем последние тикеты
    last_tickets = db.query(models.SupportTicket).order_by(desc(models.SupportTicket.created_at)).limit(3).all()
    
    # Получаем изменения за месяц (для примера просто используем случайные проценты)
    # В реальной ситуации здесь должны быть вычисления на основе данных за прошлый месяц
    month_ago = datetime.now() - timedelta(days=30)
    
    properties_prev_count = db.query(func.count(models.Property.id)).filter(
        models.Property.created_at < month_ago
    ).scalar() or 1  # Чтобы избежать деления на ноль
    
    users_prev_count = db.query(func.count(models.User.id)).filter(
        models.User.created_at < month_ago
    ).scalar() or 1
    
    requests_prev_count = db.query(func.count(models.Request.id)).filter(
        models.Request.created_at < month_ago
    ).scalar() or 1
    
    tickets_prev_count = db.query(func.count(models.SupportTicket.id)).filter(
        models.SupportTicket.created_at < month_ago
    ).scalar() or 1
    
    # Вычисляем процентное изменение
    properties_change = round(((properties_count - properties_prev_count) / properties_prev_count) * 100)
    users_change = round(((users_count - users_prev_count) / users_prev_count) * 100)
    requests_change = round(((requests_count - requests_prev_count) / requests_prev_count) * 100)
    tickets_change = round(((tickets_count - tickets_prev_count) / tickets_prev_count) * 100)
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "properties_count": properties_count,
        "users_count": users_count,
        "requests_count": requests_count,
        "tickets_count": tickets_count,
        "last_properties": last_properties,
        "last_requests": last_requests,
        "last_tickets": last_tickets,
        "properties_change": properties_change,
        "users_change": users_change,
        "requests_change": requests_change,
        "tickets_change": tickets_change
    })

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(
    request: Request, 
    page: int = 1, 
    search: str = None, 
    status: str = None,
    db: Session = Depends(deps.get_db)
):
    # Получаем число пользователей на странице и базовый запрос
    page_size = 6
    query = db.query(models.User).options(
        joinedload(models.User.properties),
    )
    
    # Применяем фильтры
    if search:
        query = query.filter(
            (models.User.full_name.ilike(f"%{search}%")) |
            (models.User.email.ilike(f"%{search}%")) |
            (models.User.phone.ilike(f"%{search}%")) |
            (models.User.id.cast(String).like(f"%{search}%"))
        )
    
    if status:
        if status.lower() == 'active':
            query = query.filter(models.User.is_active == True)
        elif status.lower() == 'inactive':
            query = query.filter(models.User.is_active == False)
    
    # Получаем общее количество с учетом фильтров
    total_users = query.count()
    
    # Вычисляем смещение для пагинации
    offset = (page - 1) * page_size
    
    # Получаем пользователей с сортировкой
    users = query.order_by(desc(models.User.created_at)).offset(offset).limit(page_size).all()
    
    # Вычисляем данные для пагинации
    total_pages = (total_users + page_size - 1) // page_size
    start_item = offset + 1 if users else 0
    end_item = min(offset + page_size, total_users)
    
    # Формируем список отображаемых страниц
    pages = []
    max_visible_pages = 5
    show_ellipsis = False
    
    if total_pages <= max_visible_pages:
        pages = list(range(1, total_pages + 1))
    else:
        # Вычисляем диапазон видимых страниц
        half_visible = max_visible_pages // 2
        
        if page <= half_visible + 1:
            # Начало пагинации: 1 2 3 ... 10
            pages = list(range(1, max_visible_pages))
            show_ellipsis = True
        elif page >= total_pages - half_visible:
            # Конец пагинации: 1 ... 8 9 10
            pages = list(range(total_pages - max_visible_pages + 2, total_pages + 1))
            show_ellipsis = True
            pages.insert(0, 1)
        else:
            # Середина пагинации: 1 ... 4 5 6 ... 10
            pages = list(range(page - half_visible + 1, page + half_visible))
            show_ellipsis = True
            pages.insert(0, 1)
            pages.append(total_pages)
    
    # Функция для форматирования времени последней активности
    def format_last_activity(last_activity):
        if not last_activity:
            return "Нет данных"
        
        now = datetime.now()
        delta = now - last_activity
        
        if delta.days == 0:
            if delta.seconds < 3600:
                return f"{delta.seconds // 60} минут назад"
            return f"Сегодня, {last_activity.strftime('%H:%M')}"
        elif delta.days == 1:
            return f"Вчера, {last_activity.strftime('%H:%M')}"
        elif delta.days < 7:
            return f"{delta.days} дней назад"
        else:
            return last_activity.strftime("%d.%m.%Y")
    
    # Преобразуем данные для шаблона
    user_list = []
    for user in users:
        # Считаем количество объявлений
        properties_count = len(user.properties) if user.properties else 0
        
        # Считаем количество туров 360
        tours_count = db.query(func.count(models.Property.id)).filter(
            models.Property.owner_id == user.id,
            models.Property.tour_360_url.isnot(None),
            models.Property.tour_360_url != ""
        ).scalar() or 0
        
        # Проверяем наличие атрибута last_login
        last_activity = "Нет данных"
        if hasattr(user, 'last_login') and user.last_login:
            last_activity = format_last_activity(user.last_login)
        
        user_list.append({
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "is_active": user.is_active,
            "properties_count": properties_count,
            "tours_count": tours_count,
            "registered_at": user.created_at.strftime("%d.%m.%Y"),
            "last_activity": last_activity
        })
    
    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "users": user_list,
        "total_users": total_users,
        "current_page": page,
        "total_pages": total_pages,
        "pages": pages,
        "show_ellipsis": show_ellipsis,
        "start_item": start_item,
        "end_item": end_item,
        "search_query": search or "",
        "status": status or ""
    })

@app.get("/admin/users/{user_id}/ban", response_class=RedirectResponse)
async def ban_user(
    request: Request, 
    user_id: int,
    db: Session = Depends(deps.get_db)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Блокируем пользователя
    user.is_active = False
    db.add(user)
    db.commit()
    
    # Возвращаемся на страницу пользователей
    return RedirectResponse(url="/admin/users", status_code=303)

@app.get("/admin/users/{user_id}/activate", response_class=RedirectResponse)
async def activate_user(
    request: Request, 
    user_id: int,
    db: Session = Depends(deps.get_db)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Активируем пользователя
    user.is_active = True
    db.add(user)
    db.commit()
    
    # Возвращаемся на страницу пользователей
    return RedirectResponse(url="/admin/users", status_code=303)

@app.get("/admin/users/export", response_class=FileResponse)
async def export_users(
    request: Request,
    search: str = None,
    status: str = None,
    db: Session = Depends(deps.get_db)
):
    # Используем тот же запрос, что и для отображения списка, но без пагинации
    query = db.query(models.User).options(
        joinedload(models.User.properties),
    )
    
    # Применяем фильтры
    if search:
        query = query.filter(
            (models.User.full_name.ilike(f"%{search}%")) |
            (models.User.email.ilike(f"%{search}%")) |
            (models.User.phone.ilike(f"%{search}%")) |
            (models.User.id.cast(String).like(f"%{search}%"))
        )
    
    if status:
        if status.lower() == 'active':
            query = query.filter(models.User.is_active == True)
        elif status.lower() == 'inactive':
            query = query.filter(models.User.is_active == False)
    
    # Получаем данные
    users = query.order_by(desc(models.User.created_at)).all()
    
    # Создаем DataFrame для экспорта
    data = []
    for user in users:
        # Считаем количество объявлений
        properties_count = len(user.properties) if user.properties else 0
        
        # Считаем количество туров 360
        tours_count = db.query(func.count(models.Property.id)).filter(
            models.Property.owner_id == user.id,
            models.Property.tour_360_url.isnot(None),
            models.Property.tour_360_url != ""
        ).scalar() or 0
        
        # Данные о последнем входе
        last_login_str = "Нет данных"
        if hasattr(user, 'last_login') and user.last_login:
            last_login_str = user.last_login.strftime("%d.%m.%Y %H:%M")
        
        data.append({
            "ID": user.id,
            "Имя": user.full_name,
            "Email": user.email,
            "Телефон": user.phone,
            "Статус": "Активен" if user.is_active else "Неактивен",
            "Роль": user.role,
            "Объявлений": properties_count,
            "360-туры": tours_count,
            "Дата регистрации": user.created_at.strftime("%d.%m.%Y"),
            "Последний вход": last_login_str
        })
    
    # Создаем DataFrame
    df = pd.DataFrame(data)
    
    # Создаем директорию для временных файлов, если она не существует
    os.makedirs("static/temp", exist_ok=True)
    
    # Генерируем уникальное имя файла
    filename = f"users_export_{uuid4().hex}.xlsx"
    filepath = f"static/temp/{filename}"
    
    # Сохраняем в Excel
    df.to_excel(filepath, index=False)
    
    # Возвращаем файл
    return FileResponse(
        path=filepath,
        filename="users_export.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.get("/admin/properties", response_class=HTMLResponse)
async def admin_properties(
    request: Request, 
    page: int = 1, 
    search: str = None, 
    status: str = None,
    category: str = Query(None),
    db: Session = Depends(deps.get_db)
):
    # Получаем число объявлений на странице и базовый запрос
    page_size = 6
    query = db.query(models.Property).options(
        joinedload(models.Property.owner),
        joinedload(models.Property.images),
        joinedload(models.Property.categories)
    )
    
    # Применяем фильтры
    if search:
        query = query.filter(
            (models.Property.title.ilike(f"%{search}%")) |
            (models.Property.address.ilike(f"%{search}%")) |
            (models.Property.city.ilike(f"%{search}%")) |
            (models.Property.id.cast(String).like(f"%{search}%"))
        )
    
    if status:
        query = query.filter(models.Property.status == status)
    
    if category and category.strip() and category.isdigit():
        category_id = int(category)
        query = query.join(models.property_category).filter(
            models.property_category.c.category_id == category_id
        )
    
    # Получаем общее количество с учетом фильтров
    total_properties = query.count()
    
    # Вычисляем смещение для пагинации
    offset = (page - 1) * page_size
    
    # Получаем объекты недвижимости с сортировкой
    properties = query.order_by(desc(models.Property.created_at)).offset(offset).limit(page_size).all()
    
    # Получаем все категории для фильтра
    categories = db.query(models.Category).all()
    
    # Вычисляем данные для пагинации
    total_pages = (total_properties + page_size - 1) // page_size
    start_item = offset + 1 if properties else 0
    end_item = min(offset + page_size, total_properties)
    
    # Формируем список отображаемых страниц (1, 2, 3... или 1, 2, 3 ... 10)
    pages = []
    max_visible_pages = 5
    
    if total_pages <= max_visible_pages:
        pages = list(range(1, total_pages + 1))
        show_ellipsis = False
    else:
        # Вычисляем диапазон видимых страниц
        half_visible = max_visible_pages // 2
        
        if page <= half_visible + 1:
            # Начало пагинации: 1 2 3 ... 10
            pages = list(range(1, max_visible_pages))
            show_ellipsis = True
        elif page >= total_pages - half_visible:
            # Конец пагинации: 1 ... 8 9 10
            pages = list(range(total_pages - max_visible_pages + 2, total_pages + 1))
            show_ellipsis = True
            pages.insert(0, 1)
        else:
            # Середина пагинации: 1 ... 4 5 6 ... 10
            pages = list(range(page - half_visible + 1, page + half_visible))
            show_ellipsis = True
            pages.insert(0, 1)
            pages.append(total_pages)
    
    def format_price(price):
        """Форматирует цену как строку с разделением тысяч"""
        if price is None:
            return "0 ₽"
        try:
            return f"{int(price):,}".replace(",", " ") + " ₽"
        except (ValueError, TypeError):
            return str(price) + " ₽"
    
    # Функция для получения основного изображения объявления
    def get_main_image(property_obj):
        if property_obj.images:
            main_images = [img for img in property_obj.images if img.is_main]
            if main_images:
                return main_images[0].url
            # Если нет основного изображения, возвращаем первое имеющееся
            if property_obj.images:
                return property_obj.images[0].url
        # Если нет изображений, возвращаем плейсхолдер
        return "/static/layout/assets/img/placeholder.jpg"
    
    # Функция для получения количества просмотров (заглушка)
    def get_views_count(property_id):
        # В будущем здесь можно реализовать реальный подсчет просмотров
        # Сейчас возвращаем случайное число для примера
        return random.randint(10, 300)
    
    # Преобразуем данные для шаблона
    property_list = []
    for prop in properties:
        property_list.append({
            "id": prop.id,
            "title": prop.title,
            "address": f"{prop.address}, {prop.city}",
            "price": format_price(prop.price),
            "price_raw": prop.price,
            "status": prop.status.value,
            "status_display": {
                "active": "Активно",
                "pending": "На проверке",
                "draft": "Черновик",
                "rejected": "Отклонено",
                "sold": "Продано"
            }.get(prop.status.value, "Неизвестно"),
            "status_class": {
                "active": "status-active",
                "pending": "status-pending",
                "draft": "status-draft",
                "rejected": "status-inactive",
                "sold": "status-sold"
            }.get(prop.status.value, "status-inactive"),
            "date": prop.created_at.strftime("%d.%m.%Y"),
            "owner": f"{prop.owner.first_name} {prop.owner.last_name}" if prop.owner else "Неизвестно",
            "area": prop.area,
            "image": get_main_image(prop),
            "views": get_views_count(prop.id),
            "has_tour": bool(prop.tour_360_url),
            "tour_url": prop.tour_360_url
        })
    
    return templates.TemplateResponse("admin/properties.html", {
        "request": request,
        "properties": property_list,
        "total_properties": total_properties,
        "current_page": page,
        "total_pages": total_pages,
        "pages": pages,
        "show_ellipsis": show_ellipsis if 'show_ellipsis' in locals() else False,
        "start_item": start_item,
        "end_item": end_item,
        "search_query": search or "",
        "status_filter": status or "",
        "category_filter": category,
        "categories": categories,
        "format_price": format_price
    })

@app.get("/admin/support", response_class=HTMLResponse)
async def admin_support(request: Request):
    ticket_id = request.query_params.get('ticket_id')
    
    # Получаем список всех тикетов
    tickets = get_support_tickets()
    
    active_ticket = None
    messages_by_date = {}
    
    # Если выбран конкретный тикет, получаем информацию о нем и сообщения
    if ticket_id:
        active_ticket = get_ticket_details(ticket_id)
        if active_ticket:
            messages_by_date = get_ticket_messages(ticket_id)
    
    return templates.TemplateResponse("admin/support.html", {
        "request": request,
        "tickets": tickets,
        "active_ticket": active_ticket,
        "messages_by_date": messages_by_date,
        "admin_name": "Администратор"
    })

@app.post("/api/v1/support/message", response_class=JSONResponse)
async def send_support_message(
    request: Request,
    content: str = Form(...),
    ticket_id: int = Form(...),
    db: Session = Depends(deps.get_db)
):
    if not ticket_id or not content:
        return JSONResponse(
            {"error": "Missing required fields"},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Получаем ID администратора из сессии
    admin_id = request.session.get('admin_id', 1)
    
    # Сохраняем сообщение в базе данных
    message_id = save_support_message(ticket_id, content, admin_id=admin_id)
    
    return JSONResponse({
        "success": True,
        "message_id": message_id,
        "admin_id": admin_id
    })

@app.get("/api/v1/support/tickets/{ticket_id}/messages/new", response_class=JSONResponse)
async def get_new_messages(
    request: Request,
    ticket_id: int,
    last_id: int = Query(0, alias="last_id"),
    db: Session = Depends(deps.get_db)
):
    # Получаем новые сообщения после last_id
    messages = get_new_ticket_messages(ticket_id, last_id)
    
    # Используем кастомную сериализацию для обработки datetime
    return JSONResponse(
        content={"success": True, "messages": messages},
        media_type="application/json"
    )

@app.put("/api/v1/support/tickets/{ticket_id}/close", response_class=JSONResponse)
async def close_ticket(
    request: Request,
    ticket_id: int,
    db: Session = Depends(deps.get_db)
):
    success = close_support_ticket(ticket_id)
    
    if success:
        return JSONResponse({"success": True})
    else:
        return JSONResponse({"error": "Failed to close ticket"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Вспомогательные функции для техподдержки
def get_support_tickets():
    """Получение списка тикетов техподдержки"""
    # Временные данные, в реальном приложении они будут из базы данных
    tickets = [
        {
            'id': 4589,
            'user': {
                'id': 100234,
                'full_name': 'Иванов Иван'
            },
            'subject': 'Проблема с загрузкой фото',
            'last_message_time': '14:25',
            'last_message_preview': 'Не могу загрузить фотографии к объявлению, выдает ошибку...',
            'status': 'new',
            'status_class': 'status-new',
            'status_display': 'Новый'
        },
        {
            'id': 4588,
            'user': {
                'id': 100235,
                'full_name': 'Петрова Елена'
            },
            'subject': 'Не отображается 360-тур',
            'last_message_time': 'Вчера',
            'last_message_preview': 'После загрузки 360-тура, он не отображается на странице объявления...',
            'status': 'waiting',
            'status_class': 'status-waiting',
            'status_display': 'Ожидает'
        },
        {
            'id': 4587,
            'user': {
                'id': 100236,
                'full_name': 'Сидоров Алексей'
            },
            'subject': 'Не могу зайти в аккаунт',
            'last_message_time': '12.06',
            'last_message_preview': 'После ввода пароля выдает ошибку аутентификации, хотя пароль...',
            'status': 'active',
            'status_class': 'status-active',
            'status_display': 'Активный'
        },
        {
            'id': 4586,
            'user': {
                'id': 100237,
                'full_name': 'Козлов Дмитрий'
            },
            'subject': 'Не приходят уведомления',
            'last_message_time': '10.06',
            'last_message_preview': 'Перестали приходить уведомления о новых сообщениях...',
            'status': 'active',
            'status_class': 'status-active',
            'status_display': 'Активный'
        },
        {
            'id': 4585,
            'user': {
                'id': 100238,
                'full_name': 'Смирнова Ольга'
            },
            'subject': 'Ошибка оплаты',
            'last_message_time': '08.06',
            'last_message_preview': 'При попытке оплаты VIP-размещения произошла ошибка...',
            'status': 'closed',
            'status_class': 'status-closed',
            'status_display': 'Закрыт'
        }
    ]
    
    return tickets

def get_ticket_details(ticket_id):
    """Получение информации о конкретном тикете"""
    tickets = get_support_tickets()
    
    # Преобразуем ticket_id в int для сравнения
    ticket_id = int(ticket_id)
    
    for ticket in tickets:
        if ticket['id'] == ticket_id:
            # Добавляем доп. информацию
            ticket['user']['phone'] = '+7 (999) 123-45-67'  # Для кнопки "Позвонить"
            return ticket
            
    return None

def get_ticket_messages(ticket_id):
    """Получение сообщений для конкретного тикета, сгруппированных по датам"""
    # Временные данные
    ticket_id = int(ticket_id)
    
    if ticket_id == 4589:  # Иванов Иван
        messages = [
            {
                'id': 1,
                'content': 'Здравствуйте, у меня возникла проблема с загрузкой фотографий к объявлению. При попытке загрузить выдает ошибку "Формат файла не поддерживается", хотя я загружаю обычные JPG.',
                'time': '11:45',
                'datetime': datetime.now().replace(hour=11, minute=45),
                'is_admin': False,
                'is_read': True
            },
            {
                'id': 2,
                'content': 'Добрый день, Иван! Спасибо за обращение. Подскажите, пожалуйста, какое устройство и браузер вы используете? Также уточните, пожалуйста, размер загружаемых файлов.',
                'time': '12:02',
                'datetime': datetime.now().replace(hour=12, minute=2),
                'is_admin': True,
                'is_read': True,
                'admin_id': 'A1'
            },
            {
                'id': 3,
                'content': 'Я использую Windows 10, Chrome последней версии. Размер файлов примерно 3-5 МБ каждый. Раньше всё работало нормально, проблема появилась сегодня утром.',
                'time': '12:15',
                'datetime': datetime.now().replace(hour=12, minute=15),
                'is_admin': False,
                'is_read': True
            },
            {
                'id': 4,
                'content': 'Спасибо за информацию! Действительно, у нас были небольшие технические работы сегодня утром, которые могли повлиять на загрузку изображений.\n\nПожалуйста, попробуйте следующее:\n1. Очистите кэш браузера\n2. Перезагрузите страницу\n3. Попробуйте загрузить фотографии повторно\n\nЕсли проблема сохранится, сообщите нам.',
                'time': '12:23',
                'datetime': datetime.now().replace(hour=12, minute=23),
                'is_admin': True,
                'is_read': True,
                'admin_id': 'A1'
            },
            {
                'id': 5,
                'content': 'Спасибо за быстрый ответ! Я очистил кэш и перезагрузил страницу, но проблема осталась. Может ли это быть связано с форматом фотографий? У меня iPhone и фотографии в формате HEIC.',
                'time': '14:25',
                'datetime': datetime.now().replace(hour=14, minute=25),
                'is_admin': False,
                'is_read': False
            }
        ]
    elif ticket_id == 4588:  # Петрова Елена
        messages = [
            {
                'id': 1,
                'content': 'Здравствуйте! После загрузки 360-тура он не отображается на странице объявления.',
                'time': '10:30',
                'datetime': (datetime.now() - timedelta(days=1)).replace(hour=10, minute=30),
                'is_admin': False,
                'is_read': True
            },
            {
                'id': 2,
                'content': 'Добрый день, Елена! Для корректного отображения 360-тура нужно дождаться его обработки нашей системой, это может занять до 30 минут.',
                'time': '11:15',
                'datetime': (datetime.now() - timedelta(days=1)).replace(hour=11, minute=15),
                'is_admin': True,
                'is_read': True,
                'admin_id': 'A2'
            }
        ]
    else:
        messages = []
    
    # Группируем сообщения по датам
    messages_by_date = {}
    
    for message in messages:
        date_str = 'Сегодня'
        
        if message['datetime'].date() < datetime.now().date():
            delta = datetime.now().date() - message['datetime'].date()
            if delta.days == 1:
                date_str = 'Вчера'
            else:
                date_str = message['datetime'].strftime('%d.%m.%Y')
        
        if date_str not in messages_by_date:
            messages_by_date[date_str] = []
        
        messages_by_date[date_str].append(message)
    
    return messages_by_date

def get_new_ticket_messages(ticket_id, last_message_id):
    """Получение новых сообщений после last_message_id"""
    ticket_id = int(ticket_id)
    all_messages = []
    
    # Сначала получаем все сообщения
    messages_by_date = get_ticket_messages(ticket_id)
    for date, messages in messages_by_date.items():
        all_messages.extend(messages)
    
    # Фильтруем только новые сообщения
    new_messages = [msg for msg in all_messages if msg['id'] > last_message_id]
    
    # Если нет новых сообщений, симулируем новое сообщение от пользователя с некоторой вероятностью
    if not new_messages and random.random() < 0.1:  # 10% шанс получения нового сообщения
        max_id = max([msg['id'] for msg in all_messages]) if all_messages else 0
        new_message = {
            'id': max_id + 1,
            'content': 'Спасибо за ответ! Я попробую следовать вашим инструкциям.',
            'time': datetime.now().strftime('%H:%M'),
            'is_admin': False,
            'is_read': False
        }
        new_messages.append(new_message)
    
    return new_messages

def save_support_message(ticket_id, content, admin_id):
    """Сохранение нового сообщения техподдержки"""
    # В реальном приложении сообщение будет сохраняться в базу данных
    # Для демонстрации просто возвращаем ID сообщения
    return random.randint(1000, 9999)

def close_support_ticket(ticket_id):
    """Закрытие тикета"""
    # В реальном приложении статус тикета будет обновляться в базе данных
    return True

@app.get("/admin/requests", response_class=HTMLResponse)
async def admin_requests(
    request: Request,
    page: int = 1,
    search: str = None,
    status: str = None,
    request_type: str = None,
    tab: str = "tour",
    property_page: int = 1,
    db: Session = Depends(deps.get_db)
):
    # Базовый запрос для заявок на съемку 360
    page_size = 6
    query = db.query(models.Request).options(
        joinedload(models.Request.user),
        joinedload(models.Request.property),
        joinedload(models.Request.property, models.Property.images)
    )
    
    # Применяем фильтры
    if search:
        query = query.filter(
            (models.Request.title.ilike(f"%{search}%")) |
            (models.Request.description.ilike(f"%{search}%")) |
            (models.Request.id.cast(String).like(f"%{search}%")) |
            (models.Request.contact_phone.ilike(f"%{search}%")) |
            (models.Request.contact_email.ilike(f"%{search}%"))
        )
    
    if status:
        query = query.filter(models.Request.status == status)
        
    if request_type:
        query = query.filter(models.Request.type == request_type)
    
    # Получаем общее количество заявок с учетом фильтров
    total_requests = query.count()
    
    # Применяем пагинацию
    offset = (page - 1) * page_size
    requests = query.order_by(desc(models.Request.created_at)).offset(offset).limit(page_size).all()
    
    # Получаем счетчики по типам заявок
    tour_requests_count = db.query(func.count(models.Request.id)).filter(
        models.Request.type == "viewing",
        models.Request.status.in_(["new", "processing"])
    ).scalar() or 0
    
    new_prop_requests_count = db.query(func.count(models.Request.id)).filter(
        models.Request.type == "sell",
        models.Request.status.in_(["new", "processing"])
    ).scalar() or 0
    
    # Обрабатываем данные для отображения
    request_list = []
    for req in requests:
        # Получаем основное изображение для объекта недвижимости
        property_image = None
        if req.property and req.property.images:
            main_images = [img for img in req.property.images if img.is_main]
            if main_images:
                property_image = main_images[0].url
            elif req.property.images:
                property_image = req.property.images[0].url
        
        # Формируем представление статуса
        status_display = {
            "new": "Новая заявка",
            "processing": "В обработке",
            "completed": "Завершена",
            "rejected": "Отклонена"
        }.get(req.status, "Неизвестно")
        
        status_class = {
            "new": "status-new",
            "processing": "status-progress",
            "completed": "status-completed",
            "rejected": "status-rejected"
        }.get(req.status, "")
        
        # Создаем представление заявки
        request_list.append({
            "id": req.id,
            "title": req.title or "Без названия",
            "description": req.description or "",
            "type": req.type,
            "type_display": {
                "viewing": "Просмотр объекта",
                "purchase": "Покупка",
                "sell": "Продажа",
                "consultation": "Консультация",
                "other": "Другое"
            }.get(req.type, "Другое"),
            "status": req.status,
            "status_display": status_display,
            "status_class": status_class,
            "created_at": req.created_at.strftime("%d.%m.%Y, %H:%M"),
            "appointment_date": req.appointment_date.strftime("%d.%m.%Y, %H:%M") if req.appointment_date else None,
            "user": {
                "id": req.user.id,
                "name": f"{req.user.first_name} {req.user.last_name}",
                "phone": req.user.phone,
                "email": req.user.email
            } if req.user else None,
            "property": {
                "id": req.property.id,
                "title": req.property.title,
                "address": f"{req.property.address}, {req.property.city}",
                "price": format_price(req.property.price),
                "price_raw": req.property.price,
                "image": property_image or "/static/layout/assets/img/placeholder.jpg",
                "area": req.property.area
            } if req.property else None,
            "contact_phone": req.contact_phone,
            "contact_email": req.contact_email,
            "notes": req.notes,
            "is_urgent": req.is_urgent
        })
    
    # Формируем объект пагинации
    total_pages = (total_requests + page_size - 1) // page_size if total_requests > 0 else 1
    start_item = offset + 1 if requests else 0
    end_item = min(offset + page_size, total_requests)
    
    # Формируем список отображаемых страниц
    pages = []
    max_visible_pages = 5
    
    if total_pages <= max_visible_pages:
        pages = list(range(1, total_pages + 1))
        show_ellipsis = False
    else:
        half_visible = max_visible_pages // 2
        
        if page <= half_visible + 1:
            # Начало пагинации: 1 2 3 ... 10
            pages = list(range(1, max_visible_pages))
            show_ellipsis = True
        elif page >= total_pages - half_visible:
            # Конец пагинации: 1 ... 8 9 10
            pages = list(range(total_pages - max_visible_pages + 2, total_pages + 1))
            show_ellipsis = True
            pages.insert(0, 1)
        else:
            # Середина пагинации: 1 ... 4 5 6 ... 10
            pages = list(range(page - half_visible + 1, page + half_visible))
            show_ellipsis = True
            pages.insert(0, 1)
            pages.append(total_pages)
    
    def format_price(price):
        """Форматирует цену как строку с разделением тысяч"""
        if price is None:
            return "0 ₽"
        try:
            return f"{int(price):,}".replace(",", " ") + " ₽"
        except (ValueError, TypeError):
            return str(price) + " ₽"
    
    # Заявки на новые объявления (для второго таба)
    property_page_size = 6
    property_query = db.query(models.Request).filter(
        models.Request.type == "sell"
    ).options(
        joinedload(models.Request.user),
        joinedload(models.Request.property),
        joinedload(models.Request.property, models.Property.images)
    )
    
    property_total = property_query.count()
    property_offset = (property_page - 1) * property_page_size
    property_requests = property_query.order_by(desc(models.Request.created_at)).offset(property_offset).limit(property_page_size).all()
    
    # Обрабатываем данные для отображения объявлений
    property_request_list = []
    for req in property_requests:
        # Получаем основное изображение для объекта недвижимости
        property_image = None
        if req.property and req.property.images:
            main_images = [img for img in req.property.images if img.is_main]
            if main_images:
                property_image = main_images[0].url
            elif req.property.images:
                property_image = req.property.images[0].url
                
        property_request_list.append({
            "id": req.id,
            "status": req.status,
            "created_at": req.created_at.strftime("%d.%m.%Y, %H:%M"),
            "user": {
                "id": req.user.id,
                "name": f"{req.user.first_name} {req.user.last_name}",
                "phone": req.user.phone,
                "email": req.user.email
            } if req.user else None,
            "property": {
                "id": req.property.id,
                "title": req.property.title,
                "address": f"{req.property.address}, {req.property.city}",
                "price": format_price(req.property.price),
                "price_raw": req.property.price,
                "image": property_image or "/static/layout/assets/img/placeholder.jpg",
                "area": req.property.area
            } if req.property else None
        })
    
    # Пагинация для объявлений
    property_total_pages = (property_total + property_page_size - 1) // property_page_size if property_total > 0 else 1
    property_start_item = property_offset + 1 if property_requests else 0
    property_end_item = min(property_offset + property_page_size, property_total)
    
    # Формируем список отображаемых страниц
    property_pages = []
    
    if property_total_pages <= max_visible_pages:
        property_pages = list(range(1, property_total_pages + 1))
    else:
        half_visible = max_visible_pages // 2
        
        if property_page <= half_visible + 1:
            property_pages = list(range(1, max_visible_pages))
        elif property_page >= property_total_pages - half_visible:
            property_pages = list(range(property_total_pages - max_visible_pages + 2, property_total_pages + 1))
            property_pages.insert(0, 1)
        else:
            property_pages = list(range(property_page - half_visible + 1, property_page + half_visible))
            property_pages.insert(0, 1)
            property_pages.append(property_total_pages)
    
    # Получение статистики активности
    # Используем реальные данные из базы вместо случайных значений
    days_of_week = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())

    # Создаем словарь для хранения статистики по дням
    activity_stats = {}
    max_count = 1  # Избегаем деления на ноль

    # Заполняем словарь с нулевыми значениями
    for i, day in enumerate(days_of_week):
        activity_stats[day] = {"count": 0, "percentage": 0}

    # Получаем реальные данные по количеству модерации за последние 7 дней
    for i in range(7):
        day_date = start_of_week + timedelta(days=i)
        day_name = days_of_week[i]
        
        # Получаем количество обработанных заявок за этот день
        day_count = db.query(func.count(models.Request.id)).filter(
            func.date(models.Request.updated_at) == day_date,
            models.Request.status.in_(["completed", "rejected"])
        ).scalar() or 0
        
        activity_stats[day_name] = {"count": day_count}
        max_count = max(max_count, day_count)

    # Вычисляем проценты для отображения графика
    for day, data in activity_stats.items():
        data["percentage"] = int((data["count"] / max_count) * 100) if max_count > 0 else 0

    # Собираем метрики на основе реальных данных
    accepted_count = db.query(func.count(models.Request.id)).filter(
        models.Request.status == "completed"
    ).scalar() or 0

    rejected_count = db.query(func.count(models.Request.id)).filter(
        models.Request.status == "rejected"
    ).scalar() or 0

    pending_count = db.query(func.count(models.Request.id)).filter(
        models.Request.status.in_(["new", "processing"])
    ).scalar() or 0

    # Вычисляем среднее время обработки (если есть данные)
    avg_time_query = db.query(
        func.avg(
            func.unix_timestamp(models.Request.updated_at) - 
            func.unix_timestamp(models.Request.created_at)
        )
    ).filter(
        models.Request.status.in_(["completed", "rejected"])
    ).scalar()

    if avg_time_query:
        # Конвертируем секунды в часы и минуты
        avg_hours = int(avg_time_query // 3600)
        avg_minutes = int((avg_time_query % 3600) // 60)
        avg_processing_time = f"{avg_hours}ч {avg_minutes}мин"
    else:
        avg_processing_time = "—"

    # Данные для метрик
    metrics = {
        "accepted": accepted_count,
        "rejected": rejected_count,
        "pending": pending_count,
        "avg_time": avg_processing_time
    }
    
    return templates.TemplateResponse("admin/requests.html", {
        "request": request,
        "requests": request_list,
        "total_requests": total_requests,
        "current_page": page,
        "total_pages": total_pages,
        "pages": pages,
        "show_ellipsis": show_ellipsis if 'show_ellipsis' in locals() else False,
        "start_item": start_item,
        "end_item": end_item,
        "search_query": search or "",
        "status_filter": status or "",
        "request_type": request_type or "",
        "tour_requests_count": tour_requests_count,
        "listing_requests_count": new_prop_requests_count,
        "property_requests": property_request_list,
        "property_total": property_total,
        "property_current_page": property_page,
        "property_total_pages": property_total_pages,
        "property_pages": property_pages,
        "property_start_item": property_start_item,
        "property_end_item": property_end_item,
        "activity_stats": activity_stats,
        "efficiency": random.randint(70, 90),
        "avg_processing_time": avg_processing_time,
        "current_time": datetime.now().strftime("%H:%M"),
        "format_price": format_price,
        "metrics": metrics
    })

# Модель настроек приложения
class AppSettings:
    def __init__(self, **kwargs):
        # Настройки уведомлений
        self.email_new_properties = kwargs.get('email_new_properties', True)
        self.email_new_users = kwargs.get('email_new_users', True)
        self.push_notifications = kwargs.get('push_notifications', False)
        self.digest_frequency = kwargs.get('digest_frequency', 'weekly')
        # Настройки внешнего вида
        self.color_scheme = kwargs.get('color_scheme', 'orange')
        self.theme = kwargs.get('theme', 'light')
        self.compact_mode = kwargs.get('compact_mode', False)
        self.animations_enabled = kwargs.get('animations_enabled', True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'email_new_properties': self.email_new_properties,
            'email_new_users': self.email_new_users,
            'push_notifications': self.push_notifications,
            'digest_frequency': self.digest_frequency,
            'color_scheme': self.color_scheme,
            'theme': self.theme,
            'compact_mode': self.compact_mode,
            'animations_enabled': self.animations_enabled,
        }

# Функция получения настроек из БД или из файла
async def get_settings() -> Dict[str, Any]:
    # TODO: В будущем можно добавить получение из БД
    # Временно возвращаем дефолтные настройки
    settings_obj = AppSettings()
    return settings_obj.to_dict()

# API эндпоинты для настроек
@app.post("/api/v1/settings")
async def save_settings(request: Request):
    try:
        # Получаем JSON данные из запроса
        data = await request.json()
        
        # Проверяем наличие всех необходимых настроек
        allowed_fields = {
            'email_new_properties', 'email_new_users', 'push_notifications', 'digest_frequency',
            'color_scheme', 'theme', 'compact_mode', 'animations_enabled'
        }
        
        # Фильтруем только разрешенные поля
        filtered_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        # Создаем новый объект настроек
        settings_obj = AppSettings(**filtered_data)
        
        # TODO: Сохранение в БД
        # В этой версии просто сохраняем в сессию пользователя, 
        # в будущем можно переключиться на базу данных
        request.session['user_settings'] = settings_obj.to_dict()
        
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)})

@app.post("/api/v1/settings/reset")
async def reset_settings(request: Request):
    try:
        # TODO: Сброс настроек в БД
        # Создаем объект настроек с дефолтными значениями
        default_settings = AppSettings()
        
        # В этой версии просто сохраняем в сессию пользователя
        request.session['user_settings'] = default_settings.to_dict()
        
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)})

@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings(request: Request):
    # Получаем настройки из сессии пользователя или используем дефолтные
    settings_data = request.session.get('user_settings') or AppSettings().to_dict()
    return templates.TemplateResponse("admin/settings.html", {"request": request, "settings": settings_data})

@app.get("/admin/properties/export", response_class=FileResponse)
async def export_properties(
    request: Request,
    search: str = None,
    status: str = None,
    category: str = Query(None),
    db: Session = Depends(deps.get_db)
):
    # Используем тот же запрос, что и для отображения списка, но без пагинации
    query = db.query(models.Property).options(
        joinedload(models.Property.owner),
        joinedload(models.Property.images),
        joinedload(models.Property.categories)
    )
    
    # Применяем фильтры
    if search:
        query = query.filter(
            (models.Property.title.ilike(f"%{search}%")) |
            (models.Property.address.ilike(f"%{search}%")) |
            (models.Property.city.ilike(f"%{search}%")) |
            (models.Property.id.cast(String).like(f"%{search}%"))
        )
    
    if status:
        query = query.filter(models.Property.status == status)
    
    if category and category.strip() and category.isdigit():
        category_id = int(category)
        query = query.join(models.property_category).filter(
            models.property_category.c.category_id == category_id
        )
    
    # Получаем данные
    properties = query.order_by(desc(models.Property.created_at)).all()
    
    # Создаем DataFrame для экспорта
    data = []
    for prop in properties:
        status_display = {
            "active": "Активно",
            "pending": "На проверке",
            "draft": "Черновик",
            "rejected": "Отклонено",
            "sold": "Продано"
        }.get(prop.status.value, "Неизвестно")
        
        owner_name = f"{prop.owner.first_name} {prop.owner.last_name}" if prop.owner else "Неизвестно"
        
        # Получаем категории
        categories = ", ".join([cat.name for cat in prop.categories]) if prop.categories else ""
        
        data.append({
            "ID": prop.id,
            "Название": prop.title,
            "Адрес": f"{prop.address}, {prop.city}",
            "Цена": prop.price,
            "Площадь": prop.area,
            "Статус": status_display,
            "Владелец": owner_name,
            "Категории": categories,
            "Дата создания": prop.created_at.strftime("%d.%m.%Y"),
            "Есть 3D-тур": "Да" if prop.tour_360_url else "Нет"
        })
    
    # Создаем DataFrame
    df = pd.DataFrame(data)
    
    # Создаем директорию для временных файлов, если она не существует
    os.makedirs("static/temp", exist_ok=True)
    
    # Генерируем уникальное имя файла
    filename = f"properties_export_{uuid4().hex}.xlsx"
    filepath = f"static/temp/{filename}"
    
    # Сохраняем в Excel
    df.to_excel(filepath, index=False)
    
    # Возвращаем файл
    return FileResponse(
        path=filepath,
        filename="properties_export.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Функция для получения статистики активности по дням недели
def get_activity_stats():
    # В реальном приложении здесь был бы запрос к базе данных
    # Для демонстрации создаем словарь с днями недели и 
    # соответствующими значениями и процентами
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    
    # Создаем словарь с днями недели в качестве ключей
    stats = {}
    max_value = 30  # Для расчета процентов
    
    for day in days:
        count = random.randint(5, max_value)
        percentage = int((count / max_value) * 100)
        stats[day] = {
            "count": count,
            "percentage": percentage
        }
    
    return stats

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 