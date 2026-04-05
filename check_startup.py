import asyncio
import sys
import os
from sqlalchemy import create_engine, text
import httpx
from config import settings

async def check_db():
    print(f"🔍 Checking Database connection to: {settings.DATABASE_URL.split('@')[-1]}")
    try:
        engine = create_engine(settings.DATABASE_URL, connect_args={"connect_timeout": 5})
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print(f"✅ Database connection successful: {result.fetchone()}")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

async def check_telegram():
    print(f"🔍 Checking Telegram Bot Token: {settings.TELEGRAM_BOT_TOKEN[:10]}...")
    if not settings.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN is missing!")
        return False
    
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getMe"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Telegram connection successful: @{data['result']['username']}")
                return True
            else:
                print(f"❌ Telegram API returned error: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        print(f"❌ Telegram connection failed: {e}")
        return False

async def main():
    print("🚀 Running Startup Diagnostic...")
    print("-" * 50)
    
    db_ok = await check_db()
    tg_ok = await check_telegram()
    
    print("-" * 50)
    if db_ok and tg_ok:
        print("🎉 All systems green!")
    else:
        print("⚠️  Some diagnostics failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())
