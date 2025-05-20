from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.property import PropertyStatus


class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CategoryBase):
    name: Optional[str] = None


class CategoryInDBBase(CategoryBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class Category(CategoryInDBBase):
    pass


class PropertyImageBase(BaseModel):
    url: str
    is_main: Optional[bool] = False


class PropertyImageCreate(PropertyImageBase):
    pass


class PropertyImageUpdate(PropertyImageBase):
    url: Optional[str] = None


class PropertyImageInDBBase(PropertyImageBase):
    id: int
    property_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class PropertyImage(PropertyImageInDBBase):
    pass


class PropertyBase(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    address: str
    city: str
    area: float
    status: Optional[PropertyStatus] = PropertyStatus.DRAFT
    is_featured: Optional[bool] = False
    tour_360_url: Optional[str] = None


class PropertyCreate(PropertyBase):
    category_ids: List[int]


class PropertyUpdate(PropertyBase):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    address: Optional[str] = None
    city: Optional[str] = None
    area: Optional[float] = None
    category_ids: Optional[List[int]] = None


class PropertyInDBBase(PropertyBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class PropertyInDB(PropertyInDBBase):
    pass


class Property(PropertyInDBBase):
    categories: List[Category] = []
    images: List[PropertyImage] = []
    owner: Dict[str, Any]


class FavoriteBase(BaseModel):
    property_id: int


class FavoriteCreate(FavoriteBase):
    pass


class FavoriteInDBBase(FavoriteBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class Favorite(FavoriteInDBBase):
    property: Property 