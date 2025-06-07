#!/usr/bin/env python3
"""
Скрипт для создания первого суперадмина
Запуск: python create_superadmin.py
"""

import sys
import os

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.api.deps import get_db
from app import models
from app.utils.security import get_password_hash
import getpass

def create_superadmin():
    """Создает первого суперадмина"""
    
    print("=== Создание суперадминистратора ===")
    print()
    
    # Получаем сессию БД
    db = next(get_db())
    
    try:
        # Запрашиваем данные
        email = input("Email суперадмина (например, superadmin@wazir.kg): ").strip()
        if not email:
            print("Email обязателен!")
            return False
            
        # Проверяем, что пользователь с таким email не существует
        existing_user = db.query(models.User).filter(models.User.email == email).first()
        if existing_user:
            print(f"Пользователь с email {email} уже существует!")
            return False
        
        full_name = input("Полное имя (необязательно): ").strip()
        if not full_name:
            full_name = "SuperAdmin"
            
        phone = input("Телефон (необязательно): ").strip()
        
        # Запрашиваем пароль
        while True:
            password = getpass.getpass("Пароль: ")
            if len(password) < 6:
                print("Пароль должен содержать минимум 6 символов!")
                continue
                
            password_confirm = getpass.getpass("Подтвердите пароль: ")
            if password != password_confirm:
                print("Пароли не совпадают!")
                continue
                
            break
        
        # Создаем пользователя
        hashed_password = get_password_hash(password)
        
        superadmin = models.User(
            email=email,
            full_name=full_name,
            phone=phone,
            hashed_password=hashed_password,
            role=models.UserRole.ADMIN,  # Используем роль ADMIN (в реальном проекте создайте SUPERADMIN)
            is_active=True
        )
        
        db.add(superadmin)
        db.commit()
        db.refresh(superadmin)
        
        print()
        print("✅ Суперадминистратор создан успешно!")
        print(f"   Email: {email}")
        print(f"   ID: {superadmin.id}")
        print()
        print("Теперь вы можете войти в суперадмин-панель:")
        print("   http://localhost:8000/superadmin/login")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при создании суперадмина: {e}")
        db.rollback()
        return False
        
    finally:
        db.close()

def list_superadmins():
    """Показывает список всех суперадминов"""
    
    print("=== Список суперадминистраторов ===")
    print()
    
    db = next(get_db())
    
    try:
        # Получаем всех администраторов
        admins = db.query(models.User).filter(models.User.role == models.UserRole.ADMIN).all()
        
        if not admins:
            print("Суперадминистраторы не найдены.")
            return
            
        print(f"Найдено {len(admins)} администраторов:")
        print()
        
        for admin in admins:
            status = "✅ Активный" if admin.is_active else "❌ Заблокирован"
            print(f"ID: {admin.id}")
            print(f"Email: {admin.email}")
            print(f"Имя: {admin.full_name or 'Не указано'}")
            print(f"Телефон: {admin.phone or 'Не указан'}")
            print(f"Статус: {status}")
            print("-" * 40)
            
    except Exception as e:
        print(f"❌ Ошибка при получении списка: {e}")
        
    finally:
        db.close()

def main():
    """Главная функция"""
    
    print("Утилита управления суперадминистраторами")
    print("=" * 50)
    print()
    print("1. Создать нового суперадмина")
    print("2. Показать список суперадминов")
    print("3. Выход")
    print()
    
    while True:
        try:
            choice = input("Выберите действие (1-3): ").strip()
            
            if choice == "1":
                create_superadmin()
                break
            elif choice == "2":
                list_superadmins()
                break
            elif choice == "3":
                print("Выход...")
                break
            else:
                print("Неверный выбор! Введите 1, 2 или 3.")
                
        except KeyboardInterrupt:
            print("\n\nПрерывание выполнения...")
            break
        except EOFError:
            print("\n\nВыход...")
            break

if __name__ == "__main__":
    main() 