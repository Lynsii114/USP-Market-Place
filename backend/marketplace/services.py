import hashlib
import base64
from io import BytesIO
import json
import logging
import math
import smtplib
import secrets
import re
import ssl
import pyotp
import qrcode
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from collections import defaultdict
from datetime import date, timedelta

from django.core.mail import BadHeaderError, send_mail
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date
# FUTURE MICROSOFT ENTRA INTEGRATION:
# import jwt
# from jwt import PyJWKClient

from .constants import ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_USERNAME
from .exceptions import ApiError
from .models import AdminNotification, Conversation, EmailVerification, Item, Message, PasswordReset, PendingRegistration, Purchase, RatingReview, User, UserNotification, UserReport
from .queries import find_student, find_user_by_login, item_status, public_items, visible_items, visible_purchases
from .serializers import serialize_conversation, serialize_item, serialize_message, serialize_notification, serialize_purchase, serialize_rating_review, serialize_user, serialize_user_report
from .validators import validate_item_payload, validate_signup


email_logger = logging.getLogger("marketplace.email")
VERIFICATION_CODE_TTL = timedelta(minutes=10)
VERIFICATION_RESEND_COOLDOWN = timedelta(minutes=1)
PENDING_REGISTRATIONS = {}


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
        admin_user.name = ADMIN_USERNAME
        admin_user.password_hash = hash_password(ADMIN_PASSWORD)
        admin_user.role = "admin"
        admin_user.status = "active"
        admin_user.verified = True
        admin_user.save()
        return admin_user

    return User.objects.create(
        username=ADMIN_USERNAME,
        name=ADMIN_USERNAME,
        email=ADMIN_EMAIL,
        password_hash=hash_password(ADMIN_PASSWORD),
        role="admin",
        status="active",
        verified=True,
    )


def notify_admin(title, message, category="activity", actor=None):
    return AdminNotification.objects.create(
        title=title,
        message=message,
        category=category,
        actor_id=actor.id if actor else None,
        actor_username=actor.username if actor else None,
    )


def notify_user(user_id, title, message, category="activity", actor=None):
    if not User.objects.filter(id=user_id).exists():
        return None
    return UserNotification.objects.create(
        user_id=user_id,
        title=title,
        message=message,
        category=category,
        actor_id=actor.id if actor else None,
        actor_username=actor.username if actor else None,
    )


def notify_order_user(purchase, user_id, title, message, actor=None):
    return notify_user(user_id, title, message, "order", actor)


def serialize_admin_item(item):
    data = serialize_item(item)
    seller = User.objects.filter(id=item.seller_id).first()
    if seller:
        data["seller"] = serialize_user(seller)
    return data


def serialize_admin_purchase(purchase):
    data = serialize_purchase(purchase)
    buyer = User.objects.filter(id=purchase.buyer_id).first()
    seller = User.objects.filter(id=purchase.seller_id).first()
    if buyer:
        data["buyer"] = serialize_user(buyer)
    if seller:
        data["seller"] = serialize_user(seller)
    return data


def serialize_admin_review(review):
    data = serialize_rating_review(review)
    reviewer = User.objects.filter(id=review.reviewer_id).first()
    seller = User.objects.filter(id=review.seller_id).first()
    if reviewer:
        data["reviewer"] = serialize_user(reviewer)
    if seller:
        data["seller"] = serialize_user(seller)
    return data


def serialize_admin_notification(notification):
    data = serialize_notification(notification)
    if notification.actor_id:
        actor = User.objects.filter(id=notification.actor_id).first()
        if actor:
            data["actor"] = serialize_user(actor)
    return data


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


def verification_email_message(code):
    return (
        "Hello,\n\n"
        "USP Marketplace received a request to register an account with this email address.\n\n"
        f"Your 6-digit verification code is: {code}\n\n"
        "This code expires in 10 minutes.\n\n"
        "If you did not request this code, you can ignore this email.\n\n"
        "USP Marketplace System"
    )


def describe_email_exception(exc):
    if isinstance(exc, ssl.SSLCertVerificationError):
        return "SMTP TLS certificate verification failed. Install or configure a trusted CA certificate bundle and check system date/time."
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        smtp_message = exc.smtp_error.decode("utf-8", errors="replace") if isinstance(exc.smtp_error, bytes) else str(exc.smtp_error)
        return f"SMTP authentication failed ({exc.smtp_code}): {smtp_message}. Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD. Gmail requires a 16-character App Password with 2-Step Verification enabled."
    if isinstance(exc, smtplib.SMTPConnectError):
        return f"SMTP connection failed ({exc.smtp_code}): {exc.smtp_error}. Check EMAIL_HOST, EMAIL_PORT, and network/firewall access."
    if isinstance(exc, smtplib.SMTPServerDisconnected):
        if settings.EMAIL_HOST == "smtp.gmail.com":
            return "Gmail closed the SMTP authentication connection. Check that EMAIL_HOST_USER is an active Gmail/Google Workspace mailbox, 2-Step Verification is enabled, the App Password was generated for that exact mailbox, and Workspace allows App Passwords/SMTP access."
        return "SMTP server disconnected before accepting the message. Check TLS/SSL settings, host, and port."
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "SMTP provider refused the recipient address."
    if isinstance(exc, smtplib.SMTPSenderRefused):
        return f"SMTP provider refused DEFAULT_FROM_EMAIL: {exc.sender}. Make sure it matches or is allowed by the SMTP account."
    if isinstance(exc, smtplib.SMTPException):
        return f"SMTP error: {exc}"
    if isinstance(exc, BadHeaderError):
        return "Email subject or body contains an invalid header."
    if isinstance(exc, TimeoutError):
        return "SMTP connection timed out. Check host, port, TLS/SSL, and network access."
    if isinstance(exc, OSError):
        return f"Network error while contacting SMTP server: {exc}"
    return str(exc) or exc.__class__.__name__


def require_smtp_settings(failure_prefix):
    if not settings.EMAIL_HOST_USER:
        raise ApiError(f"{failure_prefix}: EMAIL_HOST_USER is not configured", 500)
    if not settings.EMAIL_HOST_PASSWORD:
        raise ApiError(f"{failure_prefix}: EMAIL_HOST_PASSWORD is not configured", 500)
    if settings.EMAIL_HOST == "smtp.gmail.com" and len(settings.EMAIL_HOST_PASSWORD) != 16:
        raise ApiError(f"{failure_prefix}: EMAIL_HOST_PASSWORD must be a 16-character Gmail App Password for smtp.gmail.com", 500)
    if not settings.DEFAULT_FROM_EMAIL:
        raise ApiError(f"{failure_prefix}: DEFAULT_FROM_EMAIL is not configured", 500)
    if settings.EMAIL_USE_TLS and settings.EMAIL_USE_SSL:
        raise ApiError(f"{failure_prefix}: EMAIL_USE_TLS and EMAIL_USE_SSL cannot both be enabled", 500)


def send_email(subject, message, recipient, failure_prefix="Failed to send email"):
    if settings.EMAIL_HOST:
        require_smtp_settings(failure_prefix)
        email_logger.info(
            "[email-debug] SMTP connection stage: host=%s port=%s tls=%s ssl=%s user=%s from=%s recipient=%s",
            settings.EMAIL_HOST,
            settings.EMAIL_PORT,
            settings.EMAIL_USE_TLS,
            settings.EMAIL_USE_SSL,
            settings.EMAIL_HOST_USER,
            settings.DEFAULT_FROM_EMAIL,
            recipient,
        )
        try:
            sent_count = send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=False)
        except Exception as exc:
            detail = describe_email_exception(exc)
            email_logger.exception("[email-debug] SMTP/email sending failed for %s: %s", recipient, detail)
            raise ApiError(f"{failure_prefix}: {detail}", 502) from exc
        if sent_count != 1:
            detail = "SMTP backend did not report a sent message. Check provider logs and sender verification."
            email_logger.error("[email-debug] SMTP/email sending failed for %s: %s", recipient, detail)
            raise ApiError(f"{failure_prefix}: {detail}", 502)
        email_logger.info("[email-debug] Email sent successfully to %s", recipient)
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
            email_logger.info("[email-debug] Resend API sending stage: from=%s recipient=%s", settings.RESEND_FROM_EMAIL, recipient)
            with urlopen(request, timeout=15) as response:
                if response.status not in range(200, 300):
                    raise ApiError(f"{failure_prefix}: Email provider rejected the message", 502)
        except HTTPError as exc:
            raw_error = ""
            try:
                raw_error = exc.read().decode("utf-8")
                error_body = json.loads(raw_error)
                provider_error = error_body.get("message") or error_body.get("name")
            except (ValueError, UnicodeDecodeError):
                provider_error = raw_error.strip() or None
            detail = provider_error or f"HTTP {exc.code} from email provider"
            email_logger.exception("[email-debug] Resend/email sending failed for %s: %s", recipient, detail)
            raise ApiError(f"{failure_prefix}: Resend error: {detail}", 502) from exc
        except (URLError, TimeoutError) as exc:
            email_logger.exception("[email-debug] Resend/email sending failed for %s", recipient)
            raise ApiError(f"{failure_prefix}: Unable to connect to Resend. Check your network connection.", 502) from exc
        email_logger.info("[email-debug] Email sent successfully to %s", recipient)
        return

    email_logger.error("[email-debug] No SMTP provider configured for %s", recipient)
    raise ApiError(f"{failure_prefix}: SMTP is not configured. Set EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, and DEFAULT_FROM_EMAIL in backend/.env.", 500)


def pending_value(registration, key):
    return registration[key] if isinstance(registration, dict) else getattr(registration, key)


def set_pending_value(registration, key, value):
    if isinstance(registration, dict):
        registration[key] = value
    else:
        setattr(registration, key, value)


def save_pending_verification(registration):
    if isinstance(registration, dict):
        return
    registration.save(update_fields=["code_hash", "expires_at", "attempts"])


def cleanup_pending_registrations():
    now = timezone.now()
    expired_tokens = [
        token
        for token, registration in PENDING_REGISTRATIONS.items()
        if registration["expires_at"] <= now
    ]
    for token in expired_tokens:
        PENDING_REGISTRATIONS.pop(token, None)
    PendingRegistration.objects.filter(expires_at__lte=now).delete()


def delete_pending_registration(registration):
    if isinstance(registration, dict):
        PENDING_REGISTRATIONS.pop(registration["pending_token"], None)
    else:
        registration.delete()


def find_pending_registration(email, pending_token=""):
    cleanup_pending_registrations()
    if pending_token:
        registration = PENDING_REGISTRATIONS.get(pending_token)
        if registration and registration["email"].lower() == email.lower():
            return registration
    else:
        registration = next(
            (
                registration
                for registration in PENDING_REGISTRATIONS.values()
                if registration["email"].lower() == email.lower()
            ),
            None,
        )
        if registration:
            return registration
    return PendingRegistration.objects.filter(email__iexact=email).first()


def pending_exists_for_username(username):
    cleanup_pending_registrations()
    return (
        any(registration["username"].lower() == username.lower() for registration in PENDING_REGISTRATIONS.values())
        or PendingRegistration.objects.filter(username__iexact=username).exists()
    )


def pending_exists_for_email(email):
    cleanup_pending_registrations()
    return (
        any(registration["email"].lower() == email.lower() for registration in PENDING_REGISTRATIONS.values())
        or PendingRegistration.objects.filter(email__iexact=email).exists()
    )


def send_verification_code(registration):
    email = pending_value(registration, "email")
    registration_id = pending_value(registration, "pending_token") if isinstance(registration, dict) else registration.id
    email_logger.info("[email-debug] Registration -> code generation stage for %s", email)
    code = f"{secrets.randbelow(1_000_000):06d}"
    set_pending_value(registration, "code_hash", hash_verification_code(code))
    set_pending_value(registration, "expires_at", timezone.now() + VERIFICATION_CODE_TTL)
    set_pending_value(registration, "attempts", 0)
    email_logger.info("[email-debug] Temporary verification save stage: registration_id=%s email=%s", registration_id, email)
    save_pending_verification(registration)
    email_logger.info("[email-debug] Temporary verification save complete: registration_id=%s email=%s", registration_id, email)
    send_email(
        "Verify your USP Marketplace account",
        verification_email_message(code),
        email,
        "Failed to send verification email",
    )


def verification_resend_seconds_remaining(registration):
    sent_at = pending_value(registration, "expires_at") - VERIFICATION_CODE_TTL
    resend_at = sent_at + VERIFICATION_RESEND_COOLDOWN
    return max(0, math.ceil((resend_at - timezone.now()).total_seconds()))


def signup_user(data):
    validate_signup(data)
    username = data["username"].strip()
    email = data["email"].strip()
    student_id = email.split("@", 1)[0]

    username_registered = User.objects.filter(username__iexact=username).exists()
    email_registered = User.objects.filter(email__iexact=email).exists()
    pending_by_email = find_pending_registration(email)
    if pending_by_email and pending_value(pending_by_email, "username").lower() == username.lower():
        return {
            "user": None,
            "email": email,
            "pending_token": pending_value(pending_by_email, "pending_token") if isinstance(pending_by_email, dict) else "",
            "verification_required": True,
            "message": "A verification email has already been sent. Enter its code to continue.",
        }

    username_pending = pending_exists_for_username(username)
    email_pending = pending_exists_for_email(email)
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

    pending_token = secrets.token_urlsafe(32)
    registration = {
        "pending_token": pending_token,
        "username": username,
        "student_id": student_id,
        "email": email,
        "password_hash": hash_password(data["password"]),
        "code_hash": "",
        "expires_at": timezone.now(),
        "attempts": 0,
        "created_at": timezone.now(),
    }
    PENDING_REGISTRATIONS[pending_token] = registration
    try:
        send_verification_code(registration)
    except Exception:
        email_logger.exception("[email-debug] Registration email failed; deleting temporary pending registration token=%s email=%s so the user can retry", pending_token, email)
        delete_pending_registration(registration)
        raise
    return {
        "user": None,
        "email": email,
        "pending_token": pending_token,
        "verification_required": True,
        "message": "Verification code sent successfully",
    }


def verify_email(data):
    email = str(data.get("email", "")).strip().lower()
    code = str(data.get("code", "")).strip()
    pending_token = str(data.get("pending_token", "")).strip()
    if not email or not code.isdigit() or len(code) != 6:
        raise ApiError("Enter the six-digit verification code sent to your email", 422)

    registration = find_pending_registration(email, pending_token)
    if not registration:
        user = User.objects.filter(email__iexact=email).first()
        if user and user.status == "active":
            return {"user": serialize_user(user), "message": "Email already verified."}
        raise ApiError("Verification request not found", 404)
    if pending_value(registration, "expires_at") <= timezone.now():
        delete_pending_registration(registration)
        raise ApiError("That code has expired. Request a new code.", 400)
    if pending_value(registration, "attempts") >= 5:
        raise ApiError("Too many attempts. Request a new code.", 429)

    if not secrets.compare_digest(pending_value(registration, "code_hash"), hash_verification_code(code)):
        set_pending_value(registration, "attempts", pending_value(registration, "attempts") + 1)
        if not isinstance(registration, dict):
            registration.save(update_fields=["attempts"])
        raise ApiError("Incorrect verification code", 400)

    with transaction.atomic():
        user = User.objects.create(
            username=pending_value(registration, "username"),
            student_id=pending_value(registration, "student_id"),
            name=pending_value(registration, "username"),
            email=pending_value(registration, "email"),
            password_hash=pending_value(registration, "password_hash"),
            authenticator_secret=pyotp.random_base32(),
            role="student",
            status="active",
            verified=True,
        )
        delete_pending_registration(registration)
    return {
        "user": None,
        "authenticator_setup_required": True,
        "user_id": user.id,
        **authenticator_setup(user.authenticator_secret, user.email),
        "message": "Email verified. Set up Microsoft Authenticator to finish creating your account.",
    }


def resend_verification(data):
    email = str(data.get("email", "")).strip().lower()
    pending_token = str(data.get("pending_token", "")).strip()
    registration = find_pending_registration(email, pending_token)
    if not registration:
        raise ApiError("Verification request not found", 404)
    seconds_remaining = verification_resend_seconds_remaining(registration)
    if seconds_remaining > 0:
        raise ApiError(f"Resend code available in {seconds_remaining} seconds", 429)
    send_verification_code(registration)
    return {"message": "Verification code sent successfully"}


def cancel_verification(data):
    email = str(data.get("email", "")).strip().lower()
    pending_token = str(data.get("pending_token", "")).strip()
    if not email:
        raise ApiError("Email is required", 422)
    registration = find_pending_registration(email, pending_token)
    if registration:
        delete_pending_registration(registration)
        return {"message": "Verification cancelled.", "deleted": True}
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


def find_active_password_reset(email):
    return PasswordReset.objects.filter(
        user__email__iexact=email,
        used_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).order_by("-created_at").first()


def validate_password_reset_code(email, code):
    reset = find_active_password_reset(email)
    if not reset:
        raise ApiError("That reset code is invalid or expired", 400)
    if reset.attempts >= 5:
        raise ApiError("Too many attempts. Request a new reset code.", 429)
    if not code.isdigit() or len(code) != 6 or not secrets.compare_digest(reset.code_hash, hash_verification_code(code)):
        reset.attempts += 1
        reset.save(update_fields=["attempts"])
        raise ApiError("That reset code is invalid or expired", 400)
    return reset


def verify_password_reset_code(data):
    email = str(data.get("email", "")).strip().lower()
    code = str(data.get("code", "")).strip()
    validate_password_reset_code(email, code)
    return {"message": "Reset code verified. Choose a new password."}


def reset_password(data):
    email = str(data.get("email", "")).strip().lower()
    code = str(data.get("code", "")).strip()
    password = str(data.get("password", ""))
    if len(password) < 6:
        raise ApiError("Password must be at least 6 characters long", 422)
    reset = validate_password_reset_code(email, code)
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


''' FUTURE MICROSOFT ENTRA INTEGRATION - enable after USP provides tenant configuration.
def microsoft_login(data):
    token = str(data.get("id_token", "")).strip()
    if not token:
        raise ApiError("Microsoft sign-in token is required", 422)
    if not settings.MICROSOFT_CLIENT_ID or not settings.MICROSOFT_TENANT_ID:
        raise ApiError("Microsoft sign-in is not configured on the server", 503)

    issuer = f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}/v2.0"
    jwks_client = PyJWKClient(
        f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}/discovery/v2.0/keys"
    )
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.MICROSOFT_CLIENT_ID,
            issuer=issuer,
        )
    except (jwt.PyJWTError, Exception) as exc:
        raise ApiError("Microsoft sign-in could not be verified", 401) from exc

    email = str(claims.get("preferred_username") or claims.get("email") or "").strip().lower()
    if not re.match(r"^s\d+@(?:[a-z0-9-]+\.)*usp\.ac\.fj$", email):
        raise ApiError("Only verified USP student Microsoft accounts can sign in", 403)

    student_id = email.split("@", 1)[0].upper()
    user = User.objects.filter(email__iexact=email).first()
    if user:
        if user.status == "suspended":
            raise ApiError("Account is suspended", 403)
        if not user.authenticator_secret:
            user.authenticator_secret = pyotp.random_base32()
            user.save(update_fields=["authenticator_secret"])
            return {
                "authenticator_setup_required": True,
                "user_id": user.id,
                "username": user.username,
                **authenticator_setup(user.authenticator_secret, user.email),
                "message": "Set up Microsoft Authenticator to finish signing in",
            }
        return {"user": serialize_user(user), "message": "Microsoft sign-in successful"}

    username = student_id.lower()
    if User.objects.filter(username=username).exists():
        username = f"{username}_{student_id[-4:].lower()}"
    user = User.objects.create(
        username=username,
        student_id=student_id,
        name=claims.get("name") or username,
        email=email,
        password_hash="",
        role="student",
        status="active",
        verified=True,
    )
    PendingRegistration.objects.filter(email__iexact=email).delete()
    return {"user": serialize_user(user), "message": "USP Microsoft account connected successfully"}
'''


def list_items():
    return [serialize_item(item) for item in public_items().order_by("-id")]


def list_seller_items(seller_id):
    seller = require_active_user(seller_id)
    items = visible_items().filter(seller_id=seller.id).exclude(status="removed").order_by("-id")
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
    if not item or item.status == "removed" or item.name.startswith("__test_"):
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
    if ("price" in data or "stock" in data) and Purchase.objects.filter(
        item_id=item.id,
        payment_status="pending",
        order_stage="order_placed",
    ).exists():
        raise ApiError("An order is waiting for payment; cancel it before changing price or stock", 409)

    for field in ["name", "description", "category", "contact", "photo"]:
        if field in data:
            setattr(item, field, data[field])
    if "price" in data:
        item.price = float(data["price"])
    if "stock" in data:
        item.stock = int(data["stock"])

    if item.status != "reserved":
        item.status = item_status(item.stock)
    item.save()
    return serialize_item(item)


def delete_item(item_id, seller_id):
    item = Item.objects.filter(id=item_id).first()
    if not item:
        raise ApiError("Item not found", 404)
    if not seller_id or item.seller_id != int(seller_id):
        raise ApiError("You can only remove your own listings", 403)
    if Purchase.objects.filter(
        item_id=item.id, payment_status="pending", order_stage="order_placed",
    ).exists():
        raise ApiError("An order is waiting for payment; cancel it before deleting this listing", 409)
    item.delete()
    return {"message": "Listing removed successfully."}


def _conversation_payload(conversation, current_user_id=None, mark_read=False):
    item = Item.objects.filter(id=conversation.item_id).first()
    buyer = User.objects.filter(id=conversation.buyer_id).first()
    seller = User.objects.filter(id=conversation.seller_id).first()
    if mark_read and current_user_id:
        Message.objects.filter(conversation_id=conversation.id, receiver_id=current_user_id, is_read=False).update(is_read=True)
    messages = list(Message.objects.filter(conversation_id=conversation.id).order_by("created_at", "id"))
    return serialize_conversation(conversation, item, buyer, seller, messages, current_user_id)


def list_conversations(user_id):
    user = require_active_user(user_id)
    conversations = Conversation.objects.filter(Q(buyer_id=user.id) | Q(seller_id=user.id)).order_by("-updated_at", "-id")
    return [_conversation_payload(conversation, user.id) for conversation in conversations]


def get_unread_message_count(user_id):
    user = require_active_user(user_id)
    return {"unread_count": Message.objects.filter(receiver_id=user.id, is_read=False).count()}


def open_item_conversation(item_id, buyer_id):
    buyer = require_active_user(buyer_id)
    item = Item.objects.filter(id=item_id).first()
    if not item or item.status in {"hidden", "removed"}:
        raise ApiError("Item not found", 404)
    if item.seller_id == buyer.id:
        raise ApiError("You cannot message yourself about your own listing", 400)
    seller = require_active_user(item.seller_id)
    conversation, _ = Conversation.objects.get_or_create(
        item_id=item.id,
        buyer_id=buyer.id,
        seller_id=seller.id,
    )
    conversation.save(update_fields=["updated_at"])
    return _conversation_payload(conversation, buyer.id, mark_read=True)


def send_conversation_message(conversation_id, sender_id, body):
    sender = require_active_user(sender_id)
    message_body = str(body or "").strip()
    if len(message_body) < 1:
        raise ApiError("Message cannot be empty", 422)
    if len(message_body) > 1000:
        raise ApiError("Message is too long", 422)
    conversation = Conversation.objects.filter(id=conversation_id).first()
    if not conversation:
        raise ApiError("Conversation not found", 404)
    if sender.id not in {conversation.buyer_id, conversation.seller_id}:
        raise ApiError("You are not part of this conversation", 403)
    receiver_id = conversation.seller_id if sender.id == conversation.buyer_id else conversation.buyer_id
    Message.objects.create(
        conversation_id=conversation.id,
        sender_id=sender.id,
        receiver_id=receiver_id,
        body=message_body,
        is_read=False,
    )
    conversation.save(update_fields=["updated_at"])
    item = Item.objects.filter(id=conversation.item_id).first()
    notify_user(
        receiver_id,
        "New message",
        f"{sender.username} sent you a message about {item.name if item else 'a marketplace item'}.",
        "message",
        sender,
    )
    return _conversation_payload(conversation, sender.id)


def get_conversation(conversation_id, user_id):
    user = require_active_user(user_id)
    conversation = Conversation.objects.filter(id=conversation_id).first()
    if not conversation:
        raise ApiError("Conversation not found", 404)
    if user.id not in {conversation.buyer_id, conversation.seller_id}:
        raise ApiError("You are not part of this conversation", 403)
    return _conversation_payload(conversation, user.id, mark_read=True)


def list_item_message_buyers(item_id, seller_id):
    seller = require_active_user(seller_id)
    item = Item.objects.filter(id=item_id).first()
    if not item:
        raise ApiError("Item not found", 404)
    if item.seller_id != seller.id:
        raise ApiError("You can only reserve your own listings", 403)
    buyer_ids = Conversation.objects.filter(item_id=item.id, seller_id=seller.id).values_list("buyer_id", flat=True).distinct()
    return [serialize_user(user) for user in User.objects.filter(id__in=list(buyer_ids)).order_by("username")]


def reserve_item(item_id, seller_id, buyer_id):
    seller = require_active_user(seller_id)
    buyer = require_active_user(buyer_id)
    item = Item.objects.filter(id=item_id).first()
    if not item:
        raise ApiError("Item not found", 404)
    if item.seller_id != seller.id:
        raise ApiError("You can only reserve your own listings", 403)
    if Purchase.objects.filter(
        item_id=item.id, payment_status="pending", order_stage="order_placed",
    ).exists():
        raise ApiError("This listing is reserved for an unpaid order", 409)
    if item.status == "sold" or item.stock <= 0:
        raise ApiError("Sold items cannot be reserved", 400)
    if not Conversation.objects.filter(item_id=item.id, seller_id=seller.id, buyer_id=buyer.id).exists():
        raise ApiError("Select a buyer who has messaged about this item", 422)
    item.status = "reserved"
    item.reserved_buyer_id = buyer.id
    item.reserved_buyer_username = buyer.username
    item.save(update_fields=["status", "reserved_buyer_id", "reserved_buyer_username"])
    conversation = Conversation.objects.filter(item_id=item.id, seller_id=seller.id, buyer_id=buyer.id).first()
    if conversation:
        Message.objects.create(
            conversation_id=conversation.id,
            sender_id=seller.id,
            receiver_id=buyer.id,
            body=f"{seller.username} reserved {item.name} for you. You can now proceed with checkout.",
            is_read=False,
        )
        conversation.save(update_fields=["updated_at"])
    notify_user(
        buyer.id,
        "Listing reserved",
        f"{seller.username} reserved {item.name} for you. You can now proceed with checkout.",
        "listing",
        seller,
    )
    return {"item": serialize_item(item), "message": f"{item.name} reserved for {buyer.username}."}


def update_item_seller_status(item_id, seller_id, status):
    seller = require_active_user(seller_id)
    item = Item.objects.filter(id=item_id).first()
    if not item:
        raise ApiError("Item not found", 404)
    if item.seller_id != seller.id:
        raise ApiError("You can only update your own listings", 403)
    if Purchase.objects.filter(
        item_id=item.id, payment_status="pending", order_stage="order_placed",
    ).exists():
        raise ApiError("Release the pending order before changing this listing's status", 409)

    if status == "available":
        if item.stock <= 0:
            raise ApiError("Add stock before marking this item available", 400)
        item.status = "available"
        item.reserved_buyer_id = None
        item.reserved_buyer_username = None
    elif status == "sold":
        item.status = "sold"
        item.stock = 0
        item.reserved_buyer_id = None
        item.reserved_buyer_username = None
    elif status == "hidden":
        item.status = "hidden"
        item.reserved_buyer_id = None
        item.reserved_buyer_username = None
    else:
        raise ApiError("Unsupported listing status", 422)

    item.save()
    return {"item": serialize_item(item), "message": "Listing status updated."}


PAYMENT_METHODS = {
    "mycash": "MyCash",
    "mpaisa": "M-PAiSA",
    "cash": "Cash",
    "visa": "VISA",
}

DEMO_CARD_APPROVED = "4242424242424242"
DEMO_CARD_INSUFFICIENT_FUNDS = "4000000000009995"
DEMO_WALLET_APPROVED_CODE = "123456"
DEMO_WALLET_INSUFFICIENT_FUNDS_CODE = "000000"

DELIVERY_METHODS = {
    "self_pickup": "Self Pickup",
    "delivery": "Delivery",
}

ORDER_STAGES = [
    "order_placed",
    "payment_confirmed",
    "preparing_item",
    "ready_for_collection",
    "item_received",
    "completed",
    "cancelled",
]

SELLER_ORDER_STAGES = {"preparing_item", "ready_for_collection"}


def simulate_payment_authorization(payment_method, payment_details, amount, force_failure=False):
    if payment_method not in PAYMENT_METHODS:
        raise ApiError("Select a valid payment method", 422)
    if force_failure:
        raise ApiError("Payment declined: simulated failure. No order was placed and stock was unchanged.", 402)

    payment_details = payment_details if isinstance(payment_details, dict) else {}
    if payment_method == "visa":
        cardholder = str(payment_details.get("cardholder_name", "")).strip()
        card_number = re.sub(r"\D", "", str(payment_details.get("card_number", "")))
        expiry = str(payment_details.get("expiry", "")).strip()
        security_code = str(payment_details.get("security_code", "")).strip()
        if not cardholder:
            raise ApiError("Enter the cardholder name", 422)
        if len(security_code) != 3 or not security_code.isdigit():
            raise ApiError("Enter the three-digit demo security code", 422)
        try:
            expiry_date = datetime.strptime(expiry, "%m/%y")
        except ValueError as exc:
            raise ApiError("Enter the card expiry as MM/YY", 422) from exc
        now = timezone.now()
        if (expiry_date.year, expiry_date.month) < (now.year, now.month):
            raise ApiError("The demo card has expired", 422)
        if card_number == DEMO_CARD_INSUFFICIENT_FUNDS:
            raise ApiError("Payment declined: insufficient funds. No order was placed and stock was unchanged.", 402)
        if card_number != DEMO_CARD_APPROVED:
            raise ApiError("Use one of the demo Visa card numbers shown at checkout. Real cards are not accepted.", 422)
    elif payment_method in {"mycash", "mpaisa"}:
        phone = re.sub(r"[ ()-]", "", str(payment_details.get("phone_number", "")).strip())
        authorization_code = str(payment_details.get("authorization_code", "")).strip()
        if not re.fullmatch(r"\+?\d{7,15}", phone):
            raise ApiError("Enter a valid demo mobile number", 422)
        if authorization_code == DEMO_WALLET_INSUFFICIENT_FUNDS_CODE:
            raise ApiError("Payment declined: insufficient funds. No order was placed and stock was unchanged.", 402)
        if authorization_code != DEMO_WALLET_APPROVED_CODE:
            raise ApiError("Enter the valid demo authorization code shown at checkout.", 422)

    return {
        "status": "approved",
        "provider": f"{PAYMENT_METHODS[payment_method]} demo processor",
        "reference": f"DEMO-{secrets.token_hex(6).upper()}",
        "amount": round(amount, 2),
        "message": "Payment recorded. Contact the seller to arrange meetup/collection.",
    }


def checkout_cart(buyer_id, data):
    if not buyer_id:
        raise ApiError("User not found", 404)

    payment_method = str(data.get("payment_method", "")).strip().lower()
    if payment_method not in PAYMENT_METHODS:
        raise ApiError("Select a valid payment method", 422)
    delivery_method = str(data.get("delivery_method", "")).strip().lower()
    if delivery_method not in DELIVERY_METHODS:
        raise ApiError("Select a valid delivery method", 422)
    requested_items = data.get("items")
    if not isinstance(requested_items, list) or not requested_items:
        raise ApiError("Your cart is empty", 422)

    item_quantities = {}
    for entry in requested_items:
        if not isinstance(entry, dict):
            raise ApiError("Invalid cart item", 422)
        try:
            item_id = int(entry.get("item_id"))
            quantity = int(entry.get("quantity"))
        except (TypeError, ValueError) as exc:
            raise ApiError("Cart item IDs and quantities must be whole numbers", 422) from exc
        if item_id <= 0 or quantity <= 0:
            raise ApiError("Cart item IDs and quantities must be positive", 422)
        if item_id in item_quantities:
            raise ApiError("Each item can only appear once in your cart", 422)
        item_quantities[item_id] = quantity
    if len(item_quantities) > 50:
        raise ApiError("A checkout can contain at most 50 items", 422)

    buyer = require_active_user(buyer_id)
    with transaction.atomic():
        locked_items = {
            item.id: item
            for item in Item.objects.select_for_update().filter(id__in=item_quantities).order_by("id")
        }
        if len(locked_items) != len(item_quantities):
            raise ApiError("One or more items are no longer available", 404)

        items_subtotal_cents = 0
        for item_id, quantity in item_quantities.items():
            item = locked_items[item_id]
            if Purchase.objects.filter(
                item_id=item_id,
                buyer_id=buyer.id,
                payment_status="pending",
                order_stage="order_placed",
            ).exists():
                raise ApiError(
                    f"Cancel the existing unpaid order for {item.name} before checking it out again",
                    409,
                )
            if item.status == "removed":
                raise ApiError(f"{item.name} is no longer available", 404)
            if item.seller_id == buyer.id:
                raise ApiError("You cannot purchase your own listing", 400)
            if item.status == "reserved" and item.reserved_buyer_id != buyer.id:
                raise ApiError(f"{item.name} is reserved for another buyer", 403)
            if item.status == "sold" or item.stock <= 0:
                raise ApiError(f"{item.name} is sold out", 400)
            if quantity > item.stock:
                raise ApiError(f"Only {item.stock} unit{' is' if item.stock == 1 else 's are'} available for {item.name}", 400)
            items_subtotal_cents += round(item.price * quantity * 100)

        delivery_fee_cents = 500 if delivery_method == "delivery" else 0
        total_cents = items_subtotal_cents + delivery_fee_cents
        payment = simulate_payment_authorization(
            payment_method,
            data.get("payment_details"),
            total_cents / 100,
            force_failure=data.get("force_failure") is True,
        )
        fee_per_item, fee_remainder = divmod(delivery_fee_cents, len(item_quantities))
        orders = []
        for index, (item_id, quantity) in enumerate(item_quantities.items()):
            item = locked_items[item_id]
            item_subtotal_cents = round(item.price * quantity * 100)
            item_delivery_fee_cents = fee_per_item + (1 if index < fee_remainder else 0)
            item_total_cents = item_subtotal_cents + item_delivery_fee_cents
            purchase_item(
                item_id,
                buyer.id,
                payment_method,
                delivery_method,
                quantity,
                item_delivery_fee_cents / 100,
                item_subtotal_cents / 100,
                0,
                item_total_cents / 100,
                payment_confirmed=True,
                payment_status=payment["status"],
                payment_reference=payment["reference"],
            )
            purchase = Purchase.objects.filter(buyer_id=buyer.id, item_id=item_id).latest("id")
            orders.append(enrich_purchase_order(purchase))

    return {
        "orders": orders,
        "payment": {
            **payment,
            "method": payment_method,
            "amount": round(total_cents / 100, 2),
        },
        "total": round(total_cents / 100, 2),
    }


def purchase_item(
    item_id,
    buyer_id,
    payment_method="cash",
    delivery_method="self_pickup",
    quantity=1,
    delivery_fee=0,
    subtotal=None,
    included_tax_amount=None,
    final_total=None,
    payment_confirmed=None,
    payment_status=None,
    payment_reference="",
):
    if not buyer_id:
        raise ApiError("User not found", 404)

    delivery_method_key = str(delivery_method or "").strip().lower()
    if delivery_method_key not in DELIVERY_METHODS:
        raise ApiError("Select a valid delivery method", 422)
    try:
        requested_quantity = int(quantity or 1)
    except (TypeError, ValueError) as exc:
        raise ApiError("Quantity must be a whole number", 422) from exc
    if requested_quantity < 1:
        raise ApiError("Quantity must be at least 1", 422)

    buyer = require_active_user(buyer_id)
    item = Item.objects.filter(id=item_id).first()
    if not item or item.status == "removed":
        raise ApiError("Item not found", 404)
    payment_method_key = str(payment_method or "").strip().lower()
    if payment_method_key not in PAYMENT_METHODS:
        raise ApiError("Select a valid payment method", 422)
    if item.seller_id == buyer.id:
        raise ApiError("You cannot purchase your own listing", 400)
    if item.status == "reserved" and item.reserved_buyer_id != buyer.id:
        raise ApiError("This item is reserved for another buyer", 403)
    if item.stock <= 0 or item.status == "sold":
        item.stock = 0
        item.status = "sold"
        item.save()
        raise ApiError("Item is sold out", 400)
    if requested_quantity > item.stock:
        raise ApiError(f"Only {item.stock} unit{' is' if item.stock == 1 else 's are'} available", 400)

    if payment_confirmed is None:
        payment_confirmed = False
    awaiting_payment = payment_confirmed is False
    was_reserved = item.status == "reserved"
    if awaiting_payment:
        item.status = "reserved"
        item.reserved_buyer_id = buyer.id
        item.reserved_buyer_username = buyer.username
    else:
        item.stock -= requested_quantity
        item.status = "sold" if was_reserved or item.stock <= 0 else item_status(item.stock)
    if item.status == "sold":
        item.reserved_buyer_id = None
        item.reserved_buyer_username = None
    item.save()
    item_subtotal = float(subtotal if subtotal is not None else item.price * requested_quantity)
    item_delivery_fee = float(delivery_fee or 0)
    item_tax_amount = float(included_tax_amount if included_tax_amount is not None else 0)
    item_final_total = float(final_total if final_total is not None else item_subtotal + item_delivery_fee)
    if payment_status is None:
        payment_status = "paid" if payment_confirmed else "pending"
    purchase = Purchase.objects.create(
        buyer_id=buyer.id,
        buyer_username=buyer.username,
        item_id=item.id,
        item_name=item.name,
        price=item.price,
        category=item.category,
        seller_id=item.seller_id,
        seller_username=item.seller_username,
        seller_contact=item.contact,
        quantity=requested_quantity,
        total_amount=item_final_total,
        payment_method=payment_method_key,
        delivery_method=delivery_method_key,
        delivery_fee=item_delivery_fee,
        subtotal=item_subtotal,
        included_tax_amount=item_tax_amount,
        final_total=item_final_total,
        status="in_progress",
        order_stage="payment_confirmed" if payment_confirmed else "order_placed",
        payment_status=payment_status,
        payment_reference=payment_reference,
    )
    notify_order_user(
        purchase,
        buyer.id,
        "Order confirmed" if payment_confirmed else "Order placed — payment due",
        (
            f"Your order for {item.name} is confirmed. Payment method: {PAYMENT_METHODS[payment_method_key]}."
            if payment_confirmed
            else f"Your order for {item.name} is placed. Pay the seller directly by {PAYMENT_METHODS[payment_method_key]}."
        ),
        buyer,
    )
    notify_user(
        item.seller_id,
        "New order placed",
        f"{buyer.username} placed an order for {item.name}.",
        "sale",
        buyer,
    )
    return serialize_admin_item(item)


def list_buyer_purchases(buyer_id):
    if not User.objects.filter(id=buyer_id).exists():
        raise ApiError("User not found", 404)
    purchases = visible_purchases(include_test_records=True).filter(buyer_id=buyer_id).order_by("-id")
    return [enrich_purchase_order(purchase) for purchase in purchases]


def enrich_purchase_order(purchase):
    data = serialize_purchase(purchase)
    review = RatingReview.objects.filter(purchase_id=purchase.id, reviewer_id=purchase.buyer_id).first()
    data["has_review"] = bool(review)
    if review:
        data["review"] = serialize_rating_review(review)
    return data


def list_seller_orders(seller_id):
    seller = require_active_user(seller_id)
    purchases = visible_purchases(include_test_records=True).filter(seller_id=seller.id).order_by("-id")
    return [enrich_purchase_order(purchase) for purchase in purchases]


def update_seller_order_stage(purchase_id, seller_id, stage):
    seller = require_active_user(seller_id)
    stage = str(stage or "").strip().lower()
    if stage not in SELLER_ORDER_STAGES:
        raise ApiError("Seller can only set Preparing Item or Ready for Collection", 422)

    purchase = Purchase.objects.filter(id=purchase_id).first()
    if not purchase:
        raise ApiError("Order not found", 404)
    if purchase.seller_id != seller.id:
        raise ApiError("You can only update your own orders", 403)
    if purchase.payment_status == "pending" and purchase.order_stage == "order_placed":
        raise ApiError("Confirm payment receipt before preparing this order", 400)
    if purchase.order_stage in {"item_received", "completed"}:
        raise ApiError("This order has already been received by the buyer", 400)
    if stage == "ready_for_collection" and purchase.order_stage not in {"preparing_item", "ready_for_collection"}:
        raise ApiError("Mark the order as preparing before setting it ready for collection", 400)

    purchase.order_stage = stage
    purchase.status = "in_progress"
    purchase.save(update_fields=["order_stage", "status", "updated_at"])
    if stage == "ready_for_collection":
        notify_order_user(
            purchase,
            purchase.buyer_id,
            "Order ready for meetup",
            f"{purchase.item_name} is ready for meetup or collection.",
            seller,
        )
    elif stage == "preparing_item":
        notify_order_user(
            purchase,
            purchase.buyer_id,
            "Order confirmed by seller",
            f"{seller.username} is preparing {purchase.item_name}.",
            seller,
        )
    return enrich_purchase_order(purchase)


def confirm_payment_received(purchase_id, seller_id):
    seller = require_active_user(seller_id)
    with transaction.atomic():
        purchase = Purchase.objects.select_for_update().filter(id=purchase_id).first()
        if not purchase:
            raise ApiError("Order not found", 404)
        if purchase.seller_id != seller.id:
            raise ApiError("You can only confirm payment for your own orders", 403)
        if purchase.payment_status != "pending" or purchase.order_stage != "order_placed":
            raise ApiError("This order is not awaiting payment", 400)

        item = Item.objects.select_for_update().filter(id=purchase.item_id).first()
        if not item or item.status != "reserved" or item.reserved_buyer_id != purchase.buyer_id:
            raise ApiError("The listing reservation no longer matches this order", 409)
        if item.stock < purchase.quantity:
            raise ApiError("The reserved stock is no longer available", 409)

        item.stock -= purchase.quantity
        item.status = "sold" if item.stock <= 0 else item_status(item.stock)
        item.reserved_buyer_id = None
        item.reserved_buyer_username = None
        item.save(update_fields=["stock", "status", "reserved_buyer_id", "reserved_buyer_username"])

        purchase.payment_status = "paid"
        purchase.payment_reference = f"SELLER-CONFIRMED-{purchase.id}"
        purchase.order_stage = "payment_confirmed"
        purchase.status = "in_progress"
        purchase.save(update_fields=[
            "payment_status",
            "payment_reference",
            "order_stage",
            "status",
            "updated_at",
        ])

    notify_order_user(
        purchase,
        purchase.buyer_id,
        "Payment received",
        f"{seller.username} confirmed receiving ${purchase.total_amount:.2f} for {purchase.item_name}.",
        seller,
    )
    return enrich_purchase_order(purchase)


confirm_cash_payment = confirm_payment_received


def cancel_order(purchase_id, user_id):
    user = require_active_user(user_id)
    with transaction.atomic():
        purchase = Purchase.objects.select_for_update().filter(id=purchase_id).first()
        if not purchase:
            raise ApiError("Order not found", 404)
        if user.id not in {purchase.buyer_id, purchase.seller_id}:
            raise ApiError("You can only cancel orders you are part of", 403)
        if purchase.order_stage == "completed" or purchase.status == "completed":
            raise ApiError("Completed orders cannot be cancelled", 400)
        if purchase.order_stage in {"cancelled", "canceled"} or purchase.status in {"cancelled", "canceled"}:
            return enrich_purchase_order(purchase)

        if purchase.payment_status == "paid":
            raise ApiError("Payment has already been recorded as received. Arrange any refund directly with the buyer before changing this order.", 400)

        awaiting_payment = purchase.payment_status == "pending" or (
            not purchase.payment_status and purchase.order_stage == "order_placed"
        )
        purchase.order_stage = "cancelled"
        purchase.status = "cancelled"
        purchase.payment_status = "cancelled"
        purchase.save(update_fields=["order_stage", "status", "payment_status", "updated_at"])

        item = Item.objects.select_for_update().filter(id=purchase.item_id).first()
        if item and item.status != "removed":
            if not awaiting_payment:
                item.stock = max(0, item.stock) + (purchase.quantity or 1)
            item.status = item_status(item.stock)
            if item.reserved_buyer_id == purchase.buyer_id:
                item.reserved_buyer_id = None
                item.reserved_buyer_username = None
            item.save(update_fields=["stock", "status", "reserved_buyer_id", "reserved_buyer_username"])

    cancelled_by = "buyer" if user.id == purchase.buyer_id else "seller"
    notify_order_user(
        purchase,
        purchase.buyer_id,
        "Order cancelled",
        f"Your order for {purchase.item_name} was cancelled by the {cancelled_by}.",
        user,
    )
    notify_order_user(
        purchase,
        purchase.seller_id,
        "Order cancelled",
        f"Order #{purchase.id} for {purchase.item_name} was cancelled by {user.username}.",
        user,
    )
    return enrich_purchase_order(purchase)


def confirm_order_received(purchase_id, buyer_id):
    buyer = require_active_user(buyer_id)
    purchase = Purchase.objects.filter(id=purchase_id).first()
    if not purchase:
        raise ApiError("Order not found", 404)
    if purchase.buyer_id != buyer.id:
        raise ApiError("You can only confirm your own orders", 403)
    if purchase.order_stage not in {"ready_for_collection", "item_received", "completed"}:
        raise ApiError("This order is not ready for collection yet", 400)

    purchase.order_stage = "completed"
    purchase.status = "completed"
    purchase.save(update_fields=["order_stage", "status", "updated_at"])
    notify_order_user(
        purchase,
        buyer.id,
        "Order completed",
        f"Your order for {purchase.item_name} is complete.",
        buyer,
    )
    notify_order_user(
        purchase,
        purchase.seller_id,
        "Order completed",
        f"{buyer.username} confirmed receiving {purchase.item_name}.",
        buyer,
    )
    return enrich_purchase_order(purchase)


def dashboard(admin_id):
    require_admin(admin_id)
    today = date.today()
    purchases = list(visible_purchases().order_by("-id"))
    counted_purchases = [
        purchase
        for purchase in purchases
        if purchase.status not in {"cancelled", "canceled"} and purchase.order_stage not in {"cancelled", "canceled"}
        and purchase.payment_status != "pending"
    ]
    total_sales = sum(purchase.total_amount or purchase.price for purchase in counted_purchases)
    todays_sales = sum(
        purchase.total_amount or purchase.price
        for purchase in counted_purchases
        if purchase.purchased_at and purchase.purchased_at.date() == today
    )
    return {
        "total_students": User.objects.filter(role="student").count(),
        "total_active_listings": visible_items().filter(status="available").count(),
        "total_orders": len(purchases),
        "total_sales": total_sales,
        "todays_sales": todays_sales,
        "recent_orders": [serialize_admin_purchase(purchase) for purchase in purchases[:5]],
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

    if status == "suspended":
        subject = "Your USP Marketplace account has been suspended"
        message = (
            f"Hello {student.username},\n\n"
            "Your USP Marketplace account has been suspended by an administrator. "
            "You will not be able to use marketplace features while your account is suspended.\n\n"
            "If you believe this was a mistake, please contact the USP Marketplace admin team."
        )
        notification = "Suspension email sent to the student."
    else:
        subject = "Your USP Marketplace account has been reactivated"
        message = (
            f"Hello {student.username},\n\n"
            "Your USP Marketplace account has been reactivated by an administrator. "
            "You can now sign in and use marketplace features again.\n\n"
            "Thank you for using USP Marketplace."
        )
        notification = "Reactivation email sent to the student."

    send_email(subject, message, student.email)
    notify_user(
        student.id,
        "Account suspended" if status == "suspended" else "Account reactivated",
        "Your USP Marketplace account has been suspended by an administrator."
        if status == "suspended"
        else "Your USP Marketplace account has been reactivated by an administrator.",
        "administration",
    )
    return {
        "user": serialize_user(student),
        "message": notification,
        "email_sent": True,
    }


def delete_student(admin_id, student_id):
    require_admin(admin_id)
    student = find_student(student_id)
    if not student:
        raise ApiError("Student not found", 404)

    username = student.username
    email = student.email
    Item.objects.filter(seller_id=student.id).delete()
    PendingRegistration.objects.filter(email__iexact=email).delete()
    student.delete()
    return {"message": f"{username} was permanently deleted."}


def list_admin_notifications(admin_id):
    require_admin(admin_id)
    notifications = AdminNotification.objects.order_by("-id")[:30]
    return [serialize_admin_notification(notification) for notification in notifications]


def mark_admin_notification_viewed(admin_id, notification_id):
    require_admin(admin_id)
    notification = AdminNotification.objects.filter(id=notification_id).first()
    if not notification:
        raise ApiError("Notification not found", 404)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return serialize_admin_notification(notification)


def delete_admin_notification(admin_id, notification_id):
    require_admin(admin_id)
    deleted, _ = AdminNotification.objects.filter(id=notification_id).delete()
    if not deleted:
        raise ApiError("Notification not found", 404)
    return {"message": "Notification removed."}


def list_user_notifications(user_id):
    user = User.objects.filter(id=user_id).first()
    if not user:
        raise ApiError("User not found", 404)
    notifications = UserNotification.objects.filter(user_id=user.id).order_by("-id")[:30]
    return [serialize_notification(notification) for notification in notifications]


def mark_user_notification_viewed(user_id, notification_id):
    user = User.objects.filter(id=user_id).first()
    if not user:
        raise ApiError("User not found", 404)
    notification = UserNotification.objects.filter(id=notification_id, user_id=user.id).first()
    if not notification:
        raise ApiError("Notification not found", 404)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return serialize_notification(notification)


def delete_user_notification(user_id, notification_id):
    user = User.objects.filter(id=user_id).first()
    if not user:
        raise ApiError("User not found", 404)
    deleted, _ = UserNotification.objects.filter(id=notification_id, user_id=user.id).delete()
    if not deleted:
        raise ApiError("Notification not found", 404)
    return {"message": "Notification removed."}


def submit_user_report(data):
    reporter = require_active_user(data.get("reporter_id"))
    target_type = str(data.get("target_type", "")).strip().lower()
    reason = str(data.get("reason", "")).strip()

    if target_type not in {"listing", "user"}:
        raise ApiError("Report target must be listing or user", 422)
    if len(reason) < 8:
        raise ApiError("Report reason must be at least 8 characters long", 422)

    target_id = data.get("target_id")
    target_label = str(data.get("target_label", "")).strip()
    if target_type == "listing":
        item = Item.objects.filter(id=target_id).first()
        if not item:
            raise ApiError("Listing not found", 404)
        target_label = item.name
        target_id = item.id
    elif target_id:
        target_user = User.objects.filter(id=target_id).first()
        if target_user:
            target_label = target_user.username

    if not target_label:
        raise ApiError("Report target is required", 422)

    report_record = UserReport.objects.create(
        reporter_id=reporter.id,
        reporter_username=reporter.username,
        target_type=target_type,
        target_id=target_id or None,
        target_label=target_label,
        reason=reason,
    )
    notify_admin(
        "New user report",
        f"{reporter.username} reported {target_type} '{target_label}'.",
        "report",
        reporter,
    )
    return {"report": serialize_user_report(report_record), "message": "Report submitted to admin."}


def submit_rating_review(data):
    reviewer = require_active_user(data.get("reviewer_id"))
    purchase = None
    if data.get("purchase_id"):
        purchase = Purchase.objects.filter(id=data.get("purchase_id")).first()
        if not purchase:
            raise ApiError("Order not found", 404)
        if purchase.buyer_id != reviewer.id:
            raise ApiError("Only the buyer who purchased this item can review this order", 403)
        if RatingReview.objects.filter(purchase_id=purchase.id, reviewer_id=reviewer.id).exists():
            raise ApiError("You have already reviewed this order", 400)
        item_id = purchase.item_id
        item_name = purchase.item_name
        seller_id = purchase.seller_id
        seller_username = purchase.seller_username
    else:
        item = Item.objects.filter(id=data.get("item_id")).first()
        if not item:
            raise ApiError("Listing not found", 404)
        item_id = item.id
        item_name = item.name
        seller_id = item.seller_id
        seller_username = item.seller_username

    if seller_id == reviewer.id:
        raise ApiError("You cannot review your own listing", 400)

    try:
        rating = int(data.get("rating"))
    except (TypeError, ValueError) as exc:
        raise ApiError("Rating must be a number from 1 to 5", 422) from exc
    if rating < 1 or rating > 5:
        raise ApiError("Rating must be from 1 to 5", 422)

    review_text = str(data.get("review", "")).strip()
    if len(review_text) < 5:
        raise ApiError("Review must be at least 5 characters long", 422)

    review_record = RatingReview.objects.create(
        purchase_id=purchase.id if purchase else None,
        reviewer_id=reviewer.id,
        reviewer_username=reviewer.username,
        item_id=item_id,
        item_name=item_name,
        seller_id=seller_id,
        seller_username=seller_username,
        rating=rating,
        review=review_text,
    )
    return {"review": serialize_rating_review(review_record), "message": "Rating and review submitted."}


def list_seller_reviews(seller_id):
    seller = require_active_user(seller_id)
    reviews = list(RatingReview.objects.filter(seller_id=seller.id).order_by("-id"))
    serialized_reviews = [serialize_rating_review(review_record) for review_record in reviews]
    average_rating = (
        round(sum(review_record.rating for review_record in reviews) / len(serialized_reviews), 1)
        if serialized_reviews
        else 0
    )
    return {
        "seller": {
            "id": seller.id,
            "username": seller.username,
            "name": seller.name or seller.username,
        },
        "average_rating": average_rating,
        "review_count": len(serialized_reviews),
        "reviews": serialized_reviews,
    }


def list_user_reports(admin_id):
    require_admin(admin_id)
    reports = []
    for report_record in UserReport.objects.exclude(reporter_username__startswith="__test_").order_by("-id"):
        serialized_report = serialize_user_report(report_record)
        if report_record.target_type == "listing" and report_record.target_id:
            item = Item.objects.filter(id=report_record.target_id).first()
            if item:
                serialized_report["target_item"] = serialize_admin_item(item)
                seller = User.objects.filter(id=item.seller_id).first()
                if seller:
                    serialized_report["seller"] = serialize_user(seller)
        elif report_record.target_type == "user" and report_record.target_id:
            seller = User.objects.filter(id=report_record.target_id).first()
            if seller:
                serialized_report["seller"] = serialize_user(seller)
        reporter = User.objects.filter(id=report_record.reporter_id).first()
        if reporter:
            serialized_report["reporter"] = serialize_user(reporter)
        reports.append(serialized_report)
    return reports


def list_rating_reviews(admin_id):
    require_admin(admin_id)
    return [serialize_admin_review(review_record) for review_record in RatingReview.objects.order_by("-id")]


def list_admin_items(admin_id, search=""):
    require_admin(admin_id)
    query = visible_items()
    if search:
        query = query.filter(
            Q(name__contains=search)
            | Q(category__contains=search)
            | Q(seller_username__contains=search)
        )
    return [serialize_admin_item(item) for item in query.order_by("-id")]


def hide_listing(admin_id, item_id, reason):
    require_admin(admin_id)
    item = Item.objects.filter(id=item_id).first()
    if not item:
        raise ApiError("Item not found", 404)
    item.status = "hidden"
    item.removed_reason = reason
    item.save()
    notify_user(
        item.seller_id,
        "Listing hidden",
        f"An administrator hid your listing '{item.name}'. Reason: {reason or 'No reason provided'}.",
        "administration",
    )
    return serialize_admin_item(item)


def remove_listing(admin_id, item_id, reason):
    require_admin(admin_id)
    item = Item.objects.filter(id=item_id).first()
    if not item:
        raise ApiError("Item not found", 404)
    item.status = "removed"
    item.removed_reason = reason
    item.save()
    notify_user(
        item.seller_id,
        "Listing removed",
        f"An administrator removed your listing '{item.name}'. Reason: {reason or 'No reason provided'}.",
        "administration",
    )
    return serialize_admin_item(item)


def restore_listing(admin_id, item_id):
    require_admin(admin_id)
    item = Item.objects.filter(id=item_id).first()
    if not item:
        raise ApiError("Item not found", 404)
    item.status = item_status(item.stock)
    item.removed_reason = None
    item.save()
    notify_user(
        item.seller_id,
        "Listing restored",
        f"An administrator restored your listing '{item.name}'.",
        "administration",
    )
    return serialize_admin_item(item)


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

    return [serialize_admin_purchase(order) for order in orders]


def report(admin_id, period="daily"):
    require_admin(admin_id)
    grouped = defaultdict(lambda: {"orders": 0, "items_sold": 0, "total_sales": 0})

    for purchase in visible_purchases().order_by("-purchased_at"):
        if purchase.status in {"cancelled", "canceled"} or purchase.order_stage in {"cancelled", "canceled"}:
            continue
        if purchase.payment_status == "pending":
            continue
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
