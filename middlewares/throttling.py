import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 1.0):
        self.rate_limit = rate_limit
        self.users = {}

    async def __call__(self, handler: Callable[[Message, dict[str, Any]], Awaitable[Any]], event: Message, data: dict[str, Any]) -> Any:
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)
        uid = event.from_user.id
        now = time.time()
        last = self.users.get(uid, 0)
        if now - last < self.rate_limit:
            return
        self.users[uid] = now
        return await handler(event, data)
