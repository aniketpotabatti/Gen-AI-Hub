"""Configuration management for SemanticSearchX."""
import os
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    name: str = "SemanticSearchX"
    version: str = "1.0.0"
    environment: str = Field(default_factory=lambda: os.getenv("APP_ENV", "production"))
    debug: bool = Field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    host: str = Field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))


class VectorStoreConfig(BaseModel):
    backend: str = Field(default_factory=lambda: os.getenv("VECTOR_STORE_BACKEND", "faiss"))  # faiss | qdrant
    collection_name: str = Field(default_factory=lambda: os.getenv("QDRANT_COLLECTION", "semantic_chunks"))
    qdrant_location: str = Field(default_factory=lambda: os.getenv("QDRANT_LOCATION", ":memory:"))
    qdrant_host: Optional[str] = Field(default_factory=lambda: os.getenv("QDRANT_HOST", None))
    qdrant_port: int = Field(default_factory=lambda: int(os.getenv("QDRANT_PORT", "6333")))
    embedding_dim: int = 384


class CacheConfig(BaseModel):
    enabled: bool = Field(default_factory=lambda: os.getenv("CACHE_ENABLED", "true").lower() == "true")
    redis_url: Optional[str] = Field(default_factory=lambda: os.getenv("REDIS_URL", None))
    ttl_seconds: int = Field(default_factory=lambda: int(os.getenv("CACHE_TTL", "3600")))
    max_memory_items: int = 1000


class ObservabilityConfig(BaseModel):
    enable_metrics: bool = True
    enable_tracing: bool = True
    service_name: str = "semantic-search-x"
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    structured_json: bool = Field(default_factory=lambda: os.getenv("LOG_JSON", "false").lower() == "true")


class Settings(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)

    @classmethod
    def load_from_yaml(cls, path: Optional[str] = None) -> "Settings":
        """Load settings with YAML fallback and environment override."""
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        return cls()


# Global settings singleton
settings = Settings()
