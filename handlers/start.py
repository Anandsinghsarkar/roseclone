from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import settings
from utils.permissions import is_bot_admin, is_chat_admin, is_chat_admin_id
from utils.setup import build_setup_url

router = Router()


def main_kb(is_group=False, include_admin=False):
    rows = [
        [InlineKeyboardButton(text="🛡 Moderation", callback_data="menu:moderation"), InlineKeyboardButton(text="🔒 Locks", callback_data="menu:locks")],
        [InlineKeyboardButton(text="⚠️ Warnings", callback_data="menu:warnings"), InlineKeyboardButton(text="👋 Welcome", callback_data="menu:welcome")],
        [InlineKeyboardButton(text="📜 Rules", callback_data="menu:rules"), InlineKeyboardButton(text="📝 Notes", callback_data="menu:notes")],
        [InlineKeyboardButton(text="👮 Admins", callback_data="menu:admins"), InlineKeyboardButton(text="⌨️ Commands", callback_data="menu:custom")],
        [InlineKeyboardButton(text="🧰 Utilities", callback_data="menu:utilities"), InlineKeyboardButton(text="⚙️ Setup Panel", callback_data="menu:setup")],
    ]
    if include_admin:
        rows.append([InlineKeyboardButton(text="👑 Anonymouse Admin", callback_data="open_admin")])
    rows.append([InlineKeyboardButton(text="❓ Help", callback_data="menu:help")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(CommandStart())
async def start_cmd(message: Message):
    is_admin = await is_bot_admin(message.from_user.id) if message.from_user else False
    await message.answer(
        "👻 <b>Anonymouse</b>\n\nGroup management, moderation, warnings, locks, welcome, rules, notes aur custom commands ek hi button panel se manage karo.\n\nBot ko group admin rights dena required hai.",
        reply_markup=main_kb(message.chat.type in {"group", "supergroup"}, is_admin),
    )


@router.message(Command("menu"))
async def menu_cmd(message: Message):
    is_admin = await is_bot_admin(message.from_user.id) if message.from_user else False
    await message.answer("👻 <b>Anonymouse Menu</b>", reply_markup=main_kb(message.chat.type in {"group", "supergroup"}, is_admin))


@router.message(Command("setup"))
async def setup_cmd(message: Message):
    if message.chat.type not in {"group", "supergroup", "channel"}:
        return await message.reply("⚙️ /setup ko apne group/channel me run karo.")
    if not await is_chat_admin(message):
        return await message.reply("⛔ Sirf Telegram admin setup panel khol sakta hai.")
    try:
        url = build_setup_url(message.chat.id, message.from_user.id)
    except RuntimeError:
        return await message.reply("❌ Railway me WEB_APP_URL set karo.")
    await message.reply("✅ Admin verified. Setup link 30 minutes me expire hoga.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚙️ Open Anonymouse Panel", url=url)]]))


@router.callback_query(lambda c: c.data == "menu:setup")
async def setup_cb(callback):
    if callback.message.chat.type not in {"group", "supergroup"}:
        return await callback.answer("Setup group me open karo.", show_alert=True)
    if not await is_chat_admin_id(callback.bot, callback.message.chat.id, callback.from_user.id):
        return await callback.answer("Sirf group admin setup kar sakta hai.", show_alert=True)
    try:
        url = build_setup_url(callback.message.chat.id, callback.from_user.id)
    except RuntimeError:
        return await callback.answer("WEB_APP_URL configured nahi hai.", show_alert=True)
    await callback.message.answer("⚙️ <b>Anonymouse Setup Panel</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Open Web Panel", url=url)]]))
    await callback.answer()


MENU_TEXT = {
    "menu:moderation": "🛡 <b>Moderation</b>\nReply karke: /ban /unban /kick /mute /unmute /warn /warns /rmwarn /pin /del",
    "menu:locks": "🔒 <b>Locks</b>\n/lock TYPE • /unlock TYPE • /locks\nTypes: text, links, photos, videos, stickers, gifs, forwards, bots, audio, voice, documents\nLocked content automatically delete hoga aur warning jayegi.",
    "menu:warnings": "⚠️ <b>Warnings</b>\nLocked content par warning automatically. Threshold hit hone par configured duration ka mute. Buttons se threshold/mute duration set karo: 👑 Admin → Warning Policy.",
    "menu:welcome": "👋 <b>Welcome</b>\nVariables: {name}, {group}\n/setwelcome, /welcome, /setgoodbye, /goodbye. Web panel se message aur toggle manage karo.",
    "menu:rules": "📜 <b>Rules</b>\n/setrules, /rules. Web panel se edit karo.",
    "menu:notes": "📝 <b>Notes</b>\n/save name → reply\n/get name • /notes • /clear name",
    "menu:admins": "👮 <b>Group Admins</b>\n/admins list dekho. Group admin: <code>/promote @username</code> aur <code>/demote @username</code>.",
    "menu:custom": "⌨️ <b>Custom Commands</b>\nGroup admin: <code>/addcmd hello Hello {name}</code>\nDelete: <code>/delcmd hello</code>",
    "menu:utilities": "🧰 <b>Utilities</b>\n/id • /info • /ping • /stats",
    "menu:help": "❓ <b>Help</b>\nAnonymouse ko group admin banao. Locked content ko bot delete karega, warning dega aur policy ke hisaab se mute karega.",
}


@router.callback_query(lambda c: c.data in MENU_TEXT)
async def menu_section(callback):
    if callback.data in {"menu:moderation", "menu:locks", "menu:warnings", "menu:admins", "menu:custom"} and callback.message.chat.type in {"group", "supergroup"}:
        if not await is_chat_admin_id(callback.bot, callback.message.chat.id, callback.from_user.id):
            return await callback.answer("Ye tools sirf group admins ke liye hain.", show_alert=True)
    await callback.message.answer(MENU_TEXT[callback.data], reply_markup=main_kb(callback.message.chat.type in {"group", "supergroup"}, await is_bot_admin(callback.from_user.id)))
    await callback.answer()


@router.callback_query(lambda c: c.data == "open_admin")
async def open_admin(callback):
    if not await is_bot_admin(callback.from_user.id):
        return await callback.answer("Admin access required", show_alert=True)
    await callback.message.answer("👑 <b>Anonymouse Admin Panel</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Open Admin", callback_data="admin:open")]]))
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin:open")
async def admin_open(callback):
    if not await is_bot_admin(callback.from_user.id):
        return await callback.answer("Admin access required", show_alert=True)
    await callback.message.answer("Use /admin to open the complete admin controls.")
    await callback.answer()


@router.message(Command("panel"))
async def panel_cmd(message: Message):
    if await is_bot_admin(message.from_user.id):
        await message.answer("👑 <b>Anonymouse Admin Panel</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Open Admin", callback_data="admin:open")]]))
