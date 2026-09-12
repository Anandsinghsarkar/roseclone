# Rose Clone Bot

Telegram group-management bot built with aiogram 3.x and SQLAlchemy async.

## Railway deployment
1. Create a Railway service from this GitHub repository.
2. Railway will build the included `Dockerfile` and run `python bot.py`.
3. Add `BOT_TOKEN` and `BOT_OWNER_ID` as Railway Variables.
4. For production persistence, add a Railway PostgreSQL service and set `DATABASE_URL` to its PostgreSQL connection string.

SQLite is supported by default for simple/local deployments. Railway's normal filesystem is ephemeral, so PostgreSQL is recommended for persistent production data.

## Features
- Moderation: ban, kick, mute, warn
- Welcome and goodbye messages
- Locks system
- Notes system
- Utility commands

## Local setup
```bash
cp .env.example .env
pip install -r requirements.txt
python bot.py
```

## Docker
```bash
docker build -t roseclone .
docker run --env-file .env roseclone
```

## BotFather
- Create the bot with `/newbot`
- Disable privacy with `/setprivacy` when the bot needs group messages
- Add the bot to your group and give it the required admin permissions

Variables for welcome/goodbye/rules text: `{name}`, `{group}`.
