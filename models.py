"""SQLAlchemy models for PrepAI — MySQL-compatible."""

import uuid
from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import Text, Float, Integer, String, DateTime, Index
from sqlalchemy.orm import relationship

from extensions import db


def _uuid():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# User
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(String(36), primary_key=True, default=_uuid)
    email = db.Column(String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(String(512), nullable=False)
    full_name = db.Column(String(255), nullable=False, default="")
    target_role = db.Column(String(255), nullable=False, default="")
    created_at = db.Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    question_sessions = relationship("QuestionSession", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    mock_interviews = relationship("MockInterview", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    practice_attempts = relationship("PracticeAttempt", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.email}>"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Question Session — stores generated question sets
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class QuestionSession(db.Model):
    __tablename__ = "question_sessions"
    __table_args__ = (
        Index("ix_qs_user_created", "user_id", "created_at"),
    )

    id = db.Column(String(36), primary_key=True, default=_uuid)
    user_id = db.Column(String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic = db.Column(String(255), nullable=False, index=True)
    question_type = db.Column(String(50), nullable=False, index=True)
    difficulty = db.Column(String(20), nullable=False, index=True)
    questions = db.Column(Text, nullable=False)  # JSON blob
    created_at = db.Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    user = relationship("User", back_populates="question_sessions")

    def __repr__(self):
        return f"<QuestionSession {self.topic}>"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Mock Interview
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class MockInterview(db.Model):
    __tablename__ = "mock_interviews"
    __table_args__ = (
        Index("ix_mi_user_created", "user_id", "created_at"),
    )

    id = db.Column(String(36), primary_key=True, default=_uuid)
    user_id = db.Column(String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic = db.Column(String(255), nullable=False, index=True)
    role = db.Column(String(255), nullable=True)
    difficulty = db.Column(String(20), nullable=False)
    question_type = db.Column(String(50), nullable=False)
    seconds_per_question = db.Column(Integer, nullable=False, default=120)
    items = db.Column(Text, nullable=False)  # JSON blob
    overall_score = db.Column(Float, nullable=True)
    status = db.Column(String(20), nullable=False, default="in_progress")
    completed_at = db.Column(DateTime(timezone=True), nullable=True)
    created_at = db.Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="mock_interviews")

    def __repr__(self):
        return f"<MockInterview {self.topic} [{self.status}]>"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bookmark — user bookmarks individual questions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class Bookmark(db.Model):
    __tablename__ = "bookmarks"
    __table_args__ = (
        Index("ix_bm_user_session", "user_id", "session_id"),
    )

    id = db.Column(String(36), primary_key=True, default=_uuid)
    user_id = db.Column(String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = db.Column(String(36), db.ForeignKey("question_sessions.id", ondelete="CASCADE"), nullable=False)
    question_index = db.Column(Integer, nullable=False)  # index within the session's questions JSON
    note = db.Column(Text, nullable=True)
    created_at = db.Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    user = relationship("User", back_populates="bookmarks")
    session = relationship("QuestionSession")

    def __repr__(self):
        return f"<Bookmark session={self.session_id} q={self.question_index}>"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Practice Attempt — tracks individual question attempts
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class PracticeAttempt(db.Model):
    __tablename__ = "practice_attempts"
    __table_args__ = (
        Index("ix_pa_user_topic", "user_id", "topic"),
        Index("ix_pa_user_created", "user_id", "created_at"),
    )

    id = db.Column(String(36), primary_key=True, default=_uuid)
    user_id = db.Column(String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = db.Column(String(36), db.ForeignKey("question_sessions.id", ondelete="SET NULL"), nullable=True)
    topic = db.Column(String(255), nullable=False)
    question_type = db.Column(String(50), nullable=False)
    difficulty = db.Column(String(20), nullable=False)
    question_text = db.Column(Text, nullable=False)
    user_answer = db.Column(Text, nullable=True)
    correct_answer = db.Column(Text, nullable=True)
    is_correct = db.Column(db.Boolean, nullable=True)  # NULL = not graded (subjective)
    score = db.Column(Float, nullable=True)  # 0-10 scale for AI-graded
    time_taken_seconds = db.Column(Integer, nullable=True)
    created_at = db.Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    user = relationship("User", back_populates="practice_attempts")
    session = relationship("QuestionSession")

    def __repr__(self):
        return f"<PracticeAttempt {self.topic}>"
