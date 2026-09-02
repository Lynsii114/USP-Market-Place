import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from . import models, schemas
from .db import get_db

router = APIRouter()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def serialize_user(user: models.User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
    }


def item_status(stock: int) -> str:
    return "sold" if stock <= 0 else "available"


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
    db_user = db.query(models.User).filter(models.User.username == user.username).first()

    if not db_user or db_user.password_hash != hash_password(user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "user": serialize_user(db_user),
        "message": "Login successful",
    }


@router.post("/items", response_model=schemas.Item)
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)):
    seller = db.query(models.User).filter(models.User.id == item.seller_id).first()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")

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
        db.query(models.Item)
        .filter(~models.Item.name.startswith("__test_"))
        .order_by(models.Item.id.desc())
        .all()
    )


@router.get("/users/{seller_id}/items", response_model=list[schemas.Item])
def list_seller_items(seller_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.Item)
        .filter(models.Item.seller_id == seller_id)
        .order_by(models.Item.id.desc())
        .all()
    )


@router.get("/items/{item_id}", response_model=schemas.Item)
def read_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item


@router.put("/items/{item_id}", response_model=schemas.Item)
def update_item(item_id: int, item: schemas.ItemUpdate, seller_id: int, db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    if db_item.seller_id != seller_id:
        raise HTTPException(status_code=403, detail="You can only edit your own listings")

    updates = item.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(db_item, field, value)

    db_item.status = item_status(db_item.stock)

    db.commit()
    db.refresh(db_item)
    return db_item


@router.post("/items/{item_id}/purchase", response_model=schemas.Item)
def purchase_item(item_id: int, buyer_id: int, db: Session = Depends(get_db)):
    buyer = db.query(models.User).filter(models.User.id == buyer_id).first()
    if not buyer:
        raise HTTPException(status_code=401, detail="Login required to purchase items")

    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
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
        db.query(models.Purchase)
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
