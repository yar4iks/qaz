from datetime import datetime
import logging
import secrets

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import literal

from app import auth
from app.db import SessionLocal
from app.models import Invite, Visit


logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_admin(request: Request) -> auth.AdminSession | None:
    token = request.cookies.get("admin_session")
    if not token:
        return None
    return auth.read_session(token)


def _status_for_invite(invite: Invite, total_visits: int) -> str:
    now = datetime.utcnow()
    if invite.is_disabled:
        return "disabled"
    if invite.expires_at and invite.expires_at < now:
        return "expired"
    if invite.max_uses is not None and total_visits >= invite.max_uses:
        return "exhausted"
    return "active"


@router.get("/admin/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/admin/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    ip_address = request.client.host if request.client else "unknown"
    if auth.is_rate_limited(ip_address):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Слишком много попыток. Попробуйте позже.",
            },
            status_code=429,
        )
    auth.record_login_attempt(ip_address)
    if not auth.verify_credentials(username, password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверные учётные данные."},
            status_code=401,
        )
    auth.clear_login_attempts(ip_address)
    session_token = auth.create_session(username)
    response = RedirectResponse(url="/admin", status_code=302)
    response.set_cookie(
        "admin_session",
        session_token,
        httponly=True,
        samesite="lax",
    )
    return response


@router.post("/admin/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie("admin_session")
    return response


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    session = require_admin(request)
    if not session:
        return RedirectResponse(url="/admin/login", status_code=302)

    invites = db.execute(select(Invite).order_by(Invite.created_at.desc())).scalars().all()

    total_counts = {
        invite_id: count
        for invite_id, count in db.execute(
            select(Visit.invite_id, func.count(Visit.id))
            .where(Visit.result == "accepted")
            .group_by(Visit.invite_id)
        ).all()
    }

    unique_expr = func.count(
        func.distinct(
            cast(Visit.day_bucket, String)
            + literal("|")
            + Visit.ip
            + literal("|")
            + Visit.user_agent
        )
    )
    unique_counts = {
        invite_id: count
        for invite_id, count in db.execute(
            select(Visit.invite_id, unique_expr)
            .where(Visit.result == "accepted")
            .group_by(Visit.invite_id)
        ).all()
    }

    invite_rows = []
    for invite in invites:
        total = int(total_counts.get(invite.id, 0) or 0)
        unique = int(unique_counts.get(invite.id, 0) or 0)
        invite_rows.append(
            {
                "invite": invite,
                "total_visits": total,
                "unique_visits": unique,
                "status": _status_for_invite(invite, total),
            }
        )

    visits = (
        db.execute(
            select(Visit).order_by(Visit.created_at.desc()).limit(100)
        )
        .scalars()
        .all()
    )

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "invites": invite_rows,
            "visits": visits,
        },
    )


@router.post("/admin/invites")
async def create_invite(
    request: Request,
    note: str = Form(...),
    campaign: str = Form(...),
    expires_at: str | None = Form(None),
    max_uses: str | None = Form(None),
    db: Session = Depends(get_db),
):
    session = require_admin(request)
    if not session:
        return RedirectResponse(url="/admin/login", status_code=302)

    parsed_expires = None
    if expires_at:
        parsed_expires = datetime.fromisoformat(expires_at)

    parsed_max_uses = int(max_uses) if max_uses else None

    token = secrets.token_urlsafe(16)
    invite = Invite(
        token=token,
        note=note,
        campaign=campaign,
        expires_at=parsed_expires,
        max_uses=parsed_max_uses,
    )
    db.add(invite)
    db.commit()
    logger.info("Created invite %s for campaign %s", token, campaign)

    return RedirectResponse(url="/admin", status_code=302)


@router.post("/admin/invites/{invite_id}/disable")
async def disable_invite(
    invite_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    session = require_admin(request)
    if not session:
        return RedirectResponse(url="/admin/login", status_code=302)

    invite = db.get(Invite, invite_id)
    if invite:
        invite.is_disabled = True
        db.add(invite)
        db.commit()
    return RedirectResponse(url="/admin", status_code=302)
