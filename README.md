# Anonymouse Bot

Telegram group-management bot built with aiogram 3.x, SQLAlchemy async and FastAPI.

## Deploy
1. Create a Railway service from this repository.
2. Add `BOT_TOKEN`, `BOT_OWNER_ID`, `SETUP_TOKEN_SECRET`, `WEB_APP_URL`, and a persistent PostgreSQL `DATABASE_URL`.
3. Deploy and promote the bot to group admin with message delete and restrict-member permissions.

## Existing features
- Moderation: ban, unban, kick, mute, unmute, warn, remove warning, pin and delete.
- Locks: text, links, photos, videos, stickers, GIFs, forwards, bots, audio, voice and documents.
- Warning threshold and automatic mute policy.
- Welcome/goodbye, rules, notes, custom commands, admin management and signed web setup panel.

## Advanced Group Suite (new)
- Per-group keyword auto replies: `/addfilter keyword response`, `/delfilter keyword`, `/filters`.
- Anti-flood protection using each group's configured flood limit.
- Duplicate-message suppression.
- `/afk [reason]` status command (in-memory; resets when bot restarts).\n- `/tban 30m|2h|7d [reason]` and `/tmute 30m|2h|7d [reason]` by replying to a member; Telegram automatically expires the restriction.\n- `/logs` shows the latest 15 recorded actions from the new audit log table.
- `/report [reason]` by replying to a message (admins need to have started the bot to receive DMs).
- `/purge` by replying to the first message; deletes up to 100 messages.
- Database-backed aggregate `/stats` and `/groupstats`.
- New `group_filters` and `admin_actions` tables are created on startup; existing data is preserved.

## Commands
```
/admin /addadmin USER_ID /deladmin USER_ID
/ban /unban /kick /mute /unmute /warn /warns /rmwarn
/lock TYPE /unlock TYPE /locks
/setwelcome /welcome /setgoodbye /goodbye /setrules /rules
/save /get /notes /clear
/addcmd NAME RESPONSE /delcmd NAME
/addfilter KEYWORD RESPONSE /delfilter KEYWORD /filters
/afk [reason] /report [reason] /purge /groupstats /stats /ping /id /info /admins\n/tban DURATION [reason] /tmute DURATION [reason] /logs
```

## Notes
- Anti-flood and duplicate caches are process-local and reset on restart; they are not shared between multiple bot replicas.
- Telegram permissions and privacy settings affect what the bot can see and moderate.
- The setup dashboard uses signed, expiring setup tokens and re-checks group-admin status.

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
