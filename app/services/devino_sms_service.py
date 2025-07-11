import httpx
import logging
import random
import string
from typing import Dict, Any, Optional, Tuple
from app.core.config import settings

# Создаем цветной логгер для Devino SMS
logger = logging.getLogger("devino_sms")
logger.setLevel(logging.DEBUG)

class ColoredFormatter(logging.Formatter):
    """Форматтер с цветами для консоли"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Голубой
        'INFO': '\033[32m',     # Зеленый  
        'WARNING': '\033[33m',  # Желтый
        'ERROR': '\033[31m',    # Красный
        'CRITICAL': '\033[35m', # Пурпурный
        'RESET': '\033[0m'      # Сброс цвета
    }

    def format(self, record):
        # Добавляем цвет к уровню логирования
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset_color = self.COLORS['RESET']
        
        # Форматируем сообщение
        record.levelname = f"{log_color}{record.levelname}{reset_color}"
        return super().format(record)

# Настраиваем обработчик консоли
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = ColoredFormatter(
    '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
console_handler.setFormatter(formatter)

# Добавляем обработчик если еще не добавлен
if not logger.handlers:
    logger.addHandler(console_handler)

# Отключаем наследование от root logger чтобы избежать дублирования
logger.propagate = False

class DevinoSMSService:
    """Сервис для работы с SMS через Devino 2FA API"""
    
    def __init__(self):
        """Инициализация сервиса"""
        self.api_key = settings.DEVINO_API_KEY
        self.api_url = settings.DEVINO_API_URL or "https://phoneverification.devinotele.com"
        self.debug_mode = not self.api_key or self.api_key == "your_api_key_here"
        
        logger.info("============================================================")
        logger.info("🔧 DEVINO SMS SERVICE INITIALIZATION")
        logger.info("============================================================")
        
        if self.debug_mode:
            logger.warning("⚠️  DEBUG MODE: API Key not configured properly")
            logger.info(f"📍 Using base URL: {self.api_url}")
        else:
            logger.info("✅ Production mode active")
            logger.info(f"🔑 API Key configured: {self.api_key[:8]}...{self.api_key[-4:]}")
            logger.info(f"📍 Using base URL: {self.api_url}")
        
        logger.info("============================================================")

    def _normalize_phone(self, phone: str) -> str:
        """
        Нормализация номера телефона для Кыргызстана
        
        Args:
            phone: Номер телефона в любом формате
            
        Returns:
            str: Нормализованный номер без знака +
        """
        logger.debug(f"📱 Normalizing phone: '{phone}'")
        
        # Убираем все лишние символы
        clean_phone = ''.join(filter(str.isdigit, phone))
        
        # Если номер начинается с 8, заменяем на 7 (для России)
        if clean_phone.startswith('8') and len(clean_phone) == 11:
            clean_phone = '7' + clean_phone[1:]
        
        # Если номер начинается с 00, убираем
        if clean_phone.startswith('00'):
            clean_phone = clean_phone[2:]
        
        # Если номер не содержит код страны, добавляем код Кыргызстана
        if len(clean_phone) == 9 and clean_phone.startswith('2'):
            clean_phone = '996' + clean_phone
        elif len(clean_phone) == 9 and clean_phone.startswith(('5', '7', '9')):
            clean_phone = '996' + clean_phone
        
        logger.info(f"📱 Phone normalized: '{phone}' → '{clean_phone}'")
        return clean_phone

    def _generate_code(self, length: int = 4) -> str:
        """Генерация случайного SMS кода"""
        return ''.join(random.choices(string.digits, k=length))

    async def send_sms_code(self, phone: str, code: Optional[str] = None) -> Dict[str, Any]:
        """
        Отправка SMS кода через Devino 2FA API
        
        Args:
            phone: Номер телефона
            code: SMS код (если не указан, будет сгенерирован автоматически)
            
        Returns:
            Dict[str, Any]: Результат отправки
        """
        logger.info("============================================================")
        logger.info("🚀 SENDING SMS CODE via DEVINO 2FA API")
        logger.info("============================================================")
        
        try:
            # Шаг 1: Нормализация номера
            logger.info("📍 Step 1: Phone normalization")
            normalized_phone = self._normalize_phone(phone)
            
            # Шаг 2: Подготовка payload
            logger.info("📍 Step 2: Building request payload")
            payload = {
                "DestinationNumber": normalized_phone
            }
            
            # Добавляем код если указан
            if code:
                payload["SMSCode"] = code
                logger.debug(f"📦 Custom SMS code provided: {code}")
            else:
                logger.debug("📦 SMS code will be auto-generated by Devino")
            
            logger.debug(f"📦 Request payload: {payload}")
            
            # DEBUG режим
            if self.debug_mode:
                logger.warning("🔧 DEBUG MODE: Simulating SMS send")
                generated_code = code or self._generate_code()
                logger.info(f"📱 Phone: {normalized_phone}")
                logger.info(f"📝 Generated code: {generated_code}")
                return {
                    'success': True,
                    'message': 'SMS отправлена (DEBUG режим)',
                    'code': generated_code,
                    'phone': normalized_phone,
                    'debug': True
                }
            
            # Шаг 3: Подготовка HTTP запроса
            logger.info("📍 Step 3: Preparing HTTP request")
            logger.debug("🔧 Building request headers")
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Wazir-FastAPI/1.0",
                "X-ApiKey": self.api_key
            }
            
            logger.debug("✅ X-ApiKey header added")
            logger.debug(f"📋 Headers ready: {list(headers.keys())}")
            
            url = f"{self.api_url}/GenerateCode"
            logger.info(f"🌐 Target URL: {url}")
            
            # Шаг 4: Отправка запроса
            logger.info("📍 Step 4: Sending HTTP request")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.debug("🔌 HTTP client created with 30s timeout")
                
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers
                )
                
                logger.info(f"⏱️  Request completed in {response.elapsed.total_seconds():.2f}s")
                
                # Шаг 5: Обработка ответа
                logger.info("📍 Step 5: Processing response")
                logger.info(f"📨 HTTP Status: {response.status_code}")
                logger.debug(f"📨 Response headers: {dict(response.headers)}")
                
                try:
                    response_data = response.json()
                    logger.debug(f"📨 Raw response: {response_data}")
                except Exception as e:
                    logger.error(f"❌ Failed to parse JSON response: {e}")
                    logger.debug(f"📨 Raw response text: {response.text}")
                    response_data = {"error": "Invalid JSON response"}
                
                if response.status_code == 200:
                    # Успешный ответ
                    logger.info("✅ SMS code sent successfully")
                    return {
                        'success': True,
                        'message': 'SMS код отправлен успешно',
                        'phone': normalized_phone,
                        'response': response_data
                    }
                else:
                    # Ошибка HTTP
                    logger.error(f"❌ HTTP error {response.status_code}")
                    logger.error(f"❌ Response: {response_data}")
                    return {
                        'success': False,
                        'error': f'HTTP error: {response_data}'
                    }
                    
        except httpx.TimeoutException:
            logger.error("⏰ Request timeout (30s)")
            return {
                'success': False,
                'error': 'Таймаут запроса к Devino API'
            }
        except Exception as e:
            logger.error(f"💥 Unexpected error: {str(e)}")
            return {
                'success': False,
                'error': f'Ошибка отправки SMS: {str(e)}'
            }
        finally:
            logger.info("============================================================")

    async def verify_sms_code(self, phone: str, code: str) -> Dict[str, Any]:
        """
        Проверка SMS кода через Devino 2FA API
        
        Args:
            phone: Номер телефона
            code: Код для проверки
            
        Returns:
            Dict[str, Any]: Результат проверки
        """
        logger.info("============================================================")
        logger.info("🔍 VERIFYING SMS CODE via DEVINO 2FA API")
        logger.info("============================================================")
        
        try:
            # Шаг 1: Нормализация номера
            logger.info("📍 Step 1: Phone normalization")
            normalized_phone = self._normalize_phone(phone)
            
            # Шаг 2: Подготовка payload
            logger.info("📍 Step 2: Building request payload")
            payload = {
                "DestinationNumber": normalized_phone,
                "Code": code
            }
            
            logger.debug(f"📦 Request payload: {payload}")
            
            # DEBUG режим
            if self.debug_mode:
                logger.warning("🔧 DEBUG MODE: Simulating code verification")
                # В DEBUG режиме принимаем коды 1234, 0000, или последние 4 цифры номера
                valid_codes = ['1234', '0000', normalized_phone[-4:]]
                is_valid = code in valid_codes
                
                logger.info(f"📱 Phone: {normalized_phone}")
                logger.info(f"📝 Code to verify: {code}")
                logger.info(f"✅ Valid codes: {valid_codes}")
                logger.info(f"🎯 Verification result: {'VALID' if is_valid else 'INVALID'}")
                
                return {
                    'success': True,
                    'valid': is_valid,
                    'message': 'Код проверен (DEBUG режим)',
                    'phone': normalized_phone,
                    'debug': True
                }
            
            # Шаг 3: Подготовка HTTP запроса
            logger.info("📍 Step 3: Preparing HTTP request")
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json", 
                "User-Agent": "Wazir-FastAPI/1.0",
                "X-ApiKey": self.api_key
            }
            
            url = f"{self.api_url}/CheckCode"
            logger.info(f"🌐 Target URL: {url}")
            
            # Шаг 4: Отправка запроса
            logger.info("📍 Step 4: Sending HTTP request")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.debug("🔌 HTTP client created with 30s timeout")
                
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers
                )
                
                logger.info(f"⏱️  Request completed in {response.elapsed.total_seconds():.2f}s")
                
                # Шаг 5: Обработка ответа
                logger.info("📍 Step 5: Processing response")
                logger.info(f"📨 HTTP Status: {response.status_code}")
                
                try:
                    response_data = response.json()
                    logger.debug(f"📨 Raw response: {response_data}")
                except Exception as e:
                    logger.error(f"❌ Failed to parse JSON response: {e}")
                    response_data = {"error": "Invalid JSON response"}
                
                if response.status_code == 200:
                    # Проверяем код ответа от Devino
                    result_code = response_data.get('Code', -1)
                    if result_code == 0:
                        logger.info("✅ SMS code verified successfully")
                        return {
                            'success': True,
                            'valid': True,
                            'message': 'Код подтвержден успешно',
                            'phone': normalized_phone,
                            'response': response_data
                        }
                    else:
                        logger.warning(f"⚠️  Code verification failed: {response_data}")
                        return {
                            'success': True,
                            'valid': False,
                            'message': 'Неверный код подтверждения',
                            'phone': normalized_phone,
                            'response': response_data
                        }
                else:
                    # Ошибка HTTP
                    logger.error(f"❌ HTTP error {response.status_code}")
                    logger.error(f"❌ Response: {response_data}")
                    return {
                        'success': False,
                        'error': f'HTTP error: {response_data}'
                    }
                    
        except httpx.TimeoutException:
            logger.error("⏰ Request timeout (30s)")
            return {
                'success': False,
                'error': 'Таймаут запроса к Devino API'
            }
        except Exception as e:
            logger.error(f"💥 Unexpected error: {str(e)}")
            return {
                'success': False,
                'error': f'Ошибка проверки SMS: {str(e)}'
            }
        finally:
            logger.info("============================================================")

    async def get_balance(self) -> Dict[str, Any]:
        """
        Получение баланса (если доступно в API)
        
        Returns:
            Dict[str, Any]: Информация о балансе
        """
        logger.info("============================================================")
        logger.info("💰 CHECKING BALANCE via DEVINO API")
        logger.info("============================================================")
        
        if self.debug_mode:
            logger.warning("🔧 DEBUG MODE: Simulating balance check")
            return {
                'success': True,
                'balance': 1000.00,
                'currency': 'RUB',
                'debug': True
            }
        
        # В документации не вижу эндпоинта для баланса, возвращаем заглушку
        logger.warning("⚠️  Balance endpoint not available in Devino 2FA API")
        return {
            'success': False,
            'error': 'Balance check not supported by Devino 2FA API'
        }


devino_sms_service = DevinoSMSService()