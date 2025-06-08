#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для исправления отображения категорий и данных владельца в main.py
"""

import re

def fix_main_py():
    """Исправляет код в main.py"""
    
    # Читаем файл
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Добавляем category после views_count
    old_views = '"views_count": getattr(property, \'views_count\', 0),  # Безопасное получение значения'
    new_views = '"views_count": getattr(property, \'views_count\', 0),  # Безопасное получение значения\n        "category": db.query(models.Category).filter(models.Category.id == property.category_id).first() if property.category_id else None,'
    
    content = content.replace(old_views, new_views)
    
    # 2. Исправляем блок owner
    old_owner_block = '''        "owner": {
            "id": property.owner.id,
            "full_name": property.owner.full_name,
            "email": property.owner.email,
            "phone": property.owner.phone
        },'''
    
    new_owner_block = '''        "owner": {
            "id": property.owner.id,
            "full_name": property.owner.company_name if property.owner.role == models.UserRole.COMPANY else property.owner.full_name,
            "display_name": property.owner.company_name if property.owner.role == models.UserRole.COMPANY else property.owner.full_name,
            "company_name": property.owner.company_name if property.owner.role == models.UserRole.COMPANY else None,
            "logo_url": property.owner.company_logo_url if property.owner.role == models.UserRole.COMPANY else None,
            "email": property.owner.email,
            "phone": property.owner.phone,
            "is_company": property.owner.role == models.UserRole.COMPANY
        },'''
    
    content = content.replace(old_owner_block, new_owner_block)
    
    # Записываем файл обратно
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Файл main.py успешно обновлен!")
    print("✅ Добавлена поддержка категорий")
    print("✅ Исправлено отображение данных компаний")

if __name__ == "__main__":
    fix_main_py() 