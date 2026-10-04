"""migrate_sqlite_to_mysql.py — Transfer data from SQLite to MySQL.

Usage:
    python migrate_sqlite_to_mysql.py

Reads the SQLite database at ./prepai.sqlite3 and copies all records into
the MySQL database specified by DATABASE_URL in .env.

Safety:
  • The SQLite file is never modified or deleted.
  • Uses INSERT IGNORE to allow safe retries without duplicating records.
  • Validates row counts after transfer.
  • Reports a summary of migrated vs skipped records.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

# ── Import app context for SQLAlchemy ────────────────────────────────────

# Ensure the project root is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure console encoding for Windows compatibility
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app import create_app
from extensions import db
from models import MockInterview, QuestionSession, User


def parse_sqlite_timestamp(ts):
    """Parse an ISO timestamp string from SQLite into a datetime object."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        try:
            return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            return datetime.now(timezone.utc)


def migrate():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    sqlite_path = os.path.join(BASE_DIR, "prepai.sqlite3")

    if not os.path.exists(sqlite_path):
        print(f"⚠  SQLite database not found at {sqlite_path}")
        print("   Nothing to migrate.")
        return

    print(f"📁 SQLite source: {sqlite_path}")

    # Connect to SQLite
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Count source records
    source_counts = {}
    for table in ["users", "question_sessions", "mock_interviews"]:
        cursor.execute(f"SELECT count(*) FROM {table}")
        source_counts[table] = cursor.fetchone()[0]
        print(f"   Source {table}: {source_counts[table]} rows")

    if all(v == 0 for v in source_counts.values()):
        print("\n✅ SQLite database is empty. Nothing to migrate.")
        conn.close()
        return

    # Create Flask app context for SQLAlchemy
    app = create_app()
    with app.app_context():
        results = {"migrated": {}, "skipped": {}, "errors": {}}

        # ── Migrate users ────────────────────────────────────────────
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        migrated = 0
        skipped = 0
        errors = 0
        for row in users:
            existing = db.session.get(User, row["id"])
            if existing:
                skipped += 1
                continue
            try:
                user = User(
                    id=row["id"],
                    email=row["email"],
                    password_hash=row["password_hash"],
                    full_name=row["full_name"] or "",
                    target_role=row["target_role"] or "",
                    created_at=parse_sqlite_timestamp(row["created_at"]),
                    updated_at=parse_sqlite_timestamp(row["updated_at"]),
                )
                db.session.add(user)
                db.session.flush()
                migrated += 1
            except Exception as exc:
                db.session.rollback()
                errors += 1
                print(f"   ❌ User {row['id']}: {exc}")

        results["migrated"]["users"] = migrated
        results["skipped"]["users"] = skipped
        results["errors"]["users"] = errors

        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            print(f"   ❌ Failed to commit users: {exc}")

        # ── Migrate question_sessions ────────────────────────────────
        cursor.execute("SELECT * FROM question_sessions")
        sessions = cursor.fetchall()
        migrated = 0
        skipped = 0
        errors = 0
        for row in sessions:
            existing = db.session.get(QuestionSession, row["id"])
            if existing:
                skipped += 1
                continue
            try:
                # Validate JSON
                questions_data = row["questions"]
                json.loads(questions_data)  # Ensure valid JSON

                qs = QuestionSession(
                    id=row["id"],
                    user_id=row["user_id"],
                    topic=row["topic"],
                    question_type=row["question_type"],
                    difficulty=row["difficulty"],
                    questions=questions_data,
                    created_at=parse_sqlite_timestamp(row["created_at"]),
                )
                db.session.add(qs)
                db.session.flush()
                migrated += 1
            except Exception as exc:
                db.session.rollback()
                errors += 1
                print(f"   ❌ Session {row['id']}: {exc}")

        results["migrated"]["question_sessions"] = migrated
        results["skipped"]["question_sessions"] = skipped
        results["errors"]["question_sessions"] = errors

        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            print(f"   ❌ Failed to commit sessions: {exc}")

        # ── Migrate mock_interviews ──────────────────────────────────
        cursor.execute("SELECT * FROM mock_interviews")
        interviews = cursor.fetchall()
        migrated = 0
        skipped = 0
        errors = 0
        for row in interviews:
            existing = db.session.get(MockInterview, row["id"])
            if existing:
                skipped += 1
                continue
            try:
                items_data = row["items"]
                json.loads(items_data)  # Ensure valid JSON

                mi = MockInterview(
                    id=row["id"],
                    user_id=row["user_id"],
                    topic=row["topic"],
                    role=row["role"],
                    difficulty=row["difficulty"],
                    question_type=row["question_type"],
                    seconds_per_question=row["seconds_per_question"] or 120,
                    items=items_data,
                    overall_score=row["overall_score"],
                    status=row["status"] or "in_progress",
                    completed_at=parse_sqlite_timestamp(row["completed_at"]),
                    created_at=parse_sqlite_timestamp(row["created_at"]),
                    updated_at=parse_sqlite_timestamp(row["updated_at"]),
                )
                db.session.add(mi)
                db.session.flush()
                migrated += 1
            except Exception as exc:
                db.session.rollback()
                errors += 1
                print(f"   ❌ Interview {row['id']}: {exc}")

        results["migrated"]["mock_interviews"] = migrated
        results["skipped"]["mock_interviews"] = skipped
        results["errors"]["mock_interviews"] = errors

        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            print(f"   ❌ Failed to commit interviews: {exc}")

        # ── Verify destination counts ────────────────────────────────
        dest_counts = {
            "users": User.query.count(),
            "question_sessions": QuestionSession.query.count(),
            "mock_interviews": MockInterview.query.count(),
        }

        # ── Print summary ────────────────────────────────────────────
        print("\n" + "═" * 60)
        print("  MIGRATION SUMMARY")
        print("═" * 60)
        for table in ["users", "question_sessions", "mock_interviews"]:
            print(f"\n  {table}:")
            print(f"    Source rows:   {source_counts[table]}")
            print(f"    Migrated:     {results['migrated'][table]}")
            print(f"    Skipped:      {results['skipped'][table]}")
            print(f"    Errors:       {results['errors'][table]}")
            print(f"    Dest rows:    {dest_counts[table]}")
            if source_counts[table] == dest_counts[table]:
                print(f"    ✅ Row count matches")
            elif source_counts[table] == results["migrated"][table] + results["skipped"][table]:
                print(f"    ✅ All source rows accounted for")
            else:
                print(f"    ⚠  Row count mismatch — review errors above")

        total_errors = sum(results["errors"].values())
        if total_errors == 0:
            print(f"\n✅ Migration completed successfully!")
        else:
            print(f"\n⚠  Migration completed with {total_errors} error(s).")

    conn.close()
    print(f"\n📁 Original SQLite database preserved at: {sqlite_path}")


if __name__ == "__main__":
    migrate()
