"""Consistent read-only SQLite snapshot for offline NextToppers reports.
Never modifies the source database, API, QR records, or Cloudflare.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

TABLES = (
    "sources", "timetable_entries", "test_records", "changes",
    "qr_codes", "qr_scans", "qr_templates", "qr_assets",
)


def backup(source: Path, directory: Path) -> Path:
    source = source.expanduser().resolve(strict=True)
    directory = directory.expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != ".db":
        raise ValueError("Source must be an existing .db file")
    if directory == source.parent:
        raise ValueError("Backup folder must be separate from the live database folder")
    if not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = directory / f"timetable-backup-{stamp}-{os.getpid()}.db"
    temp = directory / f".{output.name}.partial"
    if output.exists() or temp.exists():
        raise FileExistsError("Backup filename already exists; nothing overwritten")
    try:
        with sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True, timeout=30) as live:
            with sqlite3.connect(temp) as saved:
                live.backup(saved, pages=256, sleep=0.1)
        with sqlite3.connect(f"{temp.as_uri()}?mode=ro", uri=True) as check:
            result = check.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                raise RuntimeError(f"Backup integrity error: {result}")
            existing = {row[0] for row in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            counts = {t: check.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                      for t in TABLES if t in existing}
        os.replace(temp, output)
        sha = hashlib.sha256()
        with output.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                sha.update(chunk)
        manifest = {"created_utc": stamp, "source": str(source),
                    "backup": str(output), "sha256": sha.hexdigest(),
                    "integrity_check": "ok", "table_counts": counts}
        output.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps(manifest, indent=2))
        return output
    finally:
        if temp.exists():
            temp.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy SQLite safely for offline QR reporting")
    parser.add_argument("--source", required=True, help="Confirmed active SQLite database .db path")
    parser.add_argument("--backup-dir", required=True, help="Separate, private backup folder")
    args = parser.parse_args()
    backup(Path(args.source), Path(args.backup_dir))
