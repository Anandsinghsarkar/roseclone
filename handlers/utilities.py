import time
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, func
from database.models import Group, User, Warning, Lock
from database.session import async_session
from utils.permissions import is_chat_admin

router = Router()
_afk = {}

@router.message(Command("id"))
async def id_cmd(message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    if not target: return
    await message.reply(f"👤 <b>{target.full_name}</b>\n🆔 User ID: <code>{target.id}</code>\n💬 Chat ID: <code>{message.chat.id}</code>")

@router.message(Command("info"))
async def info_cmd(message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    if target:
        await message.reply(f"👤 <b>User Info</b>\nName: {target.full_name}\nUsername: @{target.username or '—'}\nID: <code>{target.id}</code>\nIs Bot: {target.is_bot}")

@router.message(Command("ping"))
async def ping_cmd(message: Message):
    start = time.time()
    sent = await message.reply("🏓 Pinging...")
    await sent.edit_text(f"🏓 Pong! <b>{(time.time() - start) * 1000:.2f} ms</b>")

@router.message(Command("stats"))
async def stats_cmd(message: Message):
    async with async_session() as session:
        groups = await session.scalar(select(func.count(Group.id)))
        users = await session.scalar(select(func.count(User.id)))
        warns = await session.scalar(select(func.count(Warning.id)))
    await message.reply(f"📊 <b>Anonymouse Stats</b>\nGroups: <b>{groups or 0}</b>\nKnown users: <b>{users or 0}</b>\nWarnings: <b>{warns or 0}</b>")

@router.message(Command("groupstats"))
async def group_stats(message: Message):
    if message.chat.type not in {"group", "supergroup"}:
        return await message.reply("Ye command group mein use karo.")
    async with async_session() as session:
        warns = await session.scalar(select(func.count(Warning.id)).where(Warning.group_id == message.chat.id))
        locks = await session.scalar(select(func.count(Lock.id)).where(Lock.group_id == message.chat.id, Lock.enabled.is_(True)))
    await message.reply(f"📊 <b>{message.chat.title}</b>\nWarnings recorded: {warns or 0}\nActive locks: {locks or 0}")

@router.message(Command("afk"))
async def afk_cmd(message: Message):
    reason = (message.text or "").partition(" ")[2].strip() or "AFK"
    _afk[message.from_user.id] = reason[:200]
    await message.reply(f"💤 AFK enabled: {reason[:200]} (bot restart par reset hoga).")

@router.message(Command("report"))
async def report_cmd(message: Message):
    if not message.reply_to_message:
        return await message.reply("Report karne ke liye kisi message par reply karke /report [reason] bhejo.")
    reason = (message.text or "").partition(" ")[2].strip() or "No reason provided"
    try:
        admins = await message.chat.get_administrators()
        sent = 0
        for admin in admins:
            if admin.user.is_bot: continue
            try:
                await message.bot.send_message(admin.user.id, f"🚨 <b>Report: {message.chat.title}</b>\nReporter: {message.from_user.full_name}\nReason: {reason}\nMessage: {message.reply_to_message.text or message.reply_to_message.caption or '[media]'}")
                sent += 1
            except Exception:
                continue
        await message.reply(f"✅ Report {sent} admin(s) ko bhej diya. Admins ne bot ko /start kiya hona chahiye.")
    except Exception:
        await message.reply("❌ Report send nahi ho saka.")

@router.message(Command("purge"))
async def purge_cmd(message: Message):
    if not await is_chat_admin(message):
        return await message.reply("⛔ Sirf group admin purge kar sakta hai.")
    if not message.reply_to_message:
        return await message.reply("Pehle message par reply karke /purge use karo.")
    first, last = message.reply_to_message.message_id, message.message_id
    if last - first > 100:
        return await message.reply("Ek baar mein maximum 100 messages purge kar sakte hain.")
    count = 0
    for message_id in range(first, last + 1):
        try:
            await message.bot.delete_message(message.chat.id, message_id)
            count += 1
        except Exception:
            pass
    status = await message.answer(f"🧹 {count} messages delete kiye.")
    await status.delete()

@router.message(Command("admins"))
async def admins_cmd(message: Message):
    try:
        admins = await message.chat.get_administrators()
        lines = [f"• {a.user.full_name}" + (f" (@{a.user.username})" if a.user.username else "") for a in admins]
        await message.reply("👑 <b>Admins</b>\n\n" + "\n".join(lines))
    except Exception as exc:
        await message.reply(f"❌ {exc}")
