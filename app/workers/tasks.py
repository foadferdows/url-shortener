from celery import Celery
from sqlalchemy.orm import Session
import os

celery_app = Celery(
    "url_shortener",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2"),
)

@celery_app.task
def test_task():
    return "Celery is working!"


@celery_app.task(bind=True, max_retries=3)
def record_visit(self, link_id: int, visit_data: dict):
    try:
        from app.database import SessionLocal
        from app.models.visit import Visit
        from app.models.link import Link
        from app.cache.redis_client import redis_client


        db = SessionLocal()
        try:
            visit = Visit(
                link_id=link_id,
                ip_address=visit_data.get("ip_address"),
                browser=visit_data.get("browser"),
                os=visit_data.get("os"),
                device_type=visit_data.get("device_type"),
                referrer=visit_data.get("referrer"),
                country=visit_data.get("country"),
                city=visit_data.get("city"),
            )
            db.add(visit)

            redis_key = f"clicks:{visit_data.get('short_code')}"
            redis_count = redis_client.get(redis_key)
            if redis_count:
                link = db.query(Link).filter(Link.id == link_id).first()
                if link:
                    link.click_count = int(redis_count)

            db.commit()
        finally:
            db.close()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=3)
def trigger_webhook(self, link_id: int, click_count: int):
    """
    وقتی کلیک به آستانه رسید، webhook رو صدا می‌زنه
    """
    try:
        import httpx
        from app.database import SessionLocal
        from app.models.link import Link

        db = SessionLocal()
        try:
            link = db.query(Link).filter(Link.id == link_id).first()
            if not link or not link.webhook_url or link.webhook_triggered:
                return

            # payload ای که به webhook می‌فرستیم
            payload = {
                "event": "click_threshold_reached",
                "short_code": link.short_code,
                "original_url": link.original_url,
                "click_count": click_count,
                "threshold": link.webhook_threshold,
            }

            # webhook رو صدا بزن
            with httpx.Client(timeout=10) as client:
                response = client.post(link.webhook_url, json=payload)
                response.raise_for_status()

            # علامت بزن که webhook فیر شده
            link.webhook_triggered = True
            db.commit()

        finally:
            db.close()

    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=3)
def record_visit(self, link_id: int, visit_data: dict):
    try:
        import httpx
        from app.database import SessionLocal
        from app.models.visit import Visit
        from app.models.link import Link
        from app.cache.redis_client import redis_client

        db = SessionLocal()
        try:
            # GeoIP lookup
            country = None
            city = None
            ip = visit_data.get("ip_address")

            if ip and ip != "0.0.0.0" and not ip.startswith("127.") and not ip.startswith("192.168."):
                try:
                    with httpx.Client(timeout=3) as client:
                        geo_response = client.get(f"http://ip-api.com/json/{ip}?fields=country,city,status")
                        if geo_response.status_code == 200:
                            geo_data = geo_response.json()
                            if geo_data.get("status") == "success":
                                country = geo_data.get("country")
                                city = geo_data.get("city")
                except Exception:
                    pass  # GeoIP خطا داد — ادامه بده بدون location

            # ذخیره بازدید
            visit = Visit(
                link_id=link_id,
                ip_address=visit_data.get("ip_address"),
                browser=visit_data.get("browser"),
                os=visit_data.get("os"),
                device_type=visit_data.get("device_type"),
                referrer=visit_data.get("referrer"),
                country=country,
                city=city,
            )
            db.add(visit)

            # click_count رو از Redis بخون و توی DB آپدیت کن
            redis_key = f"clicks:{visit_data.get('short_code')}"
            redis_count = redis_client.get(redis_key)
            if redis_count:
                link = db.query(Link).filter(Link.id == link_id).first()
                if link:
                    link.click_count = int(redis_count)

            db.commit()
        finally:
            db.close()

    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
