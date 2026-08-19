from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

VERSION = "1.0.25"
PACKAGE_NAME = "timetable-intelligence-platform-v1.0.25-pagination-qr-library.zip"
FIXED_ZIP_TIME = (2026, 8, 13, 12, 30, 0)

ROOT = Path(__file__).resolve().parent
INSTALLER = ROOT / "installer"
SOURCE = ROOT / "apps" / "web"

PAYLOAD_MAP = {
    SOURCE / "app/qr/codes/page.tsx": Path("apps/web/app/qr/codes/page.tsx"),
    SOURCE / "app/qr/templates/page.tsx": Path("apps/web/app/qr/templates/page.tsx"),
    SOURCE / "app/qr/bulk/page.tsx": Path("apps/web/app/qr/bulk/page.tsx"),
    SOURCE / "app/qr/stats/page.tsx": Path("apps/web/app/qr/stats/page.tsx"),
    SOURCE / "app/globals.v1.0.25.append.css": Path("apps/web/app/globals.v1.0.25.append.css"),
    SOURCE / "components/pagination-controls.tsx": Path("apps/web/components/pagination-controls.tsx"),
    SOURCE / "lib/pagination.ts": Path("apps/web/lib/pagination.ts"),
    SOURCE / "lib/pagination.test.ts": Path("apps/web/lib/pagination.test.ts"),
}

ROOT_FILES = [
    INSTALLER / "RUN_V1_0_25_NOW.cmd",
    INSTALLER / "INSTALL_V1_0_25.ps1",
    INSTALLER / "README_FIRST.txt",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_deterministic_zip(source_dir: Path, output: Path) -> None:
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for file in sorted(p for p in source_dir.rglob("*") if p.is_file()):
            arc = file.relative_to(source_dir).as_posix()
            info = zipfile.ZipInfo(arc, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zf.writestr(info, file.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main() -> int:
    missing = [str(p) for p in [*ROOT_FILES, *PAYLOAD_MAP.keys()] if not p.is_file()]
    if missing:
        print("Missing required release source:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        return 2

    output_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "dist"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / PACKAGE_NAME

    with tempfile.TemporaryDirectory(prefix="v1_0_25_package_") as tmp:
        stage = Path(tmp)
        for src in ROOT_FILES:
            shutil.copyfile(src, stage / src.name)

        manifest_files = []
        for src, rel in PAYLOAD_MAP.items():
            dest = stage / "payload" / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            manifest_files.append({
                "path": rel.as_posix(),
                "size": dest.stat().st_size,
                "sha256": sha256(dest),
            })

        manifest = {"version": VERSION, "files": sorted(manifest_files, key=lambda x: x["path"])}
        (stage / "PAYLOAD_MANIFEST.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
        )

        if output.exists():
            output.unlink()
        write_deterministic_zip(stage, output)

    digest = sha256(output)
    checksum = output_dir / f"{PACKAGE_NAME}.sha256"
    checksum.write_text(f"{digest}  {PACKAGE_NAME}\n", encoding="ascii", newline="\n")
    print(output)
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
