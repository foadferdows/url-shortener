import redis
import os
import json
from typing import Optional


redis_client = redis.from_url(
    os.getenv("REDIS_URL", "redis://redis:6379/0"),
    decode_responses=True,
)



DEFAULT_TTL = 3600
HOT_LINK_TTL = 86400
HOT_LINK_THRESHOLD = 100


def cache_key(short_code: str) -> str:
    return f"link:{short_code}"



def get_cached_link(short_code: str) -> Optional[dict]:
    data = redis_client.get(cache_key(short_code))
    if data:
        return json.loads(data)
    return None


def set_cached_link(short_code: str, link_data:dict , ttl: int = DEFAULT_TTL) ->None:
    redis_client.setex(
        cache_key(short_code),
        ttl,
        json.dumps(link_data),
)



def delete_cached_link(short_code: str) -> int:
    key = f"clicks:{short_code}"
    count = redis_client.incr(key)
    return count




def increment_click_counter(short_code: str) -> int:
    """
    شمارنده کلیک رو توی Redis اضافه می‌کنه
    این write-through pattern هست — اول Redis، بعد DB
    عدد جدید رو برمی‌گردونه
    """
    key = f"clicks:{short_code}"
    count = redis_client.incr(key)
    return count


def check_rate_limit(identifier: str, limit: int, window: int = 60) -> bool:
    """
    چک می‌کنه آیا این IP/user از حد مجاز رد شده یا نه
    identifier: IP یا api_key
    limit: حداکثر تعداد request
    window: بازه زمانی به ثانیه (پیش‌فرض ۶۰ ثانیه)
    برمی‌گردونه True اگه مجاز، False اگه بلاک
    """
    key = f"rate:{identifier}"
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    results = pipe.execute()
    count = results[0]
    return count <= limit
