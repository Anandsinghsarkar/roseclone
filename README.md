# Anonymouse Bot

Telegram group-management bot built with aiogram 3.x, SQLAlchemy async and FastAPI.

## Database and backups (no PostgreSQL required)
- The bot uses local SQLite at `data/bot.db`. No PostgreSQL service, Redis, or `DATABASE_URL` variable is needed.
- Open `https://YOUR-RAILWAY-DOMAIN/backup` for the owner backup center.
- Enter the strong `SETUP_TOKEN_SECRET` configured in Railway to authorize backup actions.
- **Export:** download a consistent `.db` snapshot containing all bot database tables.
- **Import:** upload a previously exported `.db`, `.sqlite`, or `.sqlite3` file. The file is integrity-checked and checked for expected bot tables. The current database is copied to a timestamped safety file before restore.
- Restart the bot service after restoring.
- Keep backup files private and never commit them to GitHub.

### Important: persistent storage on Railway
SQLite lives in the service filesystem. Railway's ordinary container filesystem can be reset on redeploy/restart. Attach a Railway Volume mounted at **`/app/data`** to keep the live database between deployments. Export backups regularly and keep copies outside the hosting service. Export/import is a recovery tool, not automatic cloud replication.

## Deploy
1. Create a Railway service from this repository.
2. Add `BOT_TOKEN`, `BOT_OWNER_ID`, and a strong random `SETUP_TOKEN_SECRET`. Set `WEB_APP_URL` to your public Railway domain.
3. Attach a persistent Railway Volume at `/app/data` if you want SQLite data to survive redeploys and restarts.
4. Deploy and promote the bot to group admin with message delete and restrict-member permissions.

## Existing features
- Moderation: ban, unban, kick, mute, unmute, warn, remove warning, pin and delete.
- Locks: text, links, photos, videos, stickers, GIFs, forwards, bots, audio, voice and documents.
- Warning threshold and automatic mute policy.
- Welcome/goodbye, rules, notes, custom commands, admin management and signed web setup panel.

## Advanced Group Suite
- Per-group keyword auto replies: `/addfilter keyword response`, `/delfilter keyword`, `/filters`.
- Anti-flood protection and duplicate-message suppression.
- `/afk [reason]` (in-memory; resets when bot restarts).
- `/tban 30m|2h|7d [reason]` and `/tmute 30m|2h|7d [reason]` by replying to a member.
- `/logs` shows latest recorded admin actions.
- `/report [reason]`, `/purge`, database-backed `/stats` and `/groupstats`.
- CAPTCHA, anti-raid and join-request approval/decline buttons.

## Commands
```
/admin /addadmin USER_ID /deladmin USER_ID
/ban /unban /kick /mute /unmute /warn /warns /rmwarn
/lock TYPE /unlock TYPE /locks
/setwelcome /welcome /setgoodbye /goodbye /setrules /rules
/save /get /notes /clear
/addcmd NAME RESPONSE
/addfilter KEYWORD RESPONSE /delfilter KEYWORD /filters
/afk [reason] /report [reason] /purge /groupstats /stats /ping /id /info /admins
/tban DURATION [reason] /tmute DURATION [reason] /logs
/captcha on|off /antiraid on|off
```

## Local setup
```bash
cp .env.example .env
pip install -r requirements.txt
python bot.py
```

## Docker
```bash
docker build -t anonymouse .
docker run --env-file .env -p 8080:8080 -v anonymouse-data:/app/data anonymouse
```

## Notes
- Anti-flood and duplicate caches are process-local and reset on restart.
- Telegram permissions and privacy settings affect what the bot can see and moderate.
- Setup links use signed, expiring tokens and re-check group-admin status.
- CAPTCHA requires permission to restrict members; join-request controls require permission to manage join requests.
