"""Tests for mock interview and voice interview flows."""

import json
from unittest.mock import patch

from models import MockInterview


def test_mock_interview_page_renders(auth_client):
    res = auth_client.get("/mock-interview")
    assert res.status_code == 200
    assert b"Mock Interview" in res.data


def test_voice_interview_page_renders(auth_client):
    res = auth_client.get("/voice-interview")
    assert res.status_code == 200
    assert b"Voice Interview" in res.data or b"Microphone" in res.data or b"voice" in res.data.lower()


@patch("app.get_ai_service")
def test_interview_lifecycle(mock_get_ai, auth_client, test_user, db):
    mock_ai = mock_get_ai.return_value
    mock_ai.generate_interview_questions.return_value = [
        "Explain the difference between synchronous and asynchronous programming.",
        "How do you handle race conditions in multi-threaded applications?",
    ]

    # 1. Start interview
    res = auth_client.post(
        "/api/mock-interview/start",
        json={
            "topic": "Concurrency",
            "role": "Backend Engineer",
            "questionType": "technical",
            "difficulty": "medium",
            "count": 2,
            "secondsPerQuestion": 90,
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert "id" in data
    assert len(data["questions"]) == 2
    interview_id = data["id"]

    # Verify interview in DB
    interview = db.session.get(MockInterview, interview_id)
    assert interview is not None
    assert interview.status == "in_progress"

    # 2. Submit answer to question 0
    mock_ai.evaluate_answer.return_value = {
        "score": 8.5,
        "clarity": 9.0,
        "relevance": 8.0,
        "conciseness": 8.5,
        "clarity_note": "Clear explanation with examples.",
        "relevance_note": "Directly addresses async vs sync.",
        "conciseness_note": "Good length without fluff.",
        "strengths": "Great contrast between blocking vs non-blocking I/O.",
        "improvements": "Mention event loops specifically.",
        "ideal_answer": "Synchronous programming executes tasks sequentially...",
    }

    res_q0 = auth_client.post(
        "/api/mock-interview/submit",
        json={
            "interviewId": interview_id,
            "index": 0,
            "answer": "Synchronous waits for task to finish while asynchronous continues...",
            "timeTakenSeconds": 45,
        },
    )
    assert res_q0.status_code == 200
    data_q0 = res_q0.get_json()
    assert data_q0["score"] == 8.5
    assert data_q0["completed"] is False
    assert data_q0["rubric"]["clarity"] == 9.0

    # 3. Submit answer to question 1 (completes interview)
    mock_ai.evaluate_answer.return_value = {
        "score": 9.5,
        "clarity": 9.5,
        "relevance": 9.5,
        "conciseness": 9.5,
        "clarity_note": "Spot on explanation.",
        "relevance_note": "Direct and thorough.",
        "conciseness_note": "Efficient delivery.",
        "strengths": "Excellent mention of mutexes and semaphores.",
        "improvements": "None noted.",
        "ideal_answer": "Use synchronization primitives like locks, semaphores...",
    }

    res_q1 = auth_client.post(
        "/api/mock-interview/submit",
        json={
            "interviewId": interview_id,
            "index": 1,
            "answer": "Use mutex locks, atomic operations, or message queues.",
            "timeTakenSeconds": 60,
        },
    )
    assert res_q1.status_code == 200
    data_q1 = res_q1.get_json()
    assert data_q1["score"] == 9.5
    assert data_q1["completed"] is True
    assert data_q1["overall"] == 9.0

    # Verify interview DB state updated
    interview = db.session.get(MockInterview, interview_id)
    assert interview.status == "completed"
    assert interview.overall_score == 9.0
    assert interview.completed_at is not None


def test_dashboard_stats_api(auth_client, test_user, db):
    # Add a completed interview
    iv = MockInterview(
        user_id=test_user.id,
        topic="Databases",
        difficulty="medium",
        question_type="technical",
        seconds_per_question=120,
        items=json.dumps([{"question": "Q1", "score": 8.0}]),
        overall_score=8.0,
        status="completed",
    )
    db.session.add(iv)
    db.session.commit()

    res = auth_client.get("/api/dashboard/stats")
    assert res.status_code == 200
    data = res.get_json()
    assert "by_topic" in data
    assert "by_difficulty" in data
    assert "score_trend" in data
    assert len(data["score_trend"]) == 1
    assert data["score_trend"][0]["score"] == 8.0
