#!/usr/bin/env python3
"""Prepare an OFFLINE source-only review archive. Never touches runtime or GitHub."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SOURCE_FOLDERS = (
    "services/api/app",
    "services/api/tests",
    "services/api/scripts",
    "apps/web/app",
    "apps/web/components",
    "apps/web/lib",
    "apps/web/tests",
    "apps/web/e2e",
    "apps/web/public",
    "tests",
    "scripts",
    ".github/workflows",
    "worker/src",
)
SPECIFIC_FILES = (
    "services/api/pyproject.toml",
    "services/api/Dockerfile",
    "apps/web/package.json",
    "apps/web/package-lock.json",
    "apps/web/next.config.ts",
    "apps/web/tsconfig.json",
    "apps/web/vitest.config.ts",
    "apps/web/playwright.config.ts",
    "apps/web/Dockerfile",
)
ALLOWED_SUFFIXES = {
    ".py", ".pyi", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".css", ".scss", ".html", ".sql", ".ps1", ".cmd", ".bat", ".sh",
    ".toml", ".yml", ".yaml", ".md", ".txt", ".svg",
}
BLOCKED_PARTS = {
    "node_modules", ".next", ".git", ".venv", "venv", "__pycache__",
    "backups", "backup", "data", "logs", "coverage", ".runtime",
    ".wrangler", "dist", "build", "out", ".pytest_cache",
    "github-source", "qr_assets", "uploads", "private", "secrets",
}
BLOCKED_NAME_MARKERS = (
    ".env", "credential", "secret", "private_key", "oauth",
    "service_account", "token.txt", "passwords", "cookie", ".pem",
    ".p12", ".pfx", ".key", ".db", ".sqlite", ".sqlite3",
)
SUSPICIOUS = re.compile(
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    rb"|github_pat_[A-Za-z0-9_]{25,}"
    rb"|ghp_[A-Za-z0-9]{25,}"
    rb"|AIza[0-9A-Za-z_-]{30,}"
    rb"|sk-[A-Za-z0-9_-]{25,}"
    rb"|(?i:client_secret|api_secret|access_token|refresh_token|api_key)"
    rb"\s*[:=]\s*['\x22][^'\x22\r\n]{12,}['\x22]"
)


def prepare(root: Path, output: Path) -> dict:
    root = root.expanduser().resolve(strict=True)
    output = output.expanduser().resolve()
    if not root.is_dir():
        raise ValueError("The working application folder was not found.")
    if output == root or root in output.parents:
        raise ValueError("Output ZIP MUST be outside the live application folder.")
    if not (root / "services/api/app").is_dir() or not (root / "apps/web/app").is_dir():
        raise ValueError("Not the expected app source tree; nothing packaged.")
    if output.exists():
        raise FileExistsError("The output ZIP already exists; nothing overwritten.")

    candidate_paths: set[Path] = set()
    for folder in SOURCE_FOLDERS:
        base = root / folder
        if base.is_dir():
            candidate_paths.update(p for p in base.rglob("*") if p.is_file())
    candidate_paths.update(root / f for f in SPECIFIC_FILES if (root / f).is_file())
    kept: list[tuple[Path, bytes]] = []
    excluded_sensitive: list[str] = []
    excluded_other = 0
    for path in sorted(candidate_paths):
        rel = path.relative_to(root)
        filename = path.name.lower()
        if (any(part.lower() in BLOCKED_PARTS for part in rel.parts[:-1])
                or any(term in filename for term in BLOCKED_NAME_MARKERS)
                or (path.suffix.lower() not in ALLOWED_SUFFIXES and rel.as_posix() not in SPECIFIC_FILES)):
            excluded_other += 1
            continue
        if path.is_symlink():
            excluded_other += 1
            continue
        try:
            if path.stat().st_size > 2_000_000:
                excluded_other += 1
                continue
            blob = path.read_bytes()
            if b"\0" in blob or SUSPICIOUS.search(blob):
                excluded_sensitive.append(rel.as_posix())
                continue
            blob.decode("utf-8")
            kept.append((rel, blob))
        except (OSError, UnicodeDecodeError):
            excluded_other += 1

    if not kept:
        raise RuntimeError("No eligible source files found. Nothing packaged.")
    output.parent.mkdir(parents=True, exist_ok=True)
    info = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "type": "SOURCE REVIEW ONLY / NOT DEPLOYABLE / NOT PRODUCTION BACKUP",
        "included_files": len(kept),
        "excluded_sensitive_count": len(excluded_sensitive),
        "excluded_sensitive_paths": excluded_sensitive,
        "excluded_other_count": excluded_other,
        "files": {rel.as_posix(): hashlib.sha256(blob).hexdigest() for rel, blob in kept},
        "warning": "Automated filtering does not guarantee all hardcoded secrets were found. "
                   "Inspect archive before sharing; NEVER publish it directly to a public GitHub repo.",
    }
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for rel, blob in kept:
            archive.writestr(rel.as_posix(), blob)
        archive.writestr("SOURCE_REVIEW_MANIFEST.json", json.dumps(info, indent=2))
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    print("Created offline source-only review ZIP:", output)
    print("Source files included:", len(kept))
    print("Sensitive-looking files excluded:", len(excluded_sensitive))
    print("Other files excluded:", excluded_other)
    print("ZIP SHA-256:", digest)
    print("No services stopped. No live files written. No GitHub changes.")
    print("IMPORTANT: Review ZIP contents for sensitive data before sharing privately.")
    return info


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    prepare(args.root, args.output)


if __name__ == "__main__":
    main()
