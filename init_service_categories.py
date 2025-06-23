#!/usr/bin/env python3
"""
Скрипт для инициализации категорий сервисов по умолчанию
"""

import asyncio
from sqlalchemy.orm import Session
from database import SessionLocal
from app.models.service import ServiceCategory


def create_default_categories():
    """Создает категории сервисов по умолчанию"""
    
    # Список категорий по умолчанию
    default_categories = [
        {"title": "Поеси", "slug": "poesi"},
        {"title": "Медицина", "slug": "medicina"},
        {"title": "Магазины одежд", "slug": "magaziny-odezhd"},
        {"title": "Образования", "slug": "obrazovaniya"},
        {"title": "Развлечения", "slug": "razvlecheniya"},
        {"title": "Услуги", "slug": "uslugi"},
        {"title": "Спец.магазины", "slug": "spec-magaziny"},
        {"title": "Салон красоты", "slug": "salon-krasoty"},
        {"title": "Гостиницы", "slug": "gostinitsy"},
        {"title": "Комплекс услуг", "slug": "kompleks-uslug"},
        {"title": "Религия", "slug": "religiya"},
        {"title": "Спорт", "slug": "sport"},
        {"title": "Студии", "slug": "studii"},
        {"title": "Ремонт", "slug": "remont"},
        {"title": "Безопасность", "slug": "bezopasnost"},
        {"title": "Проч. товары", "slug": "proch-tovary"}
    ]
    
    db = SessionLocal()
    try:
        print("Создание категорий сервисов по умолчанию...")
        
        for category_data in default_categories:
            # Проверяем, не существует ли уже такая категория
            existing = db.query(ServiceCategory).filter(
                ServiceCategory.slug == category_data["slug"]
            ).first()
            
            if existing:
                print(f"  ⚠️  Категория '{category_data['title']}' уже существует, пропускаем")
                continue
            
            # Создаем новую категорию
            category = ServiceCategory(
                title=category_data["title"],
                slug=category_data["slug"],
                is_active=True
            )
            
            db.add(category)
            print(f"  ✅ Создана категория: {category_data['title']}")
        
        db.commit()
        print(f"\n🎉 Успешно создано категорий: {len(default_categories)}")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Ошибка при создании категорий: {str(e)}")
        raise
    finally:
        db.close()


def main():
    """Главная функция"""
    print("=" * 60)
    print("🚀 ИНИЦИАЛИЗАЦИЯ КАТЕГОРИЙ СЕРВИСОВ")
    print("=" * 60)
    
    try:
        create_default_categories()
        print("\n✨ Инициализация завершена успешно!")
        
    except Exception as e:
        print(f"\n💥 Ошибка инициализации: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 