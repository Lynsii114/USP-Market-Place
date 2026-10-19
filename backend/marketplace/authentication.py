"""Signed, expiring API identities issued only after login verification."""
import hashlib
import secrets

from django.conf import settings
from django.core import signing
from django.db import DatabaseError
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from .exceptions import ApiError
from .models import User
from .account_status import restore_expired_suspension


def credential_version(user):
    return hashlib.sha256(f"{user.password_hash}:{user.authenticator_secret}".encode()).hexdigest()


def issue_token(user, purpose="access"):
    if not settings.DEBUG and settings.SECRET_KEY == "dev-secret-key":
        raise ApiError("Configure a secure SECRET_KEY before enabling login", 503)
    return signing.dumps(
        {"id": user.id, "version": credential_version(user)},
        salt=f"marketplace.{purpose}",
    )


def token_user(token, purpose="access"):
    try:
        data = signing.loads(token, salt=f"marketplace.{purpose}", max_age=28800 if purpose == "access" else 600)
        user = User.objects.filter(id=data["id"]).first()
        if not user or not secrets.compare_digest(data["version"], credential_version(user)):
            raise ApiError("Please sign in again", 401)
    except (signing.BadSignature, KeyError, TypeError, ValueError) as exc:
        raise ApiError("Please sign in again", 401) from exc
    restore_expired_suspension(user)
    if user.status != "active":
        raise ApiError("Account is not active", 403)
    return user


class ApiIdentityMiddleware(MiddlewareMixin):
    """Authenticate API callers and bind legacy actor parameters to their identity.

    IDs selecting a target (for example the buyer in a seller reservation) are
    deliberately distinct from the ID identifying the actor for that endpoint.
    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.path.startswith("/api/") or request.method == "OPTIONS":
            return None
        name = view_func.__name__
        anonymous = {
            "health", "database_health", "signup", "verify_email", "resend_verification",
            "cancel_verification", "login", "verify_authenticator", "request_password_reset",
            "verify_password_reset_code", "reset_password",
        }
        if name in anonymous:
            return None
        public_read = request.method == "GET" and name in {
            "items_collection", "item_detail", "categories_collection", "list_seller_items", "seller_reviews",
        }
        try:
            authorization = request.headers.get("Authorization", "")
            user = None
            if authorization:
                if not authorization.startswith("Bearer "):
                    raise ApiError("Please sign in again", 401)
                user = token_user(authorization[7:])
            if not public_read and user is None:
                raise ApiError("Login required", 401)
            request.marketplace_user = user
            if request.path.startswith("/api/admin/") and user.role != "admin":
                raise ApiError("Admin access required", 403)

            customer_actions = {
                "items_collection", "item_detail", "purchase_item", "checkout_cart",
                "item_conversation", "item_reservation", "seller_item_status",
                "seller_order_stage", "confirm_payment_received", "confirm_cash_payment",
                "cancel_order", "buyer_order_received", "report_user_activity",
                "rating_review", "conversation_detail",
            }
            if user and user.role == "admin" and request.method != "GET" and name in customer_actions:
                raise ApiError("Administrator accounts can browse and moderate listings. Use a customer account to buy, sell, message or submit reviews and reports.", 403)

            # Viewer parameters can never impersonate a seller or reserved buyer.
            if public_read:
                query = request.GET.copy()
                for key in ("user_id", "viewer_id"):
                    query.pop(key, None)
                    if user:
                        query[key] = str(user.id)
                request.GET = query
                return None

            actor_field = {
                "items_collection": "seller_id", "item_detail": "seller_id",
                "purchase_item": "buyer_id", "checkout_cart": "buyer_id",
                "item_conversation": "buyer_id", "item_message_buyers": "seller_id",
                "item_reservation": "seller_id", "seller_item_status": "seller_id",
                "seller_order_stage": "seller_id", "confirm_payment_received": "seller_id",
                "cancel_order": "user_id", "buyer_order_received": "buyer_id",
                "report_user_activity": "reporter_id", "rating_review": "reviewer_id",
                "conversation_detail": "user_id" if request.method == "GET" else "sender_id",
            }.get(name)
            if request.path.startswith("/api/admin/"):
                actor_field = "admin_id"

            if name in {"list_buyer_purchases", "list_seller_orders", "user_conversations",
                        "user_unread_messages", "user_notifications", "user_notification_detail"}:
                for key in ("buyer_id", "seller_id", "user_id"):
                    if key in view_kwargs and view_kwargs[key] != user.id:
                        raise ApiError("You can only access your own account", 403)

            if actor_field:
                import json
                from .responses import json_body

                query = request.GET.copy()
                body = json_body(request) if request.body else {}
                if not isinstance(body, dict):
                    raise ApiError("Request body must be a JSON object", 422)
                for value in (query.get(actor_field), body.get(actor_field)):
                    if value is not None and str(value) != str(user.id):
                        raise ApiError("The acting user must match the signed-in account", 403)
                query[actor_field] = str(user.id)
                request.GET = query
                if request.method != "GET":
                    body[actor_field] = user.id
                    request._body = json.dumps(body).encode("utf-8")
            return None
        except ApiError as exc:
            return JsonResponse({"detail": exc.detail}, status=exc.status)
        except DatabaseError:
            return JsonResponse({"detail": "Marketplace database is temporarily unavailable"}, status=503)
