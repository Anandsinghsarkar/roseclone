from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import settings
from utils.permissions import is_bot_admin, is_chat_admin, is_chat_admin_id
from utils.setup import build_setup_url

router = Router()


def main_kb(is_group: bool = False, include_admin: bool = False):
    rows = [
        [InlineKeyboardButton(text="🛡 Moderation", callback_data="menu:moderation"), InlineKeyboardButton(text="🔒 Locks", callback_data="menu:locks")],
        [InlineKeyboardButton(text="👋 Welcome", callback_data="menu:welcome"), InlineKeyboardButton(text="📜 Rules", callback_data="menu:rules")],
        [InlineKeyboardButton(text="📝 Notes", callback_data="menu:notes"), InlineKeyboardButton(text="🧰 Utilities", callback_data="menu:utilities")],
    ]
    if is_group:
        rows.append([InlineKeyboardButton(text="⚙️ Group Setup", callback_data="menu:setup")])
    if include_admin:
        rows.append([InlineKeyboardButton(text="👑 Bot Admin", callback_data="open_admin")])
    rows.append([InlineKeyboardButton(text="❓ Help", callback_data="menu:help"), InlineKeyboardButton(text="📋 Commands", callback_data="menu:commands")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(CommandStart())
async def start_cmd(message: Message):
    is_admin = await is_bot_admin(message.from_user.id) if message.from_user else False
    text = (
        "🌹 <b>Rose Clone Bot</b>\n\n"
        "Group/channel management ke liye tools ko buttons me organize kiya gaya hai.\n"
        "Group me add karke <b>⚙️ Group Setup</b> se web dashboard kholo.\n\n"
        f"<b>Owner ID:</b> <code>{settings.BOT_OWNER_ID}</code>"
    )
    await message.answer(text, reply_markup=main_kb(message.chat.type in {"group", "supergroup"}, is_admin))


@router.message(Command("menu"))
async def menu_cmd(message: Message):
    is_admin = await is_bot_admin(message.from_user.id) if message.from_user else False
    await message.answer("🌹 <b>Rose Clone Menu</b>\n\nNeeche se tool choose karo:", reply_markup=main_kb(message.chat.type in {"group", "supergroup"}, is_admin))


@router.message(Command("setup"))
async def setup_cmd(message: Message):
    if message.chat.type not in {"group", "supergroup", "channel"}:
        return await message.reply("⚙️ /setup ko apne group ya channel me run karo.")
    if not await is_chat_admin(message):
        return await message.reply("⛔ Sirf Telegram group/channel admin setup page khol sakta hai.")
    try:
        url = build_setup_url(message.chat.id, message.from_user.id)
    except RuntimeError:
        return await message.reply("❌ Setup panel configured nahi hai. Railway me WEB_APP_URL set karo.")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚙️ Open Setup Panel", url=url)]])
    await message.reply("✅ Aap admin verify ho gaye. Setup link 30 minutes me expire ho jayega.", reply_markup=kb)


@router.callback_query(lambda c: c.data == "menu:setup")
async def setup_cb(callback):
    if callback.message.chat.type not in {"group", "supergroup"}:
        return await callback.answer("Setup button group ke andar use karo.", show_alert=True)
    if not await is_chat_admin_id(callback.bot, callback.message.chat.id, callback.from_user.id):
        return await callback.answer("Sirf group admin setup kar sakta hai.", show_alert=True)
    try:
        url = build_setup_url(callback.message.chat.id, callback.from_user.id)
    except RuntimeError:
        return await callback.answer("WEB_APP_URL configured nahi hai.", show_alert=True)
    await callback.message.answer("⚙️ <b>Group Setup Panel</b>\n\nWelcome, goodbye, rules, limits aur locks browser me manage karo. Link 30 minutes me expire hoga.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Open Setup Panel", url=url)]]))
    await callback.answer()


MENU_TEXT = {
    "menu:moderation": "🛡 <b>Moderation</b>\n\nReply karke use karo:\n/ban /unban /kick /mute /unmute\n/warn /warns /rmwarn /pin /del",
    "menu:locks": "🔒 <b>Locks</b>\n\n/lock TYPE\n/unlock TYPE\n/locks\n\nTypes: links, photos, videos, stickers, gifs, forwards, bots, text",
    "menu:welcome": "👋 <b>Welcome</b>\n\n/setwelcome TEXT\n/welcome\n/setgoodbye TEXT\n/goodbye\n\nWeb dashboard se enable/disable aur text edit kar sakte ho.",
    "menu:rules": "📜 <b>Rules</b>\n\n/setrules TEXT\n/rules\n\nWeb dashboard se rules bhi edit kar sakte ho.",
    "menu:notes": "📝 <b>Notes</b>\n\n/save name TEXT\n/get name\n/notes\n/clear name",
    "menu:utilities": "🧰 <b>Utilities</b>\n\n/id\n/info\n/ping\n/stats",
    "menu:help": "❓ <b>Help</b>\n\nBot ko group me admin rights do. Management actions ke liye aapko Telegram admin hona chahiye.",
    "menu:commands": "📋 <b>Commands</b>\n\n/admin\n/setup\n/menu\n/ban /unban /kick /mute /unmute\n/warn /warns /rmwarn\n/lock /unlock /locks\n/save /get /notes /clear\n/setwelcome /welcome /setgoodbye /goodbye\n/setrules /rules /id /info /ping /stats",
}


@router.callback_query(lambda c: c.data in MENU_TEXT)
async def menu_section(callback):
    if callback.data == "menu:moderation" and callback.message.chat.type in {"group", "supergroup"}:
        if not await is_chat_admin_id(callback.bot, callback.message.chat.id, callback.from_user.id):
            return await callback.answer("Moderation tools sirf admins use kar sakte hain.", show_alert=True)
    await callback.message.answer(MENU_TEXT[callback.data], reply_markup=main_kb(callback.message.chat.type in {"group", "supergroup"}, await is_bot_admin(callback.from_user.id)))
    await callback.answer()


@router.message(Command("panel"))
async def panel_cmd(message: Message):
    if await is_bot_admin(message.from_user.id):
        await message.answer("👑 <b>Bot Admin Panel</b>\nUse /admin", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Open Admin Panel", callback_data="open_admin")]]))


@router.callback_query(lambda c: c.data == "open_admin")
async def open_admin(callback):
    if not await is_bot_admin(callback.from_user.id):
        return await callback.answer("Admin access required", show_alert=True)
    await callback.message.answer("👑 Admin panel ke liye /admin run karo.")
    await callback.answer()
