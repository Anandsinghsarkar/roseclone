# Anonymouse Bot

Telegram group/channel management bot built with aiogram 3.x, SQLAlchemy async and a FastAPI setup dashboard.

## Railway deployment
1. Create a Railway service from this GitHub repository.
2. Railway builds the included `Dockerfile` and starts `python bot.py`.
3. Add these Railway Variables:
   - `BOT_TOKEN` — Telegram BotFather token
   - `BOT_OWNER_ID` — your Telegram numeric user ID
   - `SETUP_TOKEN_SECRET` — long random secret
   - `WEB_APP_URL` — the public HTTPS URL of this Railway service
   - `DATABASE_URL` — Railway PostgreSQL connection string for persistent production data
4. Deploy. Add Anonymouse to your group and give it the required admin permissions.

## Anonymouse features
- 🛡 Button-based moderation: ban, unban, kick, mute, unmute, warn, pin, delete
- 🔒 Lock enforcement: text, links, photos, videos, stickers, GIFs, forwards, bots, audio, voice, documents
- ⚠️ Locked content is deleted and automatically generates a warning
- 🔇 Configurable warning threshold and mute duration from **Anonymouse Admin → Warning Policy**
- 👮 Group admin list plus `/promote @username` and `/demote @username`
- 👋 Welcome/goodbye messages with `{name}` and `{group}` placeholders
- 📜 Rules
- 📝 Notes
- 🧰 Utilities
- ⌨️ Custom commands: group admins can create `/addcmd name response` and remove them with `/delcmd name`
- ⚙️ Secure web setup panel for per-group settings
- 👑 Persistent global bot-admin system

## Warning and lock behavior
Example: set `links` or `photos` as locked. A non-admin posting that content will have the message removed and receive a warning. When the configured warning threshold is reached, Anonymouse mutes the user for the configured duration. The warning counter can reset automatically after the mute.

## Setup panel
Run `/setup` inside your group, or use the **⚙️ Setup Panel** button. The setup URL is signed, expires after 30 minutes, and re-checks Telegram administrator status before saving changes.

## Bot admin
```text
/admin
/addadmin USER_ID
/deladmin USER_ID
```
Only the configured `BOT_OWNER_ID` can add/remove global bot admins.

## Local setup
```bash
cp .env.example .env
pip install -r requirements.txt
python bot.py
```

## Docker
```bash
docker build -t anonymouse .
docker run --env-file .env -p 8080:8080 anonymouse
```
