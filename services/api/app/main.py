from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .api.qr_fast import router as qr_fast_router
from .api.qr_scale import ensure_qr_scale_schema, qr_scale_aggregation_loop, router as qr_scale_router
from .api.qr_reports import router as qr_reports_router
from .config import settings
from .dependencies import get_database, get_sync_service
from .services.notifications import run_due_notifications


async def _automatic_sync_loop() -> None:
    # Keep startup fast. Pages can immediately use the last successful local
    # snapshot; automatic Google Sheet work begins only after the API and web UI
    # are stable. The SyncService itself serialises workbook jobs.
    await asyncio.sleep(120)
    database = get_database()
    service = get_sync_service()
    interval = timedelta(minutes=settings.sync_interval_minutes)
    while True:
        now = datetime.now(UTC)
        for source in database.list_sources():
            current = database.get_source(source.id)
            if current is None or not current.enabled:
                continue
            if current.last_sync_status in {"queued", "downloading", "analyzing"}:
                continue
            if current.last_sync_at and now - current.last_sync_at < interval:
                continue
            await service.sync_source(current)
        await asyncio.sleep(settings.sync_interval_minutes * 60)


async def _notification_loop() -> None:
    await asyncio.sleep(12)
    database = get_database()
    while True:
        try:
            await run_due_notifications(database)
        except Exception:
            # A channel failure is stored in delivery history; the scheduler must stay alive.
            pass
        await asyncio.sleep(settings.notification_interval_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    database = get_database()
    database.initialize()
    ensure_qr_scale_schema()
    database.reset_interrupted_syncs()
    sync_task: asyncio.Task[None] | None = None
    notification_task: asyncio.Task[None] | None = None
    qr_scale_task: asyncio.Task[None] | None = None
    if settings.auto_sync_enabled:
        sync_task = asyncio.create_task(_automatic_sync_loop())
    notification_task = asyncio.create_task(_notification_loop())
    qr_scale_task = asyncio.create_task(qr_scale_aggregation_loop())
    try:
        yield
    finally:
        for task in (sync_task, notification_task, qr_scale_task):
            if task is None:
                continue
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Dynamic Google Sheets timetable intelligence, content classification, "
            "daily change history, notifications, and exports."
        ),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    app.include_router(router)
    app.include_router(qr_fast_router)
    app.include_router(qr_scale_router)
    app.include_router(qr_reports_router)
    return app


app = create_app()
