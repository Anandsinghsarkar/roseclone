from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import delete, select

from database.models import CustomCommand
from database.session import async_session
from utils.permissions import is_chat_admin

router = Router()


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
    if message.chat.type not in {"group", "supergroup"} or not message.text or not message.text.startswith("/"):
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
