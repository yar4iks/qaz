import os
import time
from dataclasses import dataclass
from typing import Optional

from itsdangerous import BadSignature, URLSafeTimedSerializer


@dataclass
class AdminSession:
    username: str


RATE_LIMIT_WINDOW_SECONDS = 300
RATE_LIMIT_MAX_ATTEMPTS = 5
_login_attempts: dict[str, list[float]] = {}


def _serializer() -> URLSafeTimedSerializer:
    secret_key = os.getenv("SECRET_KEY", "change-me")
    return URLSafeTimedSerializer(secret_key, salt="admin-session")


def record_login_attempt(ip_address: str) -> None:
    now = time.time()
    attempts = _login_attempts.setdefault(ip_address, [])
    attempts.append(now)
    _login_attempts[ip_address] = [
        ts for ts in attempts if now - ts <= RATE_LIMIT_WINDOW_SECONDS
    ]


def is_rate_limited(ip_address: str) -> bool:
    now = time.time()
    attempts = _login_attempts.get(ip_address, [])
    attempts = [ts for ts in attempts if now - ts <= RATE_LIMIT_WINDOW_SECONDS]
    _login_attempts[ip_address] = attempts
    return len(attempts) >= RATE_LIMIT_MAX_ATTEMPTS


def clear_login_attempts(ip_address: str) -> None:
    _login_attempts.pop(ip_address, None)


def verify_credentials(username: str, password: str) -> bool:
    admin_user = os.getenv("ADMIN_USER", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin")
    return username == admin_user and password == admin_password


def create_session(username: str) -> str:
    serializer = _serializer()
    return serializer.dumps({"username": username})


def read_session(token: str, max_age_seconds: int = 60 * 60 * 12) -> Optional[AdminSession]:
    serializer = _serializer()
    try:
        data = serializer.loads(token, max_age=max_age_seconds)
    except BadSignature:
        return None
    username = data.get("username")
    if not username:
        return None
    return AdminSession(username=username)
