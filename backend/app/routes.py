import hashlib
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from . import models, schemas
from .db import get_db

router = APIRouter()
ADMIN_EMAIL = "Admin@usp.ac.fj"
ADMIN_PASSWORD = "Admin12345"
ADMIN_USERNAME = "Admin"
HIDDEN_ITEM_NAMES = ["Scientific Calculator"]


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def serialize_user(user: models.User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "created_at": user.created_at,
    }


def item_status(stock: int) -> str:
    return "sold" if stock <= 0 else "available"


def visible_item_query(db: Session):
    query = db.query(models.Item).filter(~models.Item.name.startswith("__test_"))
    for hidden_name in HIDDEN_ITEM_NAMES:
        query = query.filter(models.Item.name != hidden_name)
    return query


def visible_purchase_query(db: Session):
    query = db.query(models.Purchase).filter(~models.Purchase.item_name.startswith("__test_"))
    for hidden_name in HIDDEN_ITEM_NAMES:
        query = query.filter(models.Purchase.item_name != hidden_name)
    return query


def buyer_purchase_query(db: Session):
    query = db.query(models.Purchase)
    for hidden_name in HIDDEN_ITEM_NAMES:
        query = query.filter(models.Purchase.item_name != hidden_name)
    return query


def get_or_create_admin_user(db: Session) -> models.User:
    admin_user = db.query(models.User).filter(models.User.email == ADMIN_EMAIL).first()
    if admin_user:
        admin_user.username = ADMIN_USERNAME
        admin_user.password_hash = hash_password(ADMIN_PASSWORD)
        admin_user.role = "admin"
        admin_user.status = "active"
    else:
        admin_user = models.User(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASSWORD),
            role="admin",
            status="active",
        )
        db.add(admin_user)

    db.commit()
    db.refresh(admin_user)
    return admin_user


def require_admin(admin_id: int, db: Session) -> models.User:
    admin = db.query(models.User).filter(models.User.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=401, detail="Admin login required")
    if admin.role != "admin" or admin.status != "active":
        raise HTTPException(status_code=403, detail="Admin access required")
    return admin


def require_active_user(user_id: int, db: Session) -> models.User:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.status == "suspended":
        raise HTTPException(status_code=403, detail="Account is suspended")
    return user


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/users/signup", response_model=schemas.AuthResponse)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = (
        db.query(models.User)
        .filter((models.User.username == user.username) | (models.User.email == user.email))
        .first()
    )

    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists")

    db_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=hash_password(user.password),
        role="student",
        status="active",
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return {
        "user": serialize_user(db_user),
        "message": "Account created successfully.",
    }


@router.post("/users/login", response_model=schemas.AuthResponse)
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    login_name = user.username.strip()

    if login_name.lower() == ADMIN_EMAIL.lower() and user.password == ADMIN_PASSWORD:
        admin_user = get_or_create_admin_user(db)
        return {
            "user": serialize_user(admin_user),
            "message": "Admin login successful",
        }

    db_user = (
        db.query(models.User)
        .filter((models.User.username == login_name) | (models.User.email == login_name))
        .first()
    )

    if not db_user or db_user.password_hash != hash_password(user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if db_user.status == "suspended":
        raise HTTPException(status_code=403, detail="Account is suspended")

    return {
        "user": serialize_user(db_user),
        "message": "Login successful",
    }


@router.post("/items", response_model=schemas.Item)
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)):
    seller = require_active_user(item.seller_id, db)

    db_item = models.Item(
        name=item.name,
        price=item.price,
        description=item.description,
        category=item.category,
        contact=item.contact,
        photo=item.photo,
        stock=item.stock,
        status=item_status(item.stock),
        seller_id=seller.id,
        seller_username=seller.username,
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.get("/items", response_model=list[schemas.Item])
def list_items(db: Session = Depends(get_db)):
    return (
        visible_item_query(db)
        .filter(models.Item.status != "removed")
        .order_by(models.Item.id.desc())
        .all()
    )


@router.get("/users/{seller_id}/items", response_model=list[schemas.Item])
def list_seller_items(seller_id: int, db: Session = Depends(get_db)):
    return (
        visible_item_query(db)
        .filter(models.Item.seller_id == seller_id)
        .filter(models.Item.status != "removed")
        .order_by(models.Item.id.desc())
        .all()
    )


@router.get("/items/{item_id}", response_model=schemas.Item)
def read_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    if db_item.status == "removed" or db_item.name in HIDDEN_ITEM_NAMES or db_item.name.startswith("__test_"):
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item


@router.put("/items/{item_id}", response_model=schemas.Item)
def update_item(item_id: int, item: schemas.ItemUpdate, seller_id: int, db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    if db_item.seller_id != seller_id:
        raise HTTPException(status_code=403, detail="You can only edit your own listings")
    require_active_user(seller_id, db)

    updates = item.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(db_item, field, value)

    db_item.status = item_status(db_item.stock)

    db.commit()
    db.refresh(db_item)
    return db_item


@router.post("/items/{item_id}/purchase", response_model=schemas.Item)
def purchase_item(item_id: int, buyer_id: int, db: Session = Depends(get_db)):
    buyer = require_active_user(buyer_id, db)

    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    if db_item.status == "removed":
        raise HTTPException(status_code=404, detail="Item not found")
    if db_item.seller_id == buyer.id:
        raise HTTPException(status_code=400, detail="You cannot purchase your own listing")
    if db_item.stock <= 0 or db_item.status == "sold":
        db_item.stock = 0
        db_item.status = "sold"
        db.commit()
        raise HTTPException(status_code=400, detail="Item is sold out")

    db_item.stock -= 1
    db_item.status = item_status(db_item.stock)
    db_purchase = models.Purchase(
        buyer_id=buyer.id,
        buyer_username=buyer.username,
        item_id=db_item.id,
        item_name=db_item.name,
        price=db_item.price,
        category=db_item.category,
        seller_id=db_item.seller_id,
        seller_username=db_item.seller_username,
        seller_contact=db_item.contact,
        quantity=1,
        total_amount=db_item.price,
        status="completed",
    )
    db.add(db_purchase)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.get("/users/{buyer_id}/purchases", response_model=list[schemas.Purchase])
def list_buyer_purchases(buyer_id: int, db: Session = Depends(get_db)):
    buyer = db.query(models.User).filter(models.User.id == buyer_id).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="User not found")

    return (
        buyer_purchase_query(db)
        .filter(models.Purchase.buyer_id == buyer_id)
        .order_by(models.Purchase.id.desc())
        .all()
    )


@router.delete("/items/{item_id}")
def delete_item(item_id: int, seller_id: int, db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    if db_item.seller_id != seller_id:
        raise HTTPException(status_code=403, detail="You can only remove your own listings")

    db.delete(db_item)
    db.commit()
    return {"message": "Listing removed successfully."}


@router.get("/admin/dashboard", response_model=schemas.AdminDashboard)
def admin_dashboard(admin_id: int, db: Session = Depends(get_db)):
    require_admin(admin_id, db)
    today = date.today()
    purchases = visible_purchase_query(db).order_by(models.Purchase.id.desc()).all()
    todays_sales = sum(
        purchase.total_amount or purchase.price
        for purchase in purchases
        if purchase.purchased_at and purchase.purchased_at.date() == today
    )

    return {
        "total_students": db.query(models.User).filter(models.User.role == "student").count(),
        "total_active_listings": visible_item_query(db).filter(models.Item.status == "available").count(),
        "total_orders": len(purchases),
        "todays_sales": todays_sales,
        "recent_orders": purchases[:5],
    }


@router.get("/admin/students", response_model=list[schemas.UserPublic])
def admin_students(admin_id: int, search: str = "", db: Session = Depends(get_db)):
    require_admin(admin_id, db)
    query = db.query(models.User).filter(models.User.role == "student")
    if search:
        like = f"%{search}%"
        query = query.filter((models.User.username.like(like)) | (models.User.email.like(like)))
    return query.order_by(models.User.id.desc()).all()


@router.post("/admin/students/{student_id}/suspend", response_model=schemas.UserPublic)
def admin_suspend_student(student_id: int, admin_id: int, db: Session = Depends(get_db)):
    require_admin(admin_id, db)
    student = db.query(models.User).filter(models.User.id == student_id, models.User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    student.status = "suspended"
    db.commit()
    db.refresh(student)
    return student


@router.post("/admin/students/{student_id}/reactivate", response_model=schemas.UserPublic)
def admin_reactivate_student(student_id: int, admin_id: int, db: Session = Depends(get_db)):
    require_admin(admin_id, db)
    student = db.query(models.User).filter(models.User.id == student_id, models.User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    student.status = "active"
    db.commit()
    db.refresh(student)
    return student


@router.get("/admin/listings", response_model=list[schemas.Item])
def admin_listings(admin_id: int, search: str = "", db: Session = Depends(get_db)):
    require_admin(admin_id, db)
    query = visible_item_query(db)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (models.Item.name.like(like))
            | (models.Item.category.like(like))
            | (models.Item.seller_username.like(like))
        )
    return query.order_by(models.Item.id.desc()).all()


@router.post("/admin/listings/{item_id}/remove", response_model=schemas.Item)
def admin_remove_listing(item_id: int, admin_id: int, removal: schemas.ListingRemoval, db: Session = Depends(get_db)):
    require_admin(admin_id, db)
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db_item.status = "removed"
    db_item.removed_reason = removal.reason
    db.commit()
    db.refresh(db_item)
    return db_item


@router.post("/admin/listings/{item_id}/restore", response_model=schemas.Item)
def admin_restore_listing(item_id: int, admin_id: int, db: Session = Depends(get_db)):
    require_admin(admin_id, db)
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db_item.status = item_status(db_item.stock)
    db_item.removed_reason = None
    db.commit()
    db.refresh(db_item)
    return db_item


@router.get("/admin/orders", response_model=list[schemas.Purchase])
def admin_orders(
    admin_id: int,
    search: str = "",
    status: str = "",
    order_date: str = "",
    db: Session = Depends(get_db),
):
    require_admin(admin_id, db)
    query = visible_purchase_query(db)
    if status:
        query = query.filter(models.Purchase.status == status)
    if search:
        like = f"%{search}%"
        search_filters = [
            models.Purchase.item_name.like(like),
            models.Purchase.buyer_username.like(like),
            models.Purchase.seller_username.like(like),
        ]
        if search.isdigit():
            search_filters.append(models.Purchase.id == int(search))
        query = query.filter(or_(*search_filters))
    orders = query.order_by(models.Purchase.id.desc()).all()

    if order_date:
        try:
            selected_date = date.fromisoformat(order_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Order date must be YYYY-MM-DD")
        orders = [
            order
            for order in orders
            if order.purchased_at and order.purchased_at.date() == selected_date
        ]

    return orders


@router.get("/admin/reports", response_model=schemas.AdminReport)
def admin_reports(admin_id: int, period: str = "daily", db: Session = Depends(get_db)):
    require_admin(admin_id, db)
    purchases = visible_purchase_query(db).order_by(models.Purchase.purchased_at.desc()).all()
    grouped = defaultdict(lambda: {"orders": 0, "items_sold": 0, "total_sales": 0})

    for purchase in purchases:
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
