import re
from datetime import datetime, timedelta

from aiogram import BaseMiddleware
from aiogram.types import ChatPermissions, Message
from sqlalchemy import delete, select

from database.models import Group, Lock, User, Warning, WarningPolicy
from database.session import async_session
from utils.permissions import is_chat_admin

URL_RE = re.compile(r"(?:https?://|www\.)\S+|t\.me/\S+", re.I)


def message_lock_types(message: Message) -> set[str]:
    found = set()
    if message.text and not message.text.startswith("/"):
        found.add("text")
        if URL_RE.search(message.text):
            found.add("links")
    if message.photo: found.add("photos")
    if message.video: found.add("videos")
    if message.sticker: found.add("stickers")
    if message.animation: found.add("gifs")
    if message.audio: found.add("audio")
    if message.voice: found.add("voice")
    if message.document: found.add("documents")
    if message.forward_origin: found.add("forwards")
    if message.from_user and message.from_user.is_bot: found.add("bots")
    return found


class LockEnforcementMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if not isinstance(event, Message) or event.chat.type not in {"group", "supergroup"} or not event.from_user:
            return await handler(event, data)
        if event.text and event.text.startswith("/"):
            return await handler(event, data)
        if await is_chat_admin(event):
            await self._remember_user(event)
            return await handler(event, data)
        async with async_session() as session:
            locks = set((await session.execute(select(Lock.lock_type).where(Lock.group_id == event.chat.id, Lock.enabled.is_(True)))).scalars().all())
        violations = message_lock_types(event) & locks
        await self._remember_user(event)
        if not violations:
            return await handler(event, data)
        try:
            await event.delete()
        except Exception:
            pass
        reason = "Locked: " + ", ".join(sorted(violations))
        async with async_session() as session:
            group = await session.get(Group, event.chat.id)
            if not group:
                group = Group(id=event.chat.id, title=event.chat.title or "")
                session.add(group)
            user = await session.get(User, event.from_user.id)
            if not user:
                user = User(id=event.from_user.id, username=event.from_user.username, first_name=event.from_user.first_name or event.from_user.full_name)
                session.add(user)
            policy = await session.get(WarningPolicy, event.chat.id)
            if not policy:
                policy = WarningPolicy(group_id=event.chat.id, threshold=group.warn_limit or 3, mute_minutes=30)
                session.add(policy)
                await session.flush()
            session.add(Warning(group_id=event.chat.id, user_id=event.from_user.id, reason=reason))
            count = len((await session.execute(select(Warning.id).where(Warning.group_id == event.chat.id, Warning.user_id == event.from_user.id))).scalars().all())
            threshold = max(1, policy.threshold)
            mute_minutes = max(1, policy.mute_minutes)
            should_mute = count >= threshold
            if should_mute and policy.reset_after_mute:
                await session.execute(delete(Warning).where(Warning.group_id == event.chat.id, Warning.user_id == event.from_user.id))
            await session.commit()
        if should_mute:
            try:
                until = datetime.utcnow() + timedelta(minutes=mute_minutes)
                await event.chat.restrict(event.from_user.id, permissions=ChatPermissions(can_send_messages=False), until_date=until)
                await event.answer(f"🔇 <b>{event.from_user.full_name}</b> ko {mute_minutes} minute ke liye mute kiya gaya.\nReason: {reason}")
            except Exception:
                pass
        else:
            try:
                await event.answer(f"⚠️ <b>{event.from_user.full_name}</b> ko warning {count}/{threshold} mili.\nReason: {reason}")
            except Exception:
                pass
        return None

    async def _remember_user(self, event: Message):
        async with async_session() as session:
            user = await session.get(User, event.from_user.id)
            if not user:
                user = User(id=event.from_user.id, username=event.from_user.username, first_name=event.from_user.first_name or event.from_user.full_name)
                session.add(user)
            else:
                user.username = event.from_user.username
                user.first_name = event.from_user.first_name or event.from_user.full_name
            await session.commit()
