from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import get_db
from app.models.link import Link
from app.cache.redis_client import (
    get_cached_link,
    set_cached_link,
    increment_click_counter,
    DEFAULT_TTL,
    HOT_LINK_TTL,
    HOT_LINK_THRESHOLD,
)

router = APIRouter(tags=["Redirect"])


@router.get("/{short_code}")
def redirect(short_code: str, db: Session = Depends(get_db)):

    cached = get_cached_link(short_code)

    if cached:
        original_url = cached["original_url"]
    else:
        link = db.query(Link).filter(
            Link.short_code == short_code,
            Link.is_active == True,
        ).first()

        if not link:
            raise HTTPException(status_code=404, detail="Link not found")

        if link.expires_at and link.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Link has expired")

        original_url = link.original_url

        set_cached_link(short_code, {
            "original_url": original_url,
            "click_count": link.click_count,
        })

    click_count = increment_click_counter(short_code)

    if click_count == HOT_LINK_THRESHOLD:
        set_cached_link(short_code, {"original_url": original_url}, HOT_LINK_TTL)

    return RedirectResponse(url=original_url, status_code=302)
