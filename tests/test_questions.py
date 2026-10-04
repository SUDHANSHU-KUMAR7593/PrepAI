"""Tests for question generation, library, practice mode, and bookmarks."""

import json
from unittest.mock import patch

from models import Bookmark, PracticeAttempt, QuestionSession


def test_question_generator_empty_topic(auth_client):
    res = auth_client.post(
        "/questions",
        data={"topic": "", "question_type": "technical", "difficulty": "medium", "count": "5"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"Topic is required" in res.data


@patch("app.get_ai_service")
def test_generate_technical_questions(mock_get_ai, auth_client, test_user):
    mock_ai = mock_get_ai.return_value
    mock_ai.generate_questions_with_answers.return_value = [
        {
            "question": "What is dependency injection?",
            "answer": "A design pattern where dependencies are provided to an object.",
            "rubric": ["Separation of concerns", "Inversion of control"],
            "difficulty": "medium",
            "explanation": "Decouples component creation from usage.",
        }
    ]

    res = auth_client.post(
        "/questions",
        data={
            "topic": "Software Architecture",
            "question_type": "technical",
            "difficulty": "medium",
            "count": "1",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"Generated 1 questions with AI" in res.data
    assert b"What is dependency injection?" in res.data

    # Verify saved in DB
    session = QuestionSession.query.filter_by(user_id=test_user.id).first()
    assert session is not None
    assert session.topic == "Software Architecture"
    assert session.question_type == "technical"


@patch("app.get_ai_service")
def test_generate_mcq_questions(mock_get_ai, auth_client, test_user):
    mock_ai = mock_get_ai.return_value
    mock_ai.generate_mcq_questions.return_value = [
        {
            "question": "Which HTTP method is idempotent?",
            "options": {"A": "POST", "B": "GET", "C": "PATCH", "D": "CONNECT"},
            "correct_answer": "B",
            "explanation": "GET requests are safe and idempotent by HTTP specification.",
            "difficulty": "easy",
        }
    ]

    res = auth_client.post(
        "/questions",
        data={
            "topic": "HTTP Protocols",
            "question_type": "mcq",
            "difficulty": "easy",
            "count": "1",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"Which HTTP method is idempotent?" in res.data

    session = QuestionSession.query.filter_by(user_id=test_user.id, question_type="mcq").first()
    assert session is not None
    assert "POST" in session.questions


def test_session_detail_and_library(auth_client, test_user, db):
    qs = QuestionSession(
        user_id=test_user.id,
        topic="Database Indexing",
        question_type="technical",
        difficulty="hard",
        questions=json.dumps([
            {
                "question": "How does B+ Tree indexing work?",
                "answer": "B+ Trees maintain balanced keys...",
            }
        ]),
    )
    db.session.add(qs)
    db.session.commit()

    # Session detail
    res = auth_client.get(f"/session/{qs.id}")
    assert res.status_code == 200
    assert b"Database Indexing" in res.data
    assert b"B+ Tree" in res.data

    # Library search
    res = auth_client.get("/library?search=Database")
    assert res.status_code == 200
    assert b"Database Indexing" in res.data


def test_bookmark_toggle_api(auth_client, test_user, db):
    qs = QuestionSession(
        user_id=test_user.id,
        topic="Cloud Computing",
        question_type="technical",
        difficulty="medium",
        questions=json.dumps([{"question": "What is serverless?"}]),
    )
    db.session.add(qs)
    db.session.commit()

    # Toggle bookmark ON
    res = auth_client.post(
        "/api/bookmark/toggle",
        json={"sessionId": qs.id, "questionIndex": 0},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["bookmarked"] is True
    assert Bookmark.query.filter_by(session_id=qs.id, question_index=0).count() == 1

    # Toggle bookmark OFF
    res = auth_client.post(
        "/api/bookmark/toggle",
        json={"sessionId": qs.id, "questionIndex": 0},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["bookmarked"] is False
    assert Bookmark.query.filter_by(session_id=qs.id, question_index=0).count() == 0


def test_practice_submit_mcq_and_subjective(auth_client, test_user, db):
    # MCQ session
    qs_mcq = QuestionSession(
        user_id=test_user.id,
        topic="Python",
        question_type="mcq",
        difficulty="easy",
        questions=json.dumps([
            {
                "question": "What is type(42)?",
                "options": {"A": "int", "B": "str", "C": "float", "D": "bool"},
                "correct_answer": "A",
                "explanation": "42 is an integer.",
            }
        ]),
    )
    db.session.add(qs_mcq)
    db.session.commit()

    # Correct submission
    res = auth_client.post(
        "/api/practice/submit",
        json={
            "sessionId": qs_mcq.id,
            "questionIndex": 0,
            "answer": "A",
            "timeTaken": 15,
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["is_correct"] is True
    assert data["score"] == 10.0

    # Incorrect submission
    res = auth_client.post(
        "/api/practice/submit",
        json={
            "sessionId": qs_mcq.id,
            "questionIndex": 0,
            "answer": "B",
            "timeTaken": 10,
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["is_correct"] is False
    assert data["score"] == 0.0

    # Verify attempts in DB
    attempts = PracticeAttempt.query.filter_by(user_id=test_user.id).all()
    assert len(attempts) == 2


# ── Regression tests for HTTP 400 root cause & Gemini error handling ──────

from unittest.mock import MagicMock
from ai_service import AIService, AIServiceError, _normalize_schema


def test_schema_normalization_converts_lowercase_types_to_uppercase():
    raw_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "count": {"type": "integer"},
            "score": {"type": "number"},
            "active": {"type": "boolean"},
            "items": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["title"],
    }
    normalized = _normalize_schema(raw_schema)
    assert normalized["type"] == "OBJECT"
    assert normalized["properties"]["title"]["type"] == "STRING"
    assert normalized["properties"]["count"]["type"] == "INTEGER"
    assert normalized["properties"]["score"]["type"] == "NUMBER"
    assert normalized["properties"]["active"]["type"] == "BOOLEAN"
    assert normalized["properties"]["items"]["type"] == "ARRAY"
    assert normalized["properties"]["items"]["items"]["type"] == "STRING"


@patch("requests.post")
def test_ai_service_diagnoses_groq_key_on_http_400(mock_post):
    """Verify HTTP 400 with API_KEY_INVALID and gsk_ key gives actionable instructions."""
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 400
    mock_resp.json.return_value = {
        "error": {
            "code": 400,
            "message": "API key not valid. Please pass a valid API key.",
            "status": "INVALID_ARGUMENT",
            "details": [{"reason": "API_KEY_INVALID"}],
        }
    }
    mock_resp.text = json.dumps(mock_resp.json.return_value)
    mock_post.return_value = mock_resp

    service = AIService(api_key="gsk_12345testkey", model="gemini-1.5-flash")
    import pytest
    with pytest.raises(AIServiceError) as exc_info:
        service.generate_questions_with_answers("Algorithms", "technical", "medium", 2)
    
    assert "Groq key format" in str(exc_info.value)
    assert "AIzaSy" in str(exc_info.value)
    assert exc_info.value.status_code == 400


@patch("requests.post")
def test_ai_service_handles_model_not_found_404(mock_post):
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 404
    mock_resp.json.return_value = {"error": {"message": "models/gemini-invalid is not found for API version v1beta"}}
    mock_resp.text = json.dumps(mock_resp.json.return_value)
    mock_post.return_value = mock_resp

    service = AIService(api_key="AIzaSyValidFormatKey", model="gemini-invalid")
    import pytest
    with pytest.raises(AIServiceError) as exc_info:
        service.generate_questions_with_answers("OOP", "technical", "easy", 2)
    assert "was not found" in str(exc_info.value)
    assert exc_info.value.status_code == 404


@patch("requests.post")
def test_ai_service_handles_rate_limit_429(mock_post):
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 429
    mock_resp.json.return_value = {"error": {"message": "Resource has been exhausted"}}
    mock_resp.text = json.dumps(mock_resp.json.return_value)
    mock_post.return_value = mock_resp

    service = AIService(api_key="AIzaSyValidFormatKey", model="gemini-1.5-flash")
    import pytest
    with pytest.raises(AIServiceError) as exc_info:
        service.generate_questions_with_answers("OOP", "technical", "easy", 2)
    assert "rate limit" in str(exc_info.value).lower()
    assert exc_info.value.status_code == 429


@patch("requests.post")
def test_ai_service_handles_malformed_response(mock_post):
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": '{"broken_json": '}]}}]
    }
    mock_post.return_value = mock_resp

    service = AIService(api_key="AIzaSyValidFormatKey", model="gemini-1.5-flash")
    import pytest
    with pytest.raises(AIServiceError) as exc_info:
        service.generate_questions_with_answers("OOP", "technical", "easy", 2)
    assert "did not return valid questions" in str(exc_info.value)


@patch("app.get_ai_service")
def test_generate_coding_and_behavioral_types(mock_get_ai, auth_client, test_user):
    mock_ai = mock_get_ai.return_value
    mock_ai.generate_coding_questions.return_value = [
        {
            "question": "Implement LRU Cache",
            "constraints": "O(1) get and put",
            "example": "cache.put(1, 1)",
            "solution": "Use doubly linked list and hash map",
        }
    ]
    res = auth_client.post(
        "/questions",
        data={"topic": "Data Structures", "question_type": "coding", "difficulty": "hard", "count": "1"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"LRU Cache" in res.data


@patch("app.get_ai_service")
@patch("extensions.db.session.commit")
def test_db_persistence_failure_handled_gracefully(mock_commit, mock_get_ai, auth_client):
    mock_ai = mock_get_ai.return_value
    mock_ai.generate_questions_with_answers.return_value = [{"question": "Q1", "answer": "A1"}]
    mock_commit.side_effect = Exception("MySQL connection dropped")

    res = auth_client.post(
        "/questions",
        data={"topic": "Testing", "question_type": "technical", "difficulty": "easy", "count": "1"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    # Should render results with a warning rather than crashing 500
    assert b"could not be saved" in res.data.lower() or b"database issue" in res.data.lower()

