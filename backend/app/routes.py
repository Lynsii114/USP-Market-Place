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
        seller_id=seller.id,
        seller_username=seller.username,
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.get("/items", response_model=list[schemas.Item])
def list_items(db: Session = Depends(get_db)):
    return db.query(models.Item).order_by(models.Item.id.desc()).all()


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

    db.commit()
    db.refresh(db_item)
    return db_item


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
