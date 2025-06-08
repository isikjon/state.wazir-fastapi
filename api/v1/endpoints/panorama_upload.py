from typing import Any
from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.api import deps
from app import models
from app.utils.panorama_processor import panorama_processor
from datetime import datetime
import json

router = APIRouter()

async def check_admin_access(request: Request, db: Session):
    """Проверка доступа администратора (копия из main.py)"""
    auth_token = request.cookies.get('access_token')
    if not auth_token:
        return RedirectResponse('/admin/login', status_code=303)
    
    try:
        from jose import jwt
        from config import settings
        payload = jwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        if not payload.get("is_admin"):
            return RedirectResponse('/admin/login', status_code=303)
        
        # Получаем пользователя из базы данных
        user = db.query(models.User).filter(models.User.id == payload["sub"]).first()
        return user
        
    except Exception as e:
        print(f"Ошибка проверки доступа админа: {e}")
        return RedirectResponse('/admin/login', status_code=303)

async def check_company_access(request: Request, db: Session):
    """Проверка доступа компании (копия из main.py)"""
    auth_token = request.cookies.get('access_token')
    if not auth_token:
        return None
    
    try:
        from jose import jwt
        from config import settings
        payload = jwt.decode(auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        if not payload.get("is_company"):
            return None
        
        # Получаем пользователя из базы данных
        user = db.query(models.User).filter(models.User.id == payload["sub"]).first()
        return user
        
    except Exception as e:
        print(f"Ошибка проверки доступа компании: {e}")
        return None

@router.post("/admin/properties/{property_id}/360/upload")
async def upload_admin_property_360_file(
    property_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db)
):
    """Загрузка 360° файла для админки"""
    # Проверяем доступ администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        raise HTTPException(status_code=401, detail="Доступ запрещен")
    
    try:
        # Получаем объявление
        property_obj = db.query(models.Property).filter(
            models.Property.id == property_id
        ).first()
        
        if not property_obj:
            raise HTTPException(status_code=404, detail="Объявление не найдено")
        
        # Обрабатываем файл панорамы
        result = await panorama_processor.process_panorama(file, property_id)
        
        if result["success"]:
            # Удаляем старые файлы, если есть
            if hasattr(property_obj, 'tour_360_file_id') and property_obj.tour_360_file_id:
                panorama_processor.delete_panorama_files(property_obj.tour_360_file_id, property_id)
            
            # Сохраняем информацию о новых файлах
            if hasattr(property_obj, 'tour_360_file_id'):
                property_obj.tour_360_file_id = result["file_id"]
            if hasattr(property_obj, 'tour_360_original_url'):
                property_obj.tour_360_original_url = result["urls"]["original"]
            if hasattr(property_obj, 'tour_360_optimized_url'):
                property_obj.tour_360_optimized_url = result["urls"]["optimized"]
            if hasattr(property_obj, 'tour_360_preview_url'):
                property_obj.tour_360_preview_url = result["urls"]["preview"]
            if hasattr(property_obj, 'tour_360_thumbnail_url'):
                property_obj.tour_360_thumbnail_url = result["urls"]["thumbnail"]
            if hasattr(property_obj, 'tour_360_metadata'):
                property_obj.tour_360_metadata = json.dumps(result["panorama_info"])
            if hasattr(property_obj, 'tour_360_uploaded_at'):
                property_obj.tour_360_uploaded_at = datetime.utcnow()
            
            db.commit()
            
            return {
                "success": True,
                "message": "360° панорама успешно загружена и обработана",
                "data": {
                    "file_id": result["file_id"],
                    "urls": result["urls"],
                    "panorama_info": result["panorama_info"]
                }
            }
        else:
            raise HTTPException(status_code=400, detail="Ошибка обработки файла")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Ошибка при загрузке 360° файла: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")

@router.post("/companies/properties/{property_id}/360/upload")
async def upload_company_property_360_file(
    property_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db)
):
    """Загрузка 360° файла для компаний"""
    # Проверяем доступ компании
    current_user = await check_company_access(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    try:
        # Проверяем что объявление принадлежит компании
        property_obj = db.query(models.Property).filter(
            models.Property.id == property_id,
            models.Property.owner_id == current_user.id
        ).first()
        
        if not property_obj:
            raise HTTPException(status_code=404, detail="Объявление не найдено")
        
        # Обрабатываем файл панорамы
        result = await panorama_processor.process_panorama(file, property_id)
        
        if result["success"]:
            # Удаляем старые файлы, если есть
            if hasattr(property_obj, 'tour_360_file_id') and property_obj.tour_360_file_id:
                panorama_processor.delete_panorama_files(property_obj.tour_360_file_id, property_id)
            
            # Сохраняем информацию о новых файлах
            if hasattr(property_obj, 'tour_360_file_id'):
                property_obj.tour_360_file_id = result["file_id"]
            if hasattr(property_obj, 'tour_360_original_url'):
                property_obj.tour_360_original_url = result["urls"]["original"]
            if hasattr(property_obj, 'tour_360_optimized_url'):
                property_obj.tour_360_optimized_url = result["urls"]["optimized"]
            if hasattr(property_obj, 'tour_360_preview_url'):
                property_obj.tour_360_preview_url = result["urls"]["preview"]
            if hasattr(property_obj, 'tour_360_thumbnail_url'):
                property_obj.tour_360_thumbnail_url = result["urls"]["thumbnail"]
            if hasattr(property_obj, 'tour_360_metadata'):
                property_obj.tour_360_metadata = json.dumps(result["panorama_info"])
            if hasattr(property_obj, 'tour_360_uploaded_at'):
                property_obj.tour_360_uploaded_at = datetime.utcnow()
            
            # Если объявление активно, отправляем на модерацию
            if property_obj.status == 'active':
                property_obj.status = 'pending'
                print(f"DEBUG: Объявление {property_id} отправлено на модерацию из-за загрузки новой 360° панорамы")
            
            db.commit()
            
            return {
                "success": True,
                "message": "360° панорама успешно загружена и обработана" + (" и отправлена на модерацию" if property_obj.status == 'pending' else ""),
                "data": {
                    "file_id": result["file_id"],
                    "urls": result["urls"],
                    "panorama_info": result["panorama_info"],
                    "status": property_obj.status
                }
            }
        else:
            raise HTTPException(status_code=400, detail="Ошибка обработки файла")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Ошибка при загрузке 360° файла: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")

@router.delete("/admin/properties/{property_id}/360")
async def delete_admin_property_360(
    property_id: int,
    request: Request,
    db: Session = Depends(deps.get_db)
):
    """Удаление 360° панорамы в админке"""
    # Проверяем доступ администратора
    user = await check_admin_access(request, db)
    if isinstance(user, RedirectResponse):
        raise HTTPException(status_code=401, detail="Доступ запрещен")
    
    try:
        # Получаем объявление
        property_obj = db.query(models.Property).filter(
            models.Property.id == property_id
        ).first()
        
        if not property_obj:
            raise HTTPException(status_code=404, detail="Объявление не найдено")
        
        # Удаляем файлы с диска
        if hasattr(property_obj, 'tour_360_file_id') and property_obj.tour_360_file_id:
            panorama_processor.delete_panorama_files(property_obj.tour_360_file_id, property_id)
        
        # Очищаем поля в базе данных
        if hasattr(property_obj, 'tour_360_file_id'):
            property_obj.tour_360_file_id = None
        if hasattr(property_obj, 'tour_360_original_url'):
            property_obj.tour_360_original_url = None
        if hasattr(property_obj, 'tour_360_optimized_url'):
            property_obj.tour_360_optimized_url = None
        if hasattr(property_obj, 'tour_360_preview_url'):
            property_obj.tour_360_preview_url = None
        if hasattr(property_obj, 'tour_360_thumbnail_url'):
            property_obj.tour_360_thumbnail_url = None
        if hasattr(property_obj, 'tour_360_metadata'):
            property_obj.tour_360_metadata = None
        if hasattr(property_obj, 'tour_360_uploaded_at'):
            property_obj.tour_360_uploaded_at = None
        if hasattr(property_obj, 'tour_360_url'):
            property_obj.tour_360_url = None  # Также очищаем старое поле URL
        
        db.commit()
        
        return {
            "success": True,
            "message": "360° панорама успешно удалена"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Ошибка при удалении 360° панорамы: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")

@router.delete("/companies/properties/{property_id}/360")
async def delete_company_property_360(
    property_id: int,
    request: Request,
    db: Session = Depends(deps.get_db)
):
    """Удаление 360° панорамы для компаний"""
    # Проверяем доступ компании
    current_user = await check_company_access(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    try:
        # Проверяем что объявление принадлежит компании
        property_obj = db.query(models.Property).filter(
            models.Property.id == property_id,
            models.Property.owner_id == current_user.id
        ).first()
        
        if not property_obj:
            raise HTTPException(status_code=404, detail="Объявление не найдено")
        
        # Удаляем файлы с диска
        if hasattr(property_obj, 'tour_360_file_id') and property_obj.tour_360_file_id:
            panorama_processor.delete_panorama_files(property_obj.tour_360_file_id, property_id)
        
        # Очищаем поля в базе данных
        if hasattr(property_obj, 'tour_360_file_id'):
            property_obj.tour_360_file_id = None
        if hasattr(property_obj, 'tour_360_original_url'):
            property_obj.tour_360_original_url = None
        if hasattr(property_obj, 'tour_360_optimized_url'):
            property_obj.tour_360_optimized_url = None
        if hasattr(property_obj, 'tour_360_preview_url'):
            property_obj.tour_360_preview_url = None
        if hasattr(property_obj, 'tour_360_thumbnail_url'):
            property_obj.tour_360_thumbnail_url = None
        if hasattr(property_obj, 'tour_360_metadata'):
            property_obj.tour_360_metadata = None
        if hasattr(property_obj, 'tour_360_uploaded_at'):
            property_obj.tour_360_uploaded_at = None
        if hasattr(property_obj, 'tour_360_url'):
            property_obj.tour_360_url = None  # Также очищаем старое поле URL
        
        db.commit()
        
        return {
            "success": True,
            "message": "360° панорама успешно удалена"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Ошибка при удалении 360° панорамы: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}") 