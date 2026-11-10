import time
from collections import defaultdict, deque
from aiogram import BaseMiddleware
from aiogram.types import Message
from database.models import Group
from database.session import async_session
from utils.permissions import is_chat_admin

class AntiAbuseMiddleware(BaseMiddleware):
    def __init__(self, window_seconds: int = 6):
        self.window_seconds = window_seconds
        self.messages = defaultdict(deque)
        self.last_text = {}

    async def __call__(self, handler, event, data):
        if not isinstance(event, Message) or event.chat.type not in {"group", "supergroup"} or not event.from_user:
            return await handler(event, data)
        if event.from_user.is_bot or (event.text and event.text.startswith("/")) or await is_chat_admin(event):
            return await handler(event, data)
        now = time.monotonic()
        key = (event.chat.id, event.from_user.id)
        bucket = self.messages[key]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        bucket.append(now)
        async with async_session() as session:
            group = await session.get(Group, event.chat.id)
            limit = max(3, min(50, group.flood_limit if group else 5))
        body = (event.text or event.caption or "").strip().casefold()
        duplicate = bool(body and self.last_text.get(key) == body and now - self.last_text.get((key, "time"), 0) < 20)
        self.last_text[key] = body
        self.last_text[(key, "time")] = now
        if duplicate or len(bucket) > limit:
            try:
                await event.delete()
            except Exception:
                pass
            if len(bucket) > limit:
                bucket.clear()
                try:
                    await event.answer("🚦 Flood detected. Please slow down.")
                except Exception:
                    pass
            return None
        return await handler(event, data)
