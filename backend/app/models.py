from sqlalchemy import Column, Float, Integer, String, Text
from .db import Base


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256), nullable=False)
    price = Column(Float, nullable=False)
    description = Column(String(1000), nullable=False)
    category = Column(String(64), nullable=False)
    contact = Column(String(128), nullable=False)
    photo = Column(Text, nullable=True)
    seller_id = Column(Integer, nullable=False, index=True)
    seller_username = Column(String(64), nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
