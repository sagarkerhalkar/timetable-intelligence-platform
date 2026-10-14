from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.database import Database
from app.dependencies import get_database, get_sync_service
from app.main import create_app
from app.services.sync_service import SyncService
from app.config import Settings


@pytest.fixture
def database(tmp_path: Path) -> Database:
    return Database(tmp_path / "test.db")


@pytest.fixture
def client(database: Database) -> Iterator[TestClient]:
    test_settings = Settings(database_url=f"sqlite:///{database.path}")
    app = create_app()
    app.dependency_overrides[get_database] = lambda: database
    app.dependency_overrides[get_sync_service] = lambda: SyncService(database, test_settings)
    with TestClient(app) as test_client:
        yield test_client
