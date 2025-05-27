from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app import models, schemas, services
from app.api import deps
from app.models.user import UserRole

router = APIRouter()

@router.post("/", response_model=schemas.Property)
def create_property(
    *,
    db: Session = Depends(deps.get_db),
    property_in: schemas.PropertyCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Создание нового объявления о недвижимости
    """
    # Логируем процесс создания объявления
    print(f"DEBUG: Создание нового объявления от пользователя {current_user.id}")
    print(f"DEBUG: Данные объявления: {property_in}")
    
    # Проверяем валидность данных
    if not property_in.category_ids or len(property_in.category_ids) == 0:
        print("DEBUG: Отсутствуют category_ids, устанавливаем значение по умолчанию [1]")
        property_in.category_ids = [1]  # По умолчанию - Продажа
        
    # Убедимся, что status имеет правильное значение из enum
    print(f"DEBUG: Статус объявления: {property_in.status}")
    
    # Проверяем наличие URL изображений
    if not property_in.photo_urls or len(property_in.photo_urls) == 0:
        print("DEBUG: Отсутствуют фотографии объявления")
        raise HTTPException(
            status_code=400,
            detail="Для создания объявления необходимо загрузить минимум 2 фотографии"
        )
    
    try:
        # Создаем объект недвижимости
        property = services.property.create_with_owner(
            db=db, obj_in=property_in, owner_id=current_user.id
        )
        print(f"DEBUG: Объявление успешно создано с ID {property.id}")
        print(f"DEBUG: Созданные изображения: {[img.url for img in property.images]}")
        
        # Вернем объект используя to_dict для правильной сериализации
        property_dict = property.to_dict()
        
        # Используем PropertyInDBBase для создания схемы Pydantic
        # с правильной структурой полей
        # Преобразуем модель Property в словарь
        property_dict = property.to_dict()
        
        # Создаем ответ напрямую без использования from_orm
        return {
            **property_dict,
            "categories": [{
                "id": cat.id,
                "name": cat.name,
                "description": cat.description
            } for cat in property.categories] if property.categories else [],
            "images": [{
                "id": img.id,
                "url": img.url,
                "is_main": img.is_main
            } for img in property.images] if property.images else [],
            # Обязательно добавляем owner как словарь
            "owner": property_dict.get("owner", {
                "id": property.owner.id,
                "email": property.owner.email,
                "full_name": property.owner.full_name,
                "is_active": property.owner.is_active,
                "role": str(property.owner.role) if hasattr(property.owner, "role") else None
            })
        }
    except Exception as e:
        print(f"ERROR: Ошибка при создании объявления: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании объявления: {str(e)}"
        )

@router.get("/", response_model=List[schemas.Property])
def read_properties(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Получение списка объявлений
    """
    properties = services.property.get_multi(db, skip=skip, limit=limit)
    return properties

@router.get("/my", response_model=List[schemas.Property])
def read_user_properties(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Получение объявлений текущего пользователя
    """
    properties = services.property.get_multi_by_owner(
        db=db, owner_id=current_user.id, skip=skip, limit=limit
    )
    return properties

# Модель для обновления данных 360° панорамы
class Property360Update(BaseModel):
    tour_360_url: str
    notes: Optional[str] = None

@router.get("/{property_id}/360", response_model=Property360Update)
def get_property_360(
    property_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Получение данных 360° панорамы для объявления
    """
    property = services.property.get(db=db, id=property_id)
    
    if not property:
        raise HTTPException(
            status_code=404,
            detail="Объявление не найдено"
        )
    
    # Проверяем права доступа (владелец или администратор)
    if property.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Недостаточно прав для просмотра данных 360° панорамы"
        )
    
    return {
        "tour_360_url": property.tour_360_url or "",
        "notes": property.notes or ""
    }

@router.post("/{property_id}/360", response_model=Property360Update)
def update_property_360(
    property_id: int,
    update_data: Property360Update,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Обновление данных 360° панорамы для объявления
    """
    print(f"DEBUG: Попытка обновления 360° для объявления {property_id}")
    print(f"DEBUG: Данные для обновления: {update_data}")
    print(f"DEBUG: Текущий пользователь: {current_user.id}, имя: {current_user.full_name}, роль: {current_user.role}")
    
    try:
        property = services.property.get(db=db, id=property_id)
        
        if not property:
            print(f"DEBUG: Объявление {property_id} не найдено")
            raise HTTPException(
                status_code=404,
                detail="Объявление не найдено"
            )
        
        print(f"DEBUG: Объявление найдено, ID: {property.id}, владелец: {property.owner_id}")
        
        # Проверяем права доступа (владелец или администратор)
        if property.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
            print(f"DEBUG: Недостаточно прав для обновления 360° панорамы, владелец: {property.owner_id}, текущий пользователь: {current_user.id}")
            raise HTTPException(
                status_code=403,
                detail="Недостаточно прав для обновления 360° панорамы"
            )
        
        print(f"DEBUG: Права доступа подтверждены, обновляем данные 360° панорамы")
        
        # Обновляем данные 360° панорамы
        property.tour_360_url = update_data.tour_360_url
        if update_data.notes:
            property.notes = update_data.notes
        
        db.commit()
        db.refresh(property)
        print(f"DEBUG: Данные 360° панорамы успешно обновлены, URL: {property.tour_360_url}")
    
    except HTTPException as http_ex:
        print(f"DEBUG: HTTPException: {http_ex.detail}, status_code: {http_ex.status_code}")
        raise
    except Exception as e:
        print(f"DEBUG: Неожиданная ошибка при обновлении 360° панорамы: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обновлении данных 360° панорамы: {str(e)}"
        )
    
    return {
        "tour_360_url": property.tour_360_url,
        "notes": property.notes
    }


@router.post("/{property_id}/approve", response_model=dict)
def approve_property(
    property_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Одобрение объявления администратором
    """
    print(f"DEBUG: Попытка одобрения объявления {property_id}")
    print(f"DEBUG: Текущий пользователь: {current_user.id}, имя: {current_user.full_name}, роль: {current_user.role}")
    
    try:
        # Проверяем права пользователя (только администратор может одобрять объявления)
        if current_user.role != UserRole.ADMIN:
            print(f"DEBUG: Недостаточно прав для одобрения объявления, роль пользователя: {current_user.role}")
            raise HTTPException(
                status_code=403,
                detail="Только администратор может одобрять объявления"
            )
        
        # Получаем объявление из базы данных
        property = services.property.get(db=db, id=property_id)
        
        if not property:
            print(f"DEBUG: Объявление {property_id} не найдено")
            raise HTTPException(
                status_code=404,
                detail="Объявление не найдено"
            )
        
        print(f"DEBUG: Объявление найдено, ID: {property.id}, статус: {property.status}")
        
        # Меняем статус объявления на "active" (активно/одобрено)
        property_data = {"status": "active"}
        updated_property = services.property.update(db=db, db_obj=property, obj_in=property_data)
        
        print(f"DEBUG: Объявление успешно одобрено, новый статус: {updated_property.status}")
        
        return {
            "success": True,
            "message": "Объявление успешно одобрено",
            "property_id": property_id
        }
        
    except HTTPException as http_ex:
        print(f"DEBUG: HTTPException: {http_ex.detail}, status_code: {http_ex.status_code}")
        raise
    except Exception as e:
        print(f"DEBUG: Неожиданная ошибка при одобрении объявления: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при одобрении объявления: {str(e)}"
        )
