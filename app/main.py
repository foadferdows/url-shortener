from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import FastAPI
from dotenv import load_dotenv
from app.database import engine, Base, SessionLocal
import app.models
from app.services.shortener import get_pool_size , refill_pool
from app.api.v1 import auth, links, redirect, analytics , dashboard
from app.api.v1.middleware import rate_limit_middleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.schemas.envelope import error


load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="URL Shortener",
    description="A URL shortening service with analytics",
    version="1.0.0",
)

app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)


app.include_router(auth.router)
app.include_router(analytics.router)
app.include_router(links.router)
app.include_router(redirect.router)
app.include_router(dashboard.router)

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        if get_pool_size(db) < 500:
            print("Filling short code pool...")
            refill_pool(db)
            print("Pool ready")
    finally:
        db.close()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(status_code=404, content=error("Not found"))

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    return JSONResponse(status_code=422, content=error(str(exc.errors())))

