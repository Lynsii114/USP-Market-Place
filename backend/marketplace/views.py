from django.db import DatabaseError
from django.views.decorators.csrf import csrf_exempt

from . import services
from .exceptions import ApiError
from .responses import api_response, handle_api_error, json_body, method_not_allowed


def get_admin_id(request):
    return request.GET.get("admin_id")


def run(action):
    try:
        data, safe = action()
        return api_response(data, safe=safe)
    except ApiError as exc:
        return handle_api_error(exc)
    except DatabaseError:
        return api_response({"detail": "Database unavailable. Check that MySQL is running and DATABASE_URL is correct."}, status=503)


def health(request):
    if request.method != "GET":
        return method_not_allowed()
    return api_response({"status": "ok"})


@csrf_exempt
def signup(request):
    if request.method != "POST":
        return method_not_allowed()
    return run(lambda: (services.signup_user(json_body(request)), True))


@csrf_exempt
def verify_email(request):
    if request.method != "POST":
        return method_not_allowed()
    return run(lambda: (services.verify_email(json_body(request)), True))


@csrf_exempt
def resend_verification(request):
    if request.method != "POST":
        return method_not_allowed()
    return run(lambda: (services.resend_verification(json_body(request)), True))


@csrf_exempt
def cancel_verification(request):
    if request.method != "POST":
        return method_not_allowed()
    return run(lambda: (services.cancel_verification(json_body(request)), True))


@csrf_exempt
def request_password_reset(request):
    if request.method != "POST":
        return method_not_allowed()
    return run(lambda: (services.request_password_reset(json_body(request)), True))


@csrf_exempt
def reset_password(request):
    if request.method != "POST":
        return method_not_allowed()
    return run(lambda: (services.reset_password(json_body(request)), True))


@csrf_exempt
def login(request):
    if request.method != "POST":
        return method_not_allowed()
    return run(lambda: (services.login_user(json_body(request)), True))


@csrf_exempt
def verify_authenticator(request):
    if request.method != "POST":
        return method_not_allowed()
    return run(lambda: (services.verify_authenticator(json_body(request)), True))


@csrf_exempt
def items_collection(request):
    if request.method == "GET":
        return run(lambda: (services.list_items(), False))
    if request.method == "POST":
        return run(lambda: (services.create_item(json_body(request)), True))
    return method_not_allowed()


def list_seller_items(request, seller_id):
    if request.method != "GET":
        return method_not_allowed()
    return run(lambda: (services.list_seller_items(seller_id), False))


@csrf_exempt
def item_detail(request, item_id):
    if request.method == "GET":
        return run(lambda: (services.get_public_item(item_id), True))
    if request.method == "PUT":
        return run(lambda: (services.update_item(item_id, request.GET.get("seller_id"), json_body(request)), True))
    if request.method == "DELETE":
        return run(lambda: (services.delete_item(item_id, request.GET.get("seller_id")), True))
    return method_not_allowed()


@csrf_exempt
def purchase_item(request, item_id):
    if request.method != "POST":
        return method_not_allowed()
    data = json_body(request)
    return run(lambda: (services.purchase_item(item_id, request.GET.get("buyer_id"), data.get("payment_method", "cash")), True))


@csrf_exempt
def report_user_activity(request):
    if request.method != "POST":
        return method_not_allowed()
    return run(lambda: (services.submit_user_report(json_body(request)), True))


@csrf_exempt
def rating_review(request):
    if request.method != "POST":
        return method_not_allowed()
    return run(lambda: (services.submit_rating_review(json_body(request)), True))


def list_buyer_purchases(request, buyer_id):
    if request.method != "GET":
        return method_not_allowed()
    return run(lambda: (services.list_buyer_purchases(buyer_id), False))


def list_seller_orders(request, seller_id):
    if request.method != "GET":
        return method_not_allowed()
    return run(lambda: (services.list_seller_orders(seller_id), False))


@csrf_exempt
def seller_order_stage(request, purchase_id):
    if request.method != "POST":
        return method_not_allowed()
    data = json_body(request)
    return run(lambda: (services.update_seller_order_stage(purchase_id, data.get("seller_id"), data.get("stage")), True))


@csrf_exempt
def buyer_order_received(request, purchase_id):
    if request.method != "POST":
        return method_not_allowed()
    data = json_body(request)
    return run(lambda: (services.confirm_order_received(purchase_id, data.get("buyer_id")), True))


def admin_dashboard(request):
    if request.method != "GET":
        return method_not_allowed()
    return run(lambda: (services.dashboard(get_admin_id(request)), True))


def admin_notifications(request):
    if request.method != "GET":
        return method_not_allowed()
    return run(lambda: (services.list_admin_notifications(get_admin_id(request)), False))


@csrf_exempt
def admin_notification_detail(request, notification_id):
    if request.method == "POST":
        return run(lambda: (services.mark_admin_notification_viewed(get_admin_id(request), notification_id), True))
    if request.method == "DELETE":
        return run(lambda: (services.delete_admin_notification(get_admin_id(request), notification_id), True))
    return method_not_allowed()


def admin_students(request):
    if request.method != "GET":
        return method_not_allowed()
    return run(lambda: (services.list_students(get_admin_id(request), request.GET.get("search", "")), False))


@csrf_exempt
def admin_suspend_student(request, student_id):
    if request.method != "POST":
        return method_not_allowed()
    return run(lambda: (services.set_student_status(get_admin_id(request), student_id, "suspended"), True))


@csrf_exempt
def admin_reactivate_student(request, student_id):
    if request.method != "POST":
        return method_not_allowed()
    return run(lambda: (services.set_student_status(get_admin_id(request), student_id, "active"), True))


@csrf_exempt
def admin_delete_student(request, student_id):
    if request.method != "DELETE":
        return method_not_allowed()
    return run(lambda: (services.delete_student(get_admin_id(request), student_id), True))


def admin_listings(request):
    if request.method != "GET":
        return method_not_allowed()
    return run(lambda: (services.list_admin_items(get_admin_id(request), request.GET.get("search", "")), False))


@csrf_exempt
def admin_hide_listing(request, item_id):
    if request.method != "POST":
        return method_not_allowed()
    return run(lambda: (services.hide_listing(get_admin_id(request), item_id, json_body(request).get("reason", "")), True))


@csrf_exempt
def admin_remove_listing(request, item_id):
    if request.method != "POST":
        return method_not_allowed()
    return run(lambda: (services.remove_listing(get_admin_id(request), item_id, json_body(request).get("reason", "")), True))


@csrf_exempt
def admin_restore_listing(request, item_id):
    if request.method != "POST":
        return method_not_allowed()
    return run(lambda: (services.restore_listing(get_admin_id(request), item_id), True))


def admin_orders(request):
    if request.method != "GET":
        return method_not_allowed()
    return run(
        lambda: (
            services.list_orders(
                get_admin_id(request),
                request.GET.get("search", ""),
                request.GET.get("status", ""),
                request.GET.get("order_date", ""),
            ),
            False,
        )
    )


def admin_reports(request):
    if request.method != "GET":
        return method_not_allowed()
    return run(lambda: (services.report(get_admin_id(request), request.GET.get("period", "daily")), True))


def admin_user_reports(request):
    if request.method != "GET":
        return method_not_allowed()
    return run(lambda: (services.list_user_reports(get_admin_id(request)), False))


def admin_rating_reviews(request):
    if request.method != "GET":
        return method_not_allowed()
    return run(lambda: (services.list_rating_reviews(get_admin_id(request)), False))
