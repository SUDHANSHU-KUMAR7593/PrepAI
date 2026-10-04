"""Tests for authentication routes."""

from flask_login import current_user
from models import User


def test_auth_page_renders(client):
    res = client.get("/auth")
    assert res.status_code == 200
    assert b"Sign In" in res.data or b"sign in" in res.data.lower()


def test_signup_successful(client, db):
    res = client.post(
        "/auth",
        data={
            "mode": "signup",
            "email": "newuser@example.com",
            "password": "mypassword123",
            "full_name": "New Candidate",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    user = User.query.filter_by(email="newuser@example.com").first()
    assert user is not None
    assert user.full_name == "New Candidate"


def test_signup_duplicate_email(client, test_user):
    res = client.post(
        "/auth",
        data={
            "mode": "signup",
            "email": test_user.email,
            "password": "differentpass",
            "full_name": "Impostor",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"already exists" in res.data.lower()


def test_signup_short_password(client):
    res = client.post(
        "/auth",
        data={
            "mode": "signup",
            "email": "short@example.com",
            "password": "123",
            "full_name": "Short Pass",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"at least 6 characters" in res.data.lower()


def test_signin_success(client, test_user):
    res = client.post(
        "/auth",
        data={
            "mode": "signin",
            "email": test_user.email,
            "password": "password123",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"Signed in" in res.data or b"Dashboard" in res.data


def test_signin_invalid_credentials(client, test_user):
    res = client.post(
        "/auth",
        data={
            "mode": "signin",
            "email": test_user.email,
            "password": "wrongpassword",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"Invalid email or password" in res.data


def test_logout(auth_client):
    res = auth_client.post("/logout", follow_redirects=True)
    assert res.status_code == 200
    assert b"Signed out" in res.data or b"Sign In" in res.data


def test_protected_routes_require_login(client):
    protected_urls = [
        "/dashboard",
        "/questions",
        "/library",
        "/mock-interview",
        "/bookmarks",
        "/profile",
    ]
    for url in protected_urls:
        res = client.get(url)
        # Should redirect to login
        assert res.status_code == 302
        assert "/auth" in res.headers.get("Location", "")
