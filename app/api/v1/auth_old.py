from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from app.database import get_db
from app.models.user import User
import secrets

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# شکل داده‌ای که کاربر می‌فرسته
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


# شکل جوابی که ما می‌دیم
class RegisterResponse(BaseModel):
    email: str
    api_key: str
    message: str


@router.post("/register", response_model=RegisterResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    ثبت‌نام کاربر جدید
    - ایمیل و رمز می‌گیره
    - API Key یکتا می‌سازه
    - کاربر رو توی دیتابیس ذخیره می‌کنه
    """
    # چک کن این ایمیل قبلاً ثبت نشده باشه
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # رمز عبور رو hash کن (هیچ‌وقت رمز خام ذخیره نکن)
    hashed_password = pwd_context.hash(request.password)

    # یه API Key تصادفی بساز
    api_key = f"sk_{secrets.token_urlsafe(32)}"

    # کاربر رو بساز و ذخیره کن
    user = User(
        email=request.email,
        hashed_password=hashed_password,
        api_key=api_key,
    )
    db.add(user)
    db.commit()

    return RegisterResponse(
        email=user.email,
        api_key=api_key,
        message="Registration successful. Save your API key — it won't be shown again.",
    )
