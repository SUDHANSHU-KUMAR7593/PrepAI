"""Tests for SQLAlchemy database models."""

import json
from datetime import datetime, timezone
import pytest
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from models import Bookmark, MockInterview, PracticeAttempt, QuestionSession, User


def test_user_creation(db):
    user = User(
        email="developer@example.com",
        password_hash=generate_password_hash("securepass"),
        full_name="Jane Doe",
        target_role="Full Stack Engineer",
    )
    db.session.add(user)
    db.session.commit()

    assert user.id is not None
    assert len(user.id) == 36  # UUID format
    assert user.email == "developer@example.com"
    assert check_password_hash(user.password_hash, "securepass")
    assert repr(user) == "<User developer@example.com>"


def test_user_unique_email(db):
    u1 = User(email="unique@example.com", password_hash="hash1")
    db.session.add(u1)
    db.session.commit()

    u2 = User(email="unique@example.com", password_hash="hash2")
    db.session.add(u2)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_question_session_and_relationship(db, test_user):
    qs = QuestionSession(
        user_id=test_user.id,
        topic="Python Concurrency",
        question_type="technical",
        difficulty="hard",
        questions=json.dumps([{"question": "Explain GIL", "answer": "Global Interpreter Lock..."}]),
    )
    db.session.add(qs)
    db.session.commit()

    assert qs.id is not None
    assert qs.user.email == test_user.email
    assert test_user.question_sessions.count() == 1
    assert "GIL" in qs.questions


def test_mock_interview_and_scoring(db, test_user):
    interview = MockInterview(
        user_id=test_user.id,
        topic="System Design",
        role="Senior Backend Architect",
        difficulty="hard",
        question_type="technical",
        seconds_per_question=180,
        items=json.dumps([
            {"question": "Design URL shortener", "answer": "Use Base62...", "score": 9.0}
        ]),
        overall_score=9.0,
        status="completed",
    )
    db.session.add(interview)
    db.session.commit()

    assert interview.id is not None
    assert interview.overall_score == 9.0
    assert interview.status == "completed"
    assert test_user.mock_interviews.count() == 1


def test_bookmark_and_practice_attempt(db, test_user):
    qs = QuestionSession(
        user_id=test_user.id,
        topic="Algorithms",
        question_type="technical",
        difficulty="medium",
        questions=json.dumps([{"question": "Two Sum", "answer": "Hash map"}]),
    )
    db.session.add(qs)
    db.session.commit()

    # Bookmark
    bm = Bookmark(
        user_id=test_user.id,
        session_id=qs.id,
        question_index=0,
        note="Review before interview",
    )
    db.session.add(bm)

    # Practice Attempt
    attempt = PracticeAttempt(
        user_id=test_user.id,
        session_id=qs.id,
        topic="Algorithms",
        question_type="technical",
        difficulty="medium",
        question_text="Two Sum",
        user_answer="Use dictionary for O(n)",
        correct_answer="Hash map O(n)",
        is_correct=True,
        score=10.0,
        time_taken_seconds=45,
    )
    db.session.add(attempt)
    db.session.commit()

    assert test_user.bookmarks.count() == 1
    assert test_user.practice_attempts.count() == 1
    assert attempt.is_correct is True
    assert attempt.score == 10.0


def test_cascade_delete(db, test_user):
    qs = QuestionSession(
        user_id=test_user.id,
        topic="Databases",
        question_type="technical",
        difficulty="medium",
        questions=json.dumps([{"question": "What is ACID?"}]),
    )
    db.session.add(qs)
    db.session.commit()

    bm = Bookmark(user_id=test_user.id, session_id=qs.id, question_index=0)
    db.session.add(bm)
    db.session.commit()

    # Delete user
    db.session.delete(test_user)
    db.session.commit()

    # Verify cascaded deletion
    assert QuestionSession.query.filter_by(user_id=test_user.id).count() == 0
    assert Bookmark.query.filter_by(user_id=test_user.id).count() == 0
