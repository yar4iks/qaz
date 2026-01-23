import os
import secrets
import sqlite3
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, Response, jsonify, request

DB_PATH = os.environ.get("VISITOR_DB_PATH", "data.db")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")
ADMIN_IPS = {
    ip.strip()
    for ip in os.environ.get("ADMIN_IPS", "").split(",")
    if ip.strip()
}

app = Flask(__name__)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS visitors (
                ip TEXT PRIMARY KEY,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                visit_count INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS links (
                token TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            )
            """
        )


init_db()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_client_ip() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"


def is_admin_request() -> bool:
    auth = request.authorization
    if auth and auth.username == ADMIN_USER and auth.password == ADMIN_PASSWORD:
        return True
    client_ip = get_client_ip()
    return client_ip in ADMIN_IPS


def require_admin(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not is_admin_request():
            return Response(
                "Unauthorized",
                status=401,
                headers={"WWW-Authenticate": 'Basic realm="Admin"'},
            )
        return view_func(*args, **kwargs)

    return wrapper


def record_visit(ip: str) -> None:
    now = utc_now()
    with get_db() as conn:
        row = conn.execute(
            "SELECT visit_count FROM visitors WHERE ip = ?",
            (ip,),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE visitors SET last_seen = ?, visit_count = visit_count + 1 WHERE ip = ?",
                (now, ip),
            )
        else:
            conn.execute(
                "INSERT INTO visitors (ip, first_seen, last_seen, visit_count) VALUES (?, ?, ?, ?)",
                (ip, now, now, 1),
            )


def render_greeting(ip: str) -> Response:
    return Response(f"Hello, guest{ip}", mimetype="text/plain; charset=utf-8")


@app.route("/")
def index() -> Response:
    ip = get_client_ip()
    if not is_admin_request():
        record_visit(ip)
    return render_greeting(ip)


@app.route("/<token>")
def token_index(token: str) -> Response:
    with get_db() as conn:
        link = conn.execute(
            "SELECT token FROM links WHERE token = ?",
            (token,),
        ).fetchone()
    if link is None:
        return Response("Not Found", status=404)
    ip = get_client_ip()
    if not is_admin_request():
        record_visit(ip)
    return render_greeting(ip)


@app.route("/admin")
@require_admin
def admin_dashboard() -> Response:
    with get_db() as conn:
        visitor_rows = conn.execute(
            "SELECT ip, first_seen, last_seen, visit_count FROM visitors ORDER BY last_seen DESC"
        ).fetchall()
        total_visits = conn.execute(
            "SELECT COALESCE(SUM(visit_count), 0) AS total FROM visitors"
        ).fetchone()["total"]
        total_visitors = conn.execute(
            "SELECT COUNT(*) AS total FROM visitors"
        ).fetchone()["total"]
        link_rows = conn.execute(
            "SELECT token, created_at FROM links ORDER BY created_at DESC"
        ).fetchall()

    rows_html = "".join(
        f"<tr><td>{row['ip']}</td><td>{row['visit_count']}</td><td>{row['first_seen']}</td><td>{row['last_seen']}</td></tr>"
        for row in visitor_rows
    )
    links_html = "".join(
        f"<li>{request.url_root}{row['token']} ({row['created_at']})</li>"
        for row in link_rows
    )

    html = f"""
    <!doctype html>
    <html lang=\"en\">
      <head>
        <meta charset=\"utf-8\">
        <title>Admin</title>
      </head>
      <body>
        <h1>Admin dashboard</h1>
        <p>Total visitors: {total_visitors}</p>
        <p>Total visits: {total_visits}</p>
        <form method=\"post\" action=\"/admin/generate\">
          <button type=\"submit\">Generate new link</button>
        </form>
        <h2>Links</h2>
        <ul>
          {links_html or '<li>No links yet.</li>'}
        </ul>
        <h2>Visitors</h2>
        <table border=\"1\" cellspacing=\"0\" cellpadding=\"4\">
          <thead>
            <tr><th>IP</th><th>Visits</th><th>First seen</th><th>Last seen</th></tr>
          </thead>
          <tbody>
            {rows_html or '<tr><td colspan="4">No visitors yet.</td></tr>'}
          </tbody>
        </table>
      </body>
    </html>
    """
    return Response(html, mimetype="text/html; charset=utf-8")


@app.route("/admin/generate", methods=["POST"])
@require_admin
def generate_link() -> Response:
    token = secrets.token_urlsafe(8)
    now = utc_now()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO links (token, created_at) VALUES (?, ?)",
            (token, now),
        )
    return jsonify({"link": f"{request.url_root}{token}"})


@app.route("/admin/visitors")
@require_admin
def visitors_api() -> Response:
    with get_db() as conn:
        visitors = conn.execute(
            "SELECT ip, first_seen, last_seen, visit_count FROM visitors ORDER BY last_seen DESC"
        ).fetchall()
    return jsonify([dict(row) for row in visitors])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
