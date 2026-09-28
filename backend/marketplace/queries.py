from django.db.models import Q

from .models import Item, Purchase, User


def item_status(stock):
    return "sold" if int(stock) <= 0 else "available"


def visible_items():
    return Item.objects.exclude(name__startswith="__test_")


def public_items():
    return visible_items().exclude(status__in=["hidden", "removed"])


def visible_purchases(include_test_records=False):
    return Purchase.objects.all() if include_test_records else Purchase.objects.exclude(item_name__startswith="__test_")


def find_user_by_login(login_name):
    return User.objects.filter(Q(username=login_name) | Q(email=login_name)).first()


def find_student(student_id):
    return User.objects.filter(id=student_id, role="student").first()
