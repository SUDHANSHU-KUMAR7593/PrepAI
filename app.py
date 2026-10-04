"""PrepAI — AI-Powered Interview Preparation Platform.

Application factory + all Flask routes.
"""

import json
import logging
import os
from datetime import datetime, timezone

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from ai_service import AIService, AIServiceError, clamp_score
from config import get_config
from extensions import csrf, db, login_manager, migrate
from models import (
    Bookmark,
    MockInterview,
    PracticeAttempt,
    QuestionSession,
    User,
)

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────

QUESTION_TYPES = {"technical", "behavioral", "hr", "system-design", "mcq", "coding", "conceptual"}
DIFFICULTIES = {"easy", "medium", "hard"}


# ── Helpers ──────────────────────────────────────────────────────────────


def now_utc():
    return datetime.now(timezone.utc)


def validate_choice(value, allowed, fallback):
    return value if value in allowed else fallback


def clamp_int(value, minimum, maximum, fallback):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(minimum, min(maximum, number))


def get_ai_service():
    """Create an AIService from current app config."""
    from flask import current_app
    return AIService(
        api_key=current_app.config["AI_API_KEY"],
        model=current_app.config["AI_MODEL"],
    )


# ── Application Factory ─────────────────────────────────────────────────


def create_app(config_override=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load config
    cfg = config_override or get_config()
    app.config.from_object(cfg)

    # Validate critical config
    if not app.config.get("TESTING"):
        cfg.validate()

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)

    # Fail fast if MySQL is unreachable (prevents silent failures or fallbacks)
    if not app.config.get("TESTING"):
        with app.app_context():
            try:
                db.session.execute(text("SELECT 1"))
            except Exception as exc:
                logger.error("MySQL connection error: %s", exc)
                raise RuntimeError(
                    f"MySQL connection error: Unable to connect to database at "
                    f"'{app.config.get('SQLALCHEMY_DATABASE_URI')}'. "
                    f"Ensure MySQL service is active and credentials are correct. Error: {exc}"
                ) from exc

    # Register routes
    _register_routes(app)
    _register_context(app)
    _register_error_handlers(app)

    # Logging
    if not app.debug:
        logging.basicConfig(level=logging.INFO)

    return app


# ── Flask-Login Loader ───────────────────────────────────────────────────

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)


# ── Context Processors ───────────────────────────────────────────────────

def _register_context(app):
    @app.context_processor
    def inject_globals():
        return {
            "current_user": current_user,
            "year": datetime.now().year,
        }


# ── Error Handlers ───────────────────────────────────────────────────────

def _register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        if request.accept_mimetypes.best == "application/json":
            return jsonify({"error": "Not found"}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(429)
    def rate_limited(e):
        if request.accept_mimetypes.best == "application/json":
            return jsonify({"error": "Too many requests. Please wait."}), 429
        flash("Too many requests. Please wait a moment.", "error")
        return redirect(request.referrer or url_for("index"))

    @app.errorhandler(500)
    def server_error(e):
        logger.exception("Internal server error")
        if request.accept_mimetypes.best == "application/json":
            return jsonify({"error": "Internal server error"}), 500
        return render_template("errors/500.html"), 500


# ── Routes ───────────────────────────────────────────────────────────────

def _register_routes(app):

    # ── Public Pages ─────────────────────────────────────────────────

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return render_template("index.html")

    # ── Auth ─────────────────────────────────────────────────────────

    @app.route("/auth", methods=["GET", "POST"])
    def auth():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        mode = request.args.get("mode", "signin")
        if request.method == "POST":
            mode = request.form.get("mode", "signin")
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            full_name = request.form.get("full_name", "").strip()

            if mode == "signup":
                if not email or not password:
                    flash("Email and password are required.", "error")
                    return redirect(url_for("auth", mode="signup"))
                if len(password) < 6:
                    flash("Password must be at least 6 characters.", "error")
                    return redirect(url_for("auth", mode="signup"))
                try:
                    user = User(
                        email=email,
                        password_hash=generate_password_hash(password),
                        full_name=full_name,
                    )
                    db.session.add(user)
                    db.session.commit()
                    login_user(user)
                    flash("Account created. Welcome!", "success")
                    return redirect(url_for("dashboard"))
                except IntegrityError:
                    db.session.rollback()
                    flash("An account already exists for that email.", "error")
            else:
                user = db.session.execute(
                    db.select(User).where(User.email == email)
                ).scalar_one_or_none()
                if user and check_password_hash(user.password_hash, password):
                    login_user(user, remember=True)
                    flash("Signed in.", "success")
                    return redirect(url_for("dashboard"))
                flash("Invalid email or password.", "error")

        return render_template("auth.html", mode=mode)

    @app.route("/logout", methods=["POST"])
    def logout():
        logout_user()
        flash("Signed out.", "success")
        return redirect(url_for("index"))

    # ── Dashboard ────────────────────────────────────────────────────

    @app.route("/dashboard")
    @login_required
    def dashboard():
        # Recent question sessions
        sessions = (
            QuestionSession.query
            .filter_by(user_id=current_user.id)
            .order_by(QuestionSession.created_at.desc())
            .limit(10)
            .all()
        )
        hydrated = []
        for s in sessions:
            try:
                questions = json.loads(s.questions)
            except (json.JSONDecodeError, TypeError):
                questions = []
            hydrated.append({
                "id": s.id,
                "topic": s.topic,
                "question_type": s.question_type,
                "difficulty": s.difficulty,
                "questions": questions,
                "created_at": s.created_at.isoformat() if s.created_at else "",
            })

        total_questions = sum(len(h["questions"]) for h in hydrated)
        topics = len({h["topic"].lower() for h in hydrated})

        # Recent mock interviews
        interviews = (
            MockInterview.query
            .filter_by(user_id=current_user.id)
            .order_by(MockInterview.created_at.desc())
            .limit(10)
            .all()
        )
        interview_data = []
        for iv in interviews:
            try:
                items = json.loads(iv.items)
            except (json.JSONDecodeError, TypeError):
                items = []
            interview_data.append({
                "id": iv.id,
                "topic": iv.topic,
                "difficulty": iv.difficulty,
                "question_type": iv.question_type,
                "status": iv.status,
                "overall_score": iv.overall_score,
                "num_questions": len(items),
                "created_at": iv.created_at.isoformat() if iv.created_at else "",
            })

        # Practice stats
        total_attempts = PracticeAttempt.query.filter_by(user_id=current_user.id).count()
        correct_attempts = PracticeAttempt.query.filter_by(user_id=current_user.id, is_correct=True).count()
        accuracy = round(correct_attempts / total_attempts * 100, 1) if total_attempts > 0 else 0

        # Bookmarks count
        bookmark_count = Bookmark.query.filter_by(user_id=current_user.id).count()

        # Performance by topic
        topic_stats = {}
        all_attempts = PracticeAttempt.query.filter_by(user_id=current_user.id).all()
        for attempt in all_attempts:
            t = attempt.topic.lower()
            if t not in topic_stats:
                topic_stats[t] = {"total": 0, "correct": 0, "scores": []}
            topic_stats[t]["total"] += 1
            if attempt.is_correct:
                topic_stats[t]["correct"] += 1
            if attempt.score is not None:
                topic_stats[t]["scores"].append(attempt.score)

        topic_performance = []
        for t, stats in topic_stats.items():
            avg_score = round(sum(stats["scores"]) / len(stats["scores"]), 1) if stats["scores"] else None
            topic_performance.append({
                "topic": t,
                "total": stats["total"],
                "correct": stats["correct"],
                "accuracy": round(stats["correct"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0,
                "avg_score": avg_score,
            })
        topic_performance.sort(key=lambda x: x["accuracy"])

        return render_template(
            "dashboard.html",
            sessions=hydrated,
            interviews=interview_data,
            total_questions=total_questions,
            topics=topics,
            total_attempts=total_attempts,
            accuracy=accuracy,
            bookmark_count=bookmark_count,
            topic_performance=topic_performance,
        )

    # ── AI Question Generator ────────────────────────────────────────

    @app.route("/questions", methods=["GET", "POST"])
    @login_required
    def questions():
        results = None
        mode = None
        qtype = None
        if request.method == "POST":
            topic = request.form.get("topic", "").strip()
            qtype = validate_choice(request.form.get("question_type"), QUESTION_TYPES, "technical")
            difficulty = validate_choice(request.form.get("difficulty"), DIFFICULTIES, "medium")
            count = clamp_int(request.form.get("count"), 3, 10, 5)
            if not topic:
                flash("Topic is required.", "error")
                return redirect(url_for("questions"))

            try:
                ai = get_ai_service()
                if qtype == "mcq":
                    results = ai.generate_mcq_questions(topic, difficulty, count)
                elif qtype == "coding":
                    results = ai.generate_coding_questions(topic, difficulty, count)
                else:
                    results = ai.generate_questions_with_answers(topic, qtype, difficulty, count)
            except AIServiceError as exc:
                flash(str(exc), "error")
                return redirect(url_for("questions"))
            except Exception as exc:
                logger.exception("Unexpected error generating questions: %s", exc)
                flash(f"Unexpected error generating questions: {exc}", "error")
                return redirect(url_for("questions"))

            # Persist to database (handled separately from AI generation)
            try:
                qs = QuestionSession(
                    user_id=current_user.id,
                    topic=topic,
                    question_type=qtype,
                    difficulty=difficulty,
                    questions=json.dumps(results),
                )
                db.session.add(qs)
                db.session.commit()
            except Exception as db_exc:
                db.session.rollback()
                logger.error("Failed to save question session to MySQL: %s", db_exc)
                flash("Questions were generated, but could not be saved to your library due to a database issue.", "warning")

            mode = "ai"
            flash(f"Generated {len(results)} questions with AI.", "success")

        return render_template("questions.html", results=results, mode=mode, qtype=qtype)

    # ── Question Library ─────────────────────────────────────────────

    @app.route("/library")
    @login_required
    def library():
        page = clamp_int(request.args.get("page"), 1, 1000, 1)
        per_page = 12
        search = request.args.get("search", "").strip()
        filter_type = request.args.get("type", "")
        filter_diff = request.args.get("difficulty", "")

        query = QuestionSession.query.filter_by(user_id=current_user.id)
        if search:
            query = query.filter(QuestionSession.topic.ilike(f"%{search}%"))
        if filter_type and filter_type in QUESTION_TYPES:
            query = query.filter_by(question_type=filter_type)
        if filter_diff and filter_diff in DIFFICULTIES:
            query = query.filter_by(difficulty=filter_diff)

        query = query.order_by(QuestionSession.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        sessions = []
        for s in pagination.items:
            try:
                qs = json.loads(s.questions)
            except (json.JSONDecodeError, TypeError):
                qs = []
            sessions.append({
                "id": s.id,
                "topic": s.topic,
                "question_type": s.question_type,
                "difficulty": s.difficulty,
                "questions": qs,
                "created_at": s.created_at.isoformat() if s.created_at else "",
            })

        # Get user's bookmarks for highlighting
        bookmarks = Bookmark.query.filter_by(user_id=current_user.id).all()
        bookmarked = {(b.session_id, b.question_index) for b in bookmarks}

        return render_template(
            "library.html",
            sessions=sessions,
            pagination=pagination,
            search=search,
            filter_type=filter_type,
            filter_diff=filter_diff,
            bookmarked=bookmarked,
        )

    # ── Session Detail ───────────────────────────────────────────────

    @app.route("/session/<session_id>")
    @login_required
    def session_detail(session_id):
        qs = QuestionSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
        try:
            questions_data = json.loads(qs.questions)
        except (json.JSONDecodeError, TypeError):
            questions_data = []

        bookmarks = Bookmark.query.filter_by(user_id=current_user.id, session_id=session_id).all()
        bookmarked_indices = {b.question_index for b in bookmarks}

        return render_template(
            "session_detail.html",
            session=qs,
            questions=questions_data,
            bookmarked_indices=bookmarked_indices,
        )

    # ── Practice Mode ────────────────────────────────────────────────

    @app.route("/practice/<session_id>")
    @login_required
    def practice(session_id):
        qs = QuestionSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
        try:
            questions_data = json.loads(qs.questions)
        except (json.JSONDecodeError, TypeError):
            questions_data = []
        return render_template(
            "practice.html",
            session=qs,
            questions=questions_data,
            questions_json=json.dumps(questions_data),
        )

    @app.post("/api/practice/submit")
    @login_required
    def api_practice_submit():
        data = request.get_json(force=True)
        session_id = str(data.get("sessionId", ""))
        question_index = clamp_int(data.get("questionIndex"), 0, 100, 0)
        user_answer = str(data.get("answer", ""))[:5000]
        time_taken = clamp_int(data.get("timeTaken"), 0, 3600, 0)

        qs = QuestionSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        if not qs:
            abort(404, "Session not found")

        try:
            questions_data = json.loads(qs.questions)
        except (json.JSONDecodeError, TypeError):
            abort(400, "Invalid session data")

        if question_index >= len(questions_data):
            abort(400, "Invalid question index")

        q = questions_data[question_index]
        question_text = q.get("question", "")
        correct_answer = q.get("answer", "")
        is_mcq = qs.question_type == "mcq"

        # For MCQs, check if answer matches
        is_correct = None
        score = None
        feedback = None

        if is_mcq:
            correct_key = q.get("correct_answer", "")
            is_correct = user_answer.strip().upper() == correct_key.strip().upper()
            score = 10.0 if is_correct else 0.0
            feedback = {
                "is_correct": is_correct,
                "correct_answer": correct_key,
                "explanation": q.get("explanation", ""),
            }
        else:
            # Store without grading for now (user can see model answer)
            feedback = {
                "model_answer": correct_answer,
                "explanation": q.get("explanation", ""),
            }

        # Save attempt
        attempt = PracticeAttempt(
            user_id=current_user.id,
            session_id=session_id,
            topic=qs.topic,
            question_type=qs.question_type,
            difficulty=qs.difficulty,
            question_text=question_text,
            user_answer=user_answer,
            correct_answer=correct_answer,
            is_correct=is_correct,
            score=score,
            time_taken_seconds=time_taken,
        )
        db.session.add(attempt)
        db.session.commit()

        return jsonify({
            "success": True,
            "is_correct": is_correct,
            "score": score,
            "feedback": feedback,
        })

    # ── Bookmarks ────────────────────────────────────────────────────

    @app.post("/api/bookmark/toggle")
    @login_required
    def api_toggle_bookmark():
        data = request.get_json(force=True)
        session_id = str(data.get("sessionId", ""))
        question_index = clamp_int(data.get("questionIndex"), 0, 100, 0)

        existing = Bookmark.query.filter_by(
            user_id=current_user.id,
            session_id=session_id,
            question_index=question_index,
        ).first()

        if existing:
            db.session.delete(existing)
            db.session.commit()
            return jsonify({"bookmarked": False})
        else:
            bm = Bookmark(
                user_id=current_user.id,
                session_id=session_id,
                question_index=question_index,
            )
            db.session.add(bm)
            db.session.commit()
            return jsonify({"bookmarked": True})

    @app.route("/bookmarks")
    @login_required
    def bookmarks():
        bms = (
            Bookmark.query
            .filter_by(user_id=current_user.id)
            .order_by(Bookmark.created_at.desc())
            .all()
        )
        items = []
        for bm in bms:
            qs = db.session.get(QuestionSession, bm.session_id)
            if not qs:
                continue
            try:
                questions_data = json.loads(qs.questions)
            except (json.JSONDecodeError, TypeError):
                continue
            if bm.question_index < len(questions_data):
                items.append({
                    "bookmark_id": bm.id,
                    "session_id": bm.session_id,
                    "question_index": bm.question_index,
                    "topic": qs.topic,
                    "question_type": qs.question_type,
                    "difficulty": qs.difficulty,
                    "question": questions_data[bm.question_index],
                    "created_at": bm.created_at.isoformat() if bm.created_at else "",
                })
        return render_template("bookmarks.html", items=items)

    # ── Mock Interview ───────────────────────────────────────────────

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
            ai = get_ai_service()
            generated = ai.generate_interview_questions(topic, role, question_type, difficulty, count)
        except AIServiceError as exc:
            return jsonify({"error": str(exc)}), exc.status_code
        except Exception as exc:
            logger.exception("Unexpected error generating interview questions: %s", exc)
            return jsonify({"error": f"Failed to generate questions: {exc}"}), 500

        items = [{"question": q, "answer": "", "feedback": None, "score": None} for q in generated]
        try:
            interview = MockInterview(
                user_id=current_user.id,
                topic=topic,
                role=role,
                difficulty=difficulty,
                question_type=question_type,
                seconds_per_question=seconds,
                items=json.dumps(items),
                status="in_progress",
            )
            db.session.add(interview)
            db.session.commit()
        except Exception as db_exc:
            db.session.rollback()
            logger.error("Failed to save mock interview to MySQL: %s", db_exc)
            return jsonify({"error": "Failed to save mock interview session to database."}), 500

        return jsonify({"id": interview.id, "questions": generated, "mode": "ai"})

    @app.post("/api/mock-interview/submit")
    @login_required
    def api_submit_answer():
        data = request.get_json(force=True)
        interview_id = str(data.get("interviewId", ""))
        index = clamp_int(data.get("index"), 0, 20, 0)
        answer = str(data.get("answer", ""))[:5000]
        time_taken = clamp_int(data.get("timeTakenSeconds"), 0, 3600, 0)

        interview = MockInterview.query.filter_by(
            id=interview_id, user_id=current_user.id
        ).first()
        if not interview:
            abort(404, "Interview not found")

        items = json.loads(interview.items)
        if index >= len(items):
            abort(400, "Invalid question index")
        item = items[index]

        try:
            ai = get_ai_service()
            fb = ai.evaluate_answer(
                topic=interview.topic,
                difficulty=interview.difficulty,
                question_type=interview.question_type,
                seconds_per_question=interview.seconds_per_question,
                question=item["question"],
                answer=answer,
                time_taken=time_taken,
            )
        except AIServiceError as exc:
            return jsonify({"error": str(exc)}), exc.status_code
        except Exception as exc:
            logger.exception("Unexpected error evaluating answer: %s", exc)
            return jsonify({"error": f"Failed to evaluate answer: {exc}"}), 500

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
        scored = [i for i in items if isinstance(i.get("score"), (int, float))]
        overall = round(sum(i["score"] for i in scored) / len(scored), 1) if scored else None
        completed = len(scored) == len(items)

        interview.items = json.dumps(items)
        interview.overall_score = overall
        interview.status = "completed" if completed else "in_progress"
        interview.completed_at = now_utc() if completed else None
        interview.updated_at = now_utc()

        try:
            db.session.commit()
        except Exception as db_exc:
            db.session.rollback()
            logger.error("Failed to update mock interview in MySQL: %s", db_exc)
            return jsonify({"error": "Answer evaluated, but failed to save result to database."}), 500

        return jsonify({
            "score": score,
            "rubric": rubric,
            "strengths": fb.get("strengths", ""),
            "improvements": fb.get("improvements", ""),
            "idealAnswer": fb.get("ideal_answer", ""),
            "overall": overall,
            "completed": completed,
            "mode": "ai",
        })

    # ── Profile ──────────────────────────────────────────────────────

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            target_role = request.form.get("target_role", "").strip()
            current_user.full_name = full_name
            current_user.target_role = target_role
            current_user.updated_at = now_utc()
            db.session.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("profile"))
        return render_template("profile.html")

    # ── API: Dashboard stats (for charts) ────────────────────────────

    @app.route("/api/dashboard/stats")
    @login_required
    def api_dashboard_stats():
        """Return JSON stats for dashboard charts."""
        attempts = PracticeAttempt.query.filter_by(user_id=current_user.id).all()

        # By topic
        by_topic = {}
        for a in attempts:
            t = a.topic.lower()
            if t not in by_topic:
                by_topic[t] = {"total": 0, "correct": 0}
            by_topic[t]["total"] += 1
            if a.is_correct:
                by_topic[t]["correct"] += 1

        # By difficulty
        by_diff = {}
        for a in attempts:
            d = a.difficulty
            if d not in by_diff:
                by_diff[d] = {"total": 0, "correct": 0}
            by_diff[d]["total"] += 1
            if a.is_correct:
                by_diff[d]["correct"] += 1

        # Interview scores over time
        interviews = (
            MockInterview.query
            .filter_by(user_id=current_user.id, status="completed")
            .order_by(MockInterview.completed_at.asc())
            .all()
        )
        score_trend = [
            {
                "date": iv.completed_at.isoformat() if iv.completed_at else "",
                "score": iv.overall_score,
                "topic": iv.topic,
            }
            for iv in interviews if iv.overall_score is not None
        ]

        return jsonify({
            "by_topic": by_topic,
            "by_difficulty": by_diff,
            "score_trend": score_trend,
        })


# ── App Entrypoint ───────────────────────────────────────────────────────

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
