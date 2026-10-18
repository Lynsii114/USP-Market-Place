from .models import Item, Purchase, User


def item_status(stock):
    return "sold" if int(stock) <= 0 else "available"


def visible_items():
    return Item.objects.exclude(name__startswith="__test_")


def public_items():
    return visible_items().filter(status__in=["available", "reserved"], stock__gt=0)


def visible_purchases(include_test_records=False):
    return Purchase.objects.all() if include_test_records else Purchase.objects.exclude(item_name__startswith="__test_")


def find_user_by_login(login_name):
    if "@" in login_name:
        user = User.objects.filter(email__iexact=login_name).first()
        if user:
            return user
    return User.objects.filter(username=login_name).first()


def find_student(student_id):
    return User.objects.filter(id=student_id, role="student").first()


def reservation_stock(item):
    pending = list(Purchase.objects.filter(
        item_id=item.id, payment_status="pending", order_stage="order_placed",
    ).exclude(status__in=["cancelled", "canceled", "completed"]).order_by("id"))
    pending_units = sum(order.quantity for order in pending)
    manual = None
    if item.reserved_buyer_id is not None and not any(
        order.buyer_id == item.reserved_buyer_id for order in pending
    ):
        manual = (item.reserved_buyer_id, item.reserved_buyer_username)
    manual_units = min(1, max(0, item.stock)) if manual else 0
    return pending, manual, max(0, item.stock - pending_units - manual_units)


def purchasable_stock(item, buyer_id):
    pending, manual, available = reservation_stock(item)
    return available + (1 if manual and manual[0] == buyer_id and item.stock > 0 else 0)
