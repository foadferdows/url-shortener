from fastapi import APIRouter, Depends, HTTPException, Header
from app.schemas.envelope import success
from datetime import timezone

from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.models.link import Link
from app.services.shortener import get_code_from_pool
from app.cache.redis_client import delete_cached_link
import os

router = APIRouter(prefix="/api/v1/links", tags=["Links"])


def get_current_user(x_api_key: str = Header(...), db: Session = Depends(get_db)) -> User:
    user = db.query(User).filter(User.api_key == x_api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user


class CreateLinkRequest(BaseModel):
    url: HttpUrl
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None
    password: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_threshold: Optional[int] = None  

class LinkResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("")
def create_link(
    request: CreateLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if request.custom_alias:
        existing = db.query(Link).filter(
            Link.short_code == request.custom_alias
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="This alias is already taken")
        short_code = request.custom_alias
    else:
        short_code = get_code_from_pool(db)

    link = Link(
        short_code=short_code,
        original_url=str(request.url),
        user_id=current_user.id,
        expires_at=request.expires_at,
        webhook_url=request.webhook_url,        
        webhook_threshold=request.webhook_threshold,
    )


    db.add(link)
    db.commit()
    db.refresh(link)

    base_url = os.getenv("BASE_URL", "http://localhost:8000")


    return success({
        "short_code": link.short_code,
        "short_url": f"{base_url}/{link.short_code}",
        "original_url": link.original_url,
        "created_at": link.created_at.isoformat(),
    })


@router.get("")
def get_links(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cursor: Optional[str] = None,
    limit: int = 20,

):
    base_url = os.getenv("BASE_URL", "http://localhost:8000")

    query = db.query(Link).filter(
        Link.user_id == current_user.id,
        Link.is_active == True,
    )

    if cursor:
        try:
            cursor_time = datetime.strptime(cursor, "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc)

            query = query.filter(Link.created_at < cursor_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor format")

    links = query.order_by(Link.created_at.desc()).limit(limit + 1).all()

    has_more = len(links) > limit
    if has_more:
        links = links[:limit]

    next_cursor = None
    if has_more and links:
        next_cursor = links[-1].created_at.strftime("%Y-%m-%dT%H:%M:%S.%f")

    return success(
        data=[

        {
            "short_code": l.short_code,
            "short_url": f"{base_url}/{l.short_code}",
            "original_url": l.original_url,
            "created_at": l.created_at.isoformat(),
        }
        for l in links
        ],
        meta={
            "next_cursor": next_cursor,
            "has_more": has_more,
            "limit": limit,
        }
    )


@router.delete("/{short_code}")
def delete_link(
    short_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """لینک رو غیرفعال می‌کنه (حذف نمی‌کنه، فقط is_active=False)"""
    link = db.query(Link).filter(
        Link.short_code == short_code,
        Link.user_id == current_user.id,
    ).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    link.is_active = False
    db.commit()

    delete_cached_link(short_code)

    return success({"message": "Link deleted successfully"})

