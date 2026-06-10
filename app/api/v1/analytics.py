from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, text
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.models.link import Link
from app.models.visit import Visit
from app.schemas.envelope import success

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


def get_current_user(x_api_key: str = Header(...), db: Session = Depends(get_db)) -> User:
    user = db.query(User).filter(User.api_key == x_api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user


# ← /compare باید قبل از /{short_code} باشه
@router.get("/compare")
def compare_links(
    codes: str = Query(..., description="Comma-separated short codes, e.g. aB3kR9x,pQ7mN2j"),
    days: int = Query(default=30, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    چند لینک رو با هم مقایسه می‌کنه
    مثال: /api/v1/analytics/compare?codes=aB3kR9x,pQ7mN2j&days=30
    """
    short_code_list = [c.strip() for c in codes.split(",") if c.strip()]

    if not short_code_list:
        raise HTTPException(status_code=400, detail="At least one short code required")

    if len(short_code_list) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 links per comparison")

    result = []

    for short_code in short_code_list:
        link = db.query(Link).filter(
            Link.short_code == short_code,
            Link.user_id == current_user.id,
        ).first()

        if not link:
            continue

        daily_visits = db.query(
            cast(Visit.visited_at, Date).label("date"),
            func.count(Visit.id).label("count")
        ).filter(
            Visit.link_id == link.id,
            Visit.visited_at >= func.now() - text(f"interval '{days} days'")
        ).group_by(
            cast(Visit.visited_at, Date)
        ).order_by(
            cast(Visit.visited_at, Date)
        ).all()

        result.append({
            "short_code": short_code,
            "original_url": link.original_url,
            "total_clicks": link.click_count,
            "daily_visits": [
                {"date": str(r.date), "count": r.count}
                for r in daily_visits
            ],
        })

    return success(
        data=result,
        meta={"period_days": days, "links_compared": len(result)}
    )


@router.get("")
def get_all_analytics(
    days: int = Query(default=30, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_link_ids = [
        l.id for l in db.query(Link.id).filter(
            Link.user_id == current_user.id
        ).all()
    ]

    if not user_link_ids:
        return success({
            "top_browsers": [],
            "top_referrers": [],
            "daily_visits": [],
        })

    top_browsers = db.query(
        Visit.browser,
        func.count(Visit.id).label("count")
    ).filter(
        Visit.link_id.in_(user_link_ids),
        Visit.browser.isnot(None)
    ).group_by(Visit.browser).order_by(func.count(Visit.id).desc()).limit(5).all()

    top_referrers = db.query(
        Visit.referrer,
        func.count(Visit.id).label("count")
    ).filter(
        Visit.link_id.in_(user_link_ids),
        Visit.referrer.isnot(None)
    ).group_by(Visit.referrer).order_by(func.count(Visit.id).desc()).limit(5).all()

    daily_visits = db.query(
        cast(Visit.visited_at, Date).label("date"),
        func.count(Visit.id).label("count")
    ).filter(
        Visit.link_id.in_(user_link_ids),
        Visit.visited_at >= func.now() - text(f"interval '{days} days'")
    ).group_by(
        cast(Visit.visited_at, Date)
    ).order_by(
        cast(Visit.visited_at, Date)
    ).all()

    return success({
        "period_days": days,
        "top_browsers": [
            {"browser": r.browser, "count": r.count}
            for r in top_browsers
        ],
        "top_referrers": [
            {"referrer": r.referrer, "count": r.count}
            for r in top_referrers
        ],
        "daily_visits": [
            {"date": str(r.date), "count": r.count}
            for r in daily_visits
        ],
    })


# ← /{short_code} باید آخر باشه
@router.get("/{short_code}")
def get_link_analytics(
    short_code: str,
    days: int = Query(default=30, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    link = db.query(Link).filter(
        Link.short_code == short_code,
        Link.user_id == current_user.id,
    ).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    total_visits = db.query(Visit).filter(Visit.link_id == link.id).count()

    by_browser = db.query(
        Visit.browser,
        func.count(Visit.id).label("count")
    ).filter(
        Visit.link_id == link.id,
        Visit.browser.isnot(None)
    ).group_by(Visit.browser).order_by(func.count(Visit.id).desc()).limit(10).all()

    by_device = db.query(
        Visit.device_type,
        func.count(Visit.id).label("count")
    ).filter(
        Visit.link_id == link.id
    ).group_by(Visit.device_type).all()

    by_country = db.query(
        Visit.country,
        func.count(Visit.id).label("count")
    ).filter(
        Visit.link_id == link.id,
        Visit.country.isnot(None)
    ).group_by(Visit.country).order_by(func.count(Visit.id).desc()).limit(10).all()

    top_referrers = db.query(
        Visit.referrer,
        func.count(Visit.id).label("count")
    ).filter(
        Visit.link_id == link.id,
        Visit.referrer.isnot(None)
    ).group_by(Visit.referrer).order_by(func.count(Visit.id).desc()).limit(10).all()

    daily_visits = db.query(
        cast(Visit.visited_at, Date).label("date"),
        func.count(Visit.id).label("count")
    ).filter(
        Visit.link_id == link.id,
        Visit.visited_at >= func.now() - text(f"interval '{days} days'")
    ).group_by(
        cast(Visit.visited_at, Date)
    ).order_by(
        cast(Visit.visited_at, Date)
    ).all()

    return success({
        "short_code": short_code,
        "total_clicks": link.click_count,
        "total_visits_recorded": total_visits,
        "period_days": days,
        "by_browser": [
            {"browser": r.browser, "count": r.count}
            for r in by_browser
        ],
        "by_device": [
            {"device": r.device_type, "count": r.count}
            for r in by_device
        ],
        "by_country": [
            {"country": r.country, "count": r.count}
            for r in by_country
        ],
        "top_referrers": [
            {"referrer": r.referrer, "count": r.count}
            for r in top_referrers
        ],
        "daily_visits": [
            {"date": str(r.date), "count": r.count}
            for r in daily_visits
        ],
    })
