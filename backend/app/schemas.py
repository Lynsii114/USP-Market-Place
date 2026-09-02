import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class Item(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    name: str
    price: float


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


class AuthResponse(BaseModel):
    user: UserPublic
    message: str = "success"
