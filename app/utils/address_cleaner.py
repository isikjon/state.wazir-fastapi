import re
import logging

logger = logging.getLogger(__name__)

def clean_plus_code_from_address(address: str) -> str:
    """
    Автоматически удаляет Plus Codes из адреса, оставляя только текстовую часть.
    Логирует каждое удаление Plus Code.
    
    Примеры:
    - "GQQV+2GJ, Ош, Кыргызстан" → "Ош, Кыргызстан"
    - "HQ7F+M3 Нариман, Кыргызстан" → "Нариман, Кыргызстан"
    - "Обычный адрес" → "Обычный адрес" (без изменений)
    """
    if not address or not isinstance(address, str):
        return address
    
    plus_code_pattern = r'^[23456789CFGHJMPQRVWX]{4,8}\+[23456789CFGHJMPQRVWX]{2,3}[, ]*'
    
    # Проверяем наличие Plus Code
    plus_code_match = re.search(r'^[23456789CFGHJMPQRVWX]{4,8}\+[23456789CFGHJMPQRVWX]{2,3}', address.strip())
    
    cleaned_address = re.sub(plus_code_pattern, '', address.strip())
    cleaned_address = cleaned_address.lstrip(' ,').strip()
    
    # Логируем удаление Plus Code
    if plus_code_match and cleaned_address != address.strip():
        plus_code = plus_code_match.group()
        logger.info(f"🔄 PLUS CODE УДАЛЕН: '{plus_code}' из '{address}' → '{cleaned_address}'")
        print(f"🔄 PLUS CODE УДАЛЕН: '{plus_code}' из '{address}' → '{cleaned_address}'")
    
    return cleaned_address if cleaned_address else address

def is_plus_code_in_address(address: str) -> bool:
    if not address or not isinstance(address, str):
        return False
    
    plus_code_pattern = r'[23456789CFGHJMPQRVWX]{4,8}\+[23456789CFGHJMPQRVWX]{2,3}'
    return bool(re.search(plus_code_pattern, address.strip())) 