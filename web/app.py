from html import escape

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from config import settings
from database.models import Group, Lock
from database.session import async_session
from utils.setup import verify_setup_token


class SetupPayload(BaseModel):
    welcome_enabled: bool = True
    welcome_text: str = Field(default="👋 Welcome, {name}!")
    goodbye_enabled: bool = False
    goodbye_text: str = Field(default="👋 Goodbye, {name}!")
    rules: str = Field(default="")
    flood_limit: int = Field(default=5, ge=1, le=50)
    warn_limit: int = Field(default=3, ge=1, le=20)


class LockPayload(BaseModel):
    lock_type: str = Field(min_length=1, max_length=50)
    enabled: bool


DASHBOARD = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rose Clone • Setup</title>
<style>
:root{color-scheme:dark;--bg:#080b14;--card:#121827;--muted:#93a0b8;--text:#eef3ff;--accent:#7c5cff;--line:#263149;--good:#35d07f}
*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif;background:radial-gradient(circle at top,#19203b 0,#080b14 45%);color:var(--text);min-height:100vh}
.wrap{max-width:980px;margin:auto;padding:28px 16px 60px}.hero{display:flex;justify-content:space-between;gap:20px;align-items:center;margin-bottom:20px}.title{font-size:30px;font-weight:800}.sub{color:var(--muted);margin-top:6px}.badge{padding:9px 13px;border:1px solid var(--line);border-radius:999px;background:#0e1422;color:#b7c3dc}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}.card{background:rgba(18,24,39,.92);border:1px solid var(--line);border-radius:18px;padding:18px;box-shadow:0 16px 50px rgba(0,0,0,.24)}h2{font-size:17px;margin:0 0 14px}.row{display:flex;gap:10px;align-items:center;justify-content:space-between;margin:10px 0}.row label{color:#d6dcef}.stack{display:grid;gap:9px}input,textarea{width:100%;background:#0c1120;color:var(--text);border:1px solid var(--line);border-radius:12px;padding:11px 12px;outline:none}textarea{min-height:110px;resize:vertical}.switch{position:relative;width:48px;height:26px}.switch input{opacity:0;width:0;height:0}.slider{position:absolute;inset:0;background:#34405a;border-radius:999px;cursor:pointer}.slider:before{content:"";position:absolute;height:20px;width:20px;left:3px;top:3px;background:white;border-radius:50%;transition:.2s}.switch input:checked + .slider{background:var(--good)}.switch input:checked + .slider:before{transform:translateX(22px)}button{border:0;border-radius:12px;padding:11px 15px;font-weight:700;cursor:pointer;background:var(--accent);color:#fff}.muted{color:var(--muted);font-size:13px}.actions{display:flex;gap:10px;flex-wrap:wrap}.lock{display:flex;justify-content:space-between;align-items:center;padding:11px 12px;border:1px solid var(--line);border-radius:12px}.toast{position:fixed;right:18px;bottom:18px;background:#18223a;border:1px solid var(--line);padding:12px 15px;border-radius:12px;display:none}.danger{background:#9f3a55}.full{grid-column:1/-1}
</style></head>
<body><div class="wrap"><div class="hero"><div><div class="title">🌹 Rose Clone Setup</div><div class="sub" id="chatLabel">Loading…</div></div><div class="badge">Admin Panel</div></div>
<div class="grid"><section class="card"><h2>👋 Welcome</h2><div class="row"><label>Enable welcome</label><label class="switch"><input id="welcome_enabled" type="checkbox"><span class="slider"></span></label></div><div class="stack"><input id="welcome_text" placeholder="Welcome message"></div></section>
<section class="card"><h2>🚪 Goodbye</h2><div class="row"><label>Enable goodbye</label><label class="switch"><input id="goodbye_enabled" type="checkbox"><span class="slider"></span></label></div><div class="stack"><input id="goodbye_text" placeholder="Goodbye message"></div></section>
<section class="card"><h2>⚠️ Moderation limits</h2><div class="stack"><label class="muted">Flood limit</label><input id="flood_limit" type="number" min="1" max="50"><label class="muted">Warn limit</label><input id="warn_limit" type="number" min="1" max="20"></div></section>
<section class="card"><h2>📜 Rules</h2><textarea id="rules" placeholder="Group rules…"></textarea></section>
<section class="card full"><h2>🔒 Locks</h2><div id="locks" class="stack"></div></section>
<section class="card full"><div class="actions"><button onclick="saveAll()">💾 Save settings</button><button onclick="reloadData()">↻ Reload</button></div><p class="muted">Only the Telegram admin who generated this setup link can edit these settings. Setup links expire automatically.</p></section></div></div><div class="toast" id="toast"></div>
<script>
const token=new URLSearchParams(location.search).get('token');
function toast(t){const e=document.getElementById('toast');e.textContent=t;e.style.display='block';setTimeout(()=>e.style.display='none',2200)}
async function api(url,opt={}){opt.headers={...(opt.headers||{}),'content-type':'application/json'};const r=await fetch(url,opt);const d=await r.json();if(!r.ok)throw new Error(d.detail||'Request failed');return d}
async function reloadData(){const d=await api('/api/setup?token='+encodeURIComponent(token));document.getElementById('chatLabel').textContent=d.title+' • '+d.type;for(const k of ['welcome_enabled','goodbye_enabled'])document.getElementById(k).checked=d[k];for(const k of ['welcome_text','goodbye_text','rules','flood_limit','warn_limit'])document.getElementById(k).value=d[k]??'';renderLocks(d.locks||[])}
function renderLocks(locks){const root=document.getElementById('locks');root.innerHTML='';const types=['links','photos','videos','stickers','gifs','forwards','bots','text'];for(const t of types){const on=locks.includes(t);root.insertAdjacentHTML('beforeend',`<div class="lock"><span>${t}</span><label class="switch"><input data-lock="${t}" type="checkbox" ${on?'checked':''}><span class="slider"></span></label></div>`)}}
async function saveAll(){const body={welcome_enabled:document.getElementById('welcome_enabled').checked,welcome_text:document.getElementById('welcome_text').value,goodbye_enabled:document.getElementById('goodbye_enabled').checked,goodbye_text:document.getElementById('goodbye_text').value,rules:document.getElementById('rules').value,flood_limit:Number(document.getElementById('flood_limit').value),warn_limit:Number(document.getElementById('warn_limit').value)};await api('/api/setup?token='+encodeURIComponent(token),{method:'POST',body:JSON.stringify(body)});for(const el of document.querySelectorAll('[data-lock]'))await api('/api/lock?token='+encodeURIComponent(token),{method:'POST',body:JSON.stringify({lock_type:el.dataset.lock,enabled:el.checked})});toast('✅ Settings saved')}
if(!token){document.body.innerHTML='<div class="wrap"><div class="card"><h2>Invalid setup link</h2><p class="muted">Open the setup button from the Rose Clone bot.</p></div></div>'}else{reloadData().catch(e=>{document.body.innerHTML='<div class="wrap"><div class="card"><h2>Access denied</h2><p class="muted">'+e.message+'</p></div></div>'})}
</script></body></html>'''


def _payload(token: str):
    try:
        return verify_setup_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


async def _is_admin(bot, chat_id: int, user_id: int) -> bool:
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in {"creator", "administrator"}


def build_app(bot) -> FastAPI:
    app = FastAPI(title="Rose Clone Setup", docs_url=None, redoc_url=None)

    @app.get("/health")
    async def health():
        return {"ok": True, "service": "rose-clone"}

    @app.get("/setup", response_class=HTMLResponse)
    async def setup_page():
        return HTMLResponse(DASHBOARD)

    @app.get("/api/setup")
    async def get_setup(token: str = Query(...)):
        p = _payload(token)
        chat_id, user_id = int(p["chat_id"]), int(p["user_id"])
        if not await _is_admin(bot, chat_id, user_id):
            raise HTTPException(status_code=403, detail="Telegram admin permission required")
        chat = await bot.get_chat(chat_id)
        async with async_session() as session:
            group = await session.get(Group, chat_id)
            if not group:
                group = Group(id=chat_id, title=chat.title or "")
                session.add(group)
                await session.commit()
            locks = (await session.execute(select(Lock).where(Lock.group_id == chat_id, Lock.enabled == True))).scalars().all()
        return JSONResponse({"title": group.title or chat.title or str(chat_id), "type": chat.type, "welcome_enabled": group.welcome_enabled, "welcome_text": group.welcome_text or "", "goodbye_enabled": group.goodbye_enabled, "goodbye_text": group.goodbye_text or "", "rules": group.rules or "", "flood_limit": group.flood_limit, "warn_limit": group.warn_limit, "locks": [x.lock_type for x in locks]})

    @app.post("/api/setup")
    async def save_setup(payload: SetupPayload, token: str = Query(...)):
        p = _payload(token)
        chat_id, user_id = int(p["chat_id"]), int(p["user_id"])
        if not await _is_admin(bot, chat_id, user_id):
            raise HTTPException(status_code=403, detail="Telegram admin permission required")
        chat = await bot.get_chat(chat_id)
        async with async_session() as session:
            group = await session.get(Group, chat_id)
            if not group:
                group = Group(id=chat_id, title=chat.title or "")
                session.add(group)
            group.title = chat.title or group.title or ""
            group.welcome_enabled = payload.welcome_enabled
            group.welcome_text = payload.welcome_text
            group.goodbye_enabled = payload.goodbye_enabled
            group.goodbye_text = payload.goodbye_text
            group.rules = payload.rules
            group.flood_limit = payload.flood_limit
            group.warn_limit = payload.warn_limit
            await session.commit()
        return {"ok": True}

    @app.post("/api/lock")
    async def save_lock(payload: LockPayload, token: str = Query(...)):
        p = _payload(token)
        chat_id, user_id = int(p["chat_id"]), int(p["user_id"])
        if not await _is_admin(bot, chat_id, user_id):
            raise HTTPException(status_code=403, detail="Telegram admin permission required")
        async with async_session() as session:
            stmt = select(Lock).where(Lock.group_id == chat_id, Lock.lock_type == payload.lock_type.lower())
            lock = (await session.execute(stmt)).scalar_one_or_none()
            if lock:
                lock.enabled = payload.enabled
            elif payload.enabled:
                session.add(Lock(group_id=chat_id, lock_type=payload.lock_type.lower(), enabled=True))
            await session.commit()
        return {"ok": True}

    return app
