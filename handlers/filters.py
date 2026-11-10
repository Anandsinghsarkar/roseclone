from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, delete
from database.models import GroupFilter
from database.session import async_session
from utils.permissions import is_chat_admin

router = Router()

@router.message(Command("addfilter"))
async def add_filter(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not await is_chat_admin(message):
        return await message.reply("⛔ Sirf group admin filter add kar sakta hai.")
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        return await message.reply("Usage: /addfilter keyword response text")
    trigger, response = parts[1].strip().lower(), parts[2].strip()
    if not trigger or len(trigger) > 64 or len(response) > 3500:
        return await message.reply("❌ Keyword max 64 aur response max 3500 characters ho sakta hai.")
    async with async_session() as session:
        item = (await session.execute(select(GroupFilter).where(GroupFilter.group_id == message.chat.id, GroupFilter.trigger == trigger))).scalar_one_or_none()
        if item:
            item.response, item.enabled, item.created_by = response, True, message.from_user.id
        else:
            session.add(GroupFilter(group_id=message.chat.id, trigger=trigger, response=response, created_by=message.from_user.id))
        await session.commit()
    await message.reply(f"✅ Filter <code>{trigger}</code> save ho gaya.")

@router.message(Command("delfilter"))
async def delete_filter(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not await is_chat_admin(message):
        return await message.reply("⛔ Sirf group admin filter delete kar sakta hai.")
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply("Usage: /delfilter keyword")
    async with async_session() as session:
        result = await session.execute(delete(GroupFilter).where(GroupFilter.group_id == message.chat.id, GroupFilter.trigger == parts[1].strip().lower()))
        await session.commit()
    await message.reply("✅ Filter delete ho gaya." if result.rowcount else "❌ Filter nahi mila.")

@router.message(Command("filters"))
async def list_filters(message: Message):
    async with async_session() as session:
        rows = (await session.execute(select(GroupFilter).where(GroupFilter.group_id == message.chat.id, GroupFilter.enabled.is_(True)).order_by(GroupFilter.trigger))).scalars().all()
    if not rows:
        return await message.reply("Abhi koi custom filter nahi hai.")
    await message.reply("🎯 <b>Active filters</b>\n\n" + "\n".join(f"• <code>{x.trigger}</code>" for x in rows))

@router.message()
async def apply_filter(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not message.text or message.text.startswith("/") or not message.from_user:
        return
    if await is_chat_admin(message):
        return
    async with async_session() as session:
        rows = (await session.execute(select(GroupFilter).where(GroupFilter.group_id == message.chat.id, GroupFilter.enabled.is_(True)))).scalars().all()
    body = message.text.casefold()
    for item in rows:
        if item.trigger.casefold() in body:
            await message.answer(item.response.replace("{name}", message.from_user.full_name).replace("{group}", message.chat.title or "group"))
            break
