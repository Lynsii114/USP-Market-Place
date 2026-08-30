import hashlib
import random
import string

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from . import models, schemas
from .db import get_db

router = APIRouter()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def generate_confirmation_code() -> str:
    """Generate a 6-digit confirmation code"""
    return ''.join(random.choices(string.digits, k=6))


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

    confirmation_code = generate_confirmation_code()
    
    db_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=hash_password(user.password),
        confirmation_code=confirmation_code,
        is_verified=False,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    print(f"\n📧 Confirmation code for {db_user.email}: {confirmation_code}\n")

    return {
        "user": {
            "id": db_user.id,
            "username": db_user.username,
            "email": db_user.email,
            "is_verified": db_user.is_verified,
        },
        "message": "Account created! Check your email for verification code.",
        "confirmation_code": confirmation_code,
    }


@router.post("/users/verify", response_model=schemas.AuthResponse)
def verify_email(data: schemas.VerifyConfirmationCode, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == data.username).first()
    
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if db_user.is_verified:
        raise HTTPException(status_code=400, detail="Email already verified")
    
    if db_user.confirmation_code != data.confirmation_code:
        raise HTTPException(status_code=400, detail="Invalid confirmation code")
    
    db_user.is_verified = True
    db_user.confirmation_code = None
    db.commit()
    db.refresh(db_user)
    
    return {
        "user": {
            "id": db_user.id,
            "username": db_user.username,
            "email": db_user.email,
            "is_verified": db_user.is_verified,
        },
        "message": "Email verified successfully! You can now login.",
    }


@router.post("/users/login", response_model=schemas.AuthResponse)
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if db_user.password_hash != hash_password(user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "user": {
            "id": db_user.id,
            "username": db_user.username,
            "email": db_user.email,
        },
        "message": "Login successful",
    }


@router.post("/items", response_model=schemas.Item)
def create_item(item: schemas.Item, db: Session = Depends(get_db)):
    db_item = models.Item(name=item.name, price=item.price)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.get('/items/{item_id}', response_model=schemas.Item)
def read_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail='Item not found')
    return db_item


@router.get('/items', response_model=list[schemas.Item])
def list_items(db: Session = Depends(get_db)):
    return db.query(models.Item).all()
