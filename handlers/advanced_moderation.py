from datetime import datetime, timedelta, timezone
import re

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import ChatPermissions, Message
from sqlalchemy import select

from database.models import AdminAction
from database.session import async_session
from utils.permissions import is_chat_admin

router = Router()

_DURATION = re.compile(r"^(\d+)([mhd])$", re.IGNORECASE)


def parse_duration(value: str):
    match = _DURATION.fullmatch(value.strip())
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2).lower()
    limits = {"m": 30 * 24 * 60, "h": 30 * 24, "d": 30}
    if amount < 1 or amount > limits[unit]:
        return None
    return timedelta(minutes=amount if unit == "m" else amount * 60 if unit == "h" else amount * 1440)


async def log_action(group_id: int, actor_id: int, target_id: int | None, action: str, details: str = ""):
    async with async_session() as session:
        session.add(AdminAction(group_id=group_id, actor_id=actor_id, target_id=target_id, action=action, details=details[:1000]))
        await session.commit()


async def _target(message: Message):
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply("❌ Target user ke message par reply karke command use karo.")
        return None
    return message.reply_to_message.from_user


@router.message(Command("tban"))
async def temporary_ban(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not await is_chat_admin(message):
        return await message.reply("⛔ Sirf group admin ye command use kar sakta hai.")
    user = await _target(message)
    if not user:
        return
    parts = (message.text or "").split(maxsplit=2)
    duration = parse_duration(parts[1]) if len(parts) > 1 else None
    if duration is None:
        return await message.reply("Usage: target ke message par reply karke /tban 30m [reason] — units: m, h, d; max 30 days.")
    reason = parts[2] if len(parts) > 2 else "No reason provided"
    until = datetime.now(timezone.utc) + duration
    try:
        await message.chat.ban(user.id, until_date=until)
        await log_action(message.chat.id, message.from_user.id, user.id, "temporary_ban", f"until={until.isoformat()}; reason={reason}")
        await message.reply(f"⏳ {user.full_name} ko temporary ban kiya gaya. Duration: {parts[1]}.")
    except Exception as exc:
        await message.reply(f"❌ Temporary ban nahi ho saka: {exc}")


@router.message(Command("tmute"))
async def temporary_mute(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not await is_chat_admin(message):
        return await message.reply("⛔ Sirf group admin ye command use kar sakta hai.")
    user = await _target(message)
    if not user:
        return
    parts = (message.text or "").split(maxsplit=2)
    duration = parse_duration(parts[1]) if len(parts) > 1 else None
    if duration is None:
        return await message.reply("Usage: target ke message par reply karke /tmute 30m [reason] — units: m, h, d; max 30 days.")
    reason = parts[2] if len(parts) > 2 else "No reason provided"
    until = datetime.now(timezone.utc) + duration
    try:
        await message.bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
        await log_action(message.chat.id, message.from_user.id, user.id, "temporary_mute", f"until={until.isoformat()}; reason={reason}")
        await message.reply(f"🔇 {user.full_name} ko temporary mute kiya gaya. Duration: {parts[1]}.")
    except Exception as exc:
        await message.reply(f"❌ Temporary mute nahi ho saka: {exc}")


@router.message(Command("logs"))
async def action_logs(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not await is_chat_admin(message):
        return await message.reply("⛔ Admin-only command.")
    async with async_session() as session:
        rows = (await session.execute(
            select(AdminAction)
            .where(AdminAction.group_id == message.chat.id)
            .order_by(AdminAction.created_at.desc())
            .limit(15)
        )).scalars().all()
    if not rows:
        return await message.reply("📋 Abhi koi admin action log nahi hai.")
    lines = []
    for row in rows:
        when = row.created_at.strftime("%d-%m %H:%M") if row.created_at else "unknown"
        lines.append(f"• <b>{row.action}</b> | actor <code>{row.actor_id}</code> | target <code>{row.target_id or '—'}</code> | {when}")
    await message.reply("📋 <b>Recent admin actions</b>\n\n" + "\n".join(lines))
