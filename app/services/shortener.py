import random
import string


BASE62_CHARS = string.ascii_letters + string.digits


def generate_random_code(length: int = 7) -> str:
    return ''.join(random.choices(BASE62_CHARS , k=length))



from sqlalchemy.orm import Session
from app.models.short_code_pool import ShortCodePool


POOL_MIN_SIZE = 500
POOL_REFILL_SIZE = 1000

def get_pool_size(db: Session) -> int:
    return db.query(ShortCodePool).filter(ShortCodePool.is_used == False).count()


def refill_pool(db: Session) -> None:
    existing_codes = {
        row.code for row in db.query(ShortCodePool.code).all()
    }
    
    new_codes = []
    attempts = 0


    while len(new_codes) < POOL_REFILL_SIZE and attempts < POOL_REFILL_SIZE *3 :
        code = generate_random_code()
        if code not in existing_codes:
            existing_codes.add(code)
            new_codes.append(ShortCodePool(code=code))
        attempts += 1
    
    db.bulk_save_objects(new_codes)
    db.commit()


def get_code_from_pool(db: Session) -> str:
    if get_pool_size(db) < POOL_MIN_SIZE:
        refill_pool(db)

    entry = db.query(ShortCodePool).filter(ShortCodePool.is_used == False).with_for_update().first()


    if not entry:
        refill_pool(db)
        entry = db.query(ShortCodePool).filter(ShortCodePool.is_used == False).with_for_update().first()

    entry.is_used = True
    db.commit()

    return entry.code








