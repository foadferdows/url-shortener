from fastapi import APIRouter, Depends, HTTPException, Request
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
from app.services.analytics import collect_visit_data
from app.workers.tasks import record_visit, trigger_webhook



router = APIRouter(tags=["Redirect"])


@router.get("/{short_code}")
def redirect(short_code: str, request: Request, db: Session = Depends(get_db)):
    """
    ۱. Cache-Aside: اول Redis، بعد DB
    ۲. Redirect فوری
    ۳. Analytics در پس‌زمینه با Celery
    """
    cached = get_cached_link(short_code)

    if cached:
        original_url = cached["original_url"]
        link_id = cached.get("link_id")
    else:
        link = db.query(Link).filter(
            Link.short_code == short_code,
            Link.is_active == True,
        ).first()

        if not link:
            raise HTTPException(status_code=404, detail="Link not found")

        if link.expires_at and link.expires_at < datetime.now(timezone.utc):
            link.is_active = False
            db.commit()
            delete_cached_link(short_code)
            raise HTTPException(status_code=410, detail="Link has expired")

        original_url = link.original_url
        link_id = link.id

        set_cached_link(short_code, {
            "original_url": original_url,
            "link_id": link_id,
            "click_count": link.click_count,
        })

    click_count = increment_click_counter(short_code)

    if click_count == HOT_LINK_THRESHOLD:
        set_cached_link(short_code, {
            "original_url": original_url,
            "link_id": link_id
        }, HOT_LINK_TTL)

    if link_id:
        visit_data = collect_visit_data(request, short_code)
        record_visit.delay(link_id, visit_data)  # .delay یعنی async اجرا کن
        cached = get_cached_link(short_code) or {}
        webhook_threshold = cached.get("webhook_threshold")
        webhook_url = cached.get("webhook_url")

    if webhook_url and webhook_threshold and click_count == webhook_threshold:
        trigger_webhook.delay(link_id, click_count)


    return RedirectResponse(url=original_url, status_code=302)
