import re
import math

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


MAX_INVENTORY_INTEGER = 2_147_483_647


def whole_number(value, label, minimum=0):
    # JSON booleans and floats must not be silently converted into inventory units.
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ApiError(f"{label} must be a whole number", 422)
    if isinstance(value, str) and not re.fullmatch(r"[0-9]+", value.strip()):
        raise ApiError(f"{label} must be a whole number", 422)
    try:
        number = int(value)
    except (ValueError, OverflowError) as exc:
        raise ApiError(f"{label} must be a whole number", 422) from exc
    if not minimum <= number <= MAX_INVENTORY_INTEGER:
        raise ApiError(f"{label} must be between {minimum} and {MAX_INVENTORY_INTEGER}", 422)
    return number


def validate_item_payload(data, partial=False):
    if not isinstance(data, dict):
        raise ApiError("Listing details must be a JSON object", 422)
    required = ["name", "price", "description", "category", "contact", "stock"]
    if not partial:
        missing = [field for field in required if field not in data]
        if missing:
            raise ApiError(f"Missing field: {missing[0]}", 422)

    for field, limit in {"name": 256, "description": 1000, "category": 64, "contact": 128}.items():
        if field in data:
            value = data[field]
            if not isinstance(value, str) or not value.strip():
                raise ApiError(f"{field.capitalize()} is required", 422)
            if len(value.strip()) > limit:
                raise ApiError(f"{field.capitalize()} must be {limit} characters or fewer", 422)

    if "stock" in data:
        whole_number(data["stock"], "Stock")

    if "price" in data:
        try:
            price = float(data["price"])
        except (TypeError, ValueError, OverflowError) as exc:
            raise ApiError("Price must be a finite positive number", 422) from exc
        if isinstance(data["price"], bool) or not math.isfinite(price) or price <= 0 or price > 999_999_999.99:
            raise ApiError("Price must be greater than 0 and at most 999999999.99", 422)

    payment_method = str(data.get("payment_method", "cash")).strip().lower()
    if payment_method not in {"mpaisa", "mycash", "cash"}:
        raise ApiError("Choose M-PAiSA, MyCash, or Cash as the seller payment method", 422)
    if payment_method in {"mpaisa", "mycash"}:
        payment_number = re.sub(r"[ ()-]", "", str(data.get("payment_number", "")).strip())
        if not re.fullmatch(r"\+?\d{7,15}", payment_number):
            raise ApiError("Enter a valid phone number for the selected mobile payment method", 422)
