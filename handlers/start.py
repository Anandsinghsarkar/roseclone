from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import settings

router = Router()


@router.message(CommandStart())
async def start_cmd(message: Message):
    text = (
        "👋 <b>Welcome to Rose Clone Bot!</b>\n\n"
        "Main ek group management bot hoon. Mujhe apne group me add karke moderation, welcome, locks, notes aur utilities use kar sakte ho.\n\n"
        f"<b>Owner ID:</b> <code>{settings.BOT_OWNER_ID}</code>\n\n"
        "👇 Neeche se option chuno:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add to Group", url="https://t.me/YourBot?startgroup=true")],
        [InlineKeyboardButton(text="📚 Help", callback_data="help"), InlineKeyboardButton(text="⚙️ Commands", callback_data="commands")],
    ])
    await message.answer(text, reply_markup=kb)


@router.callback_query(lambda c: c.data == "help")
async def help_cb(callback):
    await callback.message.answer("<b>Available Commands:</b>\n\n/ban /unban /kick /mute /unmute\n/warn /rmwarn /warns\n/lock /unlock /locks\n/save /get /notes /clear\n/setwelcome /welcome /setgoodbye /goodbye\n/setrules /rules\n/id /info /ping /stats")
    await callback.answer()


@router.callback_query(lambda c: c.data == "commands")
async def commands_cb(callback):
    await callback.message.answer("<b>Command List:</b>\n\n🛡 Moderation: /ban /kick /mute /warn\n🔒 Locks: /lock /unlock /locks\n📝 Notes: /save /get /notes\n👋 Welcome: /setwelcome /welcome\n📜 Rules: /setrules /rules\nℹ️ Utility: /id /info /ping")
    await callback.answer()
