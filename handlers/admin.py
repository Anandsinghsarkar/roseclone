from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import delete, select

from config import settings
from database.models import BotAdmin, Group, User, WarningPolicy
from database.session import async_session
from utils.permissions import is_bot_admin, is_chat_admin

router = Router()


def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Stats", callback_data="admin:stats"), InlineKeyboardButton(text="👥 Bot Admins", callback_data="admin:list")],
        [InlineKeyboardButton(text="👮 Group Admins", callback_data="admin:group_list")],
        [InlineKeyboardButton(text="➕ Add Bot Admin", callback_data="admin:add_help"), InlineKeyboardButton(text="➖ Remove Bot Admin", callback_data="admin:remove_help")],
        [InlineKeyboardButton(text="⚠️ Warning Policy", callback_data="admin:warning_policy")],
        [InlineKeyboardButton(text="⌨️ Custom Commands", callback_data="admin:commands_help")],
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
    await message.answer("<b>👻 Anonymouse Admin Panel</b>\n\nGlobal bot admins, warning policy aur custom commands yahan manage karo.", reply_markup=admin_kb())


@router.message(Command("addadmin"))
async def add_admin(message: Message):
    if not await owner_only(message): return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return await message.reply("Usage: <code>/addadmin USER_ID</code>")
    try: user_id = int(parts[1].strip())
    except ValueError: return await message.reply("❌ USER_ID numeric hona chahiye.")
    async with async_session() as session:
        existing = await session.get(BotAdmin, user_id)
        if existing: return await message.reply("✅ Ye user pehle se bot admin hai.")
        session.add(BotAdmin(user_id=user_id, added_by=message.from_user.id))
        await session.commit()
    await message.reply(f"✅ <code>{user_id}</code> ko bot admin bana diya.")


@router.message(Command("deladmin"))
async def del_admin(message: Message):
    if not await owner_only(message): return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return await message.reply("Usage: <code>/deladmin USER_ID</code>")
    try: user_id = int(parts[1].strip())
    except ValueError: return await message.reply("❌ USER_ID numeric hona chahiye.")
    if user_id == settings.BOT_OWNER_ID: return await message.reply("❌ Owner ko remove nahi kiya ja sakta.")
    async with async_session() as session:
        await session.execute(delete(BotAdmin).where(BotAdmin.user_id == user_id))
        await session.commit()
    await message.reply(f"✅ <code>{user_id}</code> ka bot-admin access hata diya.")


@router.message(Command("promote"))
async def promote_cmd(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not await is_chat_admin(message):
        return await message.reply("⛔ Sirf group admin promote kar sakta hai.")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return await message.reply("Usage: <code>/promote @username</code>")
    username = parts[1].strip().lstrip("@").lower()
    async with async_session() as session:
        stmt = select(User).where(User.username == username)
        target = (await session.execute(stmt)).scalar_one_or_none()
    if not target:
        return await message.reply("❌ User database me nahi mila. Pehle us user ka koi message bot ko receive hone do.")
    try:
        await message.chat.promote(target.id, can_manage_chat=True, can_delete_messages=True, can_invite_users=True, can_restrict_members=True, can_pin_messages=True, can_change_info=False)
        await message.reply(f"✅ @{username} ko group admin bana diya.")
    except Exception as exc:
        await message.reply(f"❌ Promote failed: {exc}")


@router.message(Command("demote"))
async def demote_cmd(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not await is_chat_admin(message):
        return await message.reply("⛔ Sirf group admin demote kar sakta hai.")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return await message.reply("Usage: <code>/demote @username</code>")
    username = parts[1].strip().lstrip("@").lower()
    async with async_session() as session:
        target = (await session.execute(select(User).where(User.username == username))).scalar_one_or_none()
    if not target: return await message.reply("❌ User database me nahi mila.")
    try:
        await message.chat.promote(target.id, can_manage_chat=False, can_delete_messages=False, can_invite_users=False, can_restrict_members=False, can_pin_messages=False, can_change_info=False)
        await message.reply(f"✅ @{username} ko group admin se demote kar diya.")
    except Exception as exc:
        await message.reply(f"❌ Demote failed: {exc}")


@router.callback_query(lambda c: c.data == "admin:stats")
async def stats_cb(callback):
    if not await is_bot_admin(callback.from_user.id): return await callback.answer("Admin access required", show_alert=True)
    async with async_session() as session:
        groups = len((await session.execute(select(Group.id))).scalars().all())
        users = len((await session.execute(select(User.id))).scalars().all())
        admins = len((await session.execute(select(BotAdmin.user_id))).scalars().all())
    await callback.message.answer(f"📊 <b>Anonymouse Stats</b>\n\nGroups: <b>{groups}</b>\nUsers: <b>{users}</b>\nExtra bot admins: <b>{admins}</b>\nOwner ID: <code>{settings.BOT_OWNER_ID}</code>")
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin:list")
async def list_cb(callback):
    if not await is_bot_admin(callback.from_user.id): return await callback.answer("Admin access required", show_alert=True)
    async with async_session() as session:
        admins = (await session.execute(select(BotAdmin))).scalars().all()
    lines = [f"👑 Owner: <code>{settings.BOT_OWNER_ID}</code>"]
    lines += [f"• <code>{a.user_id}</code>" + (f" @{a.username}" if a.username else "") for a in admins]
    await callback.message.answer("<b>👥 Global bot admins</b>\n\n" + "\n".join(lines))
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin:group_list")
async def group_list_cb(callback):
    if callback.message.chat.type not in {"group", "supergroup"} or not await is_chat_admin(callback.message):
        return await callback.answer("Sirf group admin dekh sakta hai.", show_alert=True)
    try:
        admins = await callback.message.chat.get_administrators()
        text = "👮 <b>Group Admins</b>\n\n" + "\n".join([f"• {a.user.full_name}" + (f" (@{a.user.username})" if a.user.username else "") for a in admins])
        await callback.message.answer(text)
    except Exception as exc:
        await callback.message.answer(f"❌ {exc}")
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin:warning_policy")
async def warning_policy_cb(callback):
    if callback.message.chat.type not in {"group", "supergroup"} or not await is_chat_admin(callback.message):
        return await callback.answer("Sirf group admin warning policy set kar sakta hai.", show_alert=True)
    async with async_session() as session:
        policy = await session.get(WarningPolicy, callback.message.chat.id)
        if not policy:
            policy = WarningPolicy(group_id=callback.message.chat.id)
            session.add(policy); await session.commit()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ 1 Warning", callback_data="policy:threshold:1"), InlineKeyboardButton(text="⚠️ 2 Warning", callback_data="policy:threshold:2")],
        [InlineKeyboardButton(text="⚠️ 3 Warning", callback_data="policy:threshold:3"), InlineKeyboardButton(text="⚠️ 5 Warning", callback_data="policy:threshold:5")],
        [InlineKeyboardButton(text="🔇 5m", callback_data="policy:mute:5"), InlineKeyboardButton(text="🔇 15m", callback_data="policy:mute:15")],
        [InlineKeyboardButton(text="🔇 30m", callback_data="policy:mute:30"), InlineKeyboardButton(text="🔇 60m", callback_data="policy:mute:60")],
        [InlineKeyboardButton(text="🔇 24h", callback_data="policy:mute:1440")],
    ])
    await callback.message.answer("⚠️ <b>Warning Policy</b>\n\nLocked content par warning jayegi. Threshold hit hone par selected duration ka mute lagega.", reply_markup=kb)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("policy:"))
async def policy_set_cb(callback):
    if callback.message.chat.type not in {"group", "supergroup"} or not await is_chat_admin(callback.message):
        return await callback.answer("Sirf group admin change kar sakta hai.", show_alert=True)
    _, kind, raw = callback.data.split(":")
    value = int(raw)
    async with async_session() as session:
        policy = await session.get(WarningPolicy, callback.message.chat.id)
        if not policy:
            policy = WarningPolicy(group_id=callback.message.chat.id)
            session.add(policy)
        if kind == "threshold": policy.threshold = value
        else: policy.mute_minutes = value
        await session.commit()
    await callback.answer("✅ Setting updated")
    await warning_policy_cb(callback)


@router.callback_query(lambda c: c.data == "admin:add_help")
async def admin_add_help(callback):
    if not await is_bot_admin(callback.from_user.id): return await callback.answer("Admin access required", show_alert=True)
    await callback.message.answer("➕ <b>Add Bot Admin</b>\nUse <code>/addadmin USER_ID</code> (owner only).")
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin:remove_help")
async def admin_remove_help(callback):
    if not await is_bot_admin(callback.from_user.id): return await callback.answer("Admin access required", show_alert=True)
    await callback.message.answer("➖ <b>Remove Bot Admin</b>\nUse <code>/deladmin USER_ID</code> (owner only).")
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin:commands_help")
async def admin_commands_help(callback):
    if not await is_bot_admin(callback.from_user.id): return await callback.answer("Admin access required", show_alert=True)
    await callback.message.answer("⌨️ <b>Custom Commands</b>\n\nGroup admin: <code>/addcmd name Response text</code>\nRemove: <code>/delcmd name</code>\nVariables: <code>{name}</code>, <code>{group}</code>")
    await callback.answer()
