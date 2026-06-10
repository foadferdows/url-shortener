from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True)
    short_code = Column(String(20), unique=True, nullable=False, index=True)
    original_url = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    custom_alias = Column(String(50), unique=True, nullable=True)
    password_hash = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    click_count = Column(Integer, default=0)

    webhook_url = Column(String, nullable=True)
    webhook_threshold = Column(Integer, nullable=True)
    webhook_triggered = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="links")
    visits = relationship("Visit", back_populates="link")
