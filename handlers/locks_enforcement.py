import re
from datetime import datetime, timedelta

from aiogram import Router
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatPermissions, Message
from sqlalchemy import delete, select

from database.models import Group, Lock, User, Warning, WarningPolicy
from database.session import async_session
from utils.permissions import is_chat_admin

router = Router()

LOCK_TYPES = {
    "text", "links", "photos", "videos", "stickers", "gifs", "forwards", "bots", "audio", "voice", "documents"
}
URL_RE = re.compile(r"(?:https?://|www\.)\S+|t\.me/\S+", re.I)


def message_lock_types(message: Message) -> set[str]:
    found = set()
    if message.text and not message.text.startswith("/"):
        found.add("text")
        if URL_RE.search(message.text):
            found.add("links")
    if message.photo:
        found.add("photos")
    if message.video:
        found.add("videos")
    if message.sticker:
        found.add("stickers")
    if message.animation:
        found.add("gifs")
    if message.audio:
        found.add("audio")
    if message.voice:
        found.add("voice")
    if message.document:
        found.add("documents")
    if message.forward_origin:
        found.add("forwards")
    if message.from_user and message.from_user.is_bot:
        found.add("bots")
    return found


async def ensure_user(message: Message):
    if not message.from_user:
        return
    async with async_session() as session:
        user = await session.get(User, message.from_user.id)
        if not user:
            user = User(id=message.from_user.id)
            session.add(user)
        user.username = message.from_user.username
        user.first_name = message.from_user.first_name or message.from_user.full_name
        await session.commit()


async def active_locks(chat_id: int) -> set[str]:
    async with async_session() as session:
        stmt = select(Lock.lock_type).where(Lock.group_id == chat_id, Lock.enabled.is_(True))
        return set((await session.execute(stmt)).scalars().all())


async def apply_warning(message: Message, reason: str) -> tuple[int, int, bool]:
    user = message.from_user
    async with async_session() as session:
        group = await session.get(Group, message.chat.id)
        if not group:
            group = Group(id=message.chat.id, title=message.chat.title or "")
            session.add(group)
        user_row = await session.get(User, user.id)
        if not user_row:
            user_row = User(id=user.id, username=user.username, first_name=user.first_name or user.full_name)
            session.add(user_row)
        policy = await session.get(WarningPolicy, message.chat.id)
        if not policy:
            policy = WarningPolicy(group_id=message.chat.id, threshold=group.warn_limit or 3, mute_minutes=30)
            session.add(policy)
            await session.flush()
        session.add(Warning(group_id=message.chat.id, user_id=user.id, reason=reason))
        stmt = select(Warning).where(Warning.group_id == message.chat.id, Warning.user_id == user.id)
        warnings = len((await session.execute(stmt)).scalars().all())
        threshold = max(1, policy.threshold)
        mute_minutes = max(1, policy.mute_minutes)
        should_mute = warnings >= threshold
        if should_mute and policy.reset_after_mute:
            await session.execute(delete(Warning).where(Warning.group_id == message.chat.id, Warning.user_id == user.id))
        await session.commit()
    return warnings, mute_minutes, should_mute


@router.message()
async def enforce_locks(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not message.from_user:
        return
    if await is_chat_admin(message):
        await ensure_user(message)
        return
    locks = await active_locks(message.chat.id)
    if not locks:
        await ensure_user(message)
        return
    violations = message_lock_types(message) & locks
    if not violations:
        await ensure_user(message)
        return
    try:
        await message.delete()
    except Exception:
        pass
    reason = "Locked: " + ", ".join(sorted(violations))
    warnings, mute_minutes, should_mute = await apply_warning(message, reason)
    if should_mute:
        try:
            until = datetime.utcnow() + timedelta(minutes=mute_minutes)
            await message.chat.restrict(
                message.from_user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until,
            )
            await message.answer(
                f"🔇 <b>{message.from_user.full_name}</b> ko {mute_minutes} minute ke liye mute kiya gaya.\n"
                f"Reason: {reason}"
            )
        except Exception:
            pass
    else:
        await message.answer(
            f"⚠️ <b>{message.from_user.full_name}</b> warning {warnings} par hai.\n"
            f"Reason: {reason}"
        )
