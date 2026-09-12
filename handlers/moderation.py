from aiogram import Router
from aiogram.filters import Command
from aiogram.types import ChatPermissions, Message
from sqlalchemy import select

from database.models import User, Warning
from database.session import async_session
from utils.permissions import is_chat_admin

router = Router()


async def admin_only(message: Message) -> bool:
    if await is_chat_admin(message):
        return True
    await message.reply("⛔ Sirf Telegram group admin ye moderation action use kar sakta hai.")
    return False


async def target(message: Message):
    if not message.reply_to_message:
        await message.reply("❌ Kisi message pe reply karke ye command use karo.")
        return None
    return message.reply_to_message.from_user


@router.message(Command("ban"))
async def ban_cmd(message: Message):
    if not await admin_only(message): return
    user = await target(message)
    if not user: return
    try:
        await message.chat.ban(user.id)
        await message.reply(f"🚫 {user.full_name} ko ban kar diya gaya.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")


@router.message(Command("unban"))
async def unban_cmd(message: Message):
    if not await admin_only(message): return
    user = await target(message)
    if not user: return
    try:
        await message.chat.unban(user.id)
        await message.reply(f"✅ {user.full_name} ko unban kar diya gaya.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")


@router.message(Command("kick"))
async def kick_cmd(message: Message):
    if not await admin_only(message): return
    user = await target(message)
    if not user: return
    try:
        await message.chat.ban(user.id)
        await message.chat.unban(user.id)
        await message.reply(f"👢 {user.full_name} ko kick kar diya gaya.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")


@router.message(Command("mute"))
async def mute_cmd(message: Message):
    if not await admin_only(message): return
    user = await target(message)
    if not user: return
    try:
        await message.chat.restrict(user.id, permissions=ChatPermissions(can_send_messages=False))
        await message.reply(f"🔇 {user.full_name} ko mute kar diya gaya.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")


@router.message(Command("unmute"))
async def unmute_cmd(message: Message):
    if not await admin_only(message): return
    user = await target(message)
    if not user: return
    try:
        await message.chat.restrict(user.id, permissions=ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True, can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True, can_send_other_messages=True, can_add_web_page_previews=True))
        await message.reply(f"🔊 {user.full_name} ko unmute kar diya gaya.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")


@router.message(Command("warn"))
async def warn_cmd(message: Message):
    if not await admin_only(message): return
    user = await target(message)
    if not user: return
    reason = message.text.replace("/warn", "", 1).strip() or "No reason"
    async with async_session() as session:
        db_user = await session.get(User, user.id)
        if not db_user:
            db_user = User(id=user.id, first_name=user.first_name, username=user.username)
            session.add(db_user)
            await session.flush()
        session.add(Warning(group_id=message.chat.id, user_id=user.id, reason=reason))
        await session.commit()
        stmt = select(Warning).where(Warning.group_id == message.chat.id, Warning.user_id == user.id)
        warns = (await session.execute(stmt)).scalars().all()
    await message.reply(f"⚠️ {user.full_name} ko warning di. Total: {len(warns)}\nReason: {reason}")


@router.message(Command("warns"))
async def warns_cmd(message: Message):
    user = await target(message)
    if not user: return
    async with async_session() as session:
        stmt = select(Warning).where(Warning.group_id == message.chat.id, Warning.user_id == user.id)
        warns = (await session.execute(stmt)).scalars().all()
    if not warns:
        return await message.reply(f"✅ {user.full_name} ke paas koi warning nahi hai.")
    text = f"⚠️ <b>{user.full_name}</b> ki warnings ({len(warns)}):\n\n"
    for i, w in enumerate(warns, 1): text += f"{i}. {w.reason} — {w.created_at.strftime('%Y-%m-%d')}\n"
    await message.reply(text)


@router.message(Command("rmwarn"))
async def rmwarn_cmd(message: Message):
    if not await admin_only(message): return
    user = await target(message)
    if not user: return
    async with async_session() as session:
        stmt = select(Warning).where(Warning.group_id == message.chat.id, Warning.user_id == user.id).order_by(Warning.id.desc()).limit(1)
        warn = (await session.execute(stmt)).scalar_one_or_none()
        if warn:
            await session.delete(warn)
            await session.commit()
            return await message.reply(f"✅ {user.full_name} ki ek warning hata di.")
    await message.reply("❌ Koi warning nahi mili.")


@router.message(Command("pin"))
async def pin_cmd(message: Message):
    if not await admin_only(message): return
    if not await target(message): return
    try:
        await message.reply_to_message.pin()
        await message.reply("📌 Pin ho gaya.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")


@router.message(Command("del"))
async def del_cmd(message: Message):
    if not await admin_only(message): return
    if not await target(message): return
    try:
        await message.reply_to_message.delete()
        await message.delete()
    except Exception as e:
        await message.reply(f"❌ Error: {e}")
