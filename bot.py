import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from database.session import init_db
from handlers import start, moderation, welcome, locks, notes, utilities
from middlewares.throttling import ThrottlingMiddleware

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("rose_clone")


async def main():
    await init_db()
    logger.info("Database initialized")

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.message.middleware(ThrottlingMiddleware(rate_limit=1.0))

    dp.include_router(start.router)
    dp.include_router(utilities.router)
    dp.include_router(moderation.router)
    dp.include_router(welcome.router)
    dp.include_router(locks.router)
    dp.include_router(notes.router)

    logger.info("Bot starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
