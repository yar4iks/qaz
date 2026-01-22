import logging
from datetime import datetime
import secrets
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import (
    SESSION_COOKIE,
    check_rate_limit,
    create_session_cookie,
    get_admin_credentials,
    require_admin,
)
from app.db import get_session
from app.models import Invite, Visit, VisitEvent

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_form(request: Request):
    return request.app.state.templates.TemplateResponse(
        "admin_login.html", {"request": request, "error": None}
    )


@router.post("/admin/login")
async def admin_login(request: Request, username: str = Form(...), password: str = Form(...)):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"login:{client_ip}"):
        return request.app.state.templates.TemplateResponse(
            "admin_login.html",
            {"request": request, "error": "Слишком много попыток. Попробуйте позже."},
            status_code=429,
        )
    admin_user, admin_pass = get_admin_credentials()
    if username != admin_user or password != admin_pass:
        return request.app.state.templates.TemplateResponse(
            "admin_login.html",
            {"request": request, "error": "Неверные учетные данные."},
            status_code=401,
        )
    response = RedirectResponse(url="/admin", status_code=302)
    response.set_cookie(
        SESSION_COOKIE,
        create_session_cookie(),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 8,
    )
    return response


@router.post("/admin/logout")
async def admin_logout():
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_session)):
    redirect = require_admin(request)
    if redirect:
        return redirect

    invites = db.query(Invite).order_by(Invite.created_at.desc()).all()
    invite_stats = []
    for invite in invites:
        total_visits = db.query(Visit).filter(Visit.invite_id == invite.id).count()
        unique_visits = (
            db.query(Visit.day_bucket, Visit.ip, Visit.user_agent)
            .filter(Visit.invite_id == invite.id)
            .distinct()
            .count()
        )
        status = "active"
        now = datetime.utcnow()
        if invite.is_disabled:
            status = "disabled"
        elif invite.expires_at and invite.expires_at < now:
            status = "expired"
        elif invite.max_uses is not None and total_visits >= invite.max_uses:
            status = "exhausted"
        invite_stats.append(
            {
                "invite": invite,
                "total_visits": total_visits,
                "unique_visits": unique_visits,
                "status": status,
            }
        )

    events = (
        db.query(VisitEvent)
        .order_by(VisitEvent.created_at.desc())
        .limit(100)
        .all()
    )

    return request.app.state.templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "invite_stats": invite_stats,
            "events": events,
        },
    )


@router.post("/admin/invites")
async def create_invite(
    request: Request,
    note: str = Form(...),
    campaign: str = Form(...),
    expires_at: str = Form(""),
    max_uses: str = Form(""),
    db: Session = Depends(get_session),
):
    redirect = require_admin(request)
    if redirect:
        return redirect

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
    logger.info("Invite created: %s", token)
    return RedirectResponse(url="/admin", status_code=302)


@router.post("/admin/invites/{invite_id}/disable")
async def disable_invite(
    request: Request, invite_id: int, db: Session = Depends(get_session)
):
    redirect = require_admin(request)
    if redirect:
        return redirect

    invite = db.query(Invite).filter(Invite.id == invite_id).first()
    if invite:
        invite.is_disabled = True
        db.commit()
    return RedirectResponse(url="/admin", status_code=302)
