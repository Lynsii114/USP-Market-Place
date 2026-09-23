import hashlib
import base64
from io import BytesIO
import json
import secrets
import pyotp
import qrcode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from collections import defaultdict
from datetime import date, timedelta

from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date

from .constants import ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_USERNAME, HIDDEN_ITEM_NAMES
from .exceptions import ApiError
from .models import EmailVerification, Item, PasswordReset, PendingRegistration, Purchase, User
from .queries import find_student, find_user_by_login, item_status, public_items, visible_items, visible_purchases
from .serializers import serialize_item, serialize_purchase, serialize_user
from .validators import validate_item_payload, validate_signup


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def require_active_user(user_id):
    user = User.objects.filter(id=user_id).first()
    if not user:
        raise ApiError("User not found", 404)
    if user.status == "suspended":
        raise ApiError("Account is suspended", 403)
    return user


def require_admin(admin_id):
    if not admin_id:
        raise ApiError("Admin login required", 401)

    admin = User.objects.filter(id=admin_id).first()
    if not admin:
        raise ApiError("Admin login required", 401)
    if admin.role != "admin" or admin.status != "active":
        raise ApiError("Admin access required", 403)
    return admin


def get_or_create_admin_user():
    admin_user = User.objects.filter(email=ADMIN_EMAIL).first()
    if admin_user:
        admin_user.username = ADMIN_USERNAME
        admin_user.password_hash = hash_password(ADMIN_PASSWORD)
        admin_user.role = "admin"
        admin_user.status = "active"
        admin_user.save()
        return admin_user

    return User.objects.create(
        username=ADMIN_USERNAME,
        email=ADMIN_EMAIL,
        password_hash=hash_password(ADMIN_PASSWORD),
        role="admin",
        status="active",
    )


def hash_verification_code(code):
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def authenticator_setup(secret, email):
    uri = pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="USP Marketplace")
    qr_image = qrcode.make(uri)
    qr_buffer = BytesIO()
    qr_image.save(qr_buffer, format="PNG")
    return {
        "authenticator_secret": secret,
        "authenticator_uri": uri,
        "authenticator_qr": "data:image/png;base64," + base64.b64encode(qr_buffer.getvalue()).decode("ascii"),
    }


def send_email(subject, message, recipient):
    if settings.EMAIL_HOST:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [recipient])
        return

    if settings.RESEND_API_KEY:
        request = Request(
            "https://api.resend.com/emails",
            data=json.dumps({
                "from": settings.RESEND_FROM_EMAIL,
                "to": [recipient],
                "subject": subject,
                "text": message,
            }).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=15) as response:
                if response.status not in range(200, 300):
                    raise ApiError("Email provider rejected the message", 502)
        except HTTPError as exc:
            raw_error = ""
            try:
                raw_error = exc.read().decode("utf-8")
                error_body = json.loads(raw_error)
                provider_error = error_body.get("message") or error_body.get("name")
            except (ValueError, UnicodeDecodeError):
                provider_error = raw_error.strip() or None
            detail = provider_error or f"HTTP {exc.code} from email provider"
            raise ApiError(f"Resend error: {detail}", 502) from exc
        except (URLError, TimeoutError) as exc:
            raise ApiError("Unable to connect to Resend. Check your network connection.", 502) from exc
        return

    send_mail(subject, message, None, [recipient])


def send_verification_code(registration):
    code = f"{secrets.randbelow(1_000_000):06d}"
    registration.code_hash = hash_verification_code(code)
    registration.expires_at = timezone.now() + timedelta(minutes=10)
    registration.attempts = 0
    registration.save(update_fields=["code_hash", "expires_at", "attempts"])
    send_email(
        "Verify your USP Marketplace account",
        f"Your USP Marketplace verification code is {code}. It expires in 10 minutes.",
        registration.email,
    )


def signup_user(data):
    validate_signup(data)
    username = data["username"].strip()
    email = data["email"].strip()
    student_id = email.split("@", 1)[0]

    username_registered = User.objects.filter(username__iexact=username).exists()
    username_pending = PendingRegistration.objects.filter(username__iexact=username).exists()
    email_registered = User.objects.filter(email__iexact=email).exists()
    email_pending = PendingRegistration.objects.filter(email__iexact=email).exists()
    username_exists = username_registered or username_pending
    email_exists = email_registered or email_pending
    if username_exists and email_exists:
        raise ApiError("This username and email are already registered", 400)
    if username_exists:
        raise ApiError("This username is already registered", 400)
    if email_registered:
        raise ApiError("This email is already registered", 400)
    if email_pending:
        raise ApiError("A verification email has already been sent for these details", 400)

    registration = PendingRegistration.objects.create(
        username=username,
        student_id=student_id,
        email=email,
        password_hash=hash_password(data["password"]),
        code_hash="",
        expires_at=timezone.now(),
    )
    try:
        send_verification_code(registration)
    except Exception:
        registration.delete()
        raise
    return {
        "user": None,
        "email": email,
        "verification_required": True,
        "message": "Verification code sent to your personal email.",
    }


def verify_email(data):
    email = str(data.get("email", "")).strip().lower()
    code = str(data.get("code", "")).strip()
    if not email or not code.isdigit() or len(code) != 6:
        raise ApiError("Enter the six-digit verification code sent to your email", 422)

    registration = PendingRegistration.objects.filter(email__iexact=email).first()
    if not registration:
        user = User.objects.filter(email__iexact=email).first()
        if user and user.status == "active":
            return {"user": serialize_user(user), "message": "Email already verified."}
        raise ApiError("Verification request not found", 404)
    if registration.expires_at <= timezone.now():
        raise ApiError("That code has expired. Request a new code.", 400)
    if registration.attempts >= 5:
        raise ApiError("Too many attempts. Request a new code.", 429)

    if not secrets.compare_digest(registration.code_hash, hash_verification_code(code)):
        registration.attempts += 1
        registration.save(update_fields=["attempts"])
        raise ApiError("Incorrect verification code", 400)

    with transaction.atomic():
        user = User.objects.create(
            username=registration.username,
            student_id=registration.student_id,
            email=registration.email,
            password_hash=registration.password_hash,
            authenticator_secret=pyotp.random_base32(),
            role="student",
            status="active",
        )
        registration.delete()
    return {
        "user": None,
        "authenticator_setup_required": True,
        "user_id": user.id,
        **authenticator_setup(user.authenticator_secret, user.email),
        "message": "Email verified. Set up Microsoft Authenticator to finish creating your account.",
    }


def resend_verification(data):
    email = str(data.get("email", "")).strip().lower()
    registration = PendingRegistration.objects.filter(email__iexact=email).first()
    if not registration:
        raise ApiError("Verification request not found", 404)
    send_verification_code(registration)
    return {"message": "A new verification code was sent to your USP email."}


def cancel_verification(data):
    email = str(data.get("email", "")).strip().lower()
    if not email:
        raise ApiError("Email is required", 422)
    deleted, _ = PendingRegistration.objects.filter(email__iexact=email).delete()
    return {"message": "Verification cancelled.", "deleted": deleted > 0}


def request_password_reset(data):
    email = str(data.get("email", "")).strip().lower()
    user = User.objects.filter(email__iexact=email, status="active").first()
    if user:
        PasswordReset.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
        code = f"{secrets.randbelow(1_000_000):06d}"
        PasswordReset.objects.create(
            user=user,
            code_hash=hash_verification_code(code),
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        send_email(
            "Reset your USP Marketplace password",
            f"Your USP Marketplace password reset code is {code}. It expires in 10 minutes.",
            user.email,
        )
    return {"message": "If that USP email is registered, a password reset code has been sent."}


def reset_password(data):
    email = str(data.get("email", "")).strip().lower()
    code = str(data.get("code", "")).strip()
    password = str(data.get("password", ""))
    if len(password) < 6:
        raise ApiError("Password must be at least 6 characters long", 422)
    reset = PasswordReset.objects.filter(
        user__email__iexact=email,
        used_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).order_by("-created_at").first()
    if not reset:
        raise ApiError("That reset code is invalid or expired", 400)
    if reset.attempts >= 5:
        raise ApiError("Too many attempts. Request a new reset code.", 429)
    if not code.isdigit() or len(code) != 6 or not secrets.compare_digest(reset.code_hash, hash_verification_code(code)):
        reset.attempts += 1
        reset.save(update_fields=["attempts"])
        raise ApiError("That reset code is invalid or expired", 400)
    reset.user.password_hash = hash_password(password)
    reset.user.save(update_fields=["password_hash"])
    reset.used_at = timezone.now()
    reset.save(update_fields=["used_at"])
    return {"message": "Password reset successfully. You can now log in."}


def login_user(data):
    login_name = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if login_name.lower() == ADMIN_EMAIL.lower() and password == ADMIN_PASSWORD:
        admin_user = get_or_create_admin_user()
        return {"user": serialize_user(admin_user), "message": "Admin login successful"}

    user = find_user_by_login(login_name)
    if not user or user.password_hash != hash_password(password):
        raise ApiError("Invalid username or password", 401)
    if user.status == "pending_verification":
        raise ApiError("Please verify your USP email before logging in", 403)
    if user.status == "suspended":
        raise ApiError("Account is suspended", 403)
    if not user.authenticator_secret or not user.authenticator_enabled:
        user.authenticator_secret = pyotp.random_base32()
        user.authenticator_enabled = False
        user.save(update_fields=["authenticator_secret", "authenticator_enabled"])
        return {
            "authenticator_setup_required": True,
            "user_id": user.id,
            "username": user.username,
            **authenticator_setup(user.authenticator_secret, user.email),
            "message": "Set up Microsoft Authenticator to finish signing in",
        }
    return {
        "authenticator_required": True,
        "user_id": user.id,
        "message": "Enter the code from Microsoft Authenticator",
    }


def verify_authenticator(data):
    user_id = data.get("user_id")
    code = str(data.get("code", "")).strip().replace(" ", "")
    user = User.objects.filter(id=user_id).first()
    if not user or not user.authenticator_secret:
        raise ApiError("Authenticator setup is not available for this account", 400)
    if not code.isdigit() or len(code) != 6 or not pyotp.TOTP(user.authenticator_secret).verify(code, valid_window=1):
        raise ApiError("Incorrect Microsoft Authenticator code", 401)
    if not user.authenticator_enabled:
        user.authenticator_enabled = True
        user.save(update_fields=["authenticator_enabled"])
    return {"user": serialize_user(user), "message": "Login successful"}


def list_items():
    return [serialize_item(item) for item in public_items().order_by("-id")]


def list_seller_items(seller_id):
    items = public_items().filter(seller_id=seller_id).order_by("-id")
    return [serialize_item(item) for item in items]


def create_item(data):
    validate_item_payload(data)
    seller = require_active_user(data.get("seller_id"))
    stock = int(data["stock"])

    item = Item.objects.create(
        name=data["name"],
        price=float(data["price"]),
        description=data["description"],
        category=data["category"],
        contact=data["contact"],
        photo=data.get("photo"),
        stock=stock,
        status=item_status(stock),
        seller_id=seller.id,
        seller_username=seller.username,
    )
    return serialize_item(item)


def get_public_item(item_id):
    item = Item.objects.filter(id=item_id).first()
    if not item or item.status == "removed" or item.name in HIDDEN_ITEM_NAMES or item.name.startswith("__test_"):
        raise ApiError("Item not found", 404)
    return serialize_item(item)


def update_item(item_id, seller_id, data):
    item = Item.objects.filter(id=item_id).first()
    if not item:
        raise ApiError("Item not found", 404)
    if not seller_id or item.seller_id != int(seller_id):
        raise ApiError("You can only edit your own listings", 403)

    require_active_user(seller_id)
    validate_item_payload(data, partial=True)

    for field in ["name", "description", "category", "contact", "photo"]:
        if field in data:
            setattr(item, field, data[field])
    if "price" in data:
        item.price = float(data["price"])
    if "stock" in data:
        item.stock = int(data["stock"])

    item.status = item_status(item.stock)
    item.save()
    return serialize_item(item)


def delete_item(item_id, seller_id):
    item = Item.objects.filter(id=item_id).first()
    if not item:
        raise ApiError("Item not found", 404)
    if not seller_id or item.seller_id != int(seller_id):
        raise ApiError("You can only remove your own listings", 403)
    item.delete()
    return {"message": "Listing removed successfully."}


def purchase_item(item_id, buyer_id):
    if not buyer_id:
        raise ApiError("User not found", 404)

    buyer = require_active_user(buyer_id)
    item = Item.objects.filter(id=item_id).first()
    if not item or item.status == "removed":
        raise ApiError("Item not found", 404)
    if item.seller_id == buyer.id:
        raise ApiError("You cannot purchase your own listing", 400)
    if item.stock <= 0 or item.status == "sold":
        item.stock = 0
        item.status = "sold"
        item.save()
        raise ApiError("Item is sold out", 400)

    item.stock -= 1
    item.status = item_status(item.stock)
    item.save()
    Purchase.objects.create(
        buyer_id=buyer.id,
        buyer_username=buyer.username,
        item_id=item.id,
        item_name=item.name,
        price=item.price,
        category=item.category,
        seller_id=item.seller_id,
        seller_username=item.seller_username,
        seller_contact=item.contact,
        quantity=1,
        total_amount=item.price,
        status="completed",
    )
    return serialize_item(item)


def list_buyer_purchases(buyer_id):
    if not User.objects.filter(id=buyer_id).exists():
        raise ApiError("User not found", 404)
    purchases = visible_purchases(include_test_records=True).filter(buyer_id=buyer_id).order_by("-id")
    return [serialize_purchase(purchase) for purchase in purchases]


def dashboard(admin_id):
    require_admin(admin_id)
    today = date.today()
    purchases = list(visible_purchases().order_by("-id"))
    todays_sales = sum(
        purchase.total_amount or purchase.price
        for purchase in purchases
        if purchase.purchased_at and purchase.purchased_at.date() == today
    )
    return {
        "total_students": User.objects.filter(role="student").count(),
        "total_active_listings": visible_items().filter(status="available").count(),
        "total_orders": len(purchases),
        "todays_sales": todays_sales,
        "recent_orders": [serialize_purchase(purchase) for purchase in purchases[:5]],
    }


def list_students(admin_id, search=""):
    require_admin(admin_id)
    query = User.objects.filter(role="student")
    if search:
        query = query.filter(Q(username__contains=search) | Q(email__contains=search))
    return [serialize_user(user) for user in query.order_by("-id")]


def set_student_status(admin_id, student_id, status):
    require_admin(admin_id)
    student = find_student(student_id)
    if not student:
        raise ApiError("Student not found", 404)
    student.status = status
    student.save()
    return serialize_user(student)


def list_admin_items(admin_id, search=""):
    require_admin(admin_id)
    query = visible_items()
    if search:
        query = query.filter(
            Q(name__contains=search)
            | Q(category__contains=search)
            | Q(seller_username__contains=search)
        )
    return [serialize_item(item) for item in query.order_by("-id")]


def remove_listing(admin_id, item_id, reason):
    require_admin(admin_id)
    item = Item.objects.filter(id=item_id).first()
    if not item:
        raise ApiError("Item not found", 404)
    item.status = "removed"
    item.removed_reason = reason
    item.save()
    return serialize_item(item)


def restore_listing(admin_id, item_id):
    require_admin(admin_id)
    item = Item.objects.filter(id=item_id).first()
    if not item:
        raise ApiError("Item not found", 404)
    item.status = item_status(item.stock)
    item.removed_reason = None
    item.save()
    return serialize_item(item)


def list_orders(admin_id, search="", status="", order_date=""):
    require_admin(admin_id)
    query = visible_purchases()

    if status:
        query = query.filter(status=status)
    if search:
        filters = Q(item_name__contains=search) | Q(buyer_username__contains=search) | Q(seller_username__contains=search)
        if search.isdigit():
            filters |= Q(id=int(search))
        query = query.filter(filters)

    orders = list(query.order_by("-id"))
    if order_date:
        selected_date = parse_date(order_date)
        if not selected_date:
            raise ApiError("Order date must be YYYY-MM-DD", 400)
        orders = [
            order
            for order in orders
            if order.purchased_at and order.purchased_at.date() == selected_date
        ]

    return [serialize_purchase(order) for order in orders]


def report(admin_id, period="daily"):
    require_admin(admin_id)
    grouped = defaultdict(lambda: {"orders": 0, "items_sold": 0, "total_sales": 0})

    for purchase in visible_purchases().order_by("-purchased_at"):
        if not purchase.purchased_at:
            continue
        purchased_date = purchase.purchased_at.date()
        if period == "monthly":
            key = purchased_date.strftime("%Y-%m")
        elif period == "weekly":
            year, week, _ = purchased_date.isocalendar()
            key = f"{year}-W{week:02d}"
        else:
            key = purchased_date.isoformat()

        grouped[key]["orders"] += 1
        grouped[key]["items_sold"] += purchase.quantity or 1
        grouped[key]["total_sales"] += purchase.total_amount or purchase.price

    rows = [
        {
            "date": key,
            "orders": value["orders"],
            "items_sold": value["items_sold"],
            "total_sales": value["total_sales"],
        }
        for key, value in sorted(grouped.items(), reverse=True)
    ]
    return {
        "total_orders": sum(row["orders"] for row in rows),
        "total_items_sold": sum(row["items_sold"] for row in rows),
        "total_sales": sum(row["total_sales"] for row in rows),
        "rows": rows,
    }
