from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from database.models import Lock
from database.session import async_session

router = Router()


@router.message(Command("lock"))
async def lock_cmd(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("Usage: <code>/lock &lt;type&gt;</code>\nTypes: text, links, photos, videos, stickers, gifs, forwards, bots, etc.")
    lock_type = args[1].lower().strip()

    async with async_session() as session:
        stmt = select(Lock).where(Lock.group_id == message.chat.id, Lock.lock_type == lock_type)
        lock = (await session.execute(stmt)).scalar_one_or_none()
        if lock:
            lock.enabled = True
        else:
            session.add(Lock(group_id=message.chat.id, lock_type=lock_type, enabled=True))
        await session.commit()
    await message.reply(f"🔒 <b>{lock_type}</b> lock ho gaya.")


@router.message(Command("unlock"))
async def unlock_cmd(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("Usage: <code>/unlock &lt;type&gt;</code>")
    lock_type = args[1].lower().strip()

    async with async_session() as session:
        stmt = select(Lock).where(Lock.group_id == message.chat.id, Lock.lock_type == lock_type)
        lock = (await session.execute(stmt)).scalar_one_or_none()
        if lock:
            lock.enabled = False
            await session.commit()
            await message.reply(f"🔓 <b>{lock_type}</b> unlock ho gaya.")
        else:
            await message.reply("❌ Yeh lock set nahi hai.")


@router.message(Command("locks"))
async def locks_cmd(message: Message):
    async with async_session() as session:
        stmt = select(Lock).where(Lock.group_id == message.chat.id, Lock.enabled == True)
        locks = (await session.execute(stmt)).scalars().all()
    if not locks:
        return await message.reply("🔓 Koi lock active nahi hai.")
    text = "🔒 <b>Active Locks:</b>\n\n"
    for l in locks:
        text += f"• {l.lock_type}\n"
    await message.reply(text)
