from __future__ import annotations

import os
import secrets
import sqlite3
from datetime import datetime, timezone
from functools import wraps
from typing import Callable

from flask import Flask, g, redirect, render_template, request, session, url_for

DATABASE_PATH = os.environ.get("VISITOR_DB", "visitors.sqlite")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")
SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(16))

app = Flask(__name__)
app.secret_key = SECRET_KEY


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        connection = sqlite3.connect(DATABASE_PATH)
        connection.row_factory = sqlite3.Row
        g.db = connection
    return g.db


def init_db() -> None:
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT NOT NULL,
            visited_at TEXT NOT NULL
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        )
        """
    )
    db.commit()


@app.before_request
def attach_db() -> None:
    init_db()


@app.teardown_appcontext
def close_db(error: Exception | None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def get_client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def record_visit(ip_address: str) -> None:
    db = get_db()
    db.execute(
        "INSERT INTO visitors (ip_address, visited_at) VALUES (?, ?)",
        (ip_address, datetime.now(timezone.utc).isoformat()),
    )
    db.commit()


def login_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped


@app.route("/")
def index() -> str:
    ip_address = get_client_ip()
    if not session.get("admin"):
        record_visit(ip_address)
    return render_template("index.html", ip_address=ip_address)


@app.route("/l/<token>")
def link_redirect(token: str) -> str:
    db = get_db()
    link = db.execute("SELECT token FROM links WHERE token = ?", (token,)).fetchone()
    if link is None:
        return redirect(url_for("index"))
    return redirect(url_for("index", token=token))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login() -> str:
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        error = "Неверный логин или пароль."
    return render_template("admin_login.html", error=error)


@app.route("/admin/logout")
@login_required
def admin_logout() -> str:
    session.pop("admin", None)
    return redirect(url_for("index"))


@app.route("/admin")
@login_required
def admin_dashboard() -> str:
    db = get_db()
    visitors = db.execute(
        "SELECT ip_address, visited_at FROM visitors ORDER BY visited_at DESC"
    ).fetchall()
    links = db.execute(
        "SELECT token, created_at FROM links ORDER BY created_at DESC"
    ).fetchall()
    return render_template("admin_dashboard.html", visitors=visitors, links=links)


@app.route("/admin/links", methods=["POST"])
@login_required
def create_link() -> str:
    db = get_db()
    token = secrets.token_urlsafe(8)
    db.execute(
        "INSERT INTO links (token, created_at) VALUES (?, ?)",
        (token, datetime.now(timezone.utc).isoformat()),
    )
    db.commit()
    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
