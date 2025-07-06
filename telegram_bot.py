import asyncio
import logging
import os
import nest_asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import settings

# Разрешаем вложенные event loops
nest_asyncio.apply()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SMSBot:
    def __init__(self):
        self.application = None
        self.user_phone_mapping = {}  # user_id -> phone
        self.verification_codes = {}  # phone -> code
        self.pending_verifications = {}  # phone -> user_id
        self.bot_task = None
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        
        # Создаем клавиатуру с кнопкой "Поделиться номером" - ВСЕГДА
        keyboard = [[KeyboardButton("📱 Поделиться номером", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)
        
        await update.message.reply_text(
            "👋 Привет! Я бот для SMS авторизации Wazir.\n\n"
            "🔄 Нажмите кнопку ниже чтобы получить код подтверждения:\n"
            "👇 Кнопка всегда доступна для получения нового кода",
            reply_markup=reply_markup
        )
        
    async def handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик получения контакта"""
        user_id = update.effective_user.id
        contact = update.message.contact
        
        # Проверяем, что пользователь поделился своим номером
        if contact.user_id != user_id:
            await update.message.reply_text(
                "❌ Пожалуйста, поделитесь СВОИМ номером телефона"
            )
            return
        
        phone = contact.phone_number
        # Приводим к стандартному формату
        if not phone.startswith('+'):
            phone = '+' + phone
            
        # 🔥 ИСПРАВЛЕНО: Ищем СУЩЕСТВУЮЩИЙ код вместо генерации нового
        code = None
        message = None
        
        # Сначала проверяем в собственной памяти бота
        if phone in self.verification_codes:
            stored_data = self.verification_codes[phone]
            time_diff = datetime.now() - stored_data['timestamp']
            if time_diff <= timedelta(minutes=2):
                code = stored_data['code']
                time_left = 120 - int(time_diff.total_seconds())
                message = (
                    f"✅ Номер получен: {phone}\n"
                    f"🔐 ВАШ КОД ПОДТВЕРЖДЕНИЯ: {code}\n\n"
                    f"📝 Введите этот код в приложении для авторизации.\n"
                    f"⏰ Код действителен ещё {time_left} секунд.\n\n"
                    f"🔄 Это тот же код, что был сгенерирован ранее"
                )
                logger.info(f"🔄 Отправлен существующий код {code} для {phone}")
            else:
                # Код истек, удаляем его
                del self.verification_codes[phone]
        
        # Если нет кода в памяти, ищем в файле
        if not code:
            try:
                import json
                import os
                
                codes_file = "verification_codes.json"
                if os.path.exists(codes_file):
                    with open(codes_file, 'r', encoding='utf-8') as f:
                        file_codes = json.load(f)
                        
                    if phone in file_codes:
                        stored_data = file_codes[phone]
                        stored_time = datetime.fromisoformat(stored_data['timestamp'])
                        time_diff = datetime.now() - stored_time
                        
                        if time_diff <= timedelta(minutes=2):
                            code = stored_data['code']
                            time_left = 120 - int(time_diff.total_seconds())
                            message = (
                                f"✅ Номер получен: {phone}\n"
                                f"🔐 ВАШ КОД ПОДТВЕРЖДЕНИЯ: {code}\n\n"
                                f"📝 Введите этот код в приложении для авторизации.\n"
                                f"⏰ Код действителен ещё {time_left} секунд.\n\n"
                                f"🔄 Код был сгенерирован при открытии страницы"
                            )
                            logger.info(f"📁 Отправлен код {code} из файла для {phone}")
                            
                            # Сохраняем в память бота для следующих запросов
                            self.verification_codes[phone] = {
                                'code': code,
                                'timestamp': stored_time,
                                'user_id': user_id
                            }
                        else:
                            # Код истек, удаляем из файла
                            del file_codes[phone]
                            with open(codes_file, 'w', encoding='utf-8') as f:
                                json.dump(file_codes, f, ensure_ascii=False, indent=2)
                            
            except Exception as e:
                logger.error(f"❌ Ошибка чтения кода из файла: {e}")
        
        # Если все еще нет кода, генерируем новый
        if not code:
            code = self.generate_code()
            self.verification_codes[phone] = {
                'code': code,
                'timestamp': datetime.now(),
                'user_id': user_id
            }
            message = (
                f"✅ Номер получен: {phone}\n"
                f"🔐 ВАШ КОД ПОДТВЕРЖДЕНИЯ: {code}\n\n"
                f"📝 Введите этот код в приложении для авторизации.\n"
                f"⏰ Код действителен 2 минуты.\n\n"
                f"🆕 Сгенерирован новый код (страница не была загружена)"
            )
            logger.info(f"🆕 Сгенерирован новый код {code} для {phone}")
        
        # Отправляем код пользователю
        await update.message.reply_text(message)
        
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик текстовых сообщений"""
        # Всегда показываем кнопку поделиться номером
        keyboard = [[KeyboardButton("📱 Поделиться номером", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)
        
        await update.message.reply_text(
            "🔄 Для получения кода авторизации нажмите кнопку ниже:",
            reply_markup=reply_markup
        )
        
    def generate_code(self) -> str:
        """Генерация 4-значного кода"""
        import random
        return ''.join(random.choices('0123456789', k=4))
        
    def verify_code(self, phone: str, code: str) -> bool:
        """Проверка кода подтверждения"""
        if phone not in self.verification_codes:
            return False
        
        stored_data = self.verification_codes[phone]
        
        # Проверяем, не истек ли код (5 минут)
        if datetime.now() - stored_data['timestamp'] > timedelta(minutes=5):
            del self.verification_codes[phone]
            return False
        
        # Проверяем код
        if stored_data['code'] == code:
            # Удаляем код после успешной проверки
            del self.verification_codes[phone]
            return True
        
        return False
        
    def get_verification_code(self, phone: str) -> Optional[str]:
        """Получение кода для отладки"""
        if phone in self.verification_codes:
            return self.verification_codes[phone]['code']
        return None
        
    async def send_message_to_user(self, user_id: int, message: str) -> bool:
        """Отправка сообщения пользователю"""
        try:
            await self.application.bot.send_message(chat_id=user_id, text=message)
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
            return False
            
    async def start_bot(self):
        """Запуск бота с nest_asyncio"""
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN не найден в настройках")
            return
            
        logger.info("Запуск простого Telegram бота...")
        logger.info(f"🤖 Бот: @{settings.TELEGRAM_BOT_USERNAME}")
        logger.info(f"🔑 Токен: {settings.TELEGRAM_BOT_TOKEN[:10]}...")
        
        try:
            # Создаем приложение
            self.application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
            
            # Добавляем обработчики
            self.application.add_handler(CommandHandler("start", self.start))
            self.application.add_handler(MessageHandler(filters.CONTACT, self.handle_contact))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
            
            # Запускаем бота в фоновой задаче с nest_asyncio
            self.bot_task = asyncio.create_task(self.application.run_polling(allowed_updates=Update.ALL_TYPES))
            logger.info("Простой Telegram бот запущен успешно")
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            raise
        
    async def stop_bot(self):
        """Остановка бота"""
        try:
            if hasattr(self, 'bot_task') and self.bot_task:
                self.bot_task.cancel()
                try:
                    await self.bot_task
                except asyncio.CancelledError:
                    pass
            
            if hasattr(self, 'application') and self.application:
                await self.application.stop()
                
            logger.info("Простой Telegram бот остановлен")
        except Exception as e:
            logger.error(f"Ошибка остановки бота: {e}")
            
    async def main(self):
        """Запуск бота (для отдельного использования)"""
        await self.start_bot()
        # Держим бота запущенным
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
            await self.stop_bot()

# Создаем глобальный экземпляр бота
sms_bot = SMSBot()

if __name__ == "__main__":
    asyncio.run(sms_bot.main()) 