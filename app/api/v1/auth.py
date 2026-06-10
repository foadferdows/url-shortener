from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.envelope import success
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app.models.user import User
import secrets
import bcrypt

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterResponse(BaseModel):
    email: str
    api_key: str
    message: str


@router.post("/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # مستقیم از bcrypt استفاده می‌کنیم
    hashed_password = bcrypt.hashpw(
        request.password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    api_key = f"sk_{secrets.token_urlsafe(32)}"

    user = User(
        email=request.email,
        hashed_password=hashed_password,
        api_key=api_key,
    )
    db.add(user)
    db.commit()

    return success({
        "email": user.email,
        "api_key": api_key,
        "message": "Registration successful. Save your API key — it won't be shown again.",
    })

