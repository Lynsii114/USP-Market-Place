from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text

from .db import Base, engine
from .routes import router as api_router

load_dotenv()
Base.metadata.create_all(bind=engine)


def ensure_item_columns():
    inspector = inspect(engine)
    if "items" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("items")}
    required_columns = {
        "description": "VARCHAR(1000) NOT NULL DEFAULT ''",
        "category": "VARCHAR(64) NOT NULL DEFAULT 'Other'",
        "contact": "VARCHAR(128) NOT NULL DEFAULT ''",
        "photo": "LONGTEXT NULL" if engine.dialect.name == "mysql" else "TEXT NULL",
        "stock": "INTEGER NOT NULL DEFAULT 1",
        "status": "VARCHAR(32) NOT NULL DEFAULT 'available'",
        "seller_id": "INTEGER NOT NULL DEFAULT 0",
        "seller_username": "VARCHAR(64) NOT NULL DEFAULT 'Unknown'",
    }

    with engine.begin() as connection:
        for column_name, column_definition in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(f"ALTER TABLE items ADD COLUMN {column_name} {column_definition}"))

        if engine.dialect.name == "mysql" and "photo" in existing_columns:
            connection.execute(text("ALTER TABLE items MODIFY photo LONGTEXT NULL"))


ensure_item_columns()

app = FastAPI(title="USP Market Place API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    errors = exc.errors()
    detail = "Validation error"

    if errors:
        error = errors[0]
        detail = error.get("ctx", {}).get("error") or error.get("msg", "Invalid input")

    return JSONResponse(status_code=422, content={"detail": str(detail)})


app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "USP Market Place API"}
