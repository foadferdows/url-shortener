from fastapi import Request, HTTPException
from app.cache.redis_client import check_rate_limit


def get_rate_limit_identifier(request: Request) -> tuple[str, int]:
    """
    تشخیص می‌ده کاربر authenticated هست یا نه
    و limit مناسب رو برمی‌گردونه
    """
    api_key = request.headers.get("x-api-key")
    if api_key:
        return api_key, 1000  # authenticated: 1000 req/min
    
    # IP رو بگیر
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0] if forwarded else request.client.host
    return ip, 100  # unauthenticated: 100 req/min


async def rate_limit_middleware(request: Request, call_next):
    """
    Middleware — قبل از هر request اجرا می‌شه
    """
    # health و docs رو از rate limit معاف کن
    if request.url.path in ["/health", "/docs", "/openapi.json"]:
        return await call_next(request)

    identifier, limit = get_rate_limit_identifier(request)

    if not check_rate_limit(identifier, limit):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {limit} requests per minute."
        )

    return await call_next(request)
