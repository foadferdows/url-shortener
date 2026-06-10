from user_agents import parse as parse_ua
from typing import Optional


def anonymize_ip(ip: str) -> str:
    if not ip:
        return None
    parts = ip.split(".")
    if len(parts) == 4:
        parts[-1] = "0"
        return ".".join(parts)
    return ip


def parse_user_agent(user_agent_string: str) -> dict:
    if not user_agent_string:
        return {"browser": None, "os": None, "device_type": "Unknown"}

    ua = parse_ua(user_agent_string)

    if ua.is_mobile:
        device_type = "Mobile"
    elif ua.is_tablet:
        device_type = "Tablet"
    else:
        device_type = "Desktop"

    return {
        "browser": ua.browser.family,
        "os": ua.os.family,
        "device_type": device_type,
    }


def collect_visit_data(request, short_code: str) -> dict:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        ip = forwarded_for.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else None

    user_agent_string = request.headers.get("user-agent", "")
    ua_data = parse_user_agent(user_agent_string)

    return {
        "short_code": short_code,
        "ip_address": anonymize_ip(ip),
        "browser": ua_data["browser"],
        "os": ua_data["os"],
        "device_type": ua_data["device_type"],
        "referrer": request.headers.get("referer"),
        "country": None,   # بعداً با GeoIP پر می‌شه
        "city": None,
    }
