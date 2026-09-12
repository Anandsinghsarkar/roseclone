from aiogram import Router
from aiogram.filters import Command
from aiogram.types import ChatMemberUpdated, Message

from database.models import Group
from database.session import async_session

router = Router()


async def get_or_create_group(chat_id: int, title: str = "") -> Group:
    async with async_session() as session:
        group = await session.get(Group, chat_id)
        if not group:
            group = Group(id=chat_id, title=title)
            session.add(group)
            await session.commit()
            await session.refresh(group)
        return group


@router.chat_member()
async def on_member_update(event: ChatMemberUpdated):
    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status
    user = event.new_chat_member.user
    chat = event.chat

    if old_status in ("left", "kicked") and new_status == "member":
        async with async_session() as session:
            group = await session.get(Group, chat.id)
            if not group or not group.welcome_enabled:
                return
            template = group.welcome_text or "👋 Welcome {name} to {group}!"
        text = template.replace("{name}", user.full_name).replace("{group}", chat.title or "the group")
        try:
            await event.bot.send_message(chat.id, text)
        except Exception:
            pass
    elif old_status == "member" and new_status in ("left", "kicked"):
        async with async_session() as session:
            group = await session.get(Group, chat.id)
            if not group or not group.goodbye_enabled or not group.goodbye_text:
                return
            template = group.goodbye_text
        text = template.replace("{name}", user.full_name).replace("{group}", chat.title or "the group")
        try:
            await event.bot.send_message(chat.id, text)
        except Exception:
            pass


@router.message(Command("setwelcome"))
async def setwelcome_cmd(message: Message):
    if not message.reply_to_message or not message.reply_to_message.text:
        return await message.reply("❌ Kisi text message pe reply karke /setwelcome karo.\n\nVariables: {name}, {group}")
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
        enabled = group.welcome_enabled
        text = group.welcome_text
    await message.reply(f"<b>Welcome ({'ON' if enabled else 'OFF'}):</b>\n\n{text}")


@router.message(Command("setgoodbye"))
async def setgoodbye_cmd(message: Message):
    if not message.reply_to_message or not message.reply_to_message.text:
        return await message.reply("❌ Kisi text message pe reply karke /setgoodbye karo.")
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
    await message.reply(f"<b>Goodbye:</b>\n\n{text}")


@router.message(Command("setrules"))
async def setrules_cmd(message: Message):
    if not message.reply_to_message or not message.reply_to_message.text:
        return await message.reply("❌ Kisi text message pe reply karke /setrules karo.")
    async with async_session() as session:
        group = await session.get(Group, message.chat.id)
        if not group:
            group = Group(id=message.chat.id, title=message.chat.title or "")
            session.add(group)
        group.rules = message.reply_to_message.text
        await session.commit()
    await message.reply("✅ Rules set ho gaye.")


@router.message(Command("rules"))
async def rules_cmd(message: Message):
    async with async_session() as session:
        group = await session.get(Group, message.chat.id)
        if not group or not group.rules:
            return await message.reply("❌ Koi rules set nahi hai.")
        rules = group.rules
    await message.reply(f"📜 <b>Group Rules:</b>\n\n{rules}")
