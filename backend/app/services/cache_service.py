import redis
import json
import hashlib
from app.core.config import settings
from app.core.logging import logger

class CacheService:
    def __init__(self):
        try:
            self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.enabled = True
        except Exception as e:
            logger.warning(f"Redis not available: {e}. Caching disabled.")
            self.enabled = False

    def _get_key(self, prefix: str, data: str) -> str:
        return f"{prefix}:{hashlib.md5(data.encode()).hexdigest()}"

    def get_embedding(self, text: str):
        if not self.enabled: return None
        key = self._get_key("embed", text)
        cached = self.redis.get(key)
        return json.loads(cached) if cached else None

    def set_embedding(self, text: str, embedding: list):
        if not self.enabled: return
        key = self._get_key("embed", text)
        self.redis.setex(key, 86400 * 7, json.dumps(embedding)) # 7 days

    def get_query_result(self, query: str):
        if not self.enabled: return None
        key = self._get_key("query", query)
        cached = self.redis.get(key)
        return json.loads(cached) if cached else None

    def set_query_result(self, query: str, result: list):
        if not self.enabled: return
        key = self._get_key("query", query)
        self.redis.setex(key, 3600, json.dumps(result)) # 1 hour

cache = CacheService()
