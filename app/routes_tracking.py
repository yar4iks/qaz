from datetime import datetime
import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

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


def _record_visit(
    db: Session,
    invite: Invite | None,
    token: str,
    request: Request,
    result: str,
) -> None:
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    visit = Visit(
        invite_id=invite.id if invite else None,
        ip=ip_address,
        user_agent=user_agent,
        day_bucket=datetime.utcnow().date(),
        token=token,
        result=result,
    )
    db.add(visit)
    db.commit()
    logger.info("Visit %s from %s result=%s", token, ip_address, result)


@router.get("/t/{token}", response_class=HTMLResponse)
async def track_invite(token: str, request: Request):
    db = SessionLocal()
    try:
        invite = db.execute(select(Invite).where(Invite.token == token)).scalar_one_or_none()
        if not invite:
            _record_visit(db, None, token, request, "invalid")
            return templates.TemplateResponse(
                "invalid.html",
                {"request": request, "message": "Ссылка недействительна."},
                status_code=404,
            )

        now = datetime.utcnow()
        total_visits = db.execute(
            select(func.count(Visit.id))
            .where(Visit.invite_id == invite.id)
            .where(Visit.result == "accepted")
        ).scalar_one()

        if invite.is_disabled:
            _record_visit(db, invite, token, request, "disabled")
            return templates.TemplateResponse(
                "invalid.html",
                {"request": request, "message": "Приглашение деактивировано."},
                status_code=403,
            )
        if invite.expires_at and invite.expires_at < now:
            _record_visit(db, invite, token, request, "expired")
            return templates.TemplateResponse(
                "invalid.html",
                {"request": request, "message": "Срок действия приглашения истёк."},
                status_code=410,
            )
        if invite.max_uses is not None and total_visits >= invite.max_uses:
            _record_visit(db, invite, token, request, "exhausted")
            return templates.TemplateResponse(
                "invalid.html",
                {"request": request, "message": "Лимит посещений исчерпан."},
                status_code=410,
            )

        _record_visit(db, invite, token, request, "accepted")
        return templates.TemplateResponse("tracking.html", {"request": request})
    finally:
        db.close()
