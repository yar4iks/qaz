import os
import time
from typing import Optional
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from fastapi import Request
from fastapi.responses import RedirectResponse

SESSION_COOKIE = "admin_session"
SESSION_MAX_AGE = 60 * 60 * 8

_rate_limit_store: dict[str, list[float]] = {}


def get_secret_key() -> str:
    return os.getenv("SECRET_KEY", "change-me")


def get_admin_credentials() -> tuple[str, str]:
    return (
        os.getenv("ADMIN_USERNAME", "admin"),
        os.getenv("ADMIN_PASSWORD", "admin"),
    )


def get_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_secret_key())


def create_session_cookie() -> str:
    serializer = get_serializer()
    return serializer.dumps({"is_admin": True})


def is_admin_authenticated(request: Request) -> bool:
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        return False
    serializer = get_serializer()
    try:
        data = serializer.loads(cookie, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return False
    return bool(data.get("is_admin"))


def require_admin(request: Request) -> Optional[RedirectResponse]:
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=302)
    return None


def check_rate_limit(key: str, limit: int = 5, window_seconds: int = 60) -> bool:
    now = time.time()
    timestamps = _rate_limit_store.get(key, [])
    timestamps = [ts for ts in timestamps if now - ts < window_seconds]
    if len(timestamps) >= limit:
        _rate_limit_store[key] = timestamps
        return False
    timestamps.append(now)
    _rate_limit_store[key] = timestamps
    return True
