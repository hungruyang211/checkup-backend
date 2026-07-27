import sqlite3, os
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, request, jsonify

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "records.db"
JST = timedelta(hours=9)
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "换成你的密码")

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        app_name TEXT NOT NULL,
        event TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )""")
    conn.commit()
    conn.close()

init_db()

app = Flask(__name__)

@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    return response

@app.route("/report", methods=["POST", "OPTIONS"])
def report():
    if request.method == "OPTIONS":
        return ""
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {AUTH_TOKEN}":
        return jsonify({"error": "Unauthorized"}), 401
    body = request.get_json()
    if not body or "app_name" not in body or "event" not in body:
        return jsonify({"error": "Missing fields"}), 400
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("INSERT INTO records (app_name, event, timestamp) VALUES (?, ?, ?)",
                 (body["app_name"], body["event"], now))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/ping")
def ping():
    return "pong"

@app.route("/activity/summary")
def summary():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("SELECT app_name, event, timestamp FROM records ORDER BY id DESC LIMIT 5")
    recent = cur.fetchall()
    cur.execute("SELECT app_name, event, timestamp FROM records ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()
    sessions, opens = {}, {}
    for r in rows:
        app_name, ev, ts = r
        if ev == "open":
            opens[app_name] = datetime.fromisoformat(ts)
        elif ev == "close" and app_name in opens:
            gap = int((datetime.fromisoformat(ts) - opens[app_name]).total_seconds())
            sessions[app_name] = sessions.get(app_name, 0) + gap
            del opens[app_name]
    return jsonify({
        "recent_apps": [r[0] for r in recent],
        "sessions": sessions
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
