"""
IronPulse - Next-Gen Fitness Tracker
Workouts, Scroll-Morph Progress & Fitness Goal Studio

Engineered by Raj Gautam - Jaunpur, Uttar Pradesh, India
Email: graj13099@gmail.com | Instagram: @linux.userraj | GitHub: https://github.com/Rg100152

NOTE: This project intentionally contains NO phone number anywhere.
"""

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "ironpulse.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp", "avif"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB per photo
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Database helpers
# --------------------------------------------------------------------------- #
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS workouts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                exercise    TEXT NOT NULL,
                category    TEXT NOT NULL DEFAULT 'Strength',
                sets        INTEGER NOT NULL DEFAULT 0,
                reps        INTEGER NOT NULL DEFAULT 0,
                weight      REAL NOT NULL DEFAULT 0,
                calories    INTEGER NOT NULL DEFAULT 0,
                notes       TEXT DEFAULT '',
                logged_at   TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS goals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                category    TEXT NOT NULL DEFAULT 'Strength',
                target      REAL NOT NULL,
                current     REAL NOT NULL DEFAULT 0,
                baseline    REAL NOT NULL DEFAULT 0,
                unit        TEXT NOT NULL DEFAULT 'kg',
                deadline    TEXT DEFAULT '',
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS progress_photos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                photo_url   TEXT NOT NULL,
                kind        TEXT NOT NULL DEFAULT 'progress',
                pair_key    TEXT NOT NULL DEFAULT 'transformation',
                weight      REAL DEFAULT 0,
                taken_on    TEXT DEFAULT '',
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_workouts_category ON workouts(category);
            CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts(logged_at);
            CREATE INDEX IF NOT EXISTS idx_photos_pair ON progress_photos(pair_key, kind);
            """
        )


init_db()


def rows_to_list(rows):
    return [dict(row) for row in rows]


def compute_stats(db):
    total = db.execute("SELECT COUNT(*) AS n FROM workouts").fetchone()["n"]
    agg = db.execute(
        """SELECT COALESCE(SUM(sets*reps*weight), 0) AS volume,
                  COALESCE(SUM(calories), 0) AS calories
           FROM workouts"""
    ).fetchone()
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    week = db.execute(
        "SELECT COALESCE(SUM(sets*reps*weight), 0) AS v FROM workouts WHERE logged_at >= ?",
        (week_ago,),
    ).fetchone()["v"]
    days = db.execute(
        "SELECT DISTINCT date(logged_at) AS d FROM workouts ORDER BY d DESC"
    ).fetchall()
    streak = 0
    cursor = datetime.now().date()
    day_set = {datetime.strptime(r["d"], "%Y-%m-%d").date() for r in days}
    while cursor in day_set:
        streak += 1
        cursor -= timedelta(days=1)
    return {
        "total_workouts": total,
        "total_volume_kg": round(agg["volume"], 1),
        "total_calories": agg["calories"],
        "week_volume_kg": round(week, 1),
        "streak_days": streak,
    }


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    category = request.args.get("category", "All")
    with get_db() as db:
        if category == "All":
            workouts = rows_to_list(
                db.execute("SELECT * FROM workouts ORDER BY logged_at DESC, id DESC LIMIT 60")
            )
        else:
            workouts = rows_to_list(
                db.execute(
                    "SELECT * FROM workouts WHERE category = ? ORDER BY logged_at DESC, id DESC LIMIT 60",
                    (category,),
                )
            )
        goals = rows_to_list(
            db.execute("SELECT * FROM goals ORDER BY (current / MAX(target, 1)) DESC, id")
        )
        photos = rows_to_list(
            db.execute("SELECT * FROM progress_photos ORDER BY created_at DESC, id DESC")
        )
        stats = compute_stats(db)
    for goal in goals:
        if goal["baseline"] > goal["target"]:
            span = goal["baseline"] - goal["target"]
            pct = (goal["baseline"] - goal["current"]) / span * 100
        else:
            pct = goal["current"] / max(goal["target"], 1) * 100
        goal["percent"] = max(0, min(round(pct), 100))
    return render_template(
        "index.html",
        workouts=workouts,
        goals=goals,
        photos=photos,
        stats=stats,
        category=category,
    )


@app.route("/static/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# --------------------------------------------------------------------------- #
# Workouts API
# --------------------------------------------------------------------------- #
@app.route("/api/workouts", methods=["POST"])
def add_workout():
    data = request.get_json(silent=True) or request.form
    exercise = (data.get("exercise") or "").strip()
    if not exercise:
        return jsonify({"ok": False, "error": "Exercise name is required"}), 400
    try:
        values = (
            exercise,
            (data.get("category") or "Strength").strip(),
            int(data.get("sets") or 0),
            int(data.get("reps") or 0),
            float(data.get("weight") or 0),
            int(data.get("calories") or 0),
            (data.get("notes") or "").strip(),
        )
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid numeric value"}), 400
    with get_db() as db:
        cur = db.execute(
            """INSERT INTO workouts (exercise, category, sets, reps, weight, calories, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            values,
        )
        stats = compute_stats(db)
    return jsonify({"ok": True, "id": cur.lastrowid, "stats": stats}), 201


@app.route("/api/workouts/<int:workout_id>", methods=["DELETE"])
def delete_workout(workout_id):
    with get_db() as db:
        db.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))
        stats = compute_stats(db)
    return jsonify({"ok": True, "stats": stats})


# --------------------------------------------------------------------------- #
# Goals API
# --------------------------------------------------------------------------- #
@app.route("/api/goals", methods=["POST"])
def add_goal():
    data = request.get_json(silent=True) or request.form
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"ok": False, "error": "Goal title is required"}), 400
    try:
        target = float(data.get("target") or 0)
        current = float(data.get("current") or 0)
        baseline = float(data.get("baseline") or 0)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid goal numbers"}), 400
    if target <= 0:
        return jsonify({"ok": False, "error": "Target must be greater than zero"}), 400
    with get_db() as db:
        cur = db.execute(
            """INSERT INTO goals (title, category, target, current, baseline, unit, deadline)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                title,
                (data.get("category") or "Strength").strip(),
                target,
                current,
                baseline,
                (data.get("unit") or "kg").strip(),
                (data.get("deadline") or "").strip(),
            ),
        )
    return jsonify({"ok": True, "id": cur.lastrowid}), 201


@app.route("/api/goals/<int:goal_id>/progress", methods=["POST"])
def update_goal(goal_id):
    data = request.get_json(silent=True) or request.form
    try:
        current = float(data.get("current") or 0)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid progress value"}), 400
    with get_db() as db:
        db.execute("UPDATE goals SET current = ? WHERE id = ?", (current, goal_id))
    return jsonify({"ok": True, "current": current})


@app.route("/api/goals/<int:goal_id>", methods=["DELETE"])
def delete_goal(goal_id):
    with get_db() as db:
        db.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
    return jsonify({"ok": True})


# --------------------------------------------------------------------------- #
# Progress photos API
# --------------------------------------------------------------------------- #
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


@app.route("/api/photos", methods=["POST"])
def add_photo():
    title = (request.form.get("title") or "Progress").strip()
    kind = (request.form.get("kind") or "progress").strip()
    pair_key = (request.form.get("pair_key") or "transformation").strip()
    weight = request.form.get("weight") or 0
    taken_on = (request.form.get("taken_on") or "").strip()

    photo_url = (request.form.get("photo_url") or "").strip()
    file = request.files.get("photo")
    if file and file.filename and allowed_file(file.filename):
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        name = secure_filename(f"{stamp}_{file.filename}")
        file.save(UPLOAD_DIR / name)
        photo_url = url_for("uploaded_file", filename=name)
    if not photo_url:
        return jsonify({"ok": False, "error": "Upload a file or paste an image URL"}), 400

    with get_db() as db:
        cur = db.execute(
            """INSERT INTO progress_photos (title, photo_url, kind, pair_key, weight, taken_on)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (title, photo_url, kind, pair_key, float(weight or 0), taken_on),
        )
        photo = dict(db.execute("SELECT * FROM progress_photos WHERE id = ?", (cur.lastrowid,)).fetchone())
    return jsonify({"ok": True, "photo": photo}), 201


@app.route("/api/photos/<int:photo_id>", methods=["DELETE"])
def delete_photo(photo_id):
    with get_db() as db:
        db.execute("DELETE FROM progress_photos WHERE id = ?", (photo_id,))
    return jsonify({"ok": True})


@app.route("/api/stats")
def stats_api():
    with get_db() as db:
        return jsonify(compute_stats(db))


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"ok": False, "error": "Photo is too large (max 8 MB)"}), 413


if __name__ == "__main__":
    print("\n  IronPulse is LIVE  ->  http://127.0.0.1:5000")
    print("  Built by Raj Gautam | Jaunpur, UP | @linux.userraj\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
