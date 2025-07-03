import httpx
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from config import settings

# Настройка детального логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('sms_debug.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


class DevinoSMSResponse:
    """Модель ответа от Devino API"""
    def __init__(self, code: str, description: str, success: bool = False):
        self.code = code
        self.description = description
        self.success = success
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DevinoSMSResponse':
        logger.debug(f"🔍 Parsing Devino response: {data}")
        
        code = str(data.get("Code", ""))
        description = data.get("Description", "Unknown error")
        success = code == "0"
        
        logger.debug(f"🔍 Parsed - Code: {code}, Success: {success}, Description: {description}")
        
        return cls(code=code, description=description, success=success)


class DevinoSMSService:
    """Сервис для работы с Devino 2FA API"""
    
    def __init__(self):
        self.api_url = settings.DEVINO_API_URL
        self.api_key = settings.DEVINO_API_KEY
        self.timeout = settings.DEVINO_TIMEOUT
        self.debug_mode = settings.DEBUG_SMS
        
        # Максимально подробное логирование при инициализации
        logger.info("🚀 Инициализация DevinoSMSService")
        logger.info(f"   📍 API URL: {self.api_url}")
        logger.info(f"   🔑 API Key установлен: {bool(self.api_key)}")
        if self.api_key:
            logger.info(f"   🔑 API Key (первые 10 символов): {self.api_key[:10]}...")
        logger.info(f"   ⏱️ Timeout: {self.timeout}s")
        logger.info(f"   🐛 Debug режим: {self.debug_mode}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Получить заголовки для запроса"""
        logger.debug("🔧 Формирование заголовков запроса")
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if self.api_key:
            headers["X-ApiKey"] = self.api_key
            logger.debug(f"✅ X-ApiKey добавлен в заголовки")
        else:
            logger.error("❌ DEVINO_API_KEY не установлен!")
            
        logger.debug(f"🔧 Заголовки сформированы: {list(headers.keys())}")
        return headers
    
    def _log_debug(self, message: str, data: Any = None):
        """Расширенное логирование для отладки"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        if data:
            logger.info(f"📋 {message}")
            logger.info(f"   📊 Data: {json.dumps(data, ensure_ascii=False, indent=2) if isinstance(data, (dict, list)) else data}")
        else:
            logger.info(f"📋 {message}")
        
        # Дополнительно записываем в файл
        try:
            with open("sms_debug.log", "a", encoding="utf-8") as f:
                log_line = f"[{timestamp}] {message}"
                if data:
                    log_line += f" | Data: {data}"
                f.write(log_line + "\n")
        except Exception as e:
            logger.error(f"❌ Ошибка записи в лог файл: {e}")
    
    def _normalize_phone(self, phone: str) -> str:
        """Нормализация номера телефона с подробным логированием"""
        logger.debug(f"📱 Начало нормализации номера: '{phone}'")
        
        original_phone = phone
        
        # Удаляем все кроме цифр
        phone = ''.join(filter(str.isdigit, phone))
        logger.debug(f"📱 После удаления не-цифр: '{phone}'")
        
        # Логика нормализации
        if phone.startswith('996'):
            logger.debug(f"📱 Номер уже с кодом 996")
            normalized = phone
        elif phone.startswith('0') and len(phone) == 10:
            # Кыргызский номер без кода страны (0xxx xxx xxx)
            normalized = '996' + phone[1:]
            logger.debug(f"📱 Кыргызский номер (0xxx): конвертирован в 996xxx")
        elif len(phone) == 9:
            # Кыргызский номер без 0 и без кода страны
            normalized = '996' + phone
            logger.debug(f"📱 Кыргызский номер (9 цифр): добавлен код 996")
        else:
            normalized = phone
            logger.debug(f"📱 Номер оставлен как есть")
        
        logger.info(f"📱 Нормализация завершена: '{original_phone}' → '{normalized}'")
        return normalized
    
    async def send_verification_code(self, phone: str, imsi_code: Optional[str] = None) -> DevinoSMSResponse:
        """
        Отправить SMS код подтверждения с максимальным логированием
        """
        logger.info("=" * 80)
        logger.info("🚀 НАЧАЛО ОТПРАВКИ SMS КОДА")
        logger.info("=" * 80)
        
        try:
            # Нормализуем номер
            logger.info(f"📱 Исходный номер: {phone}")
            normalized_phone = self._normalize_phone(phone)
            logger.info(f"📱 Нормализованный номер: {normalized_phone}")
            
            # Подготавливаем данные запроса
            request_data = {
                "DestinationNumber": normalized_phone
            }
            
            if imsi_code:
                request_data["IMSICode"] = imsi_code
                logger.info(f"📱 IMSI код добавлен: {imsi_code}")
            
            logger.info(f"📤 Данные запроса: {json.dumps(request_data, ensure_ascii=False, indent=2)}")
            
            # Получаем заголовки
            headers = self._get_headers()
            logger.info(f"📋 Заголовки запроса: {json.dumps(dict(headers), ensure_ascii=False, indent=2)}")
            
            # Формируем полный URL
            full_url = f"{self.api_url}/GenerateCode"
            logger.info(f"🌐 Полный URL: {full_url}")
            
            # Отправляем запрос
            logger.info("🌐 Отправка HTTP запроса...")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.debug(f"🔧 HTTP клиент создан с timeout={self.timeout}")
                
                start_time = datetime.now()
                logger.info(f"⏰ Время начала запроса: {start_time}")
                
                try:
                    response = await client.post(
                        full_url,
                        headers=headers,
                        json=request_data
                    )
                    
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    logger.info(f"⏰ Запрос выполнен за: {duration:.3f}s")
                    
                    logger.info(f"📨 HTTP статус: {response.status_code}")
                    logger.info(f"📨 Заголовки ответа: {dict(response.headers)}")
                    
                    # Получаем raw текст ответа
                    response_text = response.text
                    logger.info(f"📨 Raw ответ: {response_text}")
                    
                    # Парсим JSON
                    try:
                        response_data = response.json()
                        logger.info(f"📨 Parsed JSON: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
                    except Exception as json_error:
                        logger.error(f"❌ Ошибка парсинга JSON: {json_error}")
                        logger.error(f"❌ Raw response: {response_text}")
                        return DevinoSMSResponse("json_error", f"Ошибка парсинга ответа: {json_error}")
                    
                    # Создаем объект ответа
                    devino_response = DevinoSMSResponse.from_dict(response_data)
                    
                    logger.info("📊 РЕЗУЛЬТАТ ОТПРАВКИ:")
                    logger.info(f"   ✅ Успех: {devino_response.success}")
                    logger.info(f"   🔢 Код: {devino_response.code}")
                    logger.info(f"   📝 Описание: {devino_response.description}")
                    
                    if devino_response.success:
                        logger.info("🎉 SMS КОД УСПЕШНО ОТПРАВЛЕН!")
                        self._log_debug(f"✅ SMS КОД ОТПРАВЛЕН на {normalized_phone}", {
                            "phone": normalized_phone,
                            "response": response_data
                        })
                    else:
                        logger.warning("⚠️ Ошибка отправки SMS")
                        self._log_debug(f"❌ Ошибка отправки SMS: {devino_response.description}", {
                            "phone": normalized_phone,
                            "error_code": devino_response.code,
                            "response": response_data
                        })
                    
                    return devino_response
                    
                except httpx.HTTPStatusError as http_error:
                    logger.error(f"❌ HTTP ошибка: {http_error}")
                    logger.error(f"❌ Статус: {http_error.response.status_code}")
                    logger.error(f"❌ Тело ответа: {http_error.response.text}")
                    return DevinoSMSResponse("http_error", f"HTTP ошибка: {http_error}")
                    
        except httpx.TimeoutException as timeout_error:
            error_msg = f"Таймаут при отправке SMS ({self.timeout}s)"
            logger.error(f"⏰ {error_msg}")
            logger.error(f"⏰ Timeout error: {timeout_error}")
            self._log_debug(f"❌ {error_msg}")
            return DevinoSMSResponse("timeout", error_msg)
            
        except httpx.RequestError as request_error:
            error_msg = f"Ошибка сети при отправке SMS: {str(request_error)}"
            logger.error(f"🌐 {error_msg}")
            logger.exception("Network error details:")
            self._log_debug(f"❌ {error_msg}")
            return DevinoSMSResponse("network_error", error_msg)
            
        except Exception as e:
            error_msg = f"Неожиданная ошибка при отправке SMS: {str(e)}"
            logger.error(f"💥 {error_msg}")
            logger.exception("Полная трассировка ошибки:")
            self._log_debug(f"❌ {error_msg}")
            return DevinoSMSResponse("unknown_error", error_msg)
            
        finally:
            logger.info("=" * 80)
            logger.info("🏁 КОНЕЦ ОТПРАВКИ SMS КОДА")
            logger.info("=" * 80)
    
    async def verify_code(self, phone: str, code: str) -> DevinoSMSResponse:
        """
        Проверить SMS код подтверждения с максимальным логированием
        """
        logger.info("=" * 80)
        logger.info("🔍 НАЧАЛО ПРОВЕРКИ SMS КОДА")
        logger.info("=" * 80)
        
        try:
            # Нормализуем номер
            logger.info(f"📱 Исходный номер: {phone}")
            logger.info(f"🔢 Проверяемый код: {code}")
            normalized_phone = self._normalize_phone(phone)
            logger.info(f"📱 Нормализованный номер: {normalized_phone}")
            
            # Подготавливаем данные запроса
            request_data = {
                "DestinationNumber": normalized_phone,
                "Code": code
            }
            
            logger.info(f"📤 Данные запроса: {json.dumps(request_data, ensure_ascii=False, indent=2)}")
            
            # Получаем заголовки
            headers = self._get_headers()
            logger.info(f"📋 Заголовки запроса: {json.dumps(dict(headers), ensure_ascii=False, indent=2)}")
            
            # Формируем полный URL
            full_url = f"{self.api_url}/CheckCode"
            logger.info(f"🌐 Полный URL: {full_url}")
            
            # Отправляем запрос
            logger.info("🌐 Отправка HTTP запроса на проверку...")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.debug(f"🔧 HTTP клиент создан с timeout={self.timeout}")
                
                start_time = datetime.now()
                logger.info(f"⏰ Время начала запроса: {start_time}")
                
                try:
                    response = await client.post(
                        full_url,
                        headers=headers,
                        json=request_data
                    )
                    
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    logger.info(f"⏰ Запрос выполнен за: {duration:.3f}s")
                    
                    logger.info(f"📨 HTTP статус: {response.status_code}")
                    logger.info(f"📨 Заголовки ответа: {dict(response.headers)}")
                    
                    # Получаем raw текст ответа
                    response_text = response.text
                    logger.info(f"📨 Raw ответ: {response_text}")
                    
                    # Парсим JSON
                    try:
                        response_data = response.json()
                        logger.info(f"📨 Parsed JSON: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
                    except Exception as json_error:
                        logger.error(f"❌ Ошибка парсинга JSON: {json_error}")
                        logger.error(f"❌ Raw response: {response_text}")
                        return DevinoSMSResponse("json_error", f"Ошибка парсинга ответа: {json_error}")
                    
                    # Создаем объект ответа
                    devino_response = DevinoSMSResponse.from_dict(response_data)
                    
                    logger.info("📊 РЕЗУЛЬТАТ ПРОВЕРКИ:")
                    logger.info(f"   ✅ Успех: {devino_response.success}")
                    logger.info(f"   🔢 Код: {devino_response.code}")
                    logger.info(f"   📝 Описание: {devino_response.description}")
                    
                    if devino_response.success:
                        logger.info("🎉 SMS КОД УСПЕШНО ПОДТВЕРЖДЕН!")
                        self._log_debug(f"✅ SMS КОД ПОДТВЕРЖДЕН для {normalized_phone}", {
                            "phone": normalized_phone,
                            "code": code,
                            "response": response_data
                        })
                    else:
                        logger.warning("⚠️ SMS код НЕ подтвержден")
                        self._log_debug(f"❌ Неверный SMS код: {devino_response.description}", {
                            "phone": normalized_phone,
                            "code": code,
                            "error_code": devino_response.code,
                            "response": response_data
                        })
                    
                    return devino_response
                    
                except httpx.HTTPStatusError as http_error:
                    logger.error(f"❌ HTTP ошибка: {http_error}")
                    logger.error(f"❌ Статус: {http_error.response.status_code}")
                    logger.error(f"❌ Тело ответа: {http_error.response.text}")
                    return DevinoSMSResponse("http_error", f"HTTP ошибка: {http_error}")
                    
        except httpx.TimeoutException as timeout_error:
            error_msg = f"Таймаут при проверке SMS кода ({self.timeout}s)"
            logger.error(f"⏰ {error_msg}")
            logger.error(f"⏰ Timeout error: {timeout_error}")
            self._log_debug(f"❌ {error_msg}")
            return DevinoSMSResponse("timeout", error_msg)
            
        except httpx.RequestError as request_error:
            error_msg = f"Ошибка сети при проверке SMS кода: {str(request_error)}"
            logger.error(f"🌐 {error_msg}")
            logger.exception("Network error details:")
            self._log_debug(f"❌ {error_msg}")
            return DevinoSMSResponse("network_error", error_msg)
            
        except Exception as e:
            error_msg = f"Неожиданная ошибка при проверке SMS кода: {str(e)}"
            logger.error(f"💥 {error_msg}")
            logger.exception("Полная трассировка ошибки:")
            self._log_debug(f"❌ {error_msg}")
            return DevinoSMSResponse("unknown_error", error_msg)
            
        finally:
            logger.info("=" * 80)
            logger.info("🏁 КОНЕЦ ПРОВЕРКИ SMS КОДА")
            logger.info("=" * 80)
    
    def get_error_message(self, code: str) -> str:
        """Получить понятное сообщение об ошибке по коду"""
        error_messages = {
            "0": "Успешно",
            "1": "Неверный API ключ",
            "2": "Неверный номер телефона",
            "3": "Превышен лимит запросов",
            "4": "Внутренняя ошибка сервера",
            "5": "Ошибка отправки SMS",
            "6": "Неверный IMSI код",
            "7": "Код уже существует",
            "timeout": "Превышено время ожидания",
            "network_error": "Ошибка сети",
            "unknown_error": "Неизвестная ошибка",
            "json_error": "Ошибка парсинга ответа",
            "http_error": "HTTP ошибка"
        }
        
        message = error_messages.get(code, f"Неизвестная ошибка (код: {code})")
        logger.debug(f"🔍 Получение сообщения для кода '{code}': {message}")
        return message


# Глобальный экземпляр сервиса
logger.info("🔧 Создание глобального экземпляра DevinoSMSService")
devino_sms_service = DevinoSMSService()
logger.info("✅ Глобальный экземпляр DevinoSMSService создан")