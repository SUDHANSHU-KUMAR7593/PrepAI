import json
import os
import uuid
from datetime import datetime, timezone
from functools import wraps
from urllib.parse import unquote, urlparse

import pymysql
from pymysql.cursors import DictCursor
import requests
from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.getenv("DATABASE_URL")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "prepai")
MYSQL_SSL_CA = os.getenv("MYSQL_SSL_CA")

QUESTION_TYPES = {"technical", "behavioral", "hr", "system-design"}
DIFFICULTIES = {"easy", "medium", "hard"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "").lower() in {
    "1",
    "true",
    "yes",
} or bool(os.getenv("RENDER"))


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class MySQLDatabase:
    def __init__(self):
        self.conn = pymysql.connect(**mysql_config(), cursorclass=DictCursor, autocommit=False)

    def execute(self, query, params=None):
        cursor = self.conn.cursor()
        cursor.execute(query.replace("?", "%s"), params or ())
        return cursor

    def executescript(self, script):
        for statement in script.split(";"):
            statement = statement.strip()
            if statement:
                self.execute(statement)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


def mysql_config():
    if DATABASE_URL:
        parsed = urlparse(DATABASE_URL)
        database = parsed.path.lstrip("/")
        config = {
            "host": parsed.hostname or MYSQL_HOST,
            "port": parsed.port or MYSQL_PORT,
            "user": unquote(parsed.username) if parsed.username else MYSQL_USER,
            "password": unquote(parsed.password) if parsed.password else MYSQL_PASSWORD,
            "database": database or MYSQL_DATABASE,
            "charset": "utf8mb4",
        }
    else:
        config = {
            "host": MYSQL_HOST,
            "port": MYSQL_PORT,
            "user": MYSQL_USER,
            "password": MYSQL_PASSWORD,
            "database": MYSQL_DATABASE,
            "charset": "utf8mb4",
        }

    if MYSQL_SSL_CA:
        config["ssl"] = {"ca": MYSQL_SSL_CA}
    return config


def get_db():
    return MySQLDatabase()


def ensure_index(db, table, index, columns):
    existing = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = ?
          AND index_name = ?
        """,
        (table, index),
    ).fetchone()
    if existing["count"] == 0:
        db.execute(f"CREATE INDEX {index} ON {table} ({columns})")


def init_db():
    with get_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id VARCHAR(36) PRIMARY KEY,
              email VARCHAR(255) NOT NULL UNIQUE,
              password_hash VARCHAR(255) NOT NULL,
              full_name VARCHAR(255) DEFAULT '',
              target_role VARCHAR(255) DEFAULT '',
              created_at VARCHAR(40) NOT NULL,
              updated_at VARCHAR(40) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS question_sessions (
              id VARCHAR(36) PRIMARY KEY,
              user_id VARCHAR(36) NOT NULL,
              topic TEXT NOT NULL,
              question_type VARCHAR(50) NOT NULL,
              difficulty VARCHAR(50) NOT NULL,
              questions JSON NOT NULL,
              created_at VARCHAR(40) NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS mock_interviews (
              id VARCHAR(36) PRIMARY KEY,
              user_id VARCHAR(36) NOT NULL,
              topic TEXT NOT NULL,
              role TEXT,
              difficulty VARCHAR(50) NOT NULL,
              question_type VARCHAR(50) NOT NULL,
              seconds_per_question INT NOT NULL DEFAULT 120,
              items JSON NOT NULL,
              overall_score DOUBLE,
              status VARCHAR(50) NOT NULL DEFAULT 'in_progress',
              completed_at VARCHAR(40),
              created_at VARCHAR(40) NOT NULL,
              updated_at VARCHAR(40) NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            """
        )
        ensure_index(
            db,
            "question_sessions",
            "question_sessions_user_created_idx",
            "user_id, created_at DESC",
        )
        ensure_index(
            db,
            "mock_interviews",
            "mock_interviews_user_created_idx",
            "user_id, created_at DESC",
        )


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    with get_db() as db:
        return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


@app.context_processor
def inject_user():
    return {"current_user": current_user(), "year": datetime.now().year}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth", mode="signin"))
        return view(*args, **kwargs)

    return wrapped


def validate_choice(value, allowed, fallback):
    return value if value in allowed else fallback


def clamp_int(value, minimum, maximum, fallback):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(minimum, min(maximum, number))


def ai_config():
    return {
        "api_key": os.getenv("AI_API_KEY"),
        "model": os.getenv("AI_MODEL", "gemini-3.6-flash"),
    }


def call_ai(contents, system_instruction, response_schema):
    """Call Google Gemini generateContent API with structured JSON output."""
    cfg = ai_config()
    if not cfg["api_key"]:
        raise RuntimeError("AI_API_KEY is missing. Add your Google Gemini API key to .env and restart Flask.")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{cfg['model']}:generateContent?key={cfg['api_key']}"
    )
    payload = {
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": contents,
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
            "temperature": 0.7,
        },
    }
    response = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=60)
    if response.status_code == 429:
        raise RuntimeError("Rate limit hit. Try again shortly.")
    if response.status_code == 403:
        raise RuntimeError("Invalid or unauthorized Gemini API key.")
    if not response.ok:
        raise RuntimeError(f"Gemini API request failed ({response.status_code}): {response.text[:300]}")
    return response.json()


def parse_gemini_response(payload):
    """Extract and parse the JSON text from a Gemini generateContent response."""
    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except (TypeError, KeyError, IndexError, json.JSONDecodeError):
        return None


def generate_ai_question_answers(topic, question_type, difficulty, count):
    system = (
        "You are an expert technical interviewer who generates high-quality, realistic interview questions. "
        "Always respond with valid JSON matching the provided schema."
    )
    contents = [{
        "role": "user",
        "parts": [{"text": (
            f'Generate {count} {difficulty} {question_type} interview questions about: "{topic}". '
            "For each, provide a concise model answer in 3-5 sentences."
        )}]
    }]
    schema = {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "answer": {"type": "string"}
                    },
                    "required": ["question", "answer"]
                }
            }
        },
        "required": ["questions"]
    }
    raw = call_ai(contents, system, schema)
    parsed = parse_gemini_response(raw)
    if not parsed or not parsed.get("questions"):
        raise RuntimeError("Gemini did not return valid question answers.")
    return parsed["questions"]


def generate_ai_interview_questions(topic, role, question_type, difficulty, count):
    role_text = f" for a {role}" if role else ""
    system = "You are a senior interviewer. Return a clean list of interview questions only."
    contents = [{
        "role": "user",
        "parts": [{"text": (
            f'Create {count} {difficulty} {question_type} interview questions{role_text} '
            f'on: "{topic}". Make them progressive in difficulty.'
        )}]
    }]
    schema = {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["questions"]
    }
    raw = call_ai(contents, system, schema)
    parsed = parse_gemini_response(raw)
    if not parsed or not parsed.get("questions"):
        raise RuntimeError("Gemini did not return valid interview questions.")
    return parsed["questions"]


def evaluate_ai_answer(row, question, answer, time_taken):
    system = (
        "You are a strict but fair interviewer. Evaluate the candidate's answer on clarity, "
        "relevance, and conciseness. Return structured feedback as JSON. "
        "The ideal_answer field must be a suitable model answer that teaches the topic "
        "clearly enough for a student who does not already know it."
    )
    user_prompt = (
        f"Topic: {row['topic']}\nDifficulty: {row['difficulty']}\nType: {row['question_type']}\n\n"
        f"Question: {question}\n\nCandidate's answer:\n\"\"\"{answer or '(no answer provided)'}\"\"\"\n\n"
        f"Time taken: {time_taken}s of {row['seconds_per_question']}s allowed."
    )
    contents = [{"role": "user", "parts": [{"text": user_prompt}]}]
    schema = {
        "type": "object",
        "properties": {
            "score":            {"type": "number"},
            "clarity":          {"type": "number"},
            "relevance":        {"type": "number"},
            "conciseness":      {"type": "number"},
            "clarity_note":     {"type": "string"},
            "relevance_note":   {"type": "string"},
            "conciseness_note": {"type": "string"},
            "strengths":        {"type": "string"},
            "improvements":     {"type": "string"},
            "ideal_answer":     {"type": "string"},
        },
        "required": [
            "score", "clarity", "relevance", "conciseness",
            "clarity_note", "relevance_note", "conciseness_note",
            "strengths", "improvements", "ideal_answer"
        ]
    }
    raw = call_ai(contents, system, schema)
    parsed = parse_gemini_response(raw)
    if not parsed:
        raise RuntimeError("Gemini did not return valid feedback.")
    return parsed


def clamp_score(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0
    return max(0, min(10, number))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/auth", methods=["GET", "POST"])
def auth():
    mode = request.args.get("mode", "signin")
    if request.method == "POST":
        mode = request.form.get("mode", "signin")
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()

        if mode == "signup":
            confirm_password = request.form.get("confirm_password", "")
            if not email:
                flash("Email is required.", "error")
                return redirect(url_for("auth", mode="signup"))
            if len(password) < 6:
                flash("Password must be at least 6 characters.", "error")
                return redirect(url_for("auth", mode="signup"))
            if password != confirm_password:
                flash("Passwords do not match.", "error")
                return redirect(url_for("auth", mode="signup"))

            db = get_db()
            try:
                # Explicit duplicate-email check before insert
                existing = db.execute(
                    "SELECT id FROM users WHERE email = ?", (email,)
                ).fetchone()
                if existing:
                    flash("An account already exists for that email. Please sign in instead.", "error")
                    db.close()
                    return redirect(url_for("auth", mode="signup"))

                user_id = str(uuid.uuid4())
                ts = now_iso()
                db.execute(
                    """
                    INSERT INTO users (id, email, password_hash, full_name, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, email, generate_password_hash(password), full_name, ts, ts),
                )
                db.commit()  # Explicitly commit so data is on disk before session is set
                session["user_id"] = user_id
                flash("Account created. Welcome!", "success")
                db.close()
                return redirect(url_for("dashboard"))
            except pymysql.err.IntegrityError:
                db.rollback()
                db.close()
                flash("An account already exists for that email.", "error")
                return redirect(url_for("auth", mode="signup"))
            except Exception:
                db.rollback()
                db.close()
                flash("Something went wrong. Please try again.", "error")
                return redirect(url_for("auth", mode="signup"))
        else:
            if not email or not password:
                flash("Email and password are required.", "error")
                return redirect(url_for("auth", mode="signin"))

            db = get_db()
            try:
                user = db.execute(
                    "SELECT * FROM users WHERE email = ?", (email,)
                ).fetchone()
                if user and check_password_hash(user["password_hash"], password):
                    session.clear()  # Clear any stale session before setting new one
                    session["user_id"] = user["id"]
                    db.close()
                    flash("Signed in successfully.", "success")
                    return redirect(url_for("dashboard"))
                db.close()
                flash("Invalid email or password.", "error")
            except Exception:
                db.close()
                flash("Something went wrong. Please try again.", "error")

    return render_template("auth.html", mode=mode)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Signed out.", "success")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    with get_db() as db:
        sessions = db.execute(
            """
            SELECT * FROM question_sessions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 10
            """,
            (user["id"],),
        ).fetchall()
    hydrated = []
    for row in sessions:
        values = dict(row)
        values["questions"] = json.loads(row["questions"])
        hydrated.append(values)
    total_questions = sum(len(row["questions"]) for row in hydrated)
    topics = len({row["topic"].lower() for row in hydrated})
    return render_template(
        "dashboard.html",
        sessions=hydrated,
        total_questions=total_questions,
        topics=topics,
    )


@app.route("/questions", methods=["GET", "POST"])
@login_required
def questions():
    results = None
    mode = None
    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        question_type = validate_choice(request.form.get("question_type"), QUESTION_TYPES, "technical")
        difficulty = validate_choice(request.form.get("difficulty"), DIFFICULTIES, "medium")
        count = clamp_int(request.form.get("count"), 3, 10, 5)
        if not topic:
            flash("Topic is required.", "error")
            return redirect(url_for("questions"))

        try:
            results = generate_ai_question_answers(topic, question_type, difficulty, count)
        except RuntimeError as exc:
            flash(str(exc), "error")
            return redirect(url_for("questions"))

        with get_db() as db:
            db.execute(
                """
                INSERT INTO question_sessions
                  (id, user_id, topic, question_type, difficulty, questions, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    session["user_id"],
                    topic,
                    question_type,
                    difficulty,
                    json.dumps(results),
                    now_iso(),
                ),
            )
        mode = "ai"
        flash(f"Generated {len(results)} questions with AI.", "success")

    return render_template("questions.html", results=results, mode=mode)


@app.route("/mock-interview")
@login_required
def mock_interview():
    return render_template("mock_interview.html", voice=False)


@app.route("/voice-interview")
@login_required
def voice_interview():
    return render_template("mock_interview.html", voice=True)


@app.post("/api/mock-interview/start")
@login_required
def api_start_mock_interview():
    data = request.get_json(force=True)
    topic = str(data.get("topic", "")).strip()
    if not topic:
        abort(400, "Topic is required")
    role = str(data.get("role") or "").strip() or None
    question_type = validate_choice(data.get("questionType"), QUESTION_TYPES, "technical")
    difficulty = validate_choice(data.get("difficulty"), DIFFICULTIES, "medium")
    count = clamp_int(data.get("count"), 3, 10, 5)
    seconds = clamp_int(data.get("secondsPerQuestion"), 30, 600, 120)

    try:
        generated = generate_ai_interview_questions(topic, role, question_type, difficulty, count)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 429
    items = [{"question": q, "answer": "", "feedback": None, "score": None} for q in generated]
    interview_id = str(uuid.uuid4())

    with get_db() as db:
        db.execute(
            """
            INSERT INTO mock_interviews
              (id, user_id, topic, role, difficulty, question_type, seconds_per_question,
               items, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'in_progress', ?, ?)
            """,
            (
                interview_id,
                session["user_id"],
                topic,
                role,
                difficulty,
                question_type,
                seconds,
                json.dumps(items),
                now_iso(),
                now_iso(),
            ),
        )

    return jsonify({"id": interview_id, "questions": generated, "mode": "ai"})


@app.post("/api/mock-interview/submit")
@login_required
def api_submit_answer():
    data = request.get_json(force=True)
    interview_id = str(data.get("interviewId", ""))
    index = clamp_int(data.get("index"), 0, 20, 0)
    answer = str(data.get("answer", ""))[:5000]
    time_taken = clamp_int(data.get("timeTakenSeconds"), 0, 3600, 0)

    with get_db() as db:
        row = db.execute(
            "SELECT * FROM mock_interviews WHERE id = ? AND user_id = ?",
            (interview_id, session["user_id"]),
        ).fetchone()
        if not row:
            abort(404, "Interview not found")

        items = json.loads(row["items"])
        if index >= len(items):
            abort(400, "Invalid question index")
        item = items[index]

        try:
            fb = evaluate_ai_answer(row, item["question"], answer, time_taken)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 429

        rubric = {
            "clarity": clamp_score(fb.get("clarity")),
            "relevance": clamp_score(fb.get("relevance")),
            "conciseness": clamp_score(fb.get("conciseness")),
            "clarity_note": str(fb.get("clarity_note", "")),
            "relevance_note": str(fb.get("relevance_note", "")),
            "conciseness_note": str(fb.get("conciseness_note", "")),
        }
        score = clamp_score(fb.get("score"))
        items[index] = {
            **item,
            "answer": answer,
            "timeTakenSeconds": time_taken,
            "score": score,
            "feedback": {
                "strengths": fb.get("strengths", ""),
                "improvements": fb.get("improvements", ""),
                "ideal_answer": fb.get("ideal_answer", ""),
                "rubric": rubric,
            },
        }
        scored = [item for item in items if isinstance(item.get("score"), (int, float))]
        overall = round(sum(item["score"] for item in scored) / len(scored), 1) if scored else None
        completed = len(scored) == len(items)

        db.execute(
            """
            UPDATE mock_interviews
            SET items = ?, overall_score = ?, status = ?, completed_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                json.dumps(items),
                overall,
                "completed" if completed else "in_progress",
                now_iso() if completed else None,
                now_iso(),
                interview_id,
            ),
        )

    return jsonify(
        {
            "score": score,
            "rubric": rubric,
            "strengths": fb.get("strengths", ""),
            "improvements": fb.get("improvements", ""),
            "idealAnswer": fb.get("ideal_answer", ""),
            "overall": overall,
            "completed": completed,
            "mode": "ai",
        }
    )


init_db()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host="0.0.0.0", port=port, debug=debug)
