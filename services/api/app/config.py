from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

def _load_local_environment() -> None:
    project_root = Path(__file__).resolve().parents[3]
    for filename in (".env.notifications", ".env.local"):
        path = project_root / filename
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_local_environment()


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "Timetable Intelligence API"
    app_version: str = "1.0.24.1"
    environment: str = os.getenv("APP_ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/timetable.db")
    cors_origins: tuple[str, ...] = tuple(
        item.strip()
        for item in os.getenv("CORS_ORIGINS", "http://localhost:3457,http://127.0.0.1:3457").split(",")
        if item.strip()
    )
    max_download_mb: int = int(os.getenv("MAX_DOWNLOAD_MB", "50"))
    sync_timeout_seconds: int = int(os.getenv("SYNC_TIMEOUT_SECONDS", "120"))
    auto_sync_enabled: bool = os.getenv("AUTO_SYNC_ENABLED", "true").strip().casefold() in {
        "1", "true", "yes", "on"
    }
    sync_interval_minutes: int = max(5, int(os.getenv("SYNC_INTERVAL_MINUTES", "30")))
    page_refresh_minutes: int = max(1, int(os.getenv("PAGE_REFRESH_MINUTES", "5")))
    notification_interval_seconds: int = max(30, int(os.getenv("NOTIFICATION_INTERVAL_SECONDS", "60")))
    qr_public_base_url: str = os.getenv("QR_PUBLIC_BASE_URL", "https://q.nexttoppers.workers.dev").strip().rstrip("/")

    smtp_host: str = os.getenv("SMTP_HOST", "").strip()
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "").strip()
    smtp_password: str = os.getenv("SMTP_PASSWORD", "").strip()
    smtp_from: str = os.getenv("SMTP_FROM", "").strip()
    smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "true").strip().casefold() in {"1", "true", "yes", "on"}
    google_chat_webhook_url: str = os.getenv("GOOGLE_CHAT_WEBHOOK_URL", "").strip()
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    whatsapp_webhook_url: str = os.getenv("WHATSAPP_WEBHOOK_URL", "").strip()
    push_webhook_url: str = os.getenv("PUSH_WEBHOOK_URL", "").strip()

    @property
    def database_path(self) -> Path:
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            raise ValueError("Only sqlite:/// database URLs are supported in the foundation build")
        raw = self.database_url[len(prefix) :]
        return Path(raw).resolve()


settings = Settings()

