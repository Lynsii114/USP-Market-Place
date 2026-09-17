import hashlib
from collections import defaultdict
from datetime import date

from django.db.models import Q
from django.utils.dateparse import parse_date

from .constants import ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_USERNAME, HIDDEN_ITEM_NAMES
from .exceptions import ApiError
from .models import Item, Purchase, User
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


def signup_user(data):
    validate_signup(data)
    username = data["username"].strip()
    email = data["email"].strip()

    if User.objects.filter(Q(username=username) | Q(email=email)).exists():
        raise ApiError("Username or email already exists", 400)

    user = User.objects.create(
        username=username,
        email=email,
        password_hash=hash_password(data["password"]),
        role="student",
        status="active",
    )
    return {"user": serialize_user(user), "message": "Account created successfully."}


def login_user(data):
    login_name = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if login_name.lower() == ADMIN_EMAIL.lower() and password == ADMIN_PASSWORD:
        admin_user = get_or_create_admin_user()
        return {"user": serialize_user(admin_user), "message": "Admin login successful"}

    user = find_user_by_login(login_name)
    if not user or user.password_hash != hash_password(password):
        raise ApiError("Invalid username or password", 401)
    if user.status == "suspended":
        raise ApiError("Account is suspended", 403)
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
