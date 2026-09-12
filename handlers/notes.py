from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from database.models import Note
from database.session import async_session

router = Router()


@router.message(Command("save"))
async def save_cmd(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("Usage: <code>/save &lt;name&gt;</code> (kisi message pe reply karke)")
    name = args[1].strip().lower()
    if message.reply_to_message:
        content = message.reply_to_message.text or message.reply_to_message.caption
        if not content:
            return await message.reply("❌ Sirf text/caption wale messages save ho sakte hain.")
    else:
        return await message.reply("❌ Kisi message pe reply karke /save karo.")
    async with async_session() as session:
        stmt = select(Note).where(Note.group_id == message.chat.id, Note.name == name)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.content = content
            existing.created_by = message.from_user.id
        else:
            session.add(Note(group_id=message.chat.id, name=name, content=content, created_by=message.from_user.id))
        await session.commit()
    await message.reply(f"✅ Note <b>{name}</b> save ho gaya.")


@router.message(Command("get"))
async def get_cmd(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("Usage: <code>/get &lt;name&gt;</code>")
    name = args[1].strip().lower()
    async with async_session() as session:
        stmt = select(Note).where(Note.group_id == message.chat.id, Note.name == name)
        note = (await session.execute(stmt)).scalar_one_or_none()
    if not note:
        return await message.reply(f"❌ Note <b>{name}</b> nahi mila.")
    await message.reply(note.content)


@router.message(Command("notes"))
async def notes_cmd(message: Message):
    async with async_session() as session:
        stmt = select(Note).where(Note.group_id == message.chat.id)
        notes = (await session.execute(stmt)).scalars().all()
    if not notes:
        return await message.reply("📭 Koi note nahi hai.")
    text = "📝 <b>Notes:</b>\n\n"
    for n in notes:
        text += f"• <code>{n.name}</code>\n"
    await message.reply(text)


@router.message(Command("clear"))
async def clear_cmd(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("Usage: <code>/clear &lt;name&gt;</code>")
    name = args[1].strip().lower()
    async with async_session() as session:
        stmt = select(Note).where(Note.group_id == message.chat.id, Note.name == name)
        note = (await session.execute(stmt)).scalar_one_or_none()
        if note:
            await session.delete(note)
            await session.commit()
            return await message.reply(f"🗑 Note <b>{name}</b> delete ho gaya.")
    await message.reply("❌ Note nahi mila.")
