import os
from fastapi.testclient import TestClient

from app.main import create_app
from app.db import SessionLocal
from app.models import Invite, Visit


def setup_module(module):
    os.environ["SECRET_KEY"] = "test-key"
    os.environ["ADMIN_USERNAME"] = "admin"
    os.environ["ADMIN_PASSWORD"] = "admin"


def test_create_invite_and_visit(tmp_path):
    db_path = tmp_path / "test.db"
    app = create_app(f"sqlite:///{db_path}")
    client = TestClient(app)

    response = client.post(
        "/admin/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    cookie = response.cookies.get("admin_session")
    assert cookie

    create_response = client.post(
        "/admin/invites",
        data={"note": "test", "campaign": "awareness"},
        cookies={"admin_session": cookie},
        follow_redirects=False,
    )
    assert create_response.status_code == 302

    with SessionLocal() as db:
        invite = db.query(Invite).first()
        assert invite is not None
        token = invite.token

    visit_response = client.get(f"/t/{token}")
    assert visit_response.status_code == 200

    with SessionLocal() as db:
        visits = db.query(Visit).filter(Visit.invite_id == invite.id).all()
        assert len(visits) == 1
