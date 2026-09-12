import time

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("id"))
async def id_cmd(message: Message):
    if message.reply_to_message:
        u = message.reply_to_message.from_user
        return await message.reply(f"👤 <b>{u.full_name}</b>\n🆔 User ID: <code>{u.id}</code>\n💬 Chat ID: <code>{message.chat.id}</code>")
    await message.reply(f"👤 <b>{message.from_user.full_name}</b>\n🆔 Your ID: <code>{message.from_user.id}</code>\n💬 Chat ID: <code>{message.chat.id}</code>")


@router.message(Command("info"))
async def info_cmd(message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    await message.reply(f"👤 <b>User Info</b>\n\nName: {target.full_name}\nUsername: @{target.username if target.username else '—'}\nID: <code>{target.id}</code>\nIs Bot: {target.is_bot}")


@router.message(Command("ping"))
async def ping_cmd(message: Message):
    start = time.time()
    sent = await message.reply("🏓 Pinging...")
    ms = (time.time() - start) * 1000
    await sent.edit_text(f"🏓 Pong! <b>{ms:.2f} ms</b>")


@router.message(Command("stats"))
async def stats_cmd(message: Message):
    await message.reply(f"📊 <b>Bot Stats</b>\n\nChat ID: <code>{message.chat.id}</code>\nChat Type: {message.chat.type}")


@router.message(Command("admins"))
async def admins_cmd(message: Message):
    try:
        admins = await message.chat.get_administrators()
        text = "👑 <b>Admins:</b>\n\n"
        for a in admins:
            text += f"• {a.user.full_name}"
            if a.user.username:
                text += f" (@{a.user.username})"
            text += "\n"
        await message.reply(text)
    except Exception as e:
        await message.reply(f"❌ {e}")
