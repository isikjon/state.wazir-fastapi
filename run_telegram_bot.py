#!/usr/bin/env python3
"""
Отдельный скрипт для запуска простого Telegram бота для SMS авторизации.
Запускать отдельно от FastAPI приложения.
"""

import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import settings

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Файл для хранения кодов (чтобы FastAPI мог их читать)
CODES_FILE = "verification_codes.json"

class SimpleSMSBot:
    def __init__(self):
        self.verification_codes = {}
        self.load_codes()
        
    def load_codes(self):
        """Загрузка кодов из файла"""
        try:
            if os.path.exists(CODES_FILE):
                with open(CODES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Конвертируем строки обратно в datetime
                    for phone, code_data in data.items():
                        code_data['timestamp'] = datetime.fromisoformat(code_data['timestamp'])
                    self.verification_codes = data
        except Exception as e:
            logger.error(f"Ошибка загрузки кодов: {e}")
            self.verification_codes = {}
    
    def save_codes(self):
        """Сохранение кодов в файл"""
        try:
            # Конвертируем datetime в строки для JSON
            data = {}
            for phone, code_data in self.verification_codes.items():
                data[phone] = {
                    'code': code_data['code'],
                    'timestamp': code_data['timestamp'].isoformat(),
                    'user_id': code_data.get('user_id')
                }
            
            with open(CODES_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения кодов: {e}")
    
    def generate_code(self) -> str:
        """Генерация 4-значного кода"""
        import random
        return ''.join(random.choices('0123456789', k=4))
    
    def clean_expired_codes(self):
        """Очистка истекших кодов"""
        current_time = datetime.now()
        expired_phones = []
        
        for phone, code_data in self.verification_codes.items():
            if current_time - code_data['timestamp'] > timedelta(minutes=5):
                expired_phones.append(phone)
        
        for phone in expired_phones:
            del self.verification_codes[phone]
        
        if expired_phones:
            self.save_codes()
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        keyboard = [[KeyboardButton("📱 Поделиться номером", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)
        
        await update.message.reply_text(
            "🤖 Простой SMS бот для авторизации Wazir\n\n"
            "📱 Нажмите кнопку ниже, чтобы получить код:",
            reply_markup=reply_markup
        )
    
    async def handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик получения контакта"""
        user_id = update.effective_user.id
        contact = update.message.contact
        
        if contact.user_id != user_id:
            await update.message.reply_text("❌ Поделитесь СВОИМ номером телефона")
            return
        
        phone = contact.phone_number
        if not phone.startswith('+'):
            phone = '+' + phone
        
        # Очищаем истекшие коды
        self.clean_expired_codes()
        
        # Генерируем новый код
        code = self.generate_code()
        
        # Сохраняем код
        self.verification_codes[phone] = {
            'code': code,
            'timestamp': datetime.now(),
            'user_id': user_id
        }
        self.save_codes()
        
        # Отправляем код пользователю
        await update.message.reply_text(
            f"✅ Номер: {phone}\n"
            f"🔐 КОД: {code}\n\n"
            f"📝 Введите код в приложении\n"
            f"⏰ Код действителен 5 минут"
        )
        
        logger.info(f"Код {code} для {phone} (user: {user_id})")
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик текстовых сообщений"""
        keyboard = [[KeyboardButton("📱 Поделиться номером", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)
        
        await update.message.reply_text(
            "🔄 Для получения кода нажмите кнопку:",
            reply_markup=reply_markup
        )

async def main():
    """Запуск бота"""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не найден!")
        return
    
    logger.info("🚀 Запуск простого SMS бота...")
    logger.info(f"🤖 Бот: @{settings.TELEGRAM_BOT_USERNAME}")
    
    bot = SimpleSMSBot()
    
    # Создаем приложение
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(MessageHandler(filters.CONTACT, bot.handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_text))
    
    # Запускаем бота
    logger.info("✅ Бот запущен! Нажмите Ctrl+C для остановки")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}") 