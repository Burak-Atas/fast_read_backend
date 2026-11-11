"""Small MongoDB-backed fixed-window rate limiter.

Shared by all worker processes because state lives in MongoDB. Each hit is a
document; a TTL index removes old hits automatically.
"""
from datetime import datetime, timezone

from flask import request

COLLECTION = "rate_limits"
_index_ready = False


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _ensure_index(collection):
    global _index_ready
    if not _index_ready:
        # Hits older than one day are dropped; no window here is longer.
        collection.create_index("created_at", expireAfterSeconds=86400)
        collection.create_index([("key", 1), ("created_at", 1)])
        _index_ready = True


def client_ip():
    return request.remote_addr or "unknown"


def too_many(db, key, limit, window):
    """Count hits for `key` inside `window` (timedelta)."""
    collection = db.db[COLLECTION]
    _ensure_index(collection)
    since = _utcnow() - window
    return collection.count_documents({"key": key, "created_at": {"$gt": since}}) >= limit


def hit(db, key):
    collection = db.db[COLLECTION]
    _ensure_index(collection)
    collection.insert_one({"key": key, "created_at": _utcnow()})


def check_and_hit(db, key, limit, window):
    """Record a hit and return True if the limit was already reached."""
    if too_many(db, key, limit, window):
        return True
    hit(db, key)
    return False


def clear(db, key):
    db.db[COLLECTION].delete_many({"key": key})
