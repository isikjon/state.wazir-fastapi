from typing import Any, List
from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException, Form
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session, joinedload
from app.api import deps
from app import models
from app.utils.panorama_processor import panorama_processor, PanoramaProcessor
from datetime import datetime
import json
import os
import logging
import tempfile
from pathlib import Path
from typing import Optional

# Настройка логирования с эмодзи для лучшей читаемости
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

async def check_admin_access(request: Request, db: Session):
    """Проверка доступа администратора"""
    logger.info("🔐 Проверка доступа администратора...")
    
    auth_token = request.cookies.get('access_token')
    if not auth_token:
        logger.warning("❌ Токен доступа не найден в cookies")
        return RedirectResponse('/admin/login', status_code=303)
    
    try:
        from jose import jwt
        from config import settings
        payload = jwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.debug(f"🔍 Payload токена: {payload}")
        
        if not payload.get("is_admin"):
            logger.warning("❌ Пользователь не является администратором")
            return RedirectResponse('/admin/login', status_code=303)
        
        # Получаем пользователя из базы данных
        user = db.query(models.User).filter(models.User.id == payload["sub"]).first()
        if not user:
            logger.error(f"❌ Пользователь с ID {payload['sub']} не найден в БД")
            return RedirectResponse('/admin/login', status_code=303)
        
        # Дополнительная проверка что пользователь действительно администратор
        if user.role != models.UserRole.ADMIN:
            logger.warning(f"❌ Пользователь {user.email} не является администратором (роль: {user.role})")
            return RedirectResponse('/admin/login', status_code=303)
        
        logger.info(f"✅ Администратор подтвержден: {user.email} (ID: {user.id})")
        return user
        
    except Exception as e:
        logger.error(f"💥 Ошибка проверки доступа: {str(e)}")
        return RedirectResponse('/admin/login', status_code=303)

@router.get("/admin/properties/{property_id}/360")
async def get_admin_panorama_info(
    property_id: int,
    request: Request,
    db: Session = Depends(deps.get_db)
):
    """Получение информации о панорамах для админки (новая система)"""
    logger.info(f"📊 Запрос информации о панорамах для свойства {property_id} (админка)")
    
    # Проверка доступа администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return user
    
    try:
        # Получение объявления с панорамами
        logger.debug(f"🔍 Поиск объявления с ID: {property_id}")
        property_obj = db.query(models.Property).options(
            joinedload(models.Property.panoramas)
        ).filter(models.Property.id == property_id).first()
        
        if not property_obj:
            logger.error(f"❌ Объявление с ID {property_id} не найдено")
            raise HTTPException(status_code=404, detail="Объявление не найдено")
        
        logger.debug(f"✅ Объявление найдено: {property_obj.title}")
        
        # Получаем панорамы
        panoramas = property_obj.panoramas if hasattr(property_obj, 'panoramas') else []
        
        # Формирование ответа с информацией о панорамах
        panorama_info = {
            "success": True,
            "has_360": bool(panoramas),
            "panoramas_count": len(panoramas),
            "panoramas": [p.to_dict() for p in panoramas] if panoramas else [],
            # Для обратной совместимости со старым API
            "tour_360_url": panoramas[0].url if panoramas and panoramas[0].url else None,
            "tour_360_file_id": panoramas[0].file_id if panoramas and panoramas[0].file_id else None,
            "tour_360_optimized_url": panoramas[0].optimized_url if panoramas and panoramas[0].optimized_url else None,
            "tour_360_uploaded_at": panoramas[0].uploaded_at.isoformat() if panoramas and panoramas[0].uploaded_at else None
        }
        
        logger.info(f"📋 Информация о {len(panoramas)} панорамах подготовлена для объявления {property_id}")
        
        return JSONResponse(content=panorama_info)
        
    except Exception as e:
        logger.error(f"💥 Ошибка получения информации о панорамах: {str(e)}")
        logger.exception("Полный стек ошибки:")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@router.post("/admin/properties/{property_id}/panoramas/upload")
async def upload_admin_property_panoramas(
    property_id: int,
    request: Request,
    files: List[UploadFile] = File(...),
    notes: List[str] = Form(default=[]),
    db: Session = Depends(deps.get_db)
):
    """Загрузка множественных панорам для недвижимости (админка)"""
    logger.info(f"📤 Загрузка {len(files)} панорам для свойства {property_id} (админка)")
    
    # Проверка доступа администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=403, content={"success": False, "error": "Доступ запрещен"})
    
    try:
        property_obj = db.query(models.Property).filter(models.Property.id == property_id).first()
        if not property_obj:
            return JSONResponse(status_code=404, content={"success": False, "error": "Объект недвижимости не найден"})
        
        if not files:
            return JSONResponse(status_code=400, content={"success": False, "error": "Не выбраны файлы для загрузки"})
        
        if len(files) > 10:
            return JSONResponse(status_code=400, content={"success": False, "error": "Максимум 10 панорам за одну загрузку"})
        
        uploaded_panoramas = []
        errors = []
        
        for i, file in enumerate(files):
            try:
                if not file.content_type or not file.content_type.startswith('image/'):
                    errors.append(f"Файл {file.filename}: должен быть изображением")
                    continue
                
                content = await file.read()
                file_size = len(content)
                await file.seek(0)
                
                if file_size > 300 * 1024 * 1024:  # 300 МБ
                    errors.append(f"Файл {file.filename}: превышает лимит 300 МБ")
                    continue
                
                result = await panorama_processor.upload_panorama(file, property_id)
                
                if not result.get("success"):
                    errors.append(f"Файл {file.filename}: {result.get('message', 'Ошибка загрузки')}")
                    continue
                
                panorama = models.PropertyPanorama(
                    property_id=property_id,
                    file_id=result['file_id'],
                    original_url=result['urls']['original'],
                    optimized_url=result['urls']['optimized'],
                    preview_url=result['urls']['preview'],
                    thumbnail_url=result['urls']['thumbnail'],
                    meta=json.dumps(result.get('metadata', {}), ensure_ascii=False),
                    uploaded_at=datetime.now(),
                    type="file",
                    notes=notes[i] if i < len(notes) else None
                )
                
                db.add(panorama)
                db.flush()
                
                uploaded_panoramas.append({
                    "id": panorama.id,
                    "file_id": result['file_id'],
                    "urls": result['urls'],
                    "metadata": result.get('metadata', {}),
                    "notes": panorama.notes,
                    "uploaded_at": panorama.uploaded_at.isoformat()
                })
                
            except Exception as e:
                errors.append(f"Файл {file.filename}: {str(e)}")
                continue
        
        db.commit()
        
        response_data = {
            "success": True,
            "message": f"Загружено {len(uploaded_panoramas)} панорам",
            "uploaded": uploaded_panoramas,
            "total_uploaded": len(uploaded_panoramas),
            "total_files": len(files)
        }
        
        if errors:
            response_data["errors"] = errors
            response_data["message"] += f", {len(errors)} ошибок"
        
        logger.info(f"✅ Загружено {len(uploaded_panoramas)} панорам для свойства {property_id}")
        return JSONResponse(content=response_data)
        
    except Exception as e:
        db.rollback()
        logger.error(f"💥 Ошибка при загрузке панорам: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"Ошибка сервера: {str(e)}"})

@router.post("/admin/properties/{property_id}/panoramas/url")
async def add_admin_property_panorama_url(
    property_id: int,
    request: Request,
    urls: List[str] = Form(...),
    notes: List[str] = Form(default=[]),
    db: Session = Depends(deps.get_db)
):
    """Добавление панорам по URL для недвижимости (админка)"""
    logger.info(f"🔗 Добавление {len(urls)} панорам по URL для свойства {property_id} (админка)")
    
    # Проверка доступа администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=403, content={"success": False, "error": "Доступ запрещен"})
    
    try:
        property_obj = db.query(models.Property).filter(models.Property.id == property_id).first()
        if not property_obj:
            return JSONResponse(status_code=404, content={"success": False, "error": "Объект недвижимости не найден"})
        
        if not urls:
            return JSONResponse(status_code=400, content={"success": False, "error": "Не указаны URL панорам"})
        
        if len(urls) > 10:
            return JSONResponse(status_code=400, content={"success": False, "error": "Максимум 10 панорам за одну операцию"})
        
        added_panoramas = []
        errors = []
        
        for i, url in enumerate(urls):
            try:
                if not url.strip():
                    continue
                
                panorama = models.PropertyPanorama(
                    property_id=property_id,
                    url=url.strip(),
                    type="url",
                    notes=notes[i] if i < len(notes) else None,
                    uploaded_at=datetime.now()
                )
                
                db.add(panorama)
                db.flush()
                
                added_panoramas.append({
                    "id": panorama.id,
                    "url": panorama.url,
                    "type": panorama.type,
                    "notes": panorama.notes,
                    "uploaded_at": panorama.uploaded_at.isoformat()
                })
                
            except Exception as e:
                errors.append(f"URL {url}: {str(e)}")
                continue
        
        db.commit()
        
        response_data = {
            "success": True,
            "message": f"Добавлено {len(added_panoramas)} панорам",
            "added": added_panoramas,
            "total_added": len(added_panoramas),
            "total_urls": len(urls)
        }
        
        if errors:
            response_data["errors"] = errors
            response_data["message"] += f", {len(errors)} ошибок"
        
        logger.info(f"✅ Добавлено {len(added_panoramas)} панорам по URL для свойства {property_id}")
        return JSONResponse(content=response_data)
        
    except Exception as e:
        db.rollback()
        logger.error(f"💥 Ошибка при добавлении панорам по URL: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"Ошибка сервера: {str(e)}"})

# API для удаления панорамы недвижимости
@router.delete("/admin/properties/{property_id}/panoramas/{panorama_id}")
async def delete_admin_property_panorama(
    property_id: int,
    panorama_id: int,
    request: Request,
    db: Session = Depends(deps.get_db)
):
    """Удаление панорамы недвижимости (админка)"""
    logger.info(f"🗑️ Удаление панорамы {panorama_id} для свойства {property_id} (админка)")
    
    # Проверка доступа администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=403, content={"success": False, "error": "Доступ запрещен"})
    
    try:
        # Находим панораму
        panorama = db.query(models.PropertyPanorama).filter(
            models.PropertyPanorama.id == panorama_id,
            models.PropertyPanorama.property_id == property_id
        ).first()
        
        if not panorama:
            return JSONResponse(status_code=404, content={"success": False, "error": "Панорама не найдена"})
        
        # Удаляем файлы с медиа-сервера, если есть file_id
        if panorama.file_id:
            try:
                # Здесь должна быть логика удаления файлов с медиа-сервера
                # await panorama_processor.delete_panorama_files(panorama.file_id, property_id)
                logger.info(f"Файлы панорамы {panorama.file_id} должны быть удалены с медиа-сервера")
            except Exception as e:
                logger.warning(f"Ошибка удаления файлов с медиа-сервера: {e}")
        
        # Удаляем запись из БД
        db.delete(panorama)
        db.commit()
        
        logger.info(f"✅ Панорама {panorama_id} успешно удалена")
        return JSONResponse(content={"success": True, "message": "Панорама успешно удалена"})
        
    except Exception as e:
        db.rollback()
        logger.error(f"💥 Ошибка при удалении панорамы: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"Ошибка сервера: {str(e)}"})

# API для удаления панорамы сервис-карты
@router.delete("/admin/service-cards/{card_id}/panoramas/{panorama_id}")
async def delete_admin_service_card_panorama(
    card_id: int,
    panorama_id: int,
    request: Request,
    db: Session = Depends(deps.get_db)
):
    """Удаление панорамы сервис-карты (админка)"""
    logger.info(f"🗑️ Удаление панорамы {panorama_id} для сервис-карты {card_id} (админка)")
    
    # Проверка доступа администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        return JSONResponse(status_code=403, content={"success": False, "error": "Доступ запрещен"})
    
    try:
        # Находим панораму
        panorama = db.query(models.ServiceCardPanorama).filter(
            models.ServiceCardPanorama.id == panorama_id,
            models.ServiceCardPanorama.service_card_id == card_id
        ).first()
        
        if not panorama:
            return JSONResponse(status_code=404, content={"success": False, "error": "Панорама не найдена"})
        
        # Удаляем файлы с медиа-сервера, если есть file_id
        if panorama.file_id:
            try:
                # Здесь должна быть логика удаления файлов с медиа-сервера
                # await panorama_processor.delete_panorama_files(panorama.file_id, card_id)
                logger.info(f"Файлы панорамы {panorama.file_id} должны быть удалены с медиа-сервера")
            except Exception as e:
                logger.warning(f"Ошибка удаления файлов с медиа-сервера: {e}")
        
        # Удаляем запись из БД
        db.delete(panorama)
        db.commit()
        
        logger.info(f"✅ Панорама {panorama_id} успешно удалена")
        return JSONResponse(content={"success": True, "message": "Панорама успешно удалена"})
        
    except Exception as e:
        db.rollback()
        logger.error(f"💥 Ошибка при удалении панорамы: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"Ошибка сервера: {str(e)}"})

# Для обратной совместимости - старый эндпоинт загрузки одной панорамы
@router.post("/admin/properties/{property_id}/360/upload")
async def upload_admin_panorama_legacy(
    property_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db)
):
    """Загрузка одной панорамы (для обратной совместимости)"""
    logger.info(f"📤 Загрузка панорамы для свойства {property_id} (legacy API)")
    
    # Перенаправляем на новый API
    return await upload_admin_property_panoramas(
        property_id=property_id,
        request=request,
        files=[file],
        notes=[],
        db=db
    )