from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .db import Base, engine
from .routes import router as api_router

load_dotenv()
Base.metadata.create_all(bind=engine)

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
