import hashlib
import base64
import logging
import smtplib
from io import BytesIO
import json
import math
import secrets
import re
import ssl
import pyotp
import qrcode
from threading import Thread
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from collections import defaultdict
from datetime import date, timedelta

from django.core.mail import BadHeaderError, send_mail
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings
from django.db import DatabaseError, OperationalError, connection, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date
# FUTURE MICROSOFT ENTRA INTEGRATION:
# import jwt
# from jwt import PyJWKClient

from .account_status import restore_expired_suspension, suspension_error
from .constants import ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_USERNAME
from .category_catalog import DEFAULT_CATEGORY_NAMES, canonical_category_name, builtin_category_options
from .exceptions import ApiError
from .authentication import issue_token, token_user
from .models import AdminNotification, Category, Conversation, EmailVerification, Item, Message, PasswordReset, PendingRegistration, Purchase, RatingReview, User, UserNotification, UserReport
from .queries import reservation_stock, purchasable_stock, find_student, find_user_by_login, item_status, public_items, visible_items, visible_purchases, available_seller_items
from .serializers import serialize_category, serialize_conversation, serialize_item, serialize_item_for_user, serialize_message, serialize_notification, serialize_purchase, serialize_rating_review, serialize_user, serialize_user_report
from .validators import is_usp_student_email, validate_item_payload, validate_signup, whole_number

logger = logging.getLogger(__name__)


email_logger = logging.getLogger("marketplace.email")
VERIFICATION_CODE_TTL = timedelta(minutes=10)
VERIFICATION_RESEND_COOLDOWN = timedelta(minutes=1)
PENDING_REGISTRATIONS = {}
CATEGORY_TABLE_READY = False


def hash_password(password):
    return make_password(password)


def require_active_user(user_id):
    user = User.objects.filter(id=user_id).first()
    if not user:
        raise ApiError("User not found", 404)
    restore_expired_suspension(user)
    if user.status == "suspended":
        raise suspension_error(user)
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
        if not check_password(ADMIN_PASSWORD, admin_user.password_hash):
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
        restore_expired_suspension(seller)
        data["seller"] = serialize_user(seller, include_moderation=True)
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
        f"Return to USP Marketplace to enter your code: {settings.FRONTEND_URL}\n\n"
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


def require_resend_settings(failure_prefix="Failed to send email"):
    missing = [name for name in ("RESEND_API_KEY", "RESEND_FROM_EMAIL") if not getattr(settings, name, "").strip()]
    if missing:
        raise ApiError(f"{failure_prefix}: Set {', '.join(missing)} in the environment for Resend HTTPS delivery.", 500)


def send_email(subject, message, recipient, failure_prefix="Failed to send email"):
    use_smtp = settings.EMAIL_PROVIDER == "smtp" or (
        settings.EMAIL_PROVIDER == "auto" and bool(settings.EMAIL_HOST)
    )
    if use_smtp:
        if not settings.EMAIL_HOST:
            raise ApiError(f"{failure_prefix}: EMAIL_PROVIDER=smtp requires EMAIL_HOST in backend/.env", 500)
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
            if isinstance(exc, smtplib.SMTPAuthenticationError) and settings.EMAIL_HOST == "smtp.gmail.com":
                public_detail = "Gmail rejected the SMTP login. Check EMAIL_HOST_USER and use a current 16-character Google App Password for EMAIL_HOST_PASSWORD."
            else:
                public_detail = f"SMTP email delivery failed ({type(exc).__name__}). Check the backend terminal for details."
            raise ApiError(public_detail, 502) from exc
        if sent_count != 1:
            detail = "SMTP backend did not report a sent message. Check provider logs and sender verification."
            email_logger.error("[email-debug] SMTP/email sending failed for %s: %s", recipient, detail)
            raise ApiError(f"{failure_prefix}: {detail}", 502)
        email_logger.info("[email-debug] Email sent successfully to %s", recipient)
        return

    use_resend = settings.EMAIL_PROVIDER == "resend" or (
        settings.EMAIL_PROVIDER == "auto" and bool(settings.RESEND_API_KEY)
    )
    if use_resend:
        require_resend_settings(failure_prefix)
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
                "User-Agent": "USPMarketplace/1.0",
            },
            method="POST",
        )
        try:
            email_logger.info("[email-debug] Resend API sending stage: from=%s recipient=%s", settings.RESEND_FROM_EMAIL, recipient)
            with urlopen(request, timeout=settings.EMAIL_TIMEOUT) as response:
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
            detail = str(provider_error or f"HTTP {exc.code} from email provider").replace(settings.RESEND_API_KEY, "[redacted]")
            email_logger.exception("[email-debug] Resend/email sending failed for %s: %s", recipient, detail)
            raise ApiError(f"{failure_prefix}: Resend error: {detail}", 502) from exc
        except (URLError, TimeoutError) as exc:
            email_logger.exception("[email-debug] Resend/email sending failed for %s", recipient)
            raise ApiError(f"{failure_prefix}: Unable to connect to Resend. Check your network connection.", 502) from exc
        email_logger.info("[email-debug] Email sent successfully to %s", recipient)
        return

    if settings.EMAIL_PROVIDER == "console" or settings.EMAIL_BACKEND == settings.CONSOLE_EMAIL_BACKEND:
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [recipient])
        except (smtplib.SMTPException, OSError) as exc:
            raise ApiError(
                f"{failure_prefix}: Unable to send email. Check the email settings in backend/.env.",
                502,
            ) from exc
        return

    email_logger.error("[email-debug] No SMTP provider configured for %s", recipient)
    raise ApiError(f"{failure_prefix}: Email is not configured. Set EMAIL_PROVIDER=smtp with SMTP settings, EMAIL_PROVIDER=resend with RESEND_API_KEY, or EMAIL_PROVIDER=console for local testing.", 500)


def send_email_later(subject, message, recipient, failure_prefix="Failed to send email"):
    def send_background_email():
        try:
            send_email(subject, message, recipient, failure_prefix)
        except Exception as exc:
            email_logger.warning("%s: %s", failure_prefix, describe_email_exception(exc))

    Thread(target=send_background_email, daemon=True).start()


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
            raise ApiError("Email already verified. Please sign in with your password.", 409)
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
        "user": serialize_user(user),
        "authenticator_setup_offer": True,
        "user_id": user.id,
        "login_challenge": issue_token(user, "mfa"),
        "access_token": issue_token(user),
        **authenticator_setup(user.authenticator_secret, user.email),
        "message": "Email verified successfully.",
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
            f"Your USP Marketplace password reset code is {code}. It expires in 10 minutes.\n\n"
            f"Return to USP Marketplace to enter your code: {settings.FRONTEND_URL}",
            user.email,
        )
    return {"message": "If that email is registered, a password reset code has been sent."}


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

    if ADMIN_PASSWORD and login_name.lower() == ADMIN_EMAIL.lower() and secrets.compare_digest(password, ADMIN_PASSWORD):
        admin_user = get_or_create_admin_user()
        return {"user": serialize_user(admin_user), "access_token": issue_token(admin_user), "message": "Admin login successful"}

    user = find_user_by_login(login_name)
    if user and user.role == "admin" and not settings.DEBUG and password == "Admin12345":
        raise ApiError("Replace the development administrator password before production login", 403)
    legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    legacy_match = bool(user and secrets.compare_digest(user.password_hash, legacy_hash))
    if not user or not (legacy_match or check_password(password, user.password_hash)):
        raise ApiError("Invalid username or password", 401)
    if user.status == "pending_verification":
        raise ApiError("Please verify your email before logging in", 403)
    restore_expired_suspension(user)
    if user.status == "suspended":
        raise suspension_error(user)
    if legacy_match:
        user.password_hash = hash_password(password)
        user.save(update_fields=["password_hash"])
    if not user.authenticator_secret or not user.authenticator_enabled:
        user.authenticator_secret = pyotp.random_base32()
        user.save(update_fields=["authenticator_secret"])
        return {
            "user": serialize_user(user),
            "authenticator_setup_offer": True,
            "user_id": user.id,
            "login_challenge": issue_token(user, "mfa"),
            "access_token": issue_token(user),
            "username": user.username,
            **authenticator_setup(user.authenticator_secret, user.email),
            "message": "Login successful.",
        }
    return {
        "authenticator_required": True,
        "user_id": user.id,
        "login_challenge": issue_token(user, "mfa"),
        "message": "Enter the code from Microsoft Authenticator",
    }


def verify_authenticator(data):
    user_id = data.get("user_id")
    code = str(data.get("code", "")).strip().replace(" ", "")
    user = token_user(data.get("login_challenge", ""), "mfa")
    if str(user.id) != str(user_id):
        raise ApiError("Login challenge does not match this account", 401)
    if not user or not user.authenticator_secret:
        raise ApiError("Authenticator setup is not available for this account", 400)
    if not code.isdigit() or len(code) != 6 or not pyotp.TOTP(user.authenticator_secret).verify(code, valid_window=1):
        raise ApiError("Incorrect Microsoft Authenticator code", 401)
    if not user.authenticator_enabled:
        user.authenticator_enabled = True
        user.save(update_fields=["authenticator_enabled"])
    return {"user": serialize_user(user), "access_token": issue_token(user), "message": "Login successful"}


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
    if not re.match("^s\\d+@(?:[a-z0-9-]+\\.)*usp\\.ac\\.fj$", email):
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


def visible_to_buyer(item, requesting_user_id):
    data = serialize_item_for_user(item, requesting_user_id)
    if data["available_stock"] > 0 or data["reserved_for_you"] or str(item.seller_id) == str(requesting_user_id):
        return data
    return None


def list_items(requesting_user_id=None):
    return [data for item in public_items().order_by("-id")
            if (data := visible_to_buyer(item, requesting_user_id)) is not None]


def ensure_category_table():
    global CATEGORY_TABLE_READY
    if CATEGORY_TABLE_READY:
        return
    try:
        if Category._meta.db_table not in connection.introspection.table_names():
            with connection.schema_editor() as schema_editor:
                schema_editor.create_model(Category)
        CATEGORY_TABLE_READY = True
    except (DatabaseError, OperationalError) as exc:
        logger.warning("Could not ensure categories table: %s", exc)


def list_categories():
    ensure_category_table()
    options = builtin_category_options()
    names = set(DEFAULT_CATEGORY_NAMES)
    for category in Category.objects.order_by("name"):
        name = canonical_category_name(category.name)
        if name.casefold() not in names:
            options.append({**serialize_category(category), "name": name, "built_in": False})
            names.add(name.casefold())
    return [option for option in options if option["name"] != "Other"] + [option for option in options if option["name"] == "Other"]


def create_category(admin_id, data):
    require_admin(admin_id)
    ensure_category_table()
    name = canonical_category_name(data.get("name"))
    image = str(data.get("image") or "").strip()
    icon = str(data.get("icon") or "More").strip()[:32] or "More"

    if not name:
        raise ApiError("Category name is required", 400)
    if len(name) > 64:
        raise ApiError("Category name must be 64 characters or fewer", 400)
    if name.lower() in DEFAULT_CATEGORY_NAMES or Category.objects.filter(name__iexact=name).exists():
        raise ApiError("Category already exists", 409)
    if image and not image.startswith("data:image/"):
        raise ApiError("Category image must be an uploaded image file", 400)

    category = Category.objects.create(name=name, icon=icon, image=image or None)
    notify_admin("Category added", f"{name} was added as a marketplace category.", "category")
    return serialize_category(category)


@transaction.atomic
def update_category(admin_id, category_id, data):
    require_admin(admin_id)
    ensure_category_table()
    category = Category.objects.select_for_update().filter(id=category_id).first()
    if not category:
        raise ApiError("Category not found", 404)

    if canonical_category_name(category.name).casefold() in DEFAULT_CATEGORY_NAMES:
        raise ApiError("Built-in categories cannot be edited", 403)

    name = canonical_category_name(data.get("name"))
    image = str(data.get("image") or "").strip()
    icon = str(data.get("icon") or category.icon or "More").strip()[:32] or "More"

    if not name:
        raise ApiError("Category name is required", 400)
    if len(name) > 64:
        raise ApiError("Category name must be 64 characters or fewer", 400)
    if name.lower() in DEFAULT_CATEGORY_NAMES:
        raise ApiError("Category already exists", 409)
    if Category.objects.filter(name__iexact=name).exclude(id=category.id).exists():
        raise ApiError("Category already exists", 409)
    if image and not image.startswith("data:image/"):
        raise ApiError("Category image must be an uploaded image file", 400)

    old_name = category.name
    category.name = name
    category.icon = icon
    category.image = image or None
    category.save(update_fields=["name", "icon", "image"])
    if old_name != name:
        Item.objects.filter(category__iexact=old_name).update(category=name)
    return serialize_category(category)


@transaction.atomic
def delete_category(admin_id, category_id):
    require_admin(admin_id)
    ensure_category_table()
    category = Category.objects.select_for_update().filter(id=category_id).first()
    if not category:
        raise ApiError("Category not found", 404)
    if canonical_category_name(category.name).casefold() in DEFAULT_CATEGORY_NAMES:
        raise ApiError("Built-in categories cannot be deleted", 403)
    if Item.objects.filter(category__iexact=category.name).exists():
        raise ApiError("Move this category's listings to another category before deleting it", 409)
    name = category.name
    category.delete()
    notify_admin("Category deleted", f"{name} was removed from marketplace categories.", "category")
    return {"message": "Category deleted.", "id": category_id, "name": name}


def list_seller_items(seller_id, requesting_user_id=None):
    seller = User.objects.filter(id=seller_id).first()
    if not seller:
        raise ApiError("User not found", 404)
    restore_expired_suspension(seller)
    if seller.status == "suspended":
        return []
    items = visible_items().filter(seller_id=seller.id).exclude(status="removed").order_by("-id")
    if str(requesting_user_id) != str(seller.id):
        items = items.filter(status__in=["available", "reserved"], stock__gt=0)
    result = []
    for item in items:
        data = serialize_item_for_user(item, requesting_user_id) if str(requesting_user_id) == str(seller.id) else visible_to_buyer(item, requesting_user_id)
        if data is not None:
            result.append(data)
    return result


def create_item(data):
    validate_item_payload(data)
    data = normalize_listing_fields(data)
    seller = require_active_user(data.get("seller_id"))
    stock = int(data["stock"])

    item = Item.objects.create(
        name=data["name"],
        price=float(data["price"]),
        description=data["description"],
        category=data["category"],
        contact=data["contact"],
        payment_method=str(data.get("payment_method", "cash")).strip().lower(),
        payment_number=(
            str(data.get("payment_number", "")).strip()
            if str(data.get("payment_method", "cash")).strip().lower() in {"mpaisa", "mycash"}
            else ""
        ),
        photo=data.get("photo"),
        stock=stock,
        multiple_units=data.get("multiple_units", stock > 1),
        status=item_status(stock),
        seller_id=seller.id,
        seller_username=seller.username,
    )
    return serialize_item_for_user(item, seller.id)


def get_public_item(item_id, requesting_user_id=None):
    item = available_seller_items(Item.objects.all()).filter(id=item_id).first()
    if not item or item.status == "removed" or item.name.startswith("__test_") or (
        item.status == "hidden" and str(requesting_user_id) != str(item.seller_id)
    ):
        raise ApiError("Item not found", 404)
    data = visible_to_buyer(item, requesting_user_id)
    if data is None:
        raise ApiError("Item not found", 404)
    return data


def normalize_listing_fields(data):
    result = dict(data)
    for field in ("name", "description", "category", "contact"):
        if field in result:
            result[field] = result[field].strip()
    if "category" in result:
        category = canonical_category_name(result["category"])
        if category.lower() not in DEFAULT_CATEGORY_NAMES and not Category.objects.filter(name__iexact=category).exists():
            raise ApiError("Choose an existing marketplace category", 422)
        stored_category = Category.objects.filter(name__iexact=category).first()
        result["category"] = category if category.casefold() in DEFAULT_CATEGORY_NAMES else stored_category.name
    return result


def require_seller_mutable_listing(item):
    if item.status == "removed" or (item.status == "hidden" and item.removed_reason is not None):
        raise ApiError("This listing is restricted by an administrator", 403)


def update_item(item_id, seller_id, data):
    if not seller_id:
        raise ApiError("You can only edit your own listings", 403)
    seller = require_active_user(seller_id)
    with transaction.atomic():
        item = Item.objects.select_for_update().filter(id=item_id).first()
        if not item:
            raise ApiError("Item not found", 404)
        if item.seller_id != seller.id:
            raise ApiError("You can only edit your own listings", 403)
        require_seller_mutable_listing(item)

        if not isinstance(data, dict):
            raise ApiError("Listing details must be a JSON object", 422)

        validation_data = {
            "payment_method": item.payment_method,
            "payment_number": item.payment_number,
            "photo": item.photo,
        }
        validation_data.update(data)
        validate_item_payload(validation_data, partial=True)
        data = normalize_listing_fields(data)
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
        if "multiple_units" in data:
            if not data["multiple_units"] and item.stock > 1:
                raise ApiError("Single-item listings can have at most one unit", 422)
            item.multiple_units = data["multiple_units"]
        elif item.stock > 1:
            item.multiple_units = True
        if "payment_method" in data:
            item.payment_method = str(data["payment_method"]).strip().lower()
        if item.payment_method in {"mpaisa", "mycash"}:
            if "payment_number" in data:
                item.payment_number = str(data["payment_number"]).strip()
        else:
            item.payment_number = ""

        if item.status not in {"reserved", "hidden", "removed"}:
            item.status = item_status(item.stock)
        elif item.status == "reserved" and item.stock == 0:
            item.status = "sold"
            item.reserved_buyer_id = None
            item.reserved_buyer_username = None
        item.save()
    return serialize_item_for_user(item, seller.id)


@transaction.atomic
def delete_item(item_id, seller_id):
    seller = require_active_user(seller_id)
    item = Item.objects.select_for_update().filter(id=item_id).first()
    if not item:
        raise ApiError("Item not found", 404)
    if item.seller_id != seller.id:
        raise ApiError("You can only remove your own listings", 403)
    require_seller_mutable_listing(item)
    if Purchase.objects.filter(item_id=item.id).exclude(
        order_stage__in=["completed", "cancelled", "canceled"],
    ).exists():
        raise ApiError("An active order exists; complete or cancel it before deleting this listing", 409)
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
    item = available_seller_items(Item.objects.all()).filter(id=item_id).first()
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
    with transaction.atomic():
        item = Item.objects.select_for_update().filter(id=item_id).first()
        if not item:
            raise ApiError("Item not found", 404)
        if item.seller_id != seller.id:
            raise ApiError("You can only reserve your own listings", 403)
        require_seller_mutable_listing(item)
        if item.status == "hidden":
            raise ApiError("Make the listing available before reserving it", 409)
        if Purchase.objects.filter(
            item_id=item.id, payment_status="pending", order_stage="order_placed",
        ).exists():
            raise ApiError("This listing is reserved for an unpaid order", 409)
        if item.status == "reserved":
            raise ApiError("This listing is already reserved", 409)
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
    return {"item": serialize_item_for_user(item, seller.id), "message": f"{item.name} reserved for {buyer.username}."}


def update_item_seller_status(item_id, seller_id, status):
    seller = require_active_user(seller_id)
    with transaction.atomic():
        item = Item.objects.select_for_update().filter(id=item_id).first()
        if not item:
            raise ApiError("Item not found", 404)
        if item.seller_id != seller.id:
            raise ApiError("You can only update your own listings", 403)
        require_seller_mutable_listing(item)
        if Purchase.objects.filter(
            item_id=item.id, payment_status="pending", order_stage="order_placed",
        ).exists():
            if status == "available" and reservation_stock(item)[1] is not None:
                refresh_reservation_status(item, None)
                return {"item": serialize_item_for_user(item, seller.id), "message": "Manual reservation released."}
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
    return {"item": serialize_item_for_user(item, seller.id), "message": "Listing status updated."}


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
        raise ApiError("Payment failed. No order was placed and stock was unchanged.", 402)

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
        "message": "Payment recorded. Contact the seller to arrange meetup or collection.",
    }


def checkout_response_from_purchases(purchases):
    orders = [enrich_purchase_order(purchase) for purchase in purchases]
    total = round(sum(purchase.final_total for purchase in purchases), 2)
    payment_method = purchases[0].payment_method
    payment_statuses = {purchase.payment_status for purchase in purchases}
    if "pending" in payment_statuses:
        status = "pending"
    elif payment_method == "cash":
        status = "paid"
    else:
        status = "approved"
    payment = {
        "status": status,
        "provider": "Cash handoff" if payment_method == "cash" else f"{PAYMENT_METHODS[payment_method]} demo processor",
        "reference": purchases[0].payment_reference,
        "amount": total,
        "message": (
            "Order placed. Cash is due to the seller at delivery or self-pickup. "
            "The ordered units are reserved until the seller confirms receipt."
            if status == "pending"
            else "Payment recorded. Contact the seller to arrange meetup or collection."
        ),
        "method": payment_method,
    }
    item_ids = {purchase.item_id for purchase in purchases}
    items = {
        item.id: item
        for item in Item.objects.filter(id__in=item_ids)
    }
    return {
        "orders": orders,
        "items": [
            {
                "item": serialize_admin_item(items[purchase.item_id]) if purchase.item_id in items else None,
                "payment_method": purchase.payment_method,
                "purchased_quantity": purchase.quantity,
            }
            for purchase in purchases
        ],
        "payment": payment,
        "total": total,
    }


def refresh_reservation_status(item, manual):
    pending, _, _ = reservation_stock(item)
    if manual and item.stock > 0:
        item.reserved_buyer_id, item.reserved_buyer_username = manual
    elif pending:
        item.reserved_buyer_id = pending[0].buyer_id
        item.reserved_buyer_username = pending[0].buyer_username
    else:
        item.reserved_buyer_id = None
        item.reserved_buyer_username = None
    if item.status not in {"hidden", "removed"}:
        item.status = "reserved" if item.stock > 0 and (pending or manual) else item_status(item.stock)
    item.save(update_fields=["stock", "status", "reserved_buyer_id", "reserved_buyer_username"])


def checkout_cart(buyer_id, data):
    if not isinstance(data, dict):
        raise ApiError("Checkout details must be provided as a JSON object", 422)
    if not buyer_id:
        raise ApiError("User not found", 404)

    checkout_id = data.get("checkout_id")
    if not isinstance(checkout_id, str):
        raise ApiError("A valid checkout ID is required", 422)
    checkout_id = checkout_id.strip()
    if not checkout_id or len(checkout_id) > 64:
        raise ApiError("A valid checkout ID is required", 422)

    buyer = User.objects.filter(id=buyer_id).first()
    if not buyer:
        raise ApiError("User not found", 404)
    existing_purchases = list(
        Purchase.objects.filter(buyer_id=buyer.id, checkout_id=checkout_id).order_by("id")
    )
    if existing_purchases:
        return checkout_response_from_purchases(existing_purchases)
    if buyer.status == "suspended":
        raise ApiError("Account is suspended", 403)

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
        item_id = whole_number(entry.get("item_id"), "Item ID", minimum=1)
        quantity = whole_number(entry.get("quantity"), "Quantity", minimum=1)
        if item_id in item_quantities:
            raise ApiError("Each item can only appear once in your cart", 422)
        item_quantities[item_id] = quantity
    if len(item_quantities) > 50:
        raise ApiError("A checkout can contain at most 50 items", 422)

    with transaction.atomic():
        buyer = User.objects.select_for_update().filter(id=buyer_id).first()
        if not buyer:
            raise ApiError("User not found", 404)
        existing_purchases = list(
            Purchase.objects.filter(buyer_id=buyer.id, checkout_id=checkout_id).order_by("id")
        )
        if existing_purchases:
            return checkout_response_from_purchases(existing_purchases)
        if buyer.status == "suspended":
            raise ApiError("Account is suspended", 403)

        locked_items = {
            item.id: item
            for item in available_seller_items(Item.objects.select_for_update()).filter(id__in=item_quantities).order_by("id")
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
            if item.status in {"hidden", "removed"}:
                raise ApiError(f"{item.name} is no longer available", 404)
            if item.seller_id == buyer.id:
                raise ApiError("You cannot purchase your own listing", 400)
            if item.status == "sold" or item.stock <= 0:
                raise ApiError(f"{item.name} is sold out", 400)
            available = purchasable_stock(item, buyer.id)
            if quantity > available:
                raise ApiError(f"Only {available} unit{' is' if available == 1 else 's are'} available for {item.name}", 400)
            items_subtotal_cents += round(item.price * quantity * 100)

        delivery_fee_cents = 500 if delivery_method == "delivery" else 0
        total_cents = items_subtotal_cents + delivery_fee_cents
        simulate_failure = data.get("simulate_failure") is True or data.get("force_failure") is True
        if payment_method == "cash" and not simulate_failure:
            payment = {
                "status": "pending",
                "provider": "Cash handoff",
                "reference": "",
                "amount": round(total_cents / 100, 2),
                "message": (
                    "Order placed. Cash is due to the seller at delivery or self-pickup. "
                    "The ordered units are reserved until the seller confirms receipt."
                ),
            }
        else:
            payment = simulate_payment_authorization(
                payment_method,
                data.get("payment_details"),
                total_cents / 100,
                force_failure=simulate_failure,
            )
        fee_per_item, fee_remainder = divmod(delivery_fee_cents, len(item_quantities))
        orders = []
        updated_items = []
        for index, (item_id, quantity) in enumerate(item_quantities.items()):
            item = locked_items[item_id]
            item_subtotal_cents = round(item.price * quantity * 100)
            item_delivery_fee_cents = fee_per_item + (1 if index < fee_remainder else 0)
            item_total_cents = item_subtotal_cents + item_delivery_fee_cents
            updated_item = purchase_item(
                item_id,
                buyer.id,
                payment_method,
                delivery_method,
                quantity,
                item_delivery_fee_cents / 100,
                item_subtotal_cents / 100,
                0,
                item_total_cents / 100,
                payment_confirmed=payment_method != "cash",
                payment_status=payment["status"],
                payment_reference=payment["reference"],
                simulate_failure=simulate_failure,
                checkout_id=checkout_id,
            )
            updated_items.append({
                "item": updated_item,
                "payment_method": payment_method,
                "purchased_quantity": quantity,
            })
            purchase = Purchase.objects.filter(buyer_id=buyer.id, item_id=item_id).latest("id")
            orders.append(enrich_purchase_order(purchase))

    return {
        "orders": orders,
        "items": updated_items,
        "payment": {
            **payment,
            "method": payment_method,
            "amount": round(total_cents / 100, 2),
        },
        "total": round(total_cents / 100, 2),
    }


@transaction.atomic
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
    simulate_failure=False,
    checkout_id=None,
):
    if simulate_failure:
        raise ApiError("Payment failed. No order was placed and stock was unchanged.", 402)
    if not buyer_id:
        raise ApiError("User not found", 404)

    delivery_method_key = str(delivery_method or "").strip().lower()
    if delivery_method_key not in DELIVERY_METHODS:
        raise ApiError("Select a valid delivery method", 422)
    requested_quantity = whole_number(quantity, "Quantity", minimum=1)

    buyer = require_active_user(buyer_id)
    item = available_seller_items(Item.objects.select_for_update()).filter(id=item_id).first()
    if not item or item.status in {"hidden", "removed"}:
        raise ApiError("Item not found", 404)
    payment_method_key = str(payment_method or "").strip().lower()
    if payment_method_key not in PAYMENT_METHODS:
        raise ApiError("Select a valid payment method", 422)
    if item.seller_id == buyer.id:
        raise ApiError("You cannot purchase your own listing", 400)
    if Purchase.objects.filter(item_id=item.id, buyer_id=buyer.id, payment_status="pending", order_stage="order_placed").exists():
        raise ApiError("This listing already has an unpaid order", 409)
    if item.stock <= 0 or item.status == "sold":
        item.stock = 0
        item.status = "sold"
        item.save()
        raise ApiError("Item is sold out", 400)
    pending, manual, available = reservation_stock(item)
    available = purchasable_stock(item, buyer.id)
    if requested_quantity > available:
        raise ApiError(f"Only {available} unit{' is' if available == 1 else 's are'} available", 400)

    if payment_confirmed is None:
        payment_confirmed = False
    if manual and manual[0] == buyer.id:
        manual = None
    if payment_confirmed:
        item.stock -= requested_quantity
    item_subtotal = float(subtotal if subtotal is not None else item.price * requested_quantity)
    item_delivery_fee = float(delivery_fee or 0)
    item_tax_amount = float(included_tax_amount if included_tax_amount is not None else 0)
    item_final_total = float(final_total if final_total is not None else item_subtotal + item_delivery_fee)
    if payment_status is None:
        payment_status = "paid" if payment_confirmed else "pending"
    purchase = Purchase.objects.create(
        buyer_id=buyer.id,
        checkout_id=checkout_id,
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
    refresh_reservation_status(item, manual)
    notify_order_user(
        purchase,
        buyer.id,
        "Order confirmed" if payment_confirmed else "Order placed — payment due",
        (
            f"Your order for {item.name} is confirmed. Payment method: {PAYMENT_METHODS[payment_method_key]}."
            if payment_confirmed
            else (
                f"Your order for {item.name} is reserved. Pay cash at "
                f"{DELIVERY_METHODS[delivery_method_key].lower()}; the seller will confirm receipt."
                if payment_method_key == "cash"
                else f"Your order for {item.name} is placed. Pay the seller directly by {PAYMENT_METHODS[payment_method_key]}."
            )
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


@transaction.atomic
def update_seller_order_stage(purchase_id, seller_id, stage):
    seller = require_active_user(seller_id)
    stage = str(stage or "").strip().lower()
    if stage not in SELLER_ORDER_STAGES:
        raise ApiError("Seller can only set Preparing Item or Ready for Collection", 422)

    purchase = Purchase.objects.select_for_update().filter(id=purchase_id).first()
    if not purchase:
        raise ApiError("Order not found", 404)
    if purchase.seller_id != seller.id:
        raise ApiError("You can only update your own orders", 403)
    if purchase.order_stage in {"cancelled", "canceled"} or purchase.status in {"cancelled", "canceled"}:
        raise ApiError("Cancelled orders cannot be reopened", 409)
    if purchase.payment_status not in {"paid", "approved"}:
        raise ApiError("Confirm payment receipt before preparing this order", 400)
    if purchase.order_stage in {"item_received", "completed"}:
        raise ApiError("This order has already been received by the buyer", 400)
    if stage == "ready_for_collection" and purchase.order_stage not in {"preparing_item", "ready_for_collection"}:
        raise ApiError("Mark the order as preparing before setting it ready for collection", 400)
    if stage == "preparing_item" and purchase.order_stage not in {"payment_confirmed", "preparing_item"}:
        raise ApiError("Order progress cannot move backwards", 409)

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
        if not item or item.status in {"hidden", "removed"}:
            raise ApiError("The listing is unavailable for payment confirmation", 409)
        pending, manual, _ = reservation_stock(item)
        if sum(order.quantity for order in pending) + (1 if manual else 0) > item.stock:
            raise ApiError("The reserved stock is no longer available", 409)
        item.stock -= purchase.quantity

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
        refresh_reservation_status(item, manual)

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

        if purchase.payment_status in {"paid", "approved"}:
            raise ApiError("Payment has already been recorded as received. Arrange any refund directly with the buyer before changing this order.", 400)

        item = Item.objects.select_for_update().filter(id=purchase.item_id).first()
        manual = reservation_stock(item)[1] if item else None
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
            refresh_reservation_status(item, manual)

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


@transaction.atomic
def confirm_order_received(purchase_id, buyer_id):
    buyer = require_active_user(buyer_id)
    purchase = Purchase.objects.select_for_update().filter(id=purchase_id).first()
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


def list_seller_orders(seller_id):
    if not User.objects.filter(id=seller_id).exists():
        raise ApiError("User not found", 404)
    orders = visible_purchases(include_test_records=True).filter(seller_id=seller_id).order_by("-id")
    return [serialize_purchase(order) for order in orders]


def dashboard(admin_id):
    require_admin(admin_id)
    today = timezone.localdate()
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
        if purchase.purchased_at and timezone.localtime(purchase.purchased_at).date() == today
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
    User.objects.filter(role="student", status="suspended", suspended_until__lte=timezone.now()).update(status="active", updated_at=timezone.now())
    query = User.objects.filter(role="student")
    if search:
        query = query.filter(Q(username__contains=search) | Q(email__contains=search))
    return [serialize_user(user, include_moderation=True) for user in query.order_by("-id")]


def account_action_reason(data):
    if not isinstance(data, dict):
        raise ApiError("Account action details must be a JSON object", 422)
    raw_reason = data.get("reason", "")
    if not isinstance(raw_reason, str):
        raise ApiError("Enter a written reason to continue", 422)
    reason = raw_reason.strip()
    if not reason:
        raise ApiError("A reason is required to continue", 422)
    if not 10 <= len(reason) <= 500:
        raise ApiError("Provide a reason between 10 and 500 characters", 422)
    return reason


def send_account_action_email(subject, message, email, action_label="account action"):
    try:
        send_email(subject, message, email, "Failed to send account notification")
        provider = settings.EMAIL_PROVIDER
        resend = provider == "resend" or (provider == "auto" and not settings.EMAIL_HOST and bool(settings.RESEND_API_KEY))
        console = not resend and (provider == "console" or settings.EMAIL_BACKEND == settings.CONSOLE_EMAIL_BACKEND)
        if console:
            return {"email_status": "console", "message": "Email was printed to the backend terminal only; it was not delivered to the student."}
        return {"email_status": "sent", "message": "Notification email accepted by the email provider. Inbox delivery is not guaranteed."}
    except Exception as exc:
        email_logger.warning("Account notification email failed: %s", describe_email_exception(exc))
        return {"email_status": "failed", "message": f"The {action_label} succeeded, but the notification email failed. Contact the student separately and check the backend email settings."}


def set_student_status(admin_id, student_id, status, data=None):
    admin = require_admin(admin_id)
    if status not in {"active", "suspended"}:
        raise ApiError("Invalid account status", 422)
    reason = account_action_reason(data)
    hours = whole_number(data.get("duration_hours"), "Suspension duration", minimum=1) if status == "suspended" else None
    if hours and hours > 8760:
        raise ApiError("Suspension duration must be between 1 hour and 365 days", 422)
    deadline = timezone.now() + timedelta(hours=hours) if hours else None
    deadline_text = timezone.localtime(deadline, timezone.get_fixed_timezone(720)).strftime("%d %b %Y at %I:%M %p Fiji time (UTC+12)") if deadline else ""
    with transaction.atomic():
        student = User.objects.select_for_update().filter(id=student_id, role="student").first()
        if not student:
            raise ApiError("Student not found", 404)
        if status == "active" and student.status != "suspended":
            raise ApiError("Only suspended accounts can be reactivated", 409)
        student.status = status
        student.suspension_reason = reason if status == "suspended" else ""
        student.suspended_until = deadline
        student.save(update_fields=["status", "suspension_reason", "suspended_until", "updated_at"])
        if status == "suspended":
            title = "Account suspended"
            details = f"Reason: {reason}\nDuration: {hours} hours. Suspension ends {deadline_text}. You can sign in again after that time using your password and authenticator."
            email_message = (
                f"Dear {student.name.strip() or student.username},\n\n"
                "We are writing to inform you that your USP Marketplace account has been temporarily suspended, effective immediately.\n\n"
                f"Reason for suspension: {reason}\n\n"
                f"Suspension duration: {hours} hours\n"
                f"Access resumes: {deadline_text}\n\n"
                "You will be unable to sign in or use your account during this period. "
                "Once the suspension ends, you may sign in again using your usual sign-in details.\n\n"
                "If you believe this decision was made in error or would like to request a review, "
                "please contact the USP Marketplace administration team and include your registered email address.\n\n"
                "Thank you for your understanding.\n\n"
                "Kind regards,\nUSP Marketplace Administration Team"
            )
        else:
            title = "Account reactivated"
            details = f"Your suspension has been reconsidered and your account reactivated by an administrator. Reason: {reason}\nYou can now sign in using your password and authenticator."
            email_message = f"Hello {student.username},\n\n{details}\n\nIf you believe this action was a mistake, contact the USP Marketplace admin team."
            notify_user(student.id, title, details, "administration", admin)
    result = send_account_action_email(
        f"USP Marketplace: {title.lower()}",
        email_message,
        student.email,
        action_label="account suspension" if status == "suspended" else "account reactivation",
    )
    notify_admin(title, f"{student.username}: {details} Email status: {result['email_status']}.", "administration", admin)
    return {"user": serialize_user(student, include_moderation=True), **result}


def delete_student(admin_id, student_id, data=None):
    admin = require_admin(admin_id)
    reason = account_action_reason(data)
    with transaction.atomic():
        student = User.objects.select_for_update().filter(id=student_id, role="student").first()
        if not student:
            raise ApiError("Student not found", 404)
        username, email = student.username, student.email
        display_name = student.name.strip() or username
        Item.objects.filter(seller_id=student.id).delete()
        PendingRegistration.objects.filter(email__iexact=email).delete()
        student.delete()
    result = send_account_action_email(
        "USP Marketplace: Notice of account deletion",
        (
            f"Dear {display_name},\n\n"
            "We are writing to confirm that your USP Marketplace account and its listings have been permanently deleted by an administrator.\n\n"
            f"Reason for deletion: {reason}\n\n"
            "You can no longer sign in to or use this account.\n\n"
            "If you believe this decision was made in error or have any questions, "
            "please contact the USP Marketplace administration team and include your registered email address.\n\n"
            "Kind regards,\nUSP Marketplace Administration Team"
        ),
        email,
        action_label="account deletion",
    )
    notify_admin("Student account deleted", f"{username} ({email}). Reason: {reason}. Email status: {result['email_status']}.", "administration", admin)
    return {**result, "message": f"{username} was permanently deleted. {result['message']}"}


def list_admin_notifications(admin_id):
    require_admin(admin_id)
    notifications = AdminNotification.objects.order_by("-id")
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
    notifications = UserNotification.objects.filter(user_id=user.id).order_by("-id")
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
    if not 8 <= len(reason) <= 1000:
        raise ApiError("Report reason must be between 8 and 1,000 characters", 422)

    target_id = whole_number(data.get("target_id"), "Report target ID", minimum=1)
    target_label = str(data.get("target_label", "")).strip()
    item = None
    if target_type == "listing":
        item = Item.objects.filter(id=target_id).first()
        if not item:
            raise ApiError("Listing not found", 404)
        target_label = item.name
        target_id = item.id
    elif target_id:
        target_user = User.objects.filter(id=target_id).first()
        if not target_user:
            raise ApiError("Reported user not found", 404)
        target_label = target_user.username
        target_id = target_user.id
        if data.get("listing_id"):
            item = Item.objects.filter(id=data["listing_id"]).first()
            if not item or item.seller_id != target_user.id:
                raise ApiError("The reported listing must belong to the reported seller", 422)

    if not target_label:
        raise ApiError("Report target is required", 422)

    report_record = UserReport.objects.create(
        reporter_id=reporter.id,
        reporter_username=reporter.username,
        target_type=target_type,
        target_id=target_id or None,
        target_label=target_label,
        reason=reason,
        listing_id=item.id if item else None,
        listing_snapshot=serialize_item(item) if item else {},
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
    records = list(UserReport.objects.exclude(reporter_username__startswith="__test_").order_by("-id"))
    listing_ids = {record.listing_id or record.target_id for record in records if record.listing_id or record.target_type == "listing"}
    items = Item.objects.in_bulk(listing_ids)
    user_ids = {record.reporter_id for record in records}
    user_ids.update(record.target_id for record in records if record.target_type == "user" and record.target_id)
    user_ids.update(item.seller_id for item in items.values())
    user_ids.update((record.listing_snapshot or {}).get("seller_id") for record in records if (record.listing_snapshot or {}).get("seller_id"))
    users = User.objects.in_bulk(user_ids)
    reports = []
    for record in records:
        data = serialize_user_report(record)
        listing_id = record.listing_id or (record.target_id if record.target_type == "listing" else None)
        item = items.get(listing_id)
        seller_id = item.seller_id if item else (record.target_id if record.target_type == "user" else (record.listing_snapshot or {}).get("seller_id"))
        seller = users.get(seller_id)
        data["listing_id"] = listing_id
        data["target_item"] = serialize_item(item) if item else None
        data["listing_available"] = item is not None
        data["seller"] = serialize_user(seller, include_moderation=True) if seller else None
        if data["target_item"] and seller:
            data["target_item"]["seller"] = data["seller"]
        reporter = users.get(record.reporter_id)
        data["reporter"] = serialize_user(reporter, include_moderation=True) if reporter else None
        reports.append(data)
    return reports


def review_user_report(admin_id, report_id, data):
    admin = require_admin(admin_id)
    if not isinstance(data, dict):
        raise ApiError("Action details must be a JSON object", 422)
    action = str(data.get("action", "")).strip().lower()
    if action not in {"warning", "delete"}:
        raise ApiError("Choose Send warning or Delete listing", 422)
    reason = account_action_reason(data)
    with transaction.atomic():
        record = UserReport.objects.select_for_update().filter(id=report_id).first()
        if not record:
            raise ApiError("Report not found", 404)
        if data.get("expected_status") is not None and data["expected_status"] != record.status:
            raise ApiError("This report has changed. Refresh the flags before taking action.", 409)
        if record.status == "deleted" or (action == "warning" and record.status == "warned"):
            raise ApiError("This action has already been completed for this report", 409)
        if record.email_status == "pending":
            raise ApiError("An email action is still processing for this report. Refresh before taking another action.", 409)
        listing_id = record.listing_id or (record.target_id if record.target_type == "listing" else None)
        item = Item.objects.select_for_update().filter(id=listing_id).first() if listing_id else None
        snapshot = record.listing_snapshot or {}
        seller_id = item.seller_id if item else (record.target_id if record.target_type == "user" else snapshot.get("seller_id"))
        seller = User.objects.filter(id=seller_id).first()
        if not seller or not seller.email:
            raise ApiError("The seller account is unavailable. An email action cannot be performed.", 409)
        listing_name = snapshot.get("name") or (item.name if item else record.target_label)
        if action == "delete":
            if not item or item.status == "removed":
                raise ApiError("This listing is already deleted or is no longer available", 409)
            # Orders store their own item details; preserve report evidence before
            # permanently deleting the listing itself.
            record.listing_snapshot = record.listing_snapshot or serialize_item(item)
            record.listing_id = listing_id
            item.delete()
            item = None
            title = "Listing deleted"
            details = f"An administrator permanently deleted your listing '{listing_name}' (listing #{listing_id}) from the marketplace. This listing cannot be restored. Reason: {reason}"
        else:
            title = "Marketplace warning"
            details = f"An administrator has issued a warning about '{listing_name}'{f' (listing #{listing_id})' if listing_id else ''}. Reason: {reason}. Please review your listing and follow marketplace rules."
        record.status = "deleted" if action == "delete" else "warned"
        record.review_notes = reason
        record.reviewed_by_id = admin.id
        record.reviewed_by_username = admin.username
        record.reviewed_at = timezone.now()
        record.email_status = "pending"
        record.save(update_fields=["status", "review_notes", "reviewed_by_id", "reviewed_by_username", "reviewed_at", "email_status", "listing_snapshot", "listing_id"])
        notify_user(seller.id, title, details[:1000], "administration", admin)
        notify_user(record.reporter_id, "Your report has been reviewed", f"An administrator reviewed report #{record.id} about {record.target_label} and {'deleted the listing' if action == 'delete' else 'issued a warning to the seller'}.", "administration", admin)
    email_result = send_account_action_email(
        f"USP Marketplace: {title}",
        f"Hello {seller.username},\n\n{details}\n\nIf you believe this action was a mistake, contact the USP Marketplace admin team.",
        seller.email,
        action_label="listing action",
    )
    record.email_status = email_result["email_status"]
    record.save(update_fields=["email_status"])
    notify_admin(title, f"Report #{record.id}. {details} Email status: {record.email_status}."[:1000], "report", admin)
    return {"report": serialize_user_report(record), "listing": serialize_item(item) if item else None, **email_result}


def list_rating_reviews(admin_id):
    require_admin(admin_id)
    return [serialize_admin_review(review_record) for review_record in RatingReview.objects.order_by("-id")]


def list_admin_items(admin_id, search=""):
    require_admin(admin_id)
    query = visible_items().exclude(status="removed")
    if search:
        query = query.filter(
            Q(name__contains=search)
            | Q(category__contains=search)
            | Q(seller_username__contains=search)
        )
    return [serialize_admin_item(item) for item in query.order_by("-id")]


@transaction.atomic
def hide_listing(admin_id, item_id, reason):
    require_admin(admin_id)
    item = Item.objects.select_for_update().filter(id=item_id).first()
    if not item:
        raise ApiError("Item not found", 404)
    item.status = "hidden"
    item.removed_reason = str(reason or "Hidden by an administrator")[:255]
    item.save()
    notify_user(
        item.seller_id,
        "Listing hidden",
        f"An administrator hid your listing '{item.name}'. Reason: {reason or 'No reason provided'}.",
        "administration",
    )
    return serialize_admin_item(item)


def moderate_listing(admin_id, item_id, action, data):
    admin = require_admin(admin_id)
    reason = account_action_reason(data)
    if action not in {"warning", "remove"}:
        raise ApiError("Choose Warn seller or Remove listing", 422)
    if data.get("confirmed") is not True:
        raise ApiError("Confirm this action before sending an email to the seller", 422)
    with transaction.atomic():
        item = Item.objects.select_for_update().filter(id=item_id).first()
        if not item:
            raise ApiError("Item not found", 404)
        if item.status == "removed" and action == "warning":
            raise ApiError("This listing has already been removed", 409)
        if data.get("expected_status") is not None and data["expected_status"] != item.status:
            raise ApiError("This listing has changed. Reopen the item and review it before continuing.", 409)
        seller = User.objects.filter(id=item.seller_id).first()
        if not seller or not seller.email:
            raise ApiError("The seller account is unavailable. An email action cannot be completed.", 409)
        listing_id = item.id
        title = "Listing removed" if action == "remove" else "Listing warning issued"
        audit = notify_admin(title, f"Listing #{listing_id}: {item.name}. Seller: {seller.username}. Reason: {reason}. Email status: pending.", "administration", admin)
        if action == "remove":
            item.delete()
    if action == "remove":
        explanation = "Following an administrative review, your listing has been permanently deleted from USP Marketplace and is no longer visible or available for purchase. This listing cannot be restored."
        next_steps = "Please review the marketplace rules before submitting any future listings."
    else:
        explanation = "Following an administrative review, we are issuing a formal warning regarding your listing on USP Marketplace. Your listing has not been removed by this action."
        next_steps = "Please review the concern below and update your listing where necessary to comply with the marketplace rules. Further violations may result in listing removal or account restrictions."
    result = send_account_action_email(
        f"USP Marketplace: {'Notice of listing removal' if action == 'remove' else 'Formal warning about your listing'}",
        (
            f"Dear {seller.name.strip() or seller.username},\n\n{explanation}\n\n"
            f"Listing: {item.name}\nListing reference: #{listing_id}\n\n"
            f"Reason for {'removal' if action == 'remove' else 'warning'}: {reason}\n\n"
            f"{next_steps}\n\n"
            "If you believe this decision was made in error or would like to request a review, please contact the USP Marketplace administration team and include your listing reference and registered email address.\n\n"
            "Kind regards,\nUSP Marketplace Administration Team"
        ),
        seller.email,
        action_label="listing removal" if action == "remove" else "listing warning",
    )
    audit.message = f"Listing #{listing_id}: {item.name}. Seller: {seller.username}. Reason: {reason}. Email status: {result['email_status']}."
    audit.save(update_fields=["message"])
    return {"listing": None if action == "remove" else serialize_admin_item(item), "removed_id": listing_id if action == "remove" else None, **result}


@transaction.atomic
def restore_listing(admin_id, item_id):
    require_admin(admin_id)
    item = Item.objects.select_for_update().filter(id=item_id).first()
    if not item:
        raise ApiError("Item not found", 404)
    pending, manual, _ = reservation_stock(item)
    if sum(order.quantity for order in pending) + (1 if manual else 0) > item.stock:
        raise ApiError("Insufficient stock for the outstanding reservations", 409)
    item.status = item_status(item.stock)
    refresh_reservation_status(item, manual)
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
