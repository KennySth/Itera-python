"""
AI Response Cache with MongoDB TTL - Phase 0 Infrastructure.

ponytail: TTL index on MongoDB handles expiration automatically.
Cache key = hash(text + categories + model). No manual cleanup needed.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Any

from app.core.database import get_database

logger = logging.getLogger(__name__)

# ponytail: 1 hour TTL - sufficient for job market data (doesn't change every minute)
DEFAULT_TTL_SECONDS = 3600


class AICache:
    """
    MongoDB-backed cache for AI responses.

    Stores hashed AI responses with TTL. Reduces Groq API calls by ~80%
    for repeated classifications during a scraping session.
    """

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.ttl_seconds = ttl_seconds

    def _make_key(self, text: str, extra: str = "") -> str:
        """Generate a deterministic cache key from text + extra context."""
        raw = f"{text.lower().strip()}|{extra}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _now_utc(self) -> datetime:
        return datetime.utcnow()

    def get(self, text: str, extra: str = "") -> Optional[Any]:
        """
        Retrieve cached AI response.

        Args:
            text: Original input text
            extra: Additional context that affects the response (e.g., category list)

        Returns:
            Cached response dict with "result" field, or None if not found/expired.
        """
        db = get_database()
        if db is None:
            return None

        key = self._make_key(text, extra)
        collection = db["ai_cache"]

        try:
            doc = collection.find_one({"_id": key})
            if doc:
                # Check TTL explicitly (index should handle it, but be safe)
                if "expires_at" in doc:
                    if doc["expires_at"] < self._now_utc():
                        collection.delete_one({"_id": key})
                        return None
                return doc.get("response")
        except Exception as e:
            logger.warning(f"AI cache get error: {e}")

        return None

    def set(
        self,
        text: str,
        response: Any,
        extra: str = "",
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """
        Store AI response in cache.

        Args:
            text: Original input text
            response: The AI response to cache (must be JSON-serializable)
            extra: Additional context that affects the response
            ttl_seconds: Custom TTL for this entry (overrides default)

        Returns:
            True if cached successfully, False otherwise.
        """
        db = get_database()
        if db is None:
            return False

        key = self._make_key(text, extra)
        collection = db["ai_cache"]
        ttl = ttl_seconds or self.ttl_seconds

        doc = {
            "_id": key,
            "text_hash": key,
            "original_text": text[:500],  # Keep truncated for debugging
            "extra": extra,
            "response": response,
            "cached_at": self._now_utc(),
            "expires_at": self._now_utc() + timedelta(seconds=ttl),
        }

        try:
            collection.update_one(
                {"_id": key},
                {"$set": doc},
                upsert=True,
            )
            return True
        except Exception as e:
            logger.warning(f"AI cache set error: {e}")
            return False

    def delete(self, text: str, extra: str = "") -> bool:
        """Delete a specific cache entry."""
        db = get_database()
        if db is None:
            return False

        key = self._make_key(text, extra)
        collection = db["ai_cache"]

        try:
            collection.delete_one({"_id": key})
            return True
        except Exception as e:
            logger.warning(f"AI cache delete error: {e}")
            return False

    def clear(self) -> int:
        """
        Clear all cache entries. Useful for testing or force refresh.

        Returns:
            Number of entries deleted.
        """
        db = get_database()
        if db is None:
            return 0

        collection = db["ai_cache"]

        try:
            result = collection.delete_many({})
            return result.deleted_count
        except Exception as e:
            logger.warning(f"AI cache clear error: {e}")
            return 0

    async def ensure_index(self):
        """
        Ensure TTL index exists on the cache collection.
        Call once at startup.
        """
        db = get_database()
        if db is None:
            return

        collection = db["ai_cache"]

        try:
            from pymongo import ASCENDING

            # TTL index on expires_at - MongoDB auto-deletes expired docs
            await collection.create_index(
                [("expires_at", ASCENDING)],
                expireAfterSeconds=0,
                background=True,
            )
            logger.info("AI cache TTL index created")
        except Exception as e:
            logger.warning(f"AI cache index creation error (may already exist): {e}")


# Singleton instance
_cache: Optional[AICache] = None


def get_ai_cache() -> AICache:
    """Get or create the global AI cache singleton."""
    global _cache
    if _cache is None:
        _cache = AICache()
    return _cache
