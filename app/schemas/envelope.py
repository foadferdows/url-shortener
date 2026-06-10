from pydantic import BaseModel
from typing import Any, Optional


class ResponseEnvelope(BaseModel):
    data: Any = None
    meta: Optional[dict] = None
    errors: Optional[str] = None


def success(data: Any, meta: dict = None) -> dict:
    """جواب موفق"""
    return ResponseEnvelope(data=data, meta=meta).model_dump()


def error(message: str) -> dict:
    """جواب خطا"""
    return ResponseEnvelope(errors=message).model_dump()
