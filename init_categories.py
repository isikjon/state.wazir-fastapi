#!/usr/bin/env python3
"""
Скрипт для инициализации категорий недвижимости в базе данных
"""

from sqlalchemy.orm import Session
from database import SessionLocal, engine
from app.models import Category

def init_categories():
    """Инициализация категорий недвижимости"""
    db = SessionLocal()
    
    try:
        # Проверяем, есть ли уже категории
        existing_categories = db.query(Category).count()
        if existing_categories > 0:
            print(f"Категории уже существуют ({existing_categories} шт.). Пропускаем инициализацию.")
            return
        
        # Базовые категории недвижимости
        categories = [
            {"name": "Продажа", "description": "Продажа недвижимости"},
            {"name": "Аренда", "description": "Аренда недвижимости"},
            {"name": "Новостройки", "description": "Новые жилые комплексы"},
            {"name": "Коммерческая", "description": "Коммерческая недвижимость"},
            {"name": "Ипотека", "description": "Недвижимость под ипотеку"},
        ]
        
        # Создаем категории
        for cat_data in categories:
            category = Category(
                name=cat_data["name"],
                description=cat_data["description"]
            )
            db.add(category)
        
        db.commit()
        print(f"✅ Создано {len(categories)} категорий:")
        for cat in categories:
            print(f"   - {cat['name']}: {cat['description']}")
            
    except Exception as e:
        print(f"❌ Ошибка при создании категорий: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🏗️  Инициализация категорий недвижимости...")
    init_categories()
    print("✅ Инициализация завершена!") 