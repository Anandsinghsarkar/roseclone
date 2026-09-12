# Rose Clone Bot

Telegram group/channel management bot built with aiogram 3.x, SQLAlchemy async and a FastAPI setup dashboard.

## Railway deployment
1. Create a Railway service from this GitHub repository.
2. Railway builds the included `Dockerfile` and starts `python bot.py`.
3. Add these Railway Variables:
   - `BOT_TOKEN` — Telegram BotFather token
   - `BOT_OWNER_ID` — your Telegram numeric user ID
   - `SETUP_TOKEN_SECRET` — long random secret
   - `WEB_APP_URL` — the public HTTPS URL of this Railway service, e.g. `https://your-app.up.railway.app`
4. For production persistence, add Railway PostgreSQL and set `DATABASE_URL` to its connection string.
5. Deploy. Open the bot in Telegram, add it to a group, give it admin rights, then run `/setup` or use the **⚙️ Group Setup** button.

The setup link is signed and expires after 30 minutes. The dashboard checks that the Telegram user who opened the link is still a group/channel administrator before allowing changes.

## Button dashboard
- 🛡 Moderation — ban, kick, mute, warn, pin and delete helpers
- 🔒 Locks — links, photos, videos, stickers, GIFs, forwards, bots and text
- 👋 Welcome — enable/disable and customize welcome/goodbye messages
- 📜 Rules — edit and view group rules
- 📝 Notes — save, get, list and clear notes
- 🧰 Utilities — ID, info, ping and stats
- ⚙️ Group Setup — browser dashboard for per-group/channel configuration
- 👑 Bot Admin — persistent global bot-admin management for the owner

## Admin controls
The owner can use:
```text
/admin
/addadmin USER_ID
/deladmin USER_ID
```

Global bot admins can open `/admin` and view bot statistics or the admin list. Group-level tools also verify Telegram administrator status before setup/moderation actions are used.

## Local setup
```bash
cp .env.example .env
pip install -r requirements.txt
python bot.py
```

## Docker
```bash
docker build -t roseclone .
docker run --env-file .env -p 8080:8080 roseclone
```

## BotFather
- Create the bot with `/newbot`
- Disable privacy with `/setprivacy` when the bot needs group messages
- Add the bot to the target group/channel and give it the permissions required for moderation

Welcome/goodbye/rules text supports `{name}` and `{group}` placeholders in the existing handlers.
