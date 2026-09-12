import asyncio
import logging
import os

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from database.session import init_db
from handlers import admin, start, moderation, welcome, locks, notes, utilities
from middlewares.throttling import ThrottlingMiddleware
from web.app import build_app

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("rose_clone")


async def run_web():
    app = build_app(bot)
    port = int(os.getenv("PORT", str(settings.WEB_PORT)))
    config = uvicorn.Config(app, host=settings.WEB_HOST, port=port, log_level=settings.LOG_LEVEL.lower())
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    await init_db()
    logger.info("Database initialized")

    global bot
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.message.middleware(ThrottlingMiddleware(rate_limit=1.0))

    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(utilities.router)
    dp.include_router(moderation.router)
    dp.include_router(welcome.router)
    dp.include_router(locks.router)
    dp.include_router(notes.router)

    web_task = asyncio.create_task(run_web(), name="web-dashboard")

    logger.info("Bot starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        web_task.cancel()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
