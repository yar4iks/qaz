import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Invite, Visit, VisitEvent

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/t/{token}", response_class=HTMLResponse)
async def track_visit(token: str, request: Request, db: Session = Depends(get_session)):
    invite = db.query(Invite).filter(Invite.token == token).first()
    now = datetime.utcnow()
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    if not invite:
        db.add(
            VisitEvent(
                token=token,
                invite_id=None,
                ip=ip,
                user_agent=user_agent,
                result="invalid",
            )
        )
        db.commit()
        return request.app.state.templates.TemplateResponse(
            "tracking_invalid.html",
            {
                "request": request,
                "message": "Ссылка недействительна.",
            },
            status_code=404,
        )

    total_visits = db.query(Visit).filter(Visit.invite_id == invite.id).count()
    if invite.is_disabled:
        result = "disabled"
    elif invite.expires_at and invite.expires_at < now:
        result = "expired"
    elif invite.max_uses is not None and total_visits >= invite.max_uses:
        result = "exhausted"
    else:
        result = "accepted"

    event = VisitEvent(
        token=token,
        invite_id=invite.id,
        ip=ip,
        user_agent=user_agent,
        result=result,
    )
    db.add(event)

    if result == "accepted":
        day_bucket = now.strftime("%Y-%m-%d")
        exists = (
            db.query(Visit)
            .filter(
                Visit.invite_id == invite.id,
                Visit.ip == ip,
                Visit.user_agent == user_agent,
                Visit.day_bucket == day_bucket,
            )
            .first()
        )
        if not exists:
            db.add(
                Visit(
                    invite_id=invite.id,
                    ip=ip,
                    user_agent=user_agent,
                    day_bucket=day_bucket,
                )
            )
        logger.info("Visit recorded: %s from %s", token, ip)
        db.commit()
        return request.app.state.templates.TemplateResponse(
            "tracking_valid.html",
            {"request": request},
        )

    db.commit()
    return request.app.state.templates.TemplateResponse(
        "tracking_invalid.html",
        {
            "request": request,
            "message": "Ссылка недействительна или недоступна.",
        },
        status_code=403,
    )
