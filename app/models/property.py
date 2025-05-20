from sqlalchemy import Column, String, Integer, Boolean, Float, ForeignKey, Text, Enum, Table
from sqlalchemy.orm import relationship
from database import Base
from .base import TimestampMixin
import enum


class PropertyStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"
    SOLD = "sold"


property_category = Table(
    "property_category",
    Base.metadata,
    Column("property_id", Integer, ForeignKey("properties.id")),
    Column("category_id", Integer, ForeignKey("categories.id"))
)


class Property(Base, TimestampMixin):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    description = Column(Text)
    price = Column(Float)
    address = Column(String(255))
    city = Column(String(100))
    area = Column(Float)
    status = Column(Enum(PropertyStatus), default=PropertyStatus.DRAFT)
    is_featured = Column(Boolean, default=False)
    tour_360_url = Column(String(255), nullable=True)
    
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="properties")
    
    categories = relationship("Category", secondary=property_category, back_populates="properties")
    images = relationship("PropertyImage", back_populates="property")
    favorites = relationship("Favorite", back_populates="property")


class PropertyImage(Base, TimestampMixin):
    __tablename__ = "property_images"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(255))
    is_main = Column(Boolean, default=False)
    
    property_id = Column(Integer, ForeignKey("properties.id"))
    property = relationship("Property", back_populates="images")


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True)
    description = Column(String(255), nullable=True)
    
    properties = relationship("Property", secondary=property_category, back_populates="categories")


class Favorite(Base, TimestampMixin):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    
    user_id = Column(Integer, ForeignKey("users.id"))
    property_id = Column(Integer, ForeignKey("properties.id"))
    
    user = relationship("User", back_populates="favorites")
    property = relationship("Property", back_populates="favorites") 