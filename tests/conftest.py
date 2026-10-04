"""Pytest test fixtures for PrepAI."""

import json
import os
import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from config import TestingConfig
from extensions import db as _db
from models import User, QuestionSession, MockInterview, Bookmark, PracticeAttempt


@pytest.fixture(scope="session")
def app():
    """Create application configured for testing."""
    os.environ["FLASK_ENV"] = "testing"
    test_config = TestingConfig()
    app = create_app(config_override=test_config)
    
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture(scope="function")
def db(app):
    """Provide a clean database session for each test function."""
    with app.app_context():
        # Clear tables between tests
        PracticeAttempt.query.delete()
        Bookmark.query.delete()
        MockInterview.query.delete()
        QuestionSession.query.delete()
        User.query.delete()
        _db.session.commit()
        yield _db
        _db.session.rollback()


@pytest.fixture
def client(app, db):
    """Test client."""
    return app.test_client()


@pytest.fixture
def test_user(db):
    """Create a sample user."""
    user = User(
        email="testuser@example.com",
        password_hash=generate_password_hash("password123"),
        full_name="Test Candidate",
        target_role="Software Engineer",
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def auth_client(client, test_user):
    """Authenticated test client."""
    with client.session_transaction() as sess:
        sess["_user_id"] = test_user.id
        sess["_fresh"] = True
    return client
