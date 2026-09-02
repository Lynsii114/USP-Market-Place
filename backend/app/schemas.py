import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class ItemBase(BaseModel):
    name: str
    price: float
    description: str
    category: str
    contact: str
    photo: Optional[str] = None
    stock: int

    @field_validator("stock")
    @classmethod
    def validate_stock(cls, value):
        if value < 0:
            raise ValueError("Stock cannot be negative")
        return value


class ItemCreate(ItemBase):
    seller_id: int


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
    category: Optional[str] = None
    contact: Optional[str] = None
    photo: Optional[str] = None
    stock: Optional[int] = None

    @field_validator("stock")
    @classmethod
    def validate_stock(cls, value):
        if value is not None and value < 0:
            raise ValueError("Stock cannot be negative")
        return value


class Item(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    seller_id: int
    seller_username: str
    removed_reason: Optional[str] = None
    created_at: Optional[datetime] = None


class UserCreate(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_usp_email(cls, value):
        if not value:
            raise ValueError("Email cannot be empty")

        email_lower = value.lower().strip()
        pattern = r"^s\d{8}@student\.usp\.ac\.fj$"
        if not re.match(pattern, email_lower):
            raise ValueError("Email must be in format: SXXXXXXXX@student.usp.ac.fj, where X is a number")

        return value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value):
        if not value or len(value) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if not value.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can only contain letters, numbers, hyphens, and underscores")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        if not value or len(value) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return value


class UserLogin(BaseModel):
    username: str
    password: str


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str = "student"
    status: str = "active"
    created_at: Optional[datetime] = None


class AuthResponse(BaseModel):
    user: UserPublic
    message: str = "success"


class Purchase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    buyer_id: int
    buyer_username: str
    item_id: int
    item_name: str
    price: float
    category: str
    seller_id: int
    seller_username: str
    seller_contact: str
    quantity: int = 1
    total_amount: float = 0
    status: str = "completed"
    purchased_at: datetime


class ListingRemoval(BaseModel):
    reason: str


class AdminDashboard(BaseModel):
    total_students: int
    total_active_listings: int
    total_orders: int
    todays_sales: float
    recent_orders: list[Purchase]


class ReportRow(BaseModel):
    date: str
    orders: int
    items_sold: int
    total_sales: float


class AdminReport(BaseModel):
    total_orders: int
    total_items_sold: int
    total_sales: float
    rows: list[ReportRow]
