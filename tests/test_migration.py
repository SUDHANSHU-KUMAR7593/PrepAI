"""Tests for SQLite-to-MySQL data migration script."""

import json
import os
import sqlite3
import tempfile
from unittest.mock import patch

from migrate_sqlite_to_mysql import migrate, parse_sqlite_timestamp
from models import MockInterview, QuestionSession, User


def test_parse_sqlite_timestamp():
    ts_iso = "2026-05-15T10:30:00+00:00"
    parsed = parse_sqlite_timestamp(ts_iso)
    assert parsed.year == 2026
    assert parsed.month == 5

    ts_space = "2026-05-15 10:30:00"
    parsed_space = parse_sqlite_timestamp(ts_space)
    assert parsed_space.year == 2026

    assert parse_sqlite_timestamp(None) is None


def test_migration_with_synthetic_sqlite_data(app, db):
    # Create a temporary SQLite database with schema and test rows
    with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as tmp:
        temp_sqlite_path = tmp.name

    try:
        conn = sqlite3.connect(temp_sqlite_path)
        cur = conn.cursor()

        # DDL matching original SQLite schema
        cur.executescript("""
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL DEFAULT '',
                target_role TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE question_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                question_type TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                questions TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );

            CREATE TABLE mock_interviews (
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
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)

        # Insert synthetic data
        user_id = "test-mig-user-001"
        cur.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, "migrated@example.com", "hash_xyz", "Migrated Candidate", "SRE", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
        )
        session_id = "test-mig-sess-001"
        cur.execute(
            "INSERT INTO question_sessions VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, user_id, "Kubernetes", "technical", "hard", json.dumps([{"q": "Pods vs Deployments"}]), "2026-01-01T00:00:00Z"),
        )
        interview_id = "test-mig-iv-001"
        cur.execute(
            "INSERT INTO mock_interviews VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (interview_id, user_id, "Distributed Systems", "Principal SRE", "hard", "technical", 120, json.dumps([{"q": "Raft vs Paxos"}]), 9.2, "completed", "2026-01-02T00:00:00Z", "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"),
        )
        conn.commit()
        conn.close()

        # Patch sqlite_path in migrate()
        with patch("migrate_sqlite_to_mysql.os.path.join", return_value=temp_sqlite_path):
            with patch("migrate_sqlite_to_mysql.create_app", return_value=app):
                # First run - should migrate all records
                migrate()

                with app.app_context():
                    migrated_user = db.session.get(User, user_id)
                    assert migrated_user is not None
                    assert migrated_user.email == "migrated@example.com"
                    assert migrated_user.full_name == "Migrated Candidate"

                    migrated_session = db.session.get(QuestionSession, session_id)
                    assert migrated_session is not None
                    assert migrated_session.topic == "Kubernetes"

                    migrated_iv = db.session.get(MockInterview, interview_id)
                    assert migrated_iv is not None
                    assert migrated_iv.overall_score == 9.2
                    assert migrated_iv.status == "completed"

                # Second run - should be idempotent (skip existing without errors)
                migrate()

                with app.app_context():
                    assert User.query.filter_by(id=user_id).count() == 1
                    assert QuestionSession.query.filter_by(id=session_id).count() == 1
                    assert MockInterview.query.filter_by(id=interview_id).count() == 1

        # Check that original SQLite file is still present and intact
        assert os.path.exists(temp_sqlite_path)
        check_conn = sqlite3.connect(temp_sqlite_path)
        count = check_conn.cursor().execute("SELECT count(*) FROM users").fetchone()[0]
        check_conn.close()
        assert count == 1

    finally:
        if os.path.exists(temp_sqlite_path):
            try:
                os.remove(temp_sqlite_path)
            except OSError:
                pass
