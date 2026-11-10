from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
from io import BytesIO
from sqlalchemy import select

from config import settings
from database.models import Group, GroupUser
from database.session import async_session
from utils.permissions import is_bot_admin, is_chat_admin

router = Router()


async def _target_chat(message: Message, parts: list[str]) -> int:
    if len(parts) > 1:
        return int(parts[1])
    return message.chat.id


@router.message(Command("mygroups"))
async def mygroups(message: Message):
    if not message.from_user or not await is_bot_admin(message.from_user.id):
        return await message.reply("⛔ Bot admin access required.")
    async with async_session() as session:
        groups = (await session.execute(select(Group).order_by(Group.title))).scalars().all()
    if not groups:
        return await message.reply("Abhi koi group record nahi hua. Bot ko group me add karke admin banayein aur wahan ek message/join event hone dein.")
    lines = []
    for group in groups[:50]:
        try:
            member = await message.bot.get_chat_member(group.id, (await message.bot.me()).id)
            if member.status not in {"administrator", "creator"}:
                continue
            lines.append(f"• <b>{group.title or 'Untitled group'}</b> — <code>{group.id}</code>")
        except Exception:
            continue
    await message.reply("<b>🤖 Groups where bot is currently admin</b>\n\n" + ("\n".join(lines) if lines else "No currently accessible admin groups."))


@router.message(Command("groupinfo"))
async def groupinfo(message: Message):
    if not await is_chat_admin(message):
        return await message.reply("⛔ Group admin only.")
    chat = await message.bot.get_chat(message.chat.id)
    count = await message.bot.get_chat_member_count(message.chat.id)
    me = await message.bot.get_chat_member(message.chat.id, (await message.bot.me()).id)
    await message.reply(
        f"<b>📊 Group information</b>\nName: {chat.title or '—'}\nID: <code>{chat.id}</code>"
        f"\nType: {chat.type}\nMembers: {count}\nBot status: {me.status}"
    )


@router.message(Command("groupadmins"))
async def groupadmins(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not await is_chat_admin(message):
        return await message.reply("⛔ Is command ko group admin use kare.")
    try:
        admins = await message.bot.get_chat_administrators(message.chat.id)
        lines = []
        for item in admins:
            user = item.user
            label = "🤖 BOT" if user.is_bot else ("👑 OWNER" if item.status == "creator" else "👮 ADMIN")
            lines.append(f"{label} • {user.full_name} (@{user.username or 'no_username'}) — <code>{user.id}</code>")
        await message.reply("<b>👥 Group administrators</b>\n\n" + "\n".join(lines))
    except Exception as exc:
        await message.reply(f"❌ Telegram admin list nahi de saka: {exc}")


@router.message(Command("setgrouptitle"))
async def setgrouptitle(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not await is_chat_admin(message):
        return await message.reply("⛔ Group admin only.")
    title = (message.text or "").partition(" ")[2].strip()
    if not title:
        return await message.reply("Usage: /setgrouptitle New group name")
    try:
        await message.bot.set_chat_title(message.chat.id, title[:128])
        await message.reply("✅ Group name updated.")
    except Exception as exc:
        await message.reply(f"❌ Name change failed. Bot ko Change Group Info permission chahiye.\n{exc}")


@router.message(Command("setgroupphoto"))
async def setgroupphoto(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not await is_chat_admin(message):
        return await message.reply("⛔ Group admin only.")
    replied = message.reply_to_message
    if not replied or not replied.photo:
        return await message.reply("Group photo wali image par reply karke /setgroupphoto bhejein.")
    try:
        file_info = await message.bot.get_file(replied.photo[-1].file_id)
        buffer = BytesIO()
        await message.bot.download_file(file_info.file_path, destination=buffer)
        upload = BufferedInputFile(buffer.getvalue(), filename="group-photo.jpg")
        await message.bot.set_chat_photo(message.chat.id, upload)
        await message.reply("✅ Group photo updated.")
    except Exception as exc:
        await message.reply(f"❌ Photo update failed. Bot ko Change Group Info permission chahiye.\n{exc}")


@router.message(Command("promoterights"))
async def promoterights(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not await is_chat_admin(message):
        return await message.reply("⛔ Group admin only.")
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if not target:
        return await message.reply("Target user ke message par reply karein.\nExample: /promoterights delete=on ban=off invite=on pin=off changeinfo=off promote=off")
    allowed = {"delete", "ban", "invite", "pin", "changeinfo", "promote", "manage"}
    values = {key: False for key in allowed}
    raw = (message.text or "").partition(" ")[2].strip()
    for item in raw.split():
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        if key in allowed and value.lower() in {"on", "off"}:
            values[key] = value.lower() == "on"
    try:
        await message.bot.promote_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            can_manage_chat=values["manage"],
            can_delete_messages=values["delete"],
            can_restrict_members=values["ban"],
            can_invite_users=values["invite"],
            can_pin_messages=values["pin"],
            can_change_info=values["changeinfo"],
            can_promote_members=values["promote"],
        )
        await message.reply(f"✅ {target.full_name} ke admin rights update ho gaye.\n" + "\n".join(f"• {k}: {'ON' if v else 'OFF'}" for k, v in values.items()))
    except Exception as exc:
        await message.reply(f"❌ Rights update nahi hue. Bot ko Promote Members permission aur target par sufficient authority chahiye.\n{exc}")


@router.message(Command("demoteuser"))
async def demoteuser(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not await is_chat_admin(message):
        return await message.reply("⛔ Group admin only.")
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if not target:
        return await message.reply("Jis admin ko demote karna hai uske message par reply karke /demoteuser bhejein.")
    try:
        await message.bot.promote_chat_member(
            chat_id=message.chat.id, user_id=target.id,
            can_manage_chat=False, can_delete_messages=False, can_restrict_members=False,
            can_invite_users=False, can_pin_messages=False, can_change_info=False,
            can_promote_members=False, can_manage_video_chats=False,
        )
        await message.reply(f"✅ {target.full_name} demote ho gaye.")
    except Exception as exc:
        await message.reply(f"❌ Demote failed. Telegram authority/permissions check karein.\n{exc}")



@router.message(Command("knownusers"))
async def knownusers(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not await is_chat_admin(message):
        return await message.reply("⛔ Group admin only.")
    async with async_session() as session:
        rows = (await session.execute(
            select(GroupUser).where(GroupUser.group_id == message.chat.id, GroupUser.is_bot.is_(False))
            .order_by(GroupUser.last_seen.desc()).limit(40)
        )).scalars().all()
    if not rows:
        return await message.reply("Abhi is group ke koi users bot ke saamne record nahi hue.")
    lines = [f"• {row.first_name} (@{row.username or 'no_username'}) — <code>{row.user_id}</code>" for row in rows]
    await message.reply("<b>👥 Known group users (latest 40)</b>\n" + "\n".join(lines) +
                        "\n\nNote: Ye complete live member list nahi hai; sirf woh users hain jinhe bot ne messages me dekha hai.")


@router.message(Command("knownbots"))
async def knownbots(message: Message):
    if message.chat.type not in {"group", "supergroup"} or not await is_chat_admin(message):
        return await message.reply("⛔ Group admin only.")
    async with async_session() as session:
        rows = (await session.execute(
            select(GroupUser).where(GroupUser.group_id == message.chat.id, GroupUser.is_bot.is_(True))
            .order_by(GroupUser.last_seen.desc()).limit(40)
        )).scalars().all()
    if not rows:
        return await message.reply("Bot ne abhi is group me koi doosra bot message karte nahi dekha.")
    lines = [f"• {row.first_name} (@{row.username or 'no_username'}) — <code>{row.user_id}</code>" for row in rows]
    await message.reply("<b>🤖 Known bots (latest 40)</b>\n" + "\n".join(lines) +
                        "\n\nNote: Ye complete live bot list nahi hai; sirf message kar chuke bots hain.")
