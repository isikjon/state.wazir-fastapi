from app.utils.address_cleaner import clean_plus_code_from_address, is_plus_code_in_address

def test_address_cleaner():
    """Тестируем функцию очистки Plus Codes из адресов"""
    
    print("🧪 ТЕСТИРОВАНИЕ ОЧИСТКИ Plus Codes")
    print("=" * 50)
    
    # Тестовые адреса с Plus Codes
    test_addresses = [
        "GQQV+2GJ, Ош, Кыргызстан",
        "GQPR+WX6, Ош, Кыргызстан", 
        "HQ5C+FCF, Ош, Кыргызстан",
        "HQ5C+7M9, Ош, Кыргызстан",
        "GQXM+8MF, Ош, Кыргызстан",
        "HQ7F+M3 Нариман, Кыргызстан",
        "HQ79+R47, Кызыл-Кыштак, Кыргызстан",
        "Обычный адрес без Plus Code",
        "ул. Ленина 123, Бишкек",
        "",
        None,
        "22C2+23, Каракол, Кыргызстан",
        "Бишкек, ул. Чуй 45"
    ]
    
    print("📋 Результаты очистки:")
    print()
    
    for i, address in enumerate(test_addresses, 1):
        if address is None:
            print(f"{i:2d}. None → None")
            continue
            
        has_plus_code = is_plus_code_in_address(address)
        cleaned = clean_plus_code_from_address(address)
        
        status = "🔄" if has_plus_code else "✅"
        print(f"{i:2d}. {status} '{address}' → '{cleaned}'")
    
    print("\n" + "=" * 50)
    print("✅ Тестирование завершено!")
    print("🔄 - адрес содержал Plus Code и был очищен")
    print("✅ - адрес не содержал Plus Code (оставлен без изменений)")

if __name__ == "__main__":
    test_address_cleaner() 