import re
import math
import base64
import binascii
import warnings
from io import BytesIO

from PIL import Image, UnidentifiedImageError

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


def validate_listing_photo(photo):
    if not isinstance(photo, str) or not photo.strip():
        raise ApiError("Add a photo before saving your listing", 422)
    if len(photo) > 1_400_000:
        raise ApiError("The photo is too large. Choose a smaller image", 422)
    match = re.fullmatch(r"data:image/(jpeg|png|webp|avif);base64,([A-Za-z0-9+/=]+)", photo)
    if not match:
        raise ApiError("Upload a JPEG, PNG, WebP or AVIF photo", 422)
    try:
        content = base64.b64decode(match.group(2), validate=True)
        if len(content) > 1024 * 1024:
            raise ApiError("The photo is too large. Choose a smaller image", 422)
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                if image.format != {"jpeg": "JPEG", "png": "PNG", "webp": "WEBP", "avif": "AVIF"}[match.group(1)]:
                    raise ApiError("The photo contents do not match its image format", 422)
                if image.width * image.height > 16_000_000:
                    raise ApiError("Choose a photo with smaller dimensions", 422)
                image.verify()
            with Image.open(BytesIO(content)) as image:
                image.load()
    except (ValueError, OSError, SyntaxError, binascii.Error, UnidentifiedImageError, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ApiError("This photo could not be opened. Choose another image", 422) from exc


def validate_item_payload(data, partial=False):
    if not isinstance(data, dict):
        raise ApiError("Listing details must be a JSON object", 422)
    required = ["name", "price", "description", "category", "contact", "stock", "photo"]
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
    if "multiple_units" in data:
        if not isinstance(data["multiple_units"], bool):
            raise ApiError("Multiple units must be true or false", 422)
        if data["multiple_units"] is False and "stock" in data and int(data["stock"]) > 1:
            raise ApiError("Single-item listings can have at most one unit", 422)

    if "photo" in data:
        validate_listing_photo(data["photo"])

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
