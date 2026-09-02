from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app


client = TestClient(app)


def unique_student_id() -> str:
    return str(uuid4().int % 100000000).zfill(8)


def create_test_user():
    student_id = unique_student_id()
    response = client.post(
        "/api/users/signup",
        json={
            "username": f"seller_{student_id}",
            "email": f"S{student_id}@student.usp.ac.fj",
            "password": "secret123",
        },
    )

    assert response.status_code == 200
    return response.json()["user"]


def test_health_check():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_signup_rejects_non_usp_email():
    response = client.post(
        "/api/users/signup",
        json={
            "username": "invaliduser",
            "email": "invalid@example.com",
            "password": "secret123",
        },
    )

    assert response.status_code == 422
    assert "student.usp.ac.fj" in response.json()["detail"]


def test_signup_rejects_non_numeric_student_id():
    response = client.post(
        "/api/users/signup",
        json={
            "username": "letteriduser",
            "email": "s12ab5678@student.usp.ac.fj",
            "password": "secret123",
        },
    )

    assert response.status_code == 422
    assert "SXXXXXXXX" in response.json()["detail"]


def test_signup_accepts_lowercase_student_email():
    student_id = unique_student_id()

    response = client.post(
        "/api/users/signup",
        json={
            "username": f"lowercase_{student_id}",
            "email": f"s{student_id}@student.usp.ac.fj",
            "password": "secret123",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["message"] == "Account created successfully."
    assert data["user"]["email"] == f"s{student_id}@student.usp.ac.fj"


def test_signup_accepts_uppercase_student_email():
    student_id = unique_student_id()

    response = client.post(
        "/api/users/signup",
        json={
            "username": f"uppercase_{student_id}",
            "email": f"S{student_id}@student.usp.ac.fj",
            "password": "secret123",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["message"] == "Account created successfully."
    assert data["user"]["email"] == f"S{student_id}@student.usp.ac.fj"


def test_seller_can_create_update_and_delete_listing():
    seller = create_test_user()

    create_response = client.post(
        "/api/items",
        json={
            "name": "Data Structures Textbook",
            "price": 35,
            "description": "Used textbook in good condition.",
            "category": "Books",
            "contact": "seller@student.usp.ac.fj",
            "photo": "https://example.com/book.jpg",
            "seller_id": seller["id"],
        },
    )

    created = create_response.json()

    assert create_response.status_code == 200
    assert created["seller_id"] == seller["id"]
    assert created["seller_username"] == seller["username"]

    update_response = client.put(
        f"/api/items/{created['id']}?seller_id={seller['id']}",
        json={
            "price": 30,
            "description": "Discounted textbook in good condition.",
        },
    )

    updated = update_response.json()

    assert update_response.status_code == 200
    assert updated["price"] == 30
    assert updated["description"] == "Discounted textbook in good condition."

    delete_response = client.delete(f"/api/items/{created['id']}?seller_id={seller['id']}")

    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Listing removed successfully."
