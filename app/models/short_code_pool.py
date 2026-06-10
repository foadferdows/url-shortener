from sqlalchemy import Column, Integer , String, Boolean , DateTime
from sqlalchemy.sql import func
from app.database import Base

class ShortCodePool(Base):
    __tablename__ = "short_code_pool"
    id = Column(Integer , primary_key=True)
    code = Column(String(20), unique=True, nullable=False , index=True)
    is_used = Column(Boolean, default=False , index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
