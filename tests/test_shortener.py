from app.services.shortener import generate_random_code, get_code_from_pool
from tests.conftest import TestingSessionLocal, engine
from app.database import Base


def test_generate_random_code_length():
    """کد باید ۷ کاراکتر باشه"""
    code = generate_random_code()
    assert len(code) == 7


def test_generate_random_code_charset():
    """کد باید فقط از کاراکترهای Base62 باشه"""
    import string
    valid_chars = set(string.ascii_letters + string.digits)
    for _ in range(100):
        code = generate_random_code()
        assert all(c in valid_chars for c in code)


def test_generate_unique_codes():
    """۱۰۰۰ کد تولیدشده باید همه یکتا باشن"""
    codes = {generate_random_code() for _ in range(1000)}
    assert len(codes) == 1000


def test_pool_refill(setup_database):
    """pool باید بعد از refill پر بشه"""
    from app.services.shortener import refill_pool, get_pool_size
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        refill_pool(db)
        size = get_pool_size(db)
        assert size == 1000
    finally:
        db.close()
