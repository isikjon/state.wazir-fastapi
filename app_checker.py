import asyncio
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AppChecker")

# Конфигурация
CHECK_INTERVAL = 15 * 60
TELEGRAM_CHAT_ID = "5647814502"
BOT_TOKEN = "8600961430:AAHAj4R7_gnXgd-vMTTYJOvWh22zoV3NJbI"
APP_URL = "http://localhost:8000"

# Подключаемся к БД напрямую через .env, без зависимости от модулей проекта
def get_db_url():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
    url = os.getenv('DATABASE_URL')
    if not url:
        logger.error("DATABASE_URL not found in .env")
    return url

db_url = get_db_url()
if db_url:
    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
else:
    engine = None
    SessionLocal = None


class AppChecker:
    def __init__(self):
        self.chat_id = TELEGRAM_CHAT_ID
        self.app = Application.builder().token(BOT_TOKEN).build()

    # --- Проверки ---

    def check_db(self) -> dict:
        """Проверка подключения к БД"""
        if not SessionLocal:
            return {"ok": False, "error": "DATABASE_URL не найден"}
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)[:100]}

    async def check_api_health(self) -> dict:
        """Проверка /api/v1/health/"""
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(f"{APP_URL}/api/v1/health/")
                if resp.status_code == 200:
                    return {"ok": True, "data": resp.json()}
                return {"ok": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"ok": False, "error": str(e)[:100]}

    def check_users(self) -> dict:
        """Проверка таблицы users"""
        if not SessionLocal:
            return {"ok": False, "count": 0}
        try:
            db = SessionLocal()
            total = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
            active = db.execute(text("SELECT COUNT(*) FROM users WHERE is_active = 1")).scalar()
            db.close()
            return {"ok": total > 0, "total": total, "active": active}
        except Exception as e:
            return {"ok": False, "error": str(e)[:100]}

    def check_properties(self) -> dict:
        """Проверка объявлений (properties)"""
        if not SessionLocal:
            return {"ok": False}
        try:
            db = SessionLocal()
            total = db.execute(text("SELECT COUNT(*) FROM properties")).scalar()
            images = db.execute(text("SELECT COUNT(*) FROM property_images")).scalar()
            db.close()
            return {"ok": True, "total": total, "images": images}
        except Exception as e:
            return {"ok": False, "error": str(e)[:100]}

    def check_service_cards(self) -> dict:
        """Проверка сервисных карточек"""
        if not SessionLocal:
            return {"ok": False}
        try:
            db = SessionLocal()
            cards = db.execute(text("SELECT COUNT(*) FROM service_cards")).scalar()
            card_images = db.execute(text("SELECT COUNT(*) FROM service_card_images")).scalar()
            categories = db.execute(text("SELECT COUNT(*) FROM service_categories")).scalar()
            db.close()
            return {"ok": True, "cards": cards, "images": card_images, "categories": categories}
        except Exception as e:
            return {"ok": False, "error": str(e)[:100]}

    async def check_media_upload(self) -> dict:
        """Проверка доступности эндпоинта загрузки медиа"""
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(f"{APP_URL}/api/v1/media/info")
                return {"ok": resp.status_code in (200, 401, 403), "status": resp.status_code}
        except Exception as e:
            return {"ok": False, "error": str(e)[:100]}

    async def check_auth_endpoint(self) -> dict:
        """Проверка работы эндпоинта авторизации"""
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.post(
                    f"{APP_URL}/api/v1/auth/check-exists",
                    json={"phone": "+998990000000"}
                )
                return {"ok": resp.status_code in (200, 404, 422), "status": resp.status_code}
        except Exception as e:
            return {"ok": False, "error": str(e)[:100]}

    # --- Генерация отчета ---

    async def generate_report(self) -> str:
        db_result = self.check_db()
        api_result = await self.check_api_health()
        users = self.check_users()
        props = self.check_properties()
        cards = self.check_service_cards()
        media = await self.check_media_upload()
        auth = await self.check_auth_endpoint()

        all_ok = all([
            db_result["ok"], api_result["ok"],
            users.get("ok"), props.get("ok"),
            cards.get("ok"), media.get("ok"), auth.get("ok")
        ])

        icon = "🟢" if all_ok else "🔴"

        lines = [
            f"{icon} <b>Wazir — Мониторинг</b>",
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "<b>1. Инфраструктура</b>",
            f"  {'✅' if db_result['ok'] else '❌'} База данных (MySQL)",
            f"  {'✅' if api_result['ok'] else '❌'} API /health",
        ]

        if not db_result["ok"]:
            lines.append(f"     ⤷ {db_result.get('error', '')}")
        if not api_result["ok"]:
            lines.append(f"     ⤷ {api_result.get('error', '')}")

        lines += [
            "",
            "<b>2. Авторизация и медиа</b>",
            f"  {'✅' if auth['ok'] else '❌'} Эндпоинт авторизации (HTTP {auth.get('status', '?')})",
            f"  {'✅' if media['ok'] else '❌'} Медиа-сервер (HTTP {media.get('status', '?')})",
        ]

        lines += [
            "",
            "<b>3. Пользователи</b>",
            f"  {'✅' if users.get('ok') else '❌'} Всего: {users.get('total', 0)} | Активных: {users.get('active', 0)}",
        ]

        if not users.get("ok") and "error" in users:
            lines.append(f"     ⤷ {users['error']}")

        lines += [
            "",
            "<b>4. Объявления (Properties)</b>",
            f"  {'✅' if props.get('ok') else '❌'} Объявлений: {props.get('total', 0)} | Фото: {props.get('images', 0)}",
        ]

        lines += [
            "",
            "<b>5. Сервисные карточки</b>",
            f"  {'✅' if cards.get('ok') else '❌'} Карточек: {cards.get('cards', 0)} | Фото: {cards.get('images', 0)} | Категорий: {cards.get('categories', 0)}",
        ]

        lines += [
            "",
            f"<b>Итого: {icon} {'Всё работает' if all_ok else 'ЕСТЬ ПРОБЛЕМЫ'}</b>",
            "",
            "<i>/check — проверить сейчас</i>"
        ]
        return "\n".join(lines)

    # --- Telegram-бот ---

    async def handle_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.effective_chat.id) != self.chat_id:
            return
        await update.message.reply_text("⏳ Проверяю...")
        report = await self.generate_report()
        await update.message.reply_text(report, parse_mode="HTML")

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.effective_chat.id) != self.chat_id:
            return
        await update.message.reply_text(
            "Wazir Monitoring Bot\n\n"
            "/check — мгновенная проверка\n"
            "Автоотчет каждые 15 минут"
        )

    async def periodic_loop(self):
        while True:
            try:
                report = await self.generate_report()
                await self.app.bot.send_message(
                    chat_id=self.chat_id, text=report, parse_mode="HTML"
                )
                logger.info("Periodic report sent")
            except Exception as e:
                logger.error(f"Periodic report error: {e}")
            await asyncio.sleep(CHECK_INTERVAL)

    async def run(self):
        self.app.add_handler(CommandHandler("start", self.handle_start))
        self.app.add_handler(CommandHandler("check", self.handle_check))

        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

        logger.info("Wazir Monitoring Bot started")

        await self.periodic_loop()


if __name__ == "__main__":
    try:
        asyncio.run(AppChecker().run())
    except KeyboardInterrupt:
        pass
