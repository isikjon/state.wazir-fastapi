from typing import List, Optional, Dict, Any, Union

from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder  # Исправленный импорт, теперь из FastAPI

from app.services.base import CRUDBase
from app.models.property import Property, Category, PropertyImage, Favorite, PropertyCategory
from app.schemas.property import PropertyCreate, PropertyUpdate, CategoryCreate, CategoryUpdate

class CRUDProperty(CRUDBase[Property, PropertyCreate, PropertyUpdate]):
    def create_with_owner(
        self, db: Session, *, obj_in: PropertyCreate, owner_id: int
    ) -> Property:
        # Извлекаем URL-адреса изображений перед созданием объекта недвижимости
        photo_urls = obj_in.photo_urls if obj_in.photo_urls else []
        
        # Извлекаем категории перед созданием объекта недвижимости
        category_ids = obj_in.category_ids if obj_in.category_ids else []
        
        # Проверяем и создаем категории, если они отсутствуют
        self._ensure_categories_exist(db)
        
        # Создаем объект данных, исключая photo_urls и category_ids
        obj_in_data = jsonable_encoder(obj_in, exclude={"photo_urls", "category_ids"})
        db_obj = Property(**obj_in_data, owner_id=owner_id)
        
        # Сохраняем объект в базе данных
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        # Добавляем категории
        for category_id in category_ids:
            property_category = PropertyCategory(property_id=db_obj.id, category_id=category_id)
            db.add(property_category)
        
        # Добавляем изображения
        for i, url in enumerate(photo_urls):
            is_main = i == 0  # Первое изображение будет главным
            property_image = PropertyImage(property_id=db_obj.id, url=url, is_main=is_main)
            db.add(property_image)
        
        db.commit()
        db.refresh(db_obj)
        return db_obj
        
    def _ensure_categories_exist(self, db: Session):
        """Проверяет и создает базовые категории, если они отсутствуют"""
        # Проверяем категорию с ID 1 (Продажа)
        category1 = db.query(Category).filter(Category.id == 1).first()
        if not category1:
            print("DEBUG: Создание категории 'Продажа' с ID 1")
            category1 = Category(
                id=1, 
                name="Продажа", 
                description="Объекты недвижимости для продажи"
            )
            db.add(category1)
        
        # Проверяем категорию с ID 2 (Аренда)
        category2 = db.query(Category).filter(Category.id == 2).first()
        if not category2:
            print("DEBUG: Создание категории 'Аренда' с ID 2")
            category2 = Category(
                id=2, 
                name="Аренда", 
                description="Объекты недвижимости для аренды"
            )
            db.add(category2)
        
        # Сохраняем изменения, если были созданы новые категории
        if not category1 or not category2:
            db.commit()
    
    def get_multi_by_owner(
        self, db: Session, *, owner_id: int, skip: int = 0, limit: int = 100
    ) -> List[Property]:
        return (
            db.query(self.model)
            .filter(Property.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def update_property_categories(
        self, db: Session, *, db_obj: Property, category_ids: List[int]
    ) -> Property:
        # Удаляем существующие связи
        db.query(PropertyCategory).filter(PropertyCategory.property_id == db_obj.id).delete()
        
        # Создаем новые связи
        for category_id in category_ids:
            property_category = PropertyCategory(property_id=db_obj.id, category_id=category_id)
            db.add(property_category)
        
        # Для обратной совместимости также обновляем и через отношение many-to-many
        categories = db.query(Category).filter(Category.id.in_(category_ids)).all()
        db_obj.categories = categories
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


class CRUDCategory(CRUDBase[Category, CategoryCreate, CategoryUpdate]):
    def get_by_name(self, db: Session, *, name: str) -> Optional[Category]:
        return db.query(Category).filter(Category.name == name).first()


class CRUDPropertyImage(CRUDBase[PropertyImage, Any, Any]):
    def create_property_image(
        self, db: Session, *, url: str, property_id: int, is_main: bool = False
    ) -> PropertyImage:
        db_obj = PropertyImage(url=url, property_id=property_id, is_main=is_main)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_property_images(
        self, db: Session, *, property_id: int
    ) -> List[PropertyImage]:
        return db.query(PropertyImage).filter(PropertyImage.property_id == property_id).all()


class CRUDFavorite(CRUDBase[Favorite, Any, Any]):
    def create_favorite(
        self, db: Session, *, user_id: int, property_id: int
    ) -> Favorite:
        db_obj = Favorite(user_id=user_id, property_id=property_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_user_favorites(
        self, db: Session, *, user_id: int
    ) -> List[Favorite]:
        return db.query(Favorite).filter(Favorite.user_id == user_id).all()
    
    def is_favorite(
        self, db: Session, *, user_id: int, property_id: int
    ) -> bool:
        return db.query(Favorite).filter(
            Favorite.user_id == user_id, 
            Favorite.property_id == property_id
        ).first() is not None
    
    def remove_favorite(
        self, db: Session, *, user_id: int, property_id: int
    ) -> None:
        db_obj = db.query(Favorite).filter(
            Favorite.user_id == user_id,
            Favorite.property_id == property_id
        ).first()
        if db_obj:
            db.delete(db_obj)
            db.commit()


property = CRUDProperty(Property)
category = CRUDCategory(Category)
property_image = CRUDPropertyImage(PropertyImage)
favorite = CRUDFavorite(Favorite) 