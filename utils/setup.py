import base64
import hashlib
import hmac
import json
import os
import time
from urllib.parse import quote

from config import settings


def _secret() -> bytes:
    return settings.SETUP_TOKEN_SECRET.encode("utf-8")


def create_setup_token(chat_id: int, user_id: int, ttl: int = 1800) -> str:
    payload = {"chat_id": chat_id, "user_id": user_id, "exp": int(time.time()) + ttl}
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    body = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    sig = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify_setup_token(token: str) -> dict:
    try:
        body, sig = token.split(".", 1)
        expected = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("invalid signature")
        padded = body + "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()))
        if int(payload["exp"]) < int(time.time()):
            raise ValueError("expired")
        return payload
    except Exception as exc:
        raise ValueError("invalid or expired setup token") from exc


def build_setup_url(chat_id: int, user_id: int) -> str:
    base = settings.WEB_APP_URL.strip().rstrip("/")
    if not base:
        domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()
        if domain:
            base = "https://" + domain
    if not base:
        raise RuntimeError("WEB_APP_URL is not configured")
    token = create_setup_token(chat_id, user_id)
    return f"{base}/setup?token={quote(token)}"
