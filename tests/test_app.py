import importlib
import os
from pathlib import Path

from fastapi.testclient import TestClient


def setup_test_env(tmp_path: Path):
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path}/test.db"
    os.environ["ADMIN_USER"] = "admin"
    os.environ["ADMIN_PASSWORD"] = "secret"
    os.environ["SECRET_KEY"] = "test-secret"


def test_invite_creation_and_visit(tmp_path):
    setup_test_env(tmp_path)
    import app.main

    importlib.reload(app.main)
    app = app.main.create_app()

    from app.db import init_db
    from app import auth

    init_db()

    client = TestClient(app)

    session_token = auth.create_session("admin")
    client.cookies.set("admin_session", session_token)

    response = client.post(
        "/admin/invites",
        data={"note": "Test", "campaign": "Onboarding"},
        follow_redirects=False,
    )
    assert response.status_code == 302

    dashboard = client.get("/admin")
    assert dashboard.status_code == 200
    assert "/t/" in dashboard.text

    token = dashboard.text.split("/t/")[1].split("\"")[0]
    tracking = client.get(f"/t/{token}")
    assert tracking.status_code == 200
    assert "Факт посещения" in tracking.text
