#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функциональности управления юридическими лицами.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from database import SessionLocal
from app.utils.security import get_password_hash

def test_company_creation():
    """Создание тестовой компании"""
    db = SessionLocal()
    
    try:
        # Создаем тестовую компанию
        company = User(
            email="test@company.com",
            phone="+996123456789",
            hashed_password=get_password_hash("password123"),
            full_name="Иван Петров",
            is_active=True,
            role=UserRole.COMPANY,
            company_name="Тестовая Компания ОсОО",
            company_number="123456789012",
            company_owner="Петров Иван Сергеевич",
            company_address="г. Бишкек, ул. Тестовая 1",
            company_description="Тестовая компания для проверки функциональности",
            company_logo_url="https://example.com/logo.png"
        )
        
        db.add(company)
        db.commit()
        
        print(f"✅ Тестовая компания создана с ID: {company.id}")
        print(f"📧 Email: {company.email}")
        print(f"🏢 Название: {company.company_name}")
        print(f"📄 ИНН: {company.company_number}")
        print(f"👤 Владелец: {company.company_owner}")
        
        return company.id
        
    except Exception as e:
        print(f"❌ Ошибка при создании компании: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def test_company_retrieval(company_id):
    """Проверка получения данных компании"""
    db = SessionLocal()
    
    try:
        company = db.query(User).filter(
            User.id == company_id,
            User.role == UserRole.COMPANY
        ).first()
        
        if company:
            print(f"\n✅ Компания найдена:")
            print(f"   ID: {company.id}")
            print(f"   Название: {company.company_name}")
            print(f"   Email: {company.email}")
            print(f"   Статус: {'Активна' if company.is_active else 'Заблокирована'}")
            return True
        else:
            print(f"❌ Компания с ID {company_id} не найдена")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при получении компании: {e}")
        return False
    finally:
        db.close()

def test_companies_listing():
    """Проверка списка компаний"""
    db = SessionLocal()
    
    try:
        companies = db.query(User).filter(User.role == UserRole.COMPANY).all()
        
        print(f"\n📋 Всего компаний в системе: {len(companies)}")
        
        for company in companies:
            print(f"   • {company.company_name} ({company.email})")
            
        return len(companies)
        
    except Exception as e:
        print(f"❌ Ошибка при получении списка компаний: {e}")
        return 0
    finally:
        db.close()

def cleanup_test_data():
    """Очистка тестовых данных"""
    db = SessionLocal()
    
    try:
        # Удаляем тестовые компании
        test_companies = db.query(User).filter(
            User.role == UserRole.COMPANY,
            User.email.like("%test%")
        ).all()
        
        for company in test_companies:
            print(f"🗑️ Удаляем тестовую компанию: {company.company_name}")
            db.delete(company)
        
        db.commit()
        print("✅ Тестовые данные очищены")
        
    except Exception as e:
        print(f"❌ Ошибка при очистке данных: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестирования функциональности компаний...")
    print("=" * 50)
    
    # Тест 1: Создание компании
    print("\n1️⃣ Тест создания компании")
    company_id = test_company_creation()
    
    if not company_id:
        print("❌ Тесты остановлены из-за ошибки создания")
        return
    
    # Тест 2: Получение данных компании
    print("\n2️⃣ Тест получения данных компании")
    if not test_company_retrieval(company_id):
        print("❌ Ошибка получения данных компании")
    
    # Тест 3: Список компаний
    print("\n3️⃣ Тест получения списка компаний")
    companies_count = test_companies_listing()
    
    # Очистка
    print("\n🧹 Очистка тестовых данных")
    cleanup_test_data()
    
    print("\n" + "=" * 50)
    print("✅ Тестирование завершено!")
    print(f"📊 Результаты: {companies_count} компаний обработано")

if __name__ == "__main__":
    main() 