from fastapi import APIRouter, HTTPException, Depends, Form, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging
import json
from datetime import datetime, timedelta

from app.api import deps
from app.services.devino_sms_service import devino_sms_service
from config import settings

# Настройка детального логирования для API
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/send-code")
async def send_sms_code(
    contact_type: str = Form(...),
    contact: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    """
    Отправить SMS код подтверждения с максимальным логированием
    """
    logger.info("🔥" * 50)
    logger.info("🚀 API: ЗАПРОС НА ОТПРАВКУ SMS КОДА")
    logger.info("🔥" * 50)
    
    start_time = datetime.now()
    
    try:
        # Логируем входные данные
        logger.info(f"📥 Входные параметры:")
        logger.info(f"   📞 contact_type: {contact_type}")
        logger.info(f"   📱 contact: {contact}")
        logger.info(f"   🗄️ db session: {type(db)}")
        
        # Проверяем, что это SMS (может быть и email в будущем)
        if contact_type != "phone":
            logger.warning(f"❌ Неподдерживаемый тип контакта: {contact_type}")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Поддерживается только SMS подтверждение"
                }
            )
        
        # Валидируем номер телефона
        if not contact or len(contact.strip()) < 9:
            logger.warning(f"❌ Неверный номер телефона: '{contact}' (длина: {len(contact.strip()) if contact else 0})")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Неверный номер телефона"
                }
            )
        
        phone = contact.strip()
        logger.info(f"✅ Валидация пройдена. Обрабатываемый номер: {phone}")
        
        # Отправляем код через Devino
        logger.info("📤 Вызов devino_sms_service.send_verification_code()")
        
        result = await devino_sms_service.send_verification_code(phone)
        
        logger.info(f"📨 Результат от Devino сервиса:")
        logger.info(f"   ✅ Успех: {result.success}")
        logger.info(f"   🔢 Код: {result.code}")
        logger.info(f"   📝 Описание: {result.description}")
        
        if result.success:
            logger.info("🎉 SMS код успешно отправлен через API!")
            
            response_data = {
                "success": True,
                "message": "SMS код отправлен"
            }
            
            logger.info(f"📤 Возвращаемый ответ: {json.dumps(response_data, ensure_ascii=False)}")
            
            return JSONResponse(
                status_code=200,
                content=response_data
            )
        else:
            # Получаем понятное сообщение об ошибке
            error_message = devino_sms_service.get_error_message(result.code)
            
            logger.warning(f"⚠️ Ошибка отправки SMS через API:")
            logger.warning(f"   📱 Номер: {phone}")
            logger.warning(f"   🔢 Код ошибки: {result.code}")
            logger.warning(f"   📝 Описание: {result.description}")
            logger.warning(f"   💬 Сообщение пользователю: {error_message}")
            
            error_response = {
                "success": False,
                "error": error_message
            }
            
            logger.info(f"📤 Возвращаемый ответ об ошибке: {json.dumps(error_response, ensure_ascii=False)}")
            
            return JSONResponse(
                status_code=400,
                content=error_response
            )
            
    except Exception as e:
        logger.error("💥 КРИТИЧЕСКАЯ ОШИБКА В API ОТПРАВКИ SMS:")
        logger.exception(f"   📄 Детали ошибки: {str(e)}")
        logger.error(f"   📱 Номер: {contact if 'contact' in locals() else 'UNKNOWN'}")
        
        error_response = {
            "success": False,
            "error": "Произошла ошибка. Пожалуйста, попробуйте позже."
        }
        
        logger.info(f"📤 Возвращаемый ответ об ошибке: {json.dumps(error_response, ensure_ascii=False)}")
        
        return JSONResponse(
            status_code=500,
            content=error_response
        )
        
    finally:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"⏱️ Общее время выполнения API запроса: {duration:.3f}s")
        logger.info("🔥" * 50)
        logger.info("🏁 API: КОНЕЦ ОБРАБОТКИ ОТПРАВКИ SMS")
        logger.info("🔥" * 50)


@router.post("/verify-code")
async def verify_sms_code(
    code: str = Form(...),
    contact_type: str = Form(...),
    contact: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    """
    Проверить SMS код подтверждения с максимальным логированием
    """
    logger.info("🔥" * 50)
    logger.info("🔍 API: ЗАПРОС НА ПРОВЕРКУ SMS КОДА")
    logger.info("🔥" * 50)
    
    start_time = datetime.now()
    
    try:
        # Логируем входные данные
        logger.info(f"📥 Входные параметры:")
        logger.info(f"   🔢 code: {code}")
        logger.info(f"   📞 contact_type: {contact_type}")
        logger.info(f"   📱 contact: {contact}")
        logger.info(f"   🗄️ db session: {type(db)}")
        
        # Проверяем, что это SMS
        if contact_type != "phone":
            logger.warning(f"❌ Неподдерживаемый тип контакта: {contact_type}")
            return JSONResponse(
                status_code=400,
                content={
                    "verified": False,
                    "error": "Поддерживается только SMS подтверждение"
                }
            )
        
        # Валидируем входные данные
        if not contact or not code:
            logger.warning(f"❌ Неполные данные:")
            logger.warning(f"   📱 contact: '{contact}' (пустой: {not contact})")
            logger.warning(f"   🔢 code: '{code}' (пустой: {not code})")
            
            return JSONResponse(
                status_code=400,
                content={
                    "verified": False,
                    "error": "Номер телефона и код обязательны"
                }
            )
        
        phone = contact.strip()
        verification_code = code.strip()
        
        logger.info(f"📱 Обрабатываемый номер: {phone}")
        logger.info(f"🔢 Проверяемый код: {verification_code}")
        
        # Проверяем, что код 4-значный (базовая валидация)
        if len(verification_code) != 4 or not verification_code.isdigit():
            logger.warning(f"❌ Неверный формат кода:")
            logger.warning(f"   🔢 Код: '{verification_code}'")
            logger.warning(f"   📏 Длина: {len(verification_code)}")
            logger.warning(f"   🔤 Только цифры: {verification_code.isdigit()}")
            
            return JSONResponse(
                status_code=400,
                content={
                    "verified": False,
                    "error": "Код должен состоять из 4 цифр"
                }
            )
        
        logger.info("✅ Базовая валидация пройдена")
        
        # Проверяем код через Devino
        logger.info("🔍 Вызов devino_sms_service.verify_code()")
        
        result = await devino_sms_service.verify_code(phone, verification_code)
        
        logger.info(f"📨 Результат от Devino сервиса:")
        logger.info(f"   ✅ Успех: {result.success}")
        logger.info(f"   🔢 Код: {result.code}")
        logger.info(f"   📝 Описание: {result.description}")
        
        if result.success:
            logger.info("🎉 SMS код успешно подтвержден через API!")
            
            response_data = {
                "verified": True,
                "message": "Код подтверждения верный"
            }
            
            logger.info(f"📤 Возвращаемый ответ: {json.dumps(response_data, ensure_ascii=False)}")
            
            return JSONResponse(
                status_code=200,
                content=response_data
            )
        else:
            # Получаем понятное сообщение об ошибке
            error_message = devino_sms_service.get_error_message(result.code)
            
            logger.warning(f"⚠️ Ошибка проверки SMS через API:")
            logger.warning(f"   📱 Номер: {phone}")
            logger.warning(f"   🔢 Код: {verification_code}")
            logger.warning(f"   🔢 Код ошибки: {result.code}")
            logger.warning(f"   📝 Описание: {result.description}")
            logger.warning(f"   💬 Сообщение пользователю: {error_message}")
            
            error_response = {
                "verified": False,
                "error": error_message
            }
            
            logger.info(f"📤 Возвращаемый ответ об ошибке: {json.dumps(error_response, ensure_ascii=False)}")
            
            return JSONResponse(
                status_code=400,
                content=error_response
            )
            
    except Exception as e:
        logger.error("💥 КРИТИЧЕСКАЯ ОШИБКА В API ПРОВЕРКИ SMS:")
        logger.exception(f"   📄 Детали ошибки: {str(e)}")
        logger.error(f"   📱 Номер: {contact if 'contact' in locals() else 'UNKNOWN'}")
        logger.error(f"   🔢 Код: {code if 'code' in locals() else 'UNKNOWN'}")
        
        error_response = {
            "verified": False,
            "error": "Произошла ошибка. Пожалуйста, попробуйте позже."
        }
        
        logger.info(f"📤 Возвращаемый ответ об ошибке: {json.dumps(error_response, ensure_ascii=False)}")
        
        return JSONResponse(
            status_code=500,
            content=error_response
        )
        
    finally:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"⏱️ Общее время выполнения API запроса: {duration:.3f}s")
        logger.info("🔥" * 50)
        logger.info("🏁 API: КОНЕЦ ОБРАБОТКИ ПРОВЕРКИ SMS")
        logger.info("🔥" * 50)


@router.get("/debug/last-codes")
async def get_debug_sms_codes():
    """
    DEBUG эндпоинт для получения последних SMS кодов
    """
    logger.info("🐛 DEBUG: Запрос последних SMS кодов")
    
    if not settings.DEBUG_SMS:
        logger.warning("🐛 DEBUG режим отключен")
        raise HTTPException(
            status_code=404,
            detail="Debug режим отключен"
        )
    
    try:
        # Читаем последние записи из лога
        codes = []
        logger.info("📖 Чтение файла sms_debug.log")
        
        try:
            with open("sms_debug.log", "r", encoding="utf-8") as f:
                lines = f.readlines()
                logger.info(f"📖 Прочитано {len(lines)} строк из лога")
                
                # Берем последние 20 записей для поиска кодов
                recent_lines = lines[-20:]
                logger.info(f"📖 Анализируем последние {len(recent_lines)} строк")
                
                for i, line in enumerate(recent_lines):
                    if "SMS КОД ОТПРАВЛЕН" in line or "SMS КОД ПОДТВЕРЖДЕН" in line:
                        codes.append(line.strip())
                        logger.debug(f"📖 Найдена SMS операция #{i}: {line.strip()[:100]}...")
                        
                logger.info(f"📖 Найдено {len(codes)} SMS операций")
                
        except FileNotFoundError:
            logger.warning("📖 Лог файл sms_debug.log не найден")
            codes = ["Лог файл не найден"]
        
        response_data = {
            "debug": True,
            "recent_codes": codes[-10:],  # Последние 10
            "message": "Последние SMS операции",
            "total_found": len(codes)
        }
        
        logger.info(f"📤 Возвращаем {len(response_data['recent_codes'])} записей")
        
        return JSONResponse(
            status_code=200,
            content=response_data
        )
        
    except Exception as e:
        logger.error("💥 Ошибка получения debug информации:")
        logger.exception(f"   📄 Детали: {str(e)}")
        
        return JSONResponse(
            status_code=500,
            content={
                "debug": True,
                "error": str(e)
            }
        )


@router.get("/status")
async def get_sms_service_status():
    """
    Проверка статуса SMS сервиса с подробным логированием
    """
    logger.info("📊 Запрос статуса SMS сервиса")
    
    try:
        status_info = {
            "service": "Devino SMS 2FA",
            "api_url": settings.DEVINO_API_URL,
            "api_key_configured": bool(settings.DEVINO_API_KEY),
            "debug_mode": settings.DEBUG_SMS,
            "timeout": settings.DEVINO_TIMEOUT,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info("📊 Собранная информация о статусе:")
        for key, value in status_info.items():
            logger.info(f"   📋 {key}: {value}")
        
        return JSONResponse(
            status_code=200,
            content=status_info
        )
        
    except Exception as e:
        logger.error("💥 Ошибка получения статуса сервиса:")
        logger.exception(f"   📄 Детали: {str(e)}")
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Ошибка получения статуса",
                "details": str(e)
            }
        )


@router.get("/test-connection")
async def test_devino_connection():
    """
    Тестирование подключения к Devino API
    Отправляет тестовый запрос для проверки связи
    """
    logger.info("🧪" * 50)
    logger.info("🧪 ТЕСТИРОВАНИЕ ПОДКЛЮЧЕНИЯ К DEVINO API")
    logger.info("🧪" * 50)
    
    start_time = datetime.now()
    
    try:
        # Проверяем конфигурацию
        logger.info("🔧 Проверка конфигурации:")
        logger.info(f"   🌐 API URL: {settings.DEVINO_API_URL}")
        logger.info(f"   🔑 API Key установлен: {bool(settings.DEVINO_API_KEY)}")
        logger.info(f"   ⏱️ Timeout: {settings.DEVINO_TIMEOUT}s")
        logger.info(f"   🐛 Debug режим: {settings.DEBUG_SMS}")
        
        if not settings.DEVINO_API_KEY:
            logger.error("❌ API ключ не установлен!")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "API ключ не установлен в конфигурации",
                    "details": "Добавьте DEVINO_API_KEY в .env файл"
                }
            )
        
        # Пробуем отправить SMS на тестовый номер
        test_phone = "996555000001"  # Тестовый номер
        logger.info(f"📱 Тестовый номер: {test_phone}")
        
        logger.info("🚀 Попытка отправки тестового SMS...")
        result = await devino_sms_service.send_verification_code(test_phone)
        
        logger.info("📊 Результаты тестирования:")
        logger.info(f"   ✅ Запрос выполнен: Да")
        logger.info(f"   📡 Соединение установлено: Да") 
        logger.info(f"   🎯 Код ответа: {result.code}")
        logger.info(f"   📝 Описание: {result.description}")
        logger.info(f"   ✅ Успех отправки: {result.success}")
        
        # Определяем статус подключения
        if result.code in ["0", "1", "2", "3", "4", "5", "6", "7"]:
            # Любой ответ с валидным кодом означает что API доступен
            connection_status = "SUCCESS"
            connection_message = "Подключение к Devino API успешно"
        else:
            connection_status = "PARTIAL"
            connection_message = "Частичное подключение (сетевые ошибки)"
        
        response_data = {
            "success": True,
            "connection_status": connection_status,
            "message": connection_message,
            "test_details": {
                "api_url": settings.DEVINO_API_URL,
                "test_phone": test_phone,
                "response_code": result.code,
                "response_description": result.description,
                "sms_sent_successfully": result.success,
                "api_key_configured": bool(settings.DEVINO_API_KEY),
                "debug_mode": settings.DEBUG_SMS
            },
            "recommendations": []
        }
        
        # Добавляем рекомендации на основе результатов
        if result.code == "1":
            response_data["recommendations"].append("Проверьте правильность API ключа")
        elif result.code == "2":
            response_data["recommendations"].append("Проверьте формат тестового номера")
        elif result.code == "3":
            response_data["recommendations"].append("Превышен лимит запросов - подождите или свяжитесь с провайдером")
        elif result.success:
            response_data["recommendations"].append("Подключение работает отлично!")
        else:
            response_data["recommendations"].append("Проверьте логи для получения подробной информации")
        
        logger.info(f"📤 Результат тестирования: {connection_status}")
        
        return JSONResponse(
            status_code=200,
            content=response_data
        )
        
    except Exception as e:
        logger.error("💥 Критическая ошибка при тестировании подключения:")
        logger.exception(f"   📄 Детали: {str(e)}")
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "connection_status": "ERROR",
                "message": "Ошибка при тестировании подключения",
                "error": str(e),
                "recommendations": [
                    "Проверьте настройки сети",
                    "Убедитесь что API ключ установлен",
                    "Проверьте логи для получения подробной информации"
                ]
            }
        )
        
    finally:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"⏱️ Время тестирования: {duration:.3f}s")
        logger.info("🧪" * 50)
        logger.info("🏁 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
        logger.info("🧪" * 50) 