from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import delete, select

from database.models import CustomCommand, GroupFilter
from database.session import async_session
from utils.permissions import is_chat_admin

router = Router()



@router.message(Command("addfilter"))
async def add_filter(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not await is_chat_admin(message):
        return await message.reply("⛔ Sirf group admin filter add kar sakta hai.")
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        return await message.reply("Usage: /addfilter keyword response")
    trigger, response = parts[1].strip().lower(), parts[2].strip()
    if not trigger or len(trigger) > 64 or len(response) > 3500:
        return await message.reply("❌ Keyword max 64 aur response max 3500 characters.")
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
    await message.reply("🎯 <b>Active filters</b>\\n\\n" + "\\n".join(f"• <code>{x.trigger}</code>" for x in rows))

@router.message(Command("addcmd"))
async def addcmd(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not await is_chat_admin(message):
        return await message.reply("⛔ Sirf group admin custom command bana sakta hai.")
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return await message.reply("Usage: <code>/addcmd hello Hello {name}</code>")
    command = parts[1].lower().lstrip("/")
    response = parts[2]
    if not command.isidentifier() or len(command) > 32:
        return await message.reply("❌ Command name invalid hai.")
    async with async_session() as session:
        existing = (await session.execute(select(CustomCommand).where(CustomCommand.group_id == message.chat.id, CustomCommand.command == command))).scalar_one_or_none()
        if existing:
            existing.response = response
            existing.enabled = True
            existing.created_by = message.from_user.id
        else:
            session.add(CustomCommand(group_id=message.chat.id, command=command, response=response, created_by=message.from_user.id))
        await session.commit()
    await message.reply(f"✅ /{command} custom command save ho gaya.")


@router.message(Command("delcmd"))
async def delcmd(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not await is_chat_admin(message):
        return await message.reply("⛔ Sirf group admin custom command delete kar sakta hai.")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply("Usage: <code>/delcmd hello</code>")
    command = parts[1].lower().lstrip("/")
    async with async_session() as session:
        await session.execute(delete(CustomCommand).where(CustomCommand.group_id == message.chat.id, CustomCommand.command == command))
        await session.commit()
    await message.reply(f"✅ /{command} delete ho gaya.")


@router.message()
async def custom_command_router(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not message.text:
        return
    if not message.text.startswith("/"):
        if not message.from_user or await is_chat_admin(message):
            return
        async with async_session() as session:
            filters = (await session.execute(select(GroupFilter).where(GroupFilter.group_id == message.chat.id, GroupFilter.enabled.is_(True)))).scalars().all()
        body = message.text.casefold()
        for item in filters:
            if item.trigger.casefold() in body:
                await message.answer(item.response.replace("{name}", message.from_user.full_name).replace("{group}", message.chat.title or "group"))
                break
        return
    command = message.text.split()[0].split("@")[0].lstrip("/").lower()
    if command in {"start", "menu", "setup", "panel", "admin", "addadmin", "deladmin", "promote", "demote", "addcmd", "delcmd", "ban", "unban", "kick", "mute", "unmute", "warn", "warns", "rmwarn", "pin", "del", "lock", "unlock", "locks", "save", "get", "notes", "clear", "setwelcome", "welcome", "setgoodbye", "goodbye", "setrules", "rules", "id", "info", "ping", "stats", "admins"}:
        return
    async with async_session() as session:
        stmt = select(CustomCommand).where(CustomCommand.group_id == message.chat.id, CustomCommand.command == command, CustomCommand.enabled.is_(True))
        item = (await session.execute(stmt)).scalar_one_or_none()
    if not item:
        return
    text = item.response.replace("{name}", message.from_user.full_name if message.from_user else "").replace("{group}", message.chat.title or "group")
    await message.answer(text)
