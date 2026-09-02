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
            "stock": 1,
        },
    )

    created = create_response.json()

    assert create_response.status_code == 200
    assert created["seller_id"] == seller["id"]
    assert created["seller_username"] == seller["username"]
    assert created["stock"] == 1
    assert created["status"] == "available"

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


def test_seller_must_enter_listing_stock():
    seller = create_test_user()

    response = client.post(
        "/api/items",
        json={
            "name": "Notebook",
            "price": 5,
            "description": "Unused notebook.",
            "category": "Books",
            "contact": "seller@student.usp.ac.fj",
            "seller_id": seller["id"],
        },
    )

    assert response.status_code == 422


def test_purchase_decreases_stock_and_marks_sold():
    seller = create_test_user()
    test_item_name = "__test_purchase_item__"

    create_response = client.post(
        "/api/items",
        json={
            "name": test_item_name,
            "price": 20,
            "description": "Temporary test item.",
            "category": "Electronics",
            "contact": "seller@student.usp.ac.fj",
            "seller_id": seller["id"],
            "stock": 2,
        },
    )

    created = create_response.json()

    assert create_response.status_code == 200
    assert created["stock"] == 2
    assert created["status"] == "available"

    guest_purchase = client.post(f"/api/items/{created['id']}/purchase")

    assert guest_purchase.status_code == 422

    first_purchase = client.post(f"/api/items/{created['id']}/purchase?buyer_id={seller['id']}")
    first_data = first_purchase.json()

    assert first_purchase.status_code == 200
    assert first_data["stock"] == 1
    assert first_data["status"] == "available"

    purchase_history = client.get(f"/api/users/{seller['id']}/purchases")
    purchase_history_data = purchase_history.json()

    assert purchase_history.status_code == 200
    assert purchase_history_data[0]["item_name"] == test_item_name
    assert purchase_history_data[0]["buyer_id"] == seller["id"]
    assert "purchased_at" in purchase_history_data[0]

    second_purchase = client.post(f"/api/items/{created['id']}/purchase?buyer_id={seller['id']}")
    second_data = second_purchase.json()

    assert second_purchase.status_code == 200
    assert second_data["stock"] == 0
    assert second_data["status"] == "sold"

    sold_out_purchase = client.post(f"/api/items/{created['id']}/purchase?buyer_id={seller['id']}")

    assert sold_out_purchase.status_code == 400
    assert sold_out_purchase.json()["detail"] == "Item is sold out"

    client.delete(f"/api/items/{created['id']}?seller_id={seller['id']}")
