from django.db.models import Q

from .constants import HIDDEN_ITEM_NAMES
from .models import Item, Purchase, User


def item_status(stock):
    return "sold" if int(stock) <= 0 else "available"


def visible_items():
    query = Item.objects.exclude(name__startswith="__test_")
    for hidden_name in HIDDEN_ITEM_NAMES:
        query = query.exclude(name=hidden_name)
    return query


def public_items():
    return visible_items().exclude(status="removed")


def visible_purchases(include_test_records=False):
    query = Purchase.objects.all() if include_test_records else Purchase.objects.exclude(item_name__startswith="__test_")
    for hidden_name in HIDDEN_ITEM_NAMES:
        query = query.exclude(item_name=hidden_name)
    return query


def find_user_by_login(login_name):
    return User.objects.filter(Q(username=login_name) | Q(email=login_name)).first()


def find_student(student_id):
    return User.objects.filter(id=student_id, role="student").first()
