"""Redis Caching Service (PDF Part 10.1).

Provides caching layers for:
- Embedding cache (7-day TTL)
- Query result cache (1-hour TTL)
- Response cache for AI-generated responses (30-min TTL)
- Session cache for recruiter session state (24-hour TTL)
"""

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

import json
import hashlib
from app.core.config import settings
from app.core.logging import logger


class CacheService:
    def __init__(self):
        self.enabled = False
        self.redis = None
        if REDIS_AVAILABLE:
            try:
                self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
                self.redis.ping()
                self.enabled = True
                logger.info("Connected to Redis cache successfully.")
            except Exception as e:
                logger.warning(f"Redis not available: {e}. Caching disabled.")
        else:
            logger.warning("redis-py library not installed. Caching disabled.")

    def _get_key(self, prefix: str, data: str) -> str:
        return f"{prefix}:{hashlib.md5(data.encode()).hexdigest()}"

    # --- Embedding Cache (7 days) ---
    def get_embedding(self, text: str):
        if not self.enabled:
            return None
        try:
            key = self._get_key("embed", text)
            cached = self.redis.get(key)
            return json.loads(cached) if cached else None
        except Exception:
            return None

    def set_embedding(self, text: str, embedding: list):
        if not self.enabled:
            return
        try:
            key = self._get_key("embed", text)
            self.redis.setex(key, 86400 * 7, json.dumps(embedding))  # 7 days
        except Exception:
            pass

    # --- Query Result Cache (1 hour) ---
    def get_query_result(self, query: str):
        if not self.enabled:
            return None
        try:
            key = self._get_key("query", query)
            cached = self.redis.get(key)
            return json.loads(cached) if cached else None
        except Exception:
            return None

    def set_query_result(self, query: str, result: list):
        if not self.enabled:
            return
        try:
            key = self._get_key("query", query)
            self.redis.setex(key, 3600, json.dumps(result))  # 1 hour
        except Exception:
            pass

    # --- Response Cache for AI-generated responses (30 minutes) ---
    def get_response(self, query: str):
        if not self.enabled:
            return None
        try:
            key = self._get_key("response", query)
            cached = self.redis.get(key)
            return cached if cached else None
        except Exception:
            return None

    def set_response(self, query: str, response: str):
        if not self.enabled:
            return
        try:
            key = self._get_key("response", query)
            self.redis.setex(key, 1800, response)  # 30 minutes
        except Exception:
            pass

    # --- Session Cache (24 hours) ---
    def get_session(self, session_id: str):
        if not self.enabled:
            return None
        try:
            key = f"session:{session_id}"
            cached = self.redis.get(key)
            return json.loads(cached) if cached else None
        except Exception:
            return None

    def set_session(self, session_id: str, data: dict):
        if not self.enabled:
            return
        try:
            key = f"session:{session_id}"
            self.redis.setex(key, 86400, json.dumps(data))  # 24 hours
        except Exception:
            pass


cache = CacheService()
