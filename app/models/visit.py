from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True)
    link_id = Column(Integer, ForeignKey("links.id"), nullable=False)

    ip_address = Column(String(15), nullable=True)
    browser = Column(String(50), nullable=True)
    os = Column(String(50), nullable=True)
    device_type = Column(String(20), nullable=True)
    referrer = Column(String, nullable=True)
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)

    visited_at = Column(DateTime(timezone=True), server_default=func.now())

    link = relationship("Link", back_populates="visits")

    # Index برای time-series queries
    __table_args__ = (
        Index("ix_visits_link_visited_at", "link_id", "visited_at"),
        Index("ix_visits_visited_at", "visited_at"),
    )
