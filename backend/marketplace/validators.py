import re

from .exceptions import ApiError


def validate_signup(data):
    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip()
    password = str(data.get("password", ""))

    if len(username) < 3:
        raise ApiError("Username must be at least 3 characters long", 422)
    if not username.replace("_", "").replace("-", "").isalnum():
        raise ApiError("Username can only contain letters, numbers, hyphens, and underscores", 422)
    if not re.match(r"^s\d{8}@student\.usp\.ac\.fj$", email.lower()):
        raise ApiError("Email must be in format: SXXXXXXXX@student.usp.ac.fj, where X is a number", 422)
    if len(password) < 6:
        raise ApiError("Password must be at least 6 characters long", 422)


def validate_item_payload(data, partial=False):
    required = ["name", "price", "description", "category", "contact", "stock"]
    if not partial:
        missing = [field for field in required if field not in data]
        if missing:
            raise ApiError(f"Missing field: {missing[0]}", 422)

    if "stock" in data:
        try:
            if int(data["stock"]) < 0:
                raise ApiError("Stock cannot be negative", 422)
        except (TypeError, ValueError) as exc:
            raise ApiError("Stock must be a number", 422) from exc

    if "price" in data:
        try:
            float(data["price"])
        except (TypeError, ValueError) as exc:
            raise ApiError("Price must be a number", 422) from exc

