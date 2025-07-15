from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from database import Base
from .base import TimestampMixin


class ServiceCategory(Base, TimestampMixin):
    """Модель для категорий сервисов"""
    __tablename__ = "service_categories"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)  # Название категории
    slug = Column(String(255), unique=True, nullable=False, index=True)  # URL-слаг для категории
    is_active = Column(Boolean, default=True)  # Активна ли категория
    
    # Связь с карточками заведений
    service_cards = relationship("ServiceCard", back_populates="category")


class ServiceCardPanorama(Base, TimestampMixin):
    __tablename__ = "service_card_panoramas"
    id = Column(Integer, primary_key=True, index=True)
    service_card_id = Column(Integer, ForeignKey("service_cards.id"))
    url = Column(String(255), nullable=True)
    file_id = Column(String(100), nullable=True)
    original_url = Column(String(255), nullable=True)
    optimized_url = Column(String(255), nullable=True)
    preview_url = Column(String(255), nullable=True)
    thumbnail_url = Column(String(255), nullable=True)
    metadata = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, nullable=True)
    type = Column(String(20), default="file")
    notes = Column(String(255), nullable=True)


class ServiceCard(Base, TimestampMixin):
    """Модель для карточек заведений в сервисах"""
    __tablename__ = "service_cards"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)  # Название заведения
    description = Column(Text, nullable=True)  # Описание заведения
    address = Column(String(255), nullable=True)  # Адрес заведения
    phone = Column(String(50), nullable=True)  # Телефон
    email = Column(String(255), nullable=True)  # Email
    website = Column(String(255), nullable=True)  # Веб-сайт
    image_url = Column(String(255), nullable=True)  # Основное изображение (для совместимости)
    is_active = Column(Boolean, default=True)  # Активна ли карточка
    
    # Координаты заведения
    latitude = Column(Float, nullable=True)  # Широта
    longitude = Column(Float, nullable=True)  # Долгота
    
    # Поля для системы изображений
    photos_uploaded_at = Column(DateTime, nullable=True)  # Дата последней загрузки фотографий
    
    # Связь с категорией
    category_id = Column(Integer, ForeignKey("service_categories.id"), nullable=False)
    category = relationship("ServiceCategory", back_populates="service_cards")
    
    # Связь с изображениями
    images = relationship("ServiceCardImage", back_populates="service_card", cascade="all, delete-orphan")
    panoramas = relationship("ServiceCardPanorama", backref="service_card", cascade="all, delete-orphan") 