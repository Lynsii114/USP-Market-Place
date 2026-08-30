from pydantic import BaseModel, validator
from typing import Optional


class Item(BaseModel):
    id: Optional[int] = None
    name: str
    price: float

    class Config:
        orm_mode = True


class UserCreate(BaseModel):
    username: str
    email: str
    password: str

    @validator('email')
    def validate_usp_email(cls, v):
        """Validate that email belongs to USP domain"""
        if not v:
            raise ValueError("Email cannot be empty")
        
        valid_domains = ['@usp.ac.fj', '@students.usp.ac.fj', '@usp.edu.fj']
        email_lower = v.lower().strip()
        
        # Check if email ends with valid USP domain
        if not any(email_lower.endswith(domain) for domain in valid_domains):
            raise ValueError("Email must be a valid USP student email (e.g., student@usp.ac.fj)")
        
        # Basic email format validation
        if '@' not in email_lower or '.' not in email_lower:
            raise ValueError("Invalid email format")
        
        return v

    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        if not v or len(v) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Username can only contain letters, numbers, hyphens, and underscores")
        return v

    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if not v or len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class VerifyConfirmationCode(BaseModel):
    username: str
    confirmation_code: str


class UserPublic(BaseModel):
    id: int
    username: str
    email: str
    is_verified: bool = False

    class Config:
        orm_mode = True


class AuthResponse(BaseModel):
    user: UserPublic
    message: str = "success"
    confirmation_code: Optional[str] = None
