from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True)
    link_id = Column(Integer, ForeignKey("links.id"), nullable=False)

    # اطلاعات بازدیدکننده
    ip_address = Column(String(15), nullable=True)   # آخرین octet حذف شده
    browser = Column(String(50), nullable=True)
    os = Column(String(50), nullable=True)
    device_type = Column(String(20), nullable=True)  # Mobile/Desktop/Tablet
    referrer = Column(String, nullable=True)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)

    visited_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    link = relationship("Link", back_populates="visits")
