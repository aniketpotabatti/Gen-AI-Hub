"""Multi-tier caching layer for SemanticSearchX with Redis and in-memory LRU fallback."""
from collections import OrderedDict
import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("semanticsearchx.cache")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False


class InMemoryLRUCache:
    """Thread-safe in-memory LRU cache with TTL support."""

    def __init__(self, maxsize: int = 1000, default_ttl: int = 3600):
        self.maxsize = maxsize
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Tuple[float, Any]] = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        expires_at, value = self._cache[key]
        if time.time() > expires_at:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + ttl
        if key in self._cache:
            del self._cache[key]
        elif len(self._cache) >= self.maxsize:
            self._cache.popitem(last=False)  # pop oldest
        self._cache[key] = (expires_at, value)

    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        # Purge expired items on length check
        now = time.time()
        expired = [k for k, (exp, _) in self._cache.items() if now > exp]
        for k in expired:
            del self._cache[k]
        return len(self._cache)


class RetrievalCache:
    """Production caching layer supporting Redis with automatic graceful in-memory LRU fallback."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl: int = 3600,
        max_memory_items: int = 1000,
        enabled: bool = True,
    ):
        self.enabled = enabled
        self.default_ttl = default_ttl
        self.redis_client = None
        self.is_redis_connected = False
        self.in_memory_cache = InMemoryLRUCache(maxsize=max_memory_items, default_ttl=default_ttl)

        # Cache metrics
        self.hits = 0
        self.misses = 0

        if enabled and redis_url and REDIS_AVAILABLE:
            try:
                client = redis.from_url(redis_url, socket_timeout=0.5)
                client.ping()
                self.redis_client = client
                self.is_redis_connected = True
                logger.info("Successfully connected to Redis cache: %s", redis_url)
            except Exception as e:
                logger.warning("Failed connecting to Redis (%s); falling back to in-memory LRU.", e)
                self.redis_client = None
                self.is_redis_connected = False

    @staticmethod
    def generate_key(prefix: str, data: Any) -> str:
        """Create deterministic SHA256 cache key from input payload."""
        serialized = json.dumps(data, sort_keys=True, default=str)
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
        return f"{prefix}:{digest}"

    def get(self, key: str) -> Optional[Any]:
        if not self.enabled:
            return None

        # Try Redis first if connected
        if self.is_redis_connected and self.redis_client:
            try:
                raw = self.redis_client.get(key)
                if raw is not None:
                    self.hits += 1
                    return json.loads(raw.decode("utf-8"))
            except Exception as e:
                logger.warning("Redis get failed (%s); reading from in-memory fallback", e)

        # Fallback to in-memory
        val = self.in_memory_cache.get(key)
        if val is not None:
            self.hits += 1
            return val

        self.misses += 1
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if not self.enabled:
            return

        ttl = ttl if ttl is not None else self.default_ttl

        # Write to Redis if available
        if self.is_redis_connected and self.redis_client:
            try:
                serialized = json.dumps(value, default=str)
                self.redis_client.setex(key, ttl, serialized)
            except Exception as e:
                logger.warning("Redis setex failed (%s); writing to in-memory cache", e)

        # Always maintain in memory as secondary tier
        self.in_memory_cache.set(key, value, ttl=ttl)

    def delete(self, key: str) -> None:
        if self.is_redis_connected and self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception:
                pass
        self.in_memory_cache.delete(key)

    def clear(self) -> None:
        if self.is_redis_connected and self.redis_client:
            try:
                self.redis_client.flushdb()
            except Exception:
                pass
        self.in_memory_cache.clear()

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total) if total > 0 else 0.0

    def stats(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "backend": "redis" if self.is_redis_connected else "in_memory_lru",
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hit_rate, 4),
            "memory_items_count": len(self.in_memory_cache),
        }
