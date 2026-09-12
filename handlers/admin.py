from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import delete, select

from config import settings
from database.models import BotAdmin, Group, User
from database.session import async_session
from utils.permissions import is_bot_admin

router = Router()


def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Stats", callback_data="admin:stats"), InlineKeyboardButton(text="👥 Admins", callback_data="admin:list")],
        [InlineKeyboardButton(text="➕ Add admin", callback_data="admin:add_help"), InlineKeyboardButton(text="➖ Remove admin", callback_data="admin:remove_help")],
    ])


async def owner_only(message: Message) -> bool:
    if message.from_user and message.from_user.id == settings.BOT_OWNER_ID:
        return True
    await message.reply("⛔ Sirf bot owner ye action kar sakta hai.")
    return False


@router.message(Command("admin"))
async def admin_cmd(message: Message):
    if not await is_bot_admin(message.from_user.id):
        return await message.reply("⛔ Admin access required.")
    await message.answer("<b>🌹 Rose Clone Admin Panel</b>\n\nOwner global admins manage kar sakta hai.\nAdmins group me normal Telegram admin checks ke saath kaam karte hain.", reply_markup=admin_kb())


@router.message(Command("addadmin"))
async def add_admin(message: Message):
    if not await owner_only(message):
        return
    try:
        user_id = int(message.text.split(maxsplit=1)[1])
    except (IndexError, ValueError):
        return await message.reply("Usage: <code>/addadmin 123456789</code>")
    async with async_session() as session:
        existing = await session.get(BotAdmin, user_id)
        if existing:
            return await message.reply("✅ Ye user pehle se admin hai.")
        session.add(BotAdmin(user_id=user_id, added_by=message.from_user.id))
        await session.commit()
    await message.reply(f"✅ <code>{user_id}</code> ko bot admin bana diya.")


@router.message(Command("deladmin"))
async def del_admin(message: Message):
    if not await owner_only(message):
        return
    try:
        user_id = int(message.text.split(maxsplit=1)[1])
    except (IndexError, ValueError):
        return await message.reply("Usage: <code>/deladmin 123456789</code>")
    if user_id == settings.BOT_OWNER_ID:
        return await message.reply("❌ Owner ko remove nahi kiya ja sakta.")
    async with async_session() as session:
        await session.execute(delete(BotAdmin).where(BotAdmin.user_id == user_id))
        await session.commit()
    await message.reply(f"✅ <code>{user_id}</code> ka admin access hata diya.")


@router.callback_query(lambda c: c.data == "admin:stats")
async def stats_cb(callback):
    if not await is_bot_admin(callback.from_user.id):
        return await callback.answer("Admin access required", show_alert=True)
    async with async_session() as session:
        groups = len((await session.execute(select(Group.id))).scalars().all())
        users = len((await session.execute(select(User.id))).scalars().all())
        admins = len((await session.execute(select(BotAdmin.user_id))).scalars().all())
    await callback.message.answer(f"📊 <b>Stats</b>\n\nGroups: <b>{groups}</b>\nUsers: <b>{users}</b>\nExtra admins: <b>{admins}</b>\nOwner ID: <code>{settings.BOT_OWNER_ID}</code>")
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin:list")
async def list_cb(callback):
    if not await is_bot_admin(callback.from_user.id):
        return await callback.answer("Admin access required", show_alert=True)
    async with async_session() as session:
        admins = (await session.execute(select(BotAdmin))).scalars().all()
    lines = [f"👑 Owner: <code>{settings.BOT_OWNER_ID}</code>"]
    lines += [f"• <code>{a.user_id}</code>" + (f" @{a.username}" if a.username else "") for a in admins]
    await callback.message.answer("<b>👥 Global admins</b>\n\n" + "\n".join(lines))
    await callback.answer()


@router.callback_query(lambda c: c.data in {"admin:add_help", "admin:remove_help"})
async def admin_help_cb(callback):
    if not await is_bot_admin(callback.from_user.id):
        return await callback.answer("Admin access required", show_alert=True)
    if callback.data == "admin:add_help":
        text = "➕ Add admin\nUse <code>/addadmin USER_ID</code>"
    else:
        text = "➖ Remove admin\nUse <code>/deladmin USER_ID</code>"
    await callback.message.answer(text)
    await callback.answer()
