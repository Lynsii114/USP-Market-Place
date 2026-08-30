from fastapi.testclient import TestClient
from app.main import app


def test_signup_and_login_work():
    client = TestClient(app)

    signup = client.post(
        "/api/users/signup",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "secret123",
        },
    )

    assert signup.status_code == 200, signup.text
    assert signup.json()["user"]["username"] == "alice"

    login = client.post(
        "/api/users/login",
        json={
            "username": "alice",
            "password": "secret123",
        },
    )

    assert login.status_code == 200, login.text
    assert login.json()["user"]["email"] == "alice@example.com"
