"""inspect_db.py — Diagnostic utility to inspect the PrepAI MySQL database."""

import os
import sys

# Ensure UTF-8 console output on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app import create_app
from extensions import db
from models import Bookmark, MockInterview, PracticeAttempt, QuestionSession, User
from sqlalchemy import inspect, text

def inspect_mysql():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        print("=" * 60)
        print("  PrepAI MySQL Database Inspection")
        print("=" * 60)
        print(f"Database URL: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
        
        version = db.session.execute(text("SELECT VERSION()")).scalar()
        print(f"MySQL Version: {version}\n")
        
        print("Tables found:", tables)
        print("-" * 60)
        
        models_map = {
            "users": User,
            "question_sessions": QuestionSession,
            "mock_interviews": MockInterview,
            "bookmarks": Bookmark,
            "practice_attempts": PracticeAttempt,
        }
        
        for table_name in tables:
            columns = inspector.get_columns(table_name)
            col_summary = ", ".join(f"{col['name']} ({col['type']})" for col in columns[:4])
            if len(columns) > 4:
                col_summary += f", ... (+{len(columns) - 4} more)"
            
            model = models_map.get(table_name)
            count = model.query.count() if model else db.session.execute(text(f"SELECT count(*) FROM {table_name}")).scalar()
            
            print(f"Table: {table_name} [{count} rows]")
            print(f"  Columns: {col_summary}")
        
        print("=" * 60)
        print("Status: Database verified and healthy!")

if __name__ == "__main__":
    inspect_mysql()
