from app.schemas.envelope import success
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.user import User
from app.models.link import Link
from app.models.visit import Visit

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


def get_current_user(x_api_key: str = Header(...), db: Session = Depends(get_db)) -> User:
    user = db.query(User).filter(User.api_key == x_api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user


@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_links = db.query(Link).filter(
        Link.user_id == current_user.id,
        Link.is_active == True,
    ).count()

    total_clicks = db.query(
        func.sum(Link.click_count)
    ).filter(
        Link.user_id == current_user.id,
    ).scalar() or 0

    top_link = db.query(Link).filter(
        Link.user_id == current_user.id,
    ).order_by(Link.click_count.desc()).first()

    user_link_ids = [
        l.id for l in db.query(Link.id).filter(
            Link.user_id == current_user.id
        ).all()
    ]

    by_device = db.query(
        Visit.device_type,
        func.count(Visit.id).label("count")
    ).filter(
        Visit.link_id.in_(user_link_ids)
    ).group_by(Visit.device_type).all()

    return success({
        "total_links": total_links,
        "total_clicks": total_clicks,
        "top_link": {
            "short_code": top_link.short_code,
            "click_count": top_link.click_count,
        } if top_link else None,
        "by_device": [
            {"device": r.device_type, "count": r.count}
            for r in by_device
        ],
    })

