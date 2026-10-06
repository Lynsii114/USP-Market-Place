import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from .exceptions import ApiError


def is_usp_student_email(email):
    return bool(re.fullmatch(r"S\d+@student\.usp\.ac\.fj", email, flags=re.IGNORECASE))


def validate_signup(data):
    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip()
    password = str(data.get("password", ""))

    if len(username) < 3:
        raise ApiError("Username must be at least 3 characters long", 422)
    if not username.replace("_", "").replace("-", "").isalnum():
        raise ApiError("Username can only contain letters, numbers, hyphens, and underscores", 422)
    if settings.ALLOW_NON_USP_EMAILS:
        try:
            validate_email(email)
        except ValidationError as exc:
            raise ApiError("Enter a valid email address", 422) from exc
    elif not is_usp_student_email(email):
        raise ApiError("Use your USP student email, for example S12345678@student.usp.ac.fj", 422)
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
