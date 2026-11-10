from collections import defaultdict, deque
from datetime import datetime, timedelta
from html import escape

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import (
    ChatMemberUpdated, ChatJoinRequest, Message, CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions,
)
from sqlalchemy import select, delete

from database.models import Group, GroupSecurity, CaptchaPending
from database.session import async_session
from utils.permissions import is_chat_admin

router = Router()
_join_windows = defaultdict(deque)


async def get_or_create_group(chat_id: int, title: str = "") -> Group:
    async with async_session() as session:
        group = await session.get(Group, chat_id)
        if not group:
            group = Group(id=chat_id, title=title)
            session.add(group)
            await session.commit()
            await session.refresh(group)
        return group




async def _render_member_template(bot, user, group_title: str, template: str) -> str:
    username = f"@{user.username}" if user.username else "No username"
    mention = f'<a href="tg://user?id={user.id}">{escape(user.full_name)}</a>'
    values = {
        "{name}": escape(user.full_name),
        "{username}": escape(username),
        "{id}": str(user.id),
        "{mention}": mention,
        "{group}": escape(group_title),
    }
    for key, value in values.items():
        template = template.replace(key, value)
    return template[:1024]


async def _security_for_join(chat_id: int, user_id: int, title: str):
    now = datetime.utcnow()
    window = _join_windows[chat_id]
    window.append(now)
    while window and (now - window[0]).total_seconds() > 30:
        window.popleft()

    async with async_session() as session:
        security = await session.get(GroupSecurity, chat_id)
        if not security:
            security = GroupSecurity(group_id=chat_id)
            session.add(security)
            await session.flush()

        if security.antiraid_enabled and len(window) >= security.join_threshold:
            security.raid_until = now + timedelta(minutes=10)

        raid_active = bool(security.raid_until and security.raid_until > now)
        require_captcha = security.captcha_enabled or raid_active
        if require_captcha:
            existing = (await session.execute(
                select(CaptchaPending).where(
                    CaptchaPending.group_id == chat_id,
                    CaptchaPending.user_id == user_id,
                )
            )).scalar_one_or_none()
            if not existing:
                session.add(CaptchaPending(group_id=chat_id, user_id=user_id))
        await session.commit()
        return require_captcha


@router.chat_member()
async def on_member_update(event: ChatMemberUpdated):
    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status
    user = event.new_chat_member.user
    chat = event.chat

    if old_status in ("left", "kicked") and new_status == "member":
        require_captcha = await _security_for_join(chat.id, user.id, chat.title or "")
        if require_captcha and not user.is_bot:
            try:
                await event.bot.restrict_chat_member(
                    chat_id=chat.id,
                    user_id=user.id,
                    permissions=ChatPermissions(can_send_messages=False),
                )
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="✅ I'm human — Verify", callback_data=f"captcha:{chat.id}:{user.id}")
                ]])
                await event.bot.send_message(
                    chat.id,
                    f"🛡️ {user.full_name}, group me message bhejne se pehle verification complete karein.",
                    reply_markup=keyboard,
                )
            except Exception:
                # If the bot lacks restrict permissions, do not block the member silently.
                async with async_session() as session:
                    await session.execute(delete(CaptchaPending).where(
                        CaptchaPending.group_id == chat.id, CaptchaPending.user_id == user.id
                    ))
                    await session.commit()
        else:
            async with async_session() as session:
                group = await session.get(Group, chat.id)
                if not group or not group.welcome_enabled:
                    return
                template = group.welcome_text or "👋 Welcome {name} to {group}!"
            try:
                caption = await _render_member_template(event.bot, user, chat.title or "the group", template)
                photos = await event.bot.get_user_profile_photos(user.id, limit=1)
                if photos.total_count and photos.photos:
                    await event.bot.send_photo(chat.id, photos.photos[0][-1].file_id, caption=caption)
                else:
                    await event.bot.send_message(chat.id, caption)
            except Exception:
                pass

    elif old_status == "member" and new_status in ("left", "kicked"):
        async with async_session() as session:
            group = await session.get(Group, chat.id)
            if not group or not group.goodbye_enabled or not group.goodbye_text:
                return
            template = group.goodbye_text
        try:
            caption = await _render_member_template(event.bot, user, chat.title or "the group", template)
            photos = await event.bot.get_user_profile_photos(user.id, limit=1)
            if photos.total_count and photos.photos:
                await event.bot.send_photo(chat.id, photos.photos[0][-1].file_id, caption=caption)
            else:
                await event.bot.send_message(chat.id, caption)
        except Exception:
            pass


@router.callback_query(lambda c: c.data and c.data.startswith("captcha:"))
async def captcha_verify(callback: CallbackQuery):
    try:
        _, chat_raw, user_raw = callback.data.split(":")
        chat_id, expected_user = int(chat_raw), int(user_raw)
    except (ValueError, AttributeError):
        return await callback.answer("Invalid verification.", show_alert=True)
    if callback.from_user.id != expected_user:
        return await callback.answer("Ye verification kisi aur member ke liye hai.", show_alert=True)

    async with async_session() as session:
        pending = (await session.execute(select(CaptchaPending).where(
            CaptchaPending.group_id == chat_id,
            CaptchaPending.user_id == expected_user,
        ))).scalar_one_or_none()
        if not pending:
            return await callback.answer("Verification already completed or expired.", show_alert=True)
        await session.delete(pending)
        await session.commit()

    try:
        await callback.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=expected_user,
            permissions=ChatPermissions(
                can_send_messages=True, can_send_audios=True, can_send_documents=True,
                can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
                can_send_voice_notes=True, can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        await callback.message.edit_text("✅ Verification complete. Welcome!")
        await callback.answer("Verified!")
    except Exception:
        await callback.answer("Verification failed. Please contact a group admin.", show_alert=True)


@router.chat_join_request()
async def join_request_received(event: ChatJoinRequest):
    user = event.from_user
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Approve", callback_data=f"join:approve:{event.chat.id}:{user.id}"),
        InlineKeyboardButton(text="❌ Decline", callback_data=f"join:decline:{event.chat.id}:{user.id}"),
    ]])
    try:
        await event.bot.send_message(
            event.chat.id,
            f"📨 Join request from {user.full_name} (<code>{user.id}</code>)",
            reply_markup=keyboard,
        )
    except Exception:
        pass


@router.callback_query(lambda c: c.data and c.data.startswith("join:"))
async def join_request_action(callback: CallbackQuery):
    try:
        action, decision, chat_raw, user_raw = callback.data.split(":")
        chat_id, user_id = int(chat_raw), int(user_raw)
    except (ValueError, AttributeError):
        return await callback.answer("Invalid request.", show_alert=True)
    if decision not in {"approve", "decline"}:
        return await callback.answer("Invalid action.", show_alert=True)
    try:
        member = await callback.bot.get_chat_member(chat_id, callback.from_user.id)
        if member.status not in {"creator", "administrator"}:
            return await callback.answer("Only group admins can review join requests.", show_alert=True)
        if decision == "approve":
            await callback.bot.approve_chat_join_request(chat_id, user_id)
        else:
            await callback.bot.decline_chat_join_request(chat_id, user_id)
        await callback.message.edit_text(f"{'✅ Approved' if decision == 'approve' else '❌ Declined'} join request for <code>{user_id}</code> by <code>{callback.from_user.id}</code>.")
        await callback.answer("Done.")
    except Exception:
        await callback.answer("Could not process request. Check bot permissions and request status.", show_alert=True)


@router.message(Command("captcha"))
async def captcha_cmd(message: Message):
    if not await is_chat_admin(message):
        return await message.reply("⛔ Sirf group admin CAPTCHA setting badal sakta hai.")
    parts = (message.text or "").split()
    if len(parts) != 2 or parts[1].lower() not in {"on", "off"}:
        return await message.reply("Usage: /captcha on ya /captcha off")
    async with async_session() as session:
        security = await session.get(GroupSecurity, message.chat.id)
        if not security:
            security = GroupSecurity(group_id=message.chat.id)
            session.add(security)
        security.captcha_enabled = parts[1].lower() == "on"
        await session.commit()
    await message.reply(f"🛡️ CAPTCHA {'enabled' if parts[1].lower() == 'on' else 'disabled'}.")


@router.message(Command("antiraid"))
async def antiraid_cmd(message: Message):
    if not await is_chat_admin(message):
        return await message.reply("⛔ Sirf group admin Anti-Raid setting badal sakta hai.")
    parts = (message.text or "").split()
    if len(parts) != 2 or parts[1].lower() not in {"on", "off"}:
        return await message.reply("Usage: /antiraid on ya /antiraid off")
    async with async_session() as session:
        security = await session.get(GroupSecurity, message.chat.id)
        if not security:
            security = GroupSecurity(group_id=message.chat.id)
            session.add(security)
        security.antiraid_enabled = parts[1].lower() == "on"
        if not security.antiraid_enabled:
            security.raid_until = None
        await session.commit()
    await message.reply("🚨 Anti-Raid enabled. 5 joins in 30 seconds activate CAPTCHA for 10 minutes." if parts[1].lower() == "on" else "🛡️ Anti-Raid disabled.")


@router.message(Command("setwelcome"))
async def setwelcome_cmd(message: Message):
    if not await is_chat_admin(message):
        return await message.reply("⛔ Sirf Telegram admin welcome change kar sakta hai.")
    if not message.reply_to_message or not message.reply_to_message.text:
        return await message.reply("❌ Kisi text message pe reply karke /setwelcome karo. Variables: {name}, {username}, {mention}, {id}, {group}. Profile photo is attached automatically when available.")
    async with async_session() as session:
        group = await session.get(Group, message.chat.id)
        if not group:
            group = Group(id=message.chat.id, title=message.chat.title or "")
            session.add(group)
        group.welcome_text = message.reply_to_message.text
        group.welcome_enabled = True
        await session.commit()
    await message.reply("✅ Welcome message set ho gaya.")


@router.message(Command("welcome"))
async def welcome_cmd(message: Message):
    async with async_session() as session:
        group = await session.get(Group, message.chat.id)
        if not group or not group.welcome_text:
            return await message.reply("❌ Koi welcome message set nahi hai.")
        enabled, text = group.welcome_enabled, group.welcome_text
    await message.reply(f"<b>Welcome ({'ON' if enabled else 'OFF'}):</b>\\n\\n{text}")


@router.message(Command("setgoodbye"))
async def setgoodbye_cmd(message: Message):
    if not await is_chat_admin(message):
        return await message.reply("⛔ Sirf Telegram admin goodbye change kar sakta hai.")
    if not message.reply_to_message or not message.reply_to_message.text:
        return await message.reply("❌ Kisi text message pe reply karke /setgoodbye karo. Variables: {name}, {username}, {mention}, {id}, {group}.")
    async with async_session() as session:
        group = await session.get(Group, message.chat.id)
        if not group:
            group = Group(id=message.chat.id, title=message.chat.title or "")
            session.add(group)
        group.goodbye_text = message.reply_to_message.text
        group.goodbye_enabled = True
        await session.commit()
    await message.reply("✅ Goodbye message set ho gaya.")


@router.message(Command("goodbye"))
async def goodbye_cmd(message: Message):
    async with async_session() as session:
        group = await session.get(Group, message.chat.id)
        if not group or not group.goodbye_text:
            return await message.reply("❌ Koi goodbye message set nahi hai.")
        text = group.goodbye_text
    await message.reply(f"<b>Goodbye:</b>\\n\\n{text}")


@router.message(Command("setrules"))
async def setrules_cmd(message: Message):
    if not await is_chat_admin(message):
        return await message.reply("⛔ Sirf Telegram admin rules change kar sakta hai.")
    if not message.reply_to_message or not message.reply_to_message.text:
        return await message.reply("❌ Kisi text message pe reply karke /setrules karo.")
    async with async_session() as session:
        group = await session.get(Group, message.chat.id)
        if not group:
            group = Group(id=message.chat.id, title=message.chat.title or "")
            session.add(group)
        group.rules = message.reply_to_message.text
        await session.commit()
    await message.reply("✅ Group rules set ho gaye.")


@router.message(Command("rules"))
async def rules_cmd(message: Message):
    async with async_session() as session:
        group = await session.get(Group, message.chat.id)
        if not group or not group.rules:
            return await message.reply("❌ Koi rules set nahi hai.")
        rules = group.rules
    await message.reply(f"📜 <b>Group Rules:</b>\\n\\n{rules}")
