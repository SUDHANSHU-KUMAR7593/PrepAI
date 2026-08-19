import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from functools import wraps

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
DATABASE = os.path.join(BASE_DIR, "prepai.sqlite3")

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


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id TEXT PRIMARY KEY,
              email TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL,
              full_name TEXT DEFAULT '',
              target_role TEXT DEFAULT '',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS question_sessions (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              topic TEXT NOT NULL,
              question_type TEXT NOT NULL,
              difficulty TEXT NOT NULL,
              questions TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS mock_interviews (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              topic TEXT NOT NULL,
              role TEXT,
              difficulty TEXT NOT NULL,
              question_type TEXT NOT NULL,
              seconds_per_question INTEGER NOT NULL DEFAULT 120,
              items TEXT NOT NULL,
              overall_score REAL,
              status TEXT NOT NULL DEFAULT 'in_progress',
              completed_at TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS question_sessions_user_created_idx
              ON question_sessions (user_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS mock_interviews_user_created_idx
              ON mock_interviews (user_id, created_at DESC);
            """
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
        "model": os.getenv("AI_MODEL", "gemini-2.0-flash"),
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

        with get_db() as db:
            if mode == "signup":
                if len(password) < 6:
                    flash("Password must be at least 6 characters.", "error")
                    return redirect(url_for("auth", mode="signup"))
                try:
                    user_id = str(uuid.uuid4())
                    db.execute(
                        """
                        INSERT INTO users (id, email, password_hash, full_name, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (user_id, email, generate_password_hash(password), full_name, now_iso(), now_iso()),
                    )
                    session["user_id"] = user_id
                    flash("Account created. Welcome!", "success")
                    return redirect(url_for("dashboard"))
                except sqlite3.IntegrityError:
                    flash("An account already exists for that email.", "error")
            else:
                user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
                if user and check_password_hash(user["password_hash"], password):
                    session["user_id"] = user["id"]
                    flash("Signed in.", "success")
                    return redirect(url_for("dashboard"))
                flash("Invalid email or password.", "error")

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
