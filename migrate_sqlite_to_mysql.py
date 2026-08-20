import os
import sqlite3

from dotenv import load_dotenv

from app import get_db, init_db

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DATABASE = os.getenv("SQLITE_DATABASE", os.path.join(BASE_DIR, "prepai.sqlite3"))


TABLES = {
    "users": [
        "id",
        "email",
        "password_hash",
        "full_name",
        "target_role",
        "created_at",
        "updated_at",
    ],
    "question_sessions": [
        "id",
        "user_id",
        "topic",
        "question_type",
        "difficulty",
        "questions",
        "created_at",
    ],
    "mock_interviews": [
        "id",
        "user_id",
        "topic",
        "role",
        "difficulty",
        "question_type",
        "seconds_per_question",
        "items",
        "overall_score",
        "status",
        "completed_at",
        "created_at",
        "updated_at",
    ],
}


def sqlite_rows(table):
    with sqlite3.connect(SQLITE_DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(f"SELECT * FROM {table}").fetchall()]


def insert_rows(table, columns, rows):
    if not rows:
        return 0

    placeholders = ", ".join(["?"] * len(columns))
    column_sql = ", ".join(columns)
    updates = ", ".join([f"{column} = VALUES({column})" for column in columns if column != "id"])
    sql = f"""
        INSERT INTO {table} ({column_sql})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE {updates}
    """

    with get_db() as db:
        for row in rows:
            db.execute(sql, tuple(row[column] for column in columns))
    return len(rows)


def main():
    if not os.path.exists(SQLITE_DATABASE):
        raise SystemExit(f"SQLite database not found: {SQLITE_DATABASE}")

    init_db()
    for table, columns in TABLES.items():
        count = insert_rows(table, columns, sqlite_rows(table))
        print(f"Migrated {count} rows into {table}.")


if __name__ == "__main__":
    main()
