from typing import List, Optional, Dict, Any, Union

from sqlalchemy.orm import Session

from app.services.base import CRUDBase
from app.models.property import Property, Category, PropertyImage, Favorite
from app.schemas.property import PropertyCreate, PropertyUpdate, CategoryCreate, CategoryUpdate


class CRUDProperty(CRUDBase[Property, PropertyCreate, PropertyUpdate]):
    def create_with_owner(
        self, db: Session, *, obj_in: PropertyCreate, owner_id: int
    ) -> Property:
        obj_in_data = obj_in.dict(exclude={"category_ids"})
        db_obj = Property(**obj_in_data, owner_id=owner_id)
        
        # Добавляем категории к объекту
        if obj_in.category_ids:
            categories = db.query(Category).filter(Category.id.in_(obj_in.category_ids)).all()
            db_obj.categories = categories
            
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
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