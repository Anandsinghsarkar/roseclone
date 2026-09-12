from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from database.models import Note
from database.session import async_session
from utils.permissions import is_chat_admin

router = Router()


@router.message(Command("save"))
async def save_cmd(message: Message):
    if not await is_chat_admin(message): return await message.reply("⛔ Sirf Telegram admin notes save/update kar sakta hai.")
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return await message.reply("Usage: <code>/save &lt;name&gt;</code> (kisi message pe reply karke)")
    name = args[1].strip().lower()
    if not message.reply_to_message: return await message.reply("❌ Kisi message pe reply karke /save karo.")
    content = message.reply_to_message.text or message.reply_to_message.caption
    if not content: return await message.reply("❌ Sirf text/caption wale messages save ho sakte hain.")
    async with async_session() as session:
        stmt = select(Note).where(Note.group_id == message.chat.id, Note.name == name)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing: existing.content, existing.created_by = content, message.from_user.id
        else: session.add(Note(group_id=message.chat.id, name=name, content=content, created_by=message.from_user.id))
        await session.commit()
    await message.reply(f"✅ Note <b>{name}</b> save ho gaya.")


@router.message(Command("get"))
async def get_cmd(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return await message.reply("Usage: <code>/get &lt;name&gt;</code>")
    name = args[1].strip().lower()
    async with async_session() as session:
        note = (await session.execute(select(Note).where(Note.group_id == message.chat.id, Note.name == name))).scalar_one_or_none()
    if not note: return await message.reply(f"❌ Note <b>{name}</b> nahi mila.")
    await message.reply(note.content)


@router.message(Command("notes"))
async def notes_cmd(message: Message):
    async with async_session() as session:
        notes = (await session.execute(select(Note).where(Note.group_id == message.chat.id))).scalars().all()
    if not notes: return await message.reply("📭 Koi note nahi hai.")
    await message.reply("📝 <b>Notes:</b>\n\n" + "\n".join(f"• <code>{n.name}</code>" for n in notes))


@router.message(Command("clear"))
async def clear_cmd(message: Message):
    if not await is_chat_admin(message): return await message.reply("⛔ Sirf Telegram admin notes delete kar sakta hai.")
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return await message.reply("Usage: <code>/clear &lt;name&gt;</code>")
    name = args[1].strip().lower()
    async with async_session() as session:
        note = (await session.execute(select(Note).where(Note.group_id == message.chat.id, Note.name == name))).scalar_one_or_none()
        if note:
            await session.delete(note); await session.commit()
            return await message.reply(f"🗑 Note <b>{name}</b> delete ho gaya.")
    await message.reply("❌ Note nahi mila.")
