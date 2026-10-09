"""Safely install additive QR reports into an EXISTING Windows app checkout.

Default is read-only preflight. --apply backs up edited files, copies only a
new API router and web page, and adds a single router.include_router line.
No service restart, data migration, Cloudflare deploy, KV write or QR mutation.
"""
from __future__ import annotations

import argparse
import ast
import datetime
import py_compile
import shutil
from pathlib import Path


HERE = Path(__file__).resolve().parent
MARKER = "# NEXTTOPPERS_QR_REPORTS_V3_INCLUDE"
HOOK = (
    "\n" + MARKER + "\n"
    "from .qr_reporting_v3 import router as _qr_reports_v3_router\n"
    "router.include_router(_qr_reports_v3_router)\n"
)


def install(app_root: Path, apply: bool) -> list[str]:
    root = app_root.expanduser().resolve()
    routes = root / "services/api/app/api/routes.py"
    api_target = routes.with_name("qr_reporting_v3.py")
    page_target = root / "apps/web/app/qr/reports/page.tsx"
    importer_target = root / "services/api/scripts/import_store_downloads_v3.py"
    source_api = HERE / "services/api/app/api/qr_reporting_v3.py"
    source_page = HERE / "apps/web/app/qr/reports/page.tsx"
    source_importer = HERE / "scripts/import_store_downloads_v3.py"

    if not routes.is_file():
        raise RuntimeError(f"Actual API routes.py not found: {routes}")
    if not source_api.is_file() or not source_page.is_file() or not source_importer.is_file():
        raise RuntimeError("Missing complete v3 source payload")
    code = routes.read_text(encoding="utf-8-sig")
    if "router = APIRouter(prefix=\"/api/v1\")" not in code:
        raise RuntimeError("API prefix does not match expected existing app; refusing to patch")
    if "qr_reporting_v3" in code and MARKER not in code:
        raise RuntimeError("Unknown reporting integration exists; refusing duplicate import")
    ast.parse(source_api.read_text(encoding="utf-8"))
    ast.parse(source_importer.read_text(encoding="utf-8"))
    ast.parse(code if MARKER in code else code+HOOK)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    actions = [
        f"API router: {api_target}",
        f"Store importer: {importer_target}",
        f"Web page: {page_target}",
        f"Existing routes.py: {'already hooked' if MARKER in code else 'append isolated include_router hook'}",
        "UNCHANGED: live database, worker, KV, 3456/3457/3550 processes",
    ]
    if not apply:
        return ["DRY RUN ONLY (no writes)", *actions]
    if page_target.exists() and page_target.read_bytes() != source_page.read_bytes():
        raise RuntimeError(f"Existing page would be overwritten: {page_target}")
    if api_target.exists() and api_target.read_bytes() != source_api.read_bytes():
        raise RuntimeError(f"Existing API module would be overwritten: {api_target}")
    if importer_target.exists() and importer_target.read_bytes() != source_importer.read_bytes():
        raise RuntimeError(f"Existing importer would be overwritten: {importer_target}")

    backup_dir = root / "qr_v3_safe_backups" / stamp
    backup_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(routes, backup_dir / "routes.py")
    copied = []
    try:
        for source, target in ((source_api, api_target),
                               (source_importer, importer_target),
                               (source_page,page_target)):
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists():
                shutil.copy2(source,target)
                copied.append(target)
        if MARKER not in code:
            routes.write_text(code+HOOK,encoding="utf-8")
        py_compile.compile(str(routes),doraise=True)
        py_compile.compile(str(api_target),doraise=True)
        py_compile.compile(str(importer_target),doraise=True)
    except Exception:
        shutil.copy2(backup_dir/"routes.py", routes)
        for target in copied:
            target.unlink(missing_ok=True)
        raise
    return [f"FILES INSTALLED (not deployed/restarted). Backup: {backup_dir}",
            *actions,
            "Next: run backend/web tests against a COPY of the database, then restart only with explicit operator approval."]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--app-root",type=Path,required=True)
    parser.add_argument("--apply",action="store_true",help="Apply additive file changes after review")
    args=parser.parse_args()
    try:
        lines=install(args.app_root,args.apply)
    except Exception as error:
        parser.exit(1,f"STOP — no unsafe continuation: {error}\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
