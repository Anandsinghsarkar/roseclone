from aiogram.enums import ChatMemberStatus
from sqlalchemy import select

from config import settings
from database.models import BotAdmin
from database.session import async_session


async def is_bot_admin(user_id: int) -> bool:
    if user_id == settings.BOT_OWNER_ID:
        return True
    async with async_session() as session:
        return (await session.execute(select(BotAdmin).where(BotAdmin.user_id == user_id))).scalar_one_or_none() is not None


async def is_chat_admin_id(bot, chat_id: int, user_id: int) -> bool:
    if await is_bot_admin(user_id):
        return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR, "administrator", "creator"}
    except Exception:
        return False


async def is_chat_admin(message) -> bool:
    if not message.from_user:
        return False
    return await is_chat_admin_id(message.bot, message.chat.id, message.from_user.id)
