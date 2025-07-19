from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api import deps
from app import models

router = APIRouter()

@router.get("/")
async def get_property_categories(db: Session = Depends(deps.get_db)):
    """Получение списка категорий недвижимости для форм"""
    try:
        # Получаем все категории из базы данных
        categories = db.query(models.Category).all()
        
        # Если категорий нет, создаем базовые
        if not categories:
            print("DEBUG: Категории не найдены, создаем базовые")
            basic_categories = [
                {"id": 1, "name": "Продажа", "description": "Продажа недвижимости"},
                {"id": 2, "name": "Аренда", "description": "Аренда недвижимости"},
                {"id": 3, "name": "Новостройки", "description": "Новые объекты недвижимости"},
                {"id": 4, "name": "Посуточная", "description": "Посуточная аренда"},
                {"id": 5, "name": "Коммерческая", "description": "Коммерческая недвижимость"},
                {"id": 6, "name": "Ипотека", "description": "Недвижимость в ипотеку"}
            ]
            
            for cat_data in basic_categories:
                category = models.Category(
                    id=cat_data["id"],
                    name=cat_data["name"],
                    description=cat_data["description"]
                )
                db.add(category)
            
            db.commit()
            categories = db.query(models.Category).all()
        
        # Возвращаем категории в формате для JavaScript
        return [
            {
                "id": category.id,
                "name": category.name,
                "description": category.description or ""
            }
            for category in categories
        ]
        
    except Exception as e:
        print(f"DEBUG: Ошибка получения категорий: {e}")
        # Возвращаем заглушки если что-то пошло не так
        return [
            {"id": 1, "name": "Продажа", "description": "Продажа недвижимости"},
            {"id": 2, "name": "Аренда", "description": "Аренда недвижимости"},
            {"id": 3, "name": "Новостройки", "description": "Новые объекты недвижимости"},
            {"id": 4, "name": "Посуточная", "description": "Посуточная аренда"},
            {"id": 5, "name": "Коммерческая", "description": "Коммерческая недвижимость"},
            {"id": 6, "name": "Ипотека", "description": "Недвижимость в ипотеку"}
        ] 