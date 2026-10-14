from __future__ import annotations

from functools import lru_cache

from .config import settings
from .database import Database
from .services.sync_service import SyncService


@lru_cache(maxsize=1)
def get_database() -> Database:
    return Database(settings.database_path)


@lru_cache(maxsize=1)
def get_sync_service() -> SyncService:
    return SyncService(get_database(), settings)
