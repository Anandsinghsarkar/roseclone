import hmac
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from starlette.background import BackgroundTask

from config import settings
from database.session import DB_PATH, engine


BACKUP_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Anonymouse • Data Backup</title>
<style>
:root{color-scheme:dark;--card:#121827;--muted:#93a0b8;--text:#eef3ff;--accent:#7c5cff;--line:#263149}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top,#19203b,#080b14 55%);color:var(--text);font-family:system-ui,sans-serif;min-height:100vh}.wrap{max-width:720px;margin:auto;padding:28px 16px}.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:20px;margin:14px 0}h1{font-size:27px;margin:0 0 8px}h2{font-size:18px;margin:0 0 12px}.muted{color:var(--muted);font-size:14px;line-height:1.6}input{width:100%;padding:13px;border-radius:11px;border:1px solid var(--line);background:#0c1120;color:var(--text);margin:8px 0 12px}button{padding:12px 16px;border:0;border-radius:11px;background:var(--accent);color:white;font-weight:700;cursor:pointer;margin:4px}.green{background:#168a57}.status{padding:12px;border-radius:10px;background:#0c1120;margin-top:12px;white-space:pre-wrap}.warn{border-left:3px solid #e5a23b;padding-left:12px}
</style></head><body><main class="wrap"><h1>🗄️ Data Backup Center</h1><p class="muted">Download a full SQLite database backup or restore a previously exported backup.</p>
<section class="card"><h2>🔐 Owner access</h2><p class="muted">Enter your SETUP_TOKEN_SECRET from hosting environment variables. It is used only for this session and is not saved.</p><input id="secret" type="password" autocomplete="off" placeholder="Backup access secret"></section>
<section class="card"><h2>⬇️ Export / Download</h2><p class="muted">Creates a consistent snapshot of all bot database tables.</p><button class="green" onclick="exportDb()">Download database backup</button></section>
<section class="card"><h2>⬆️ Import / Restore</h2><p class="muted">Choose a backup .db, .sqlite or .sqlite3 file created from this bot.</p><input id="backupFile" type="file" accept=".db,.sqlite,.sqlite3,application/octet-stream"><p class="muted warn">Restore replaces the current database. The current database is first copied into a safety backup. Restart the bot after restoring.</p><button onclick="importDb()">Validate and restore backup</button></section>
<div id="status" class="status muted">Waiting for action…</div><p><a href="/setup" style="color:#b7a8ff">← Back to setup dashboard</a></p></main>
<script>
const secret=()=>document.getElementById('secret').value.trim();
function status(t){document.getElementById('status').textContent=t}
function headers(){return {'X-Backup-Token':secret()}}
async function exportDb(){if(!secret())return status('Enter the owner secret first.');status('Preparing database snapshot…');try{const r=await fetch('/api/backup/export',{headers:headers()});if(!r.ok)throw new Error((await r.json()).detail||'Export failed');const blob=await r.blob();const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='anonymouse-backup-'+new Date().toISOString().replace(/[:.]/g,'-')+'.db';a.click();URL.revokeObjectURL(a.href);status('Backup downloaded successfully. Keep a copy somewhere safe.')}catch(e){status(e.message)}}
async function importDb(){if(!secret())return status('Enter the owner secret first.');const f=document.getElementById('backupFile').files[0];if(!f)return status('Select a database backup file.');if(!confirm('This will replace the current database. Continue?'))return;status('Uploading and validating backup…');try{const form=new FormData();form.append('file',f);const r=await fetch('/api/backup/import',{method:'POST',headers:headers(),body:form});const d=await r.json();if(!r.ok)throw new Error(d.detail||'Restore failed');status(d.message+' Restart the bot service before normal use.')}catch(e){status(e.message)}}
</script></body></html>"""


def _authorize(token: str | None) -> None:
    expected = settings.SETUP_TOKEN_SECRET
    if not token or not expected or expected == "change-this-secret-in-railway":
        raise HTTPException(status_code=503, detail="Set a strong SETUP_TOKEN_SECRET before using backups")
    if not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Invalid owner backup secret")


def _validate_sqlite(path: str) -> None:
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0] != "ok":
                raise ValueError("SQLite integrity check failed")
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"groups", "users", "bot_admins"}.issubset(tables):
                raise ValueError("This file is not a compatible Anonymouse bot database")
        finally:
            conn.close()
    except (sqlite3.DatabaseError, OSError) as exc:
        raise ValueError("Invalid or corrupted SQLite backup file") from exc


def register_backup_routes(app: FastAPI) -> None:
    @app.get("/backup", response_class=HTMLResponse)
    async def backup_page():
        return HTMLResponse(BACKUP_PAGE)

    @app.get("/api/backup/export")
    async def export_backup(x_backup_token: str | None = Header(default=None)):
        _authorize(x_backup_token)
        if not DB_PATH.exists():
            raise HTTPException(status_code=404, detail="Database file does not exist yet")
        fd, snapshot = tempfile.mkstemp(prefix="anonymouse-export-", suffix=".db", dir=str(DB_PATH.parent))
        os.close(fd)
        try:
            source = sqlite3.connect(str(DB_PATH))
            target = sqlite3.connect(snapshot)
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()
        except Exception:
            Path(snapshot).unlink(missing_ok=True)
            raise
        filename = "anonymouse-backup-" + datetime.utcnow().strftime("%Y%m%d-%H%M%S") + ".db"
        return FileResponse(snapshot, media_type="application/octet-stream", filename=filename,
                            background=BackgroundTask(os.unlink, snapshot))

    @app.post("/api/backup/import")
    async def import_backup(file: UploadFile = File(...), x_backup_token: str | None = Header(default=None)):
        _authorize(x_backup_token)
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in {".db", ".sqlite", ".sqlite3"}:
            raise HTTPException(status_code=400, detail="Upload a .db, .sqlite or .sqlite3 backup")
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        fd, candidate = tempfile.mkstemp(prefix="anonymouse-import-", suffix=".db", dir=str(DB_PATH.parent))
        os.close(fd)
        size = 0
        try:
            with open(candidate, "wb") as output:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > 100 * 1024 * 1024:
                        raise HTTPException(status_code=413, detail="Backup file exceeds 100 MB limit")
                    output.write(chunk)
            _validate_sqlite(candidate)
            await engine.dispose()
            safety_copy = None
            if DB_PATH.exists():
                safety_copy = DB_PATH.with_name("bot-before-restore-" + datetime.utcnow().strftime("%Y%m%d-%H%M%S") + ".db")
                shutil.copy2(DB_PATH, safety_copy)
            os.replace(candidate, DB_PATH)
            return {"ok": True, "message": "Database restored successfully. A pre-restore safety copy was created." if safety_copy else "Database restored successfully."}
        except HTTPException:
            raise
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Restore failed; check server logs and keep the pre-restore copy.") from exc
        finally:
            Path(candidate).unlink(missing_ok=True)
            await file.close()
