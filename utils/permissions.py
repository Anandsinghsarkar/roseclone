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


async def is_chat_admin(message) -> bool:
    if not message.from_user:
        return False
    if await is_bot_admin(message.from_user.id):
        return True
    if message.chat.type not in {"group", "supergroup", "channel"}:
        return False
    try:
        member = await message.chat.get_member(message.from_user.id)
        return member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}
    except Exception:
        return False
