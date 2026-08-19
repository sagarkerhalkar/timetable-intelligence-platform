from __future__ import annotations
from pathlib import Path
import hashlib, json, zipfile, sys

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
V125 = REPO_ROOT / 'release-source' / 'v1.0.25'
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE / 'timetable-intelligence-platform-v1.0.25.1-powershell-parser-fix.zip'
FIXED_DT = (2026, 8, 13, 14, 39, 0)

manifest = json.loads((HERE / 'PAYLOAD_MANIFEST.json').read_text(encoding='utf-8'))
source_map = {
    'apps/web/app/globals.v1.0.25.append.css': V125 / 'apps/web/app/globals.v1.0.25.append.css',
    'apps/web/app/qr/bulk/page.tsx': V125 / 'apps/web/app/qr/bulk/page.tsx',
    'apps/web/app/qr/codes/page.tsx': V125 / 'apps/web/app/qr/codes/page.tsx',
    'apps/web/app/qr/stats/page.tsx': V125 / 'apps/web/app/qr/stats/page.tsx',
    'apps/web/app/qr/templates/page.tsx': V125 / 'apps/web/app/qr/templates/page.tsx',
    'apps/web/components/pagination-controls.tsx': V125 / 'apps/web/components/pagination-controls.tsx',
    'apps/web/lib/pagination.test.ts': V125 / 'apps/web/lib/pagination.test.ts',
    'apps/web/lib/pagination.ts': V125 / 'apps/web/lib/pagination.ts',
}

entries: dict[str, bytes] = {}
for name in ['RUN_V1_0_25_1_NOW.cmd','PRECHECK_V1_0_25_1.ps1','INSTALL_V1_0_25_1.ps1','PAYLOAD_MANIFEST.json']:
    entries[name] = (HERE / name).read_bytes()

for item in manifest['files']:
    rel = item['path']
    src = source_map.get(rel)
    if src is None or not src.is_file():
        raise SystemExit(f'Missing release source for payload: {rel} -> {src}')
    data = src.read_bytes()
    if len(data) != item['size']:
        raise SystemExit(f'Size mismatch for {rel}: {len(data)} != {item["size"]}')
    digest = hashlib.sha256(data).hexdigest()
    if digest != item['sha256']:
        raise SystemExit(f'SHA256 mismatch for {rel}: {digest} != {item["sha256"]}')
    entries['payload/' + rel] = data

OUT.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(OUT, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for name in sorted(entries):
        zi = zipfile.ZipInfo(name, FIXED_DT)
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        zf.writestr(zi, entries[name])

digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
(OUT.with_suffix(OUT.suffix + '.sha256')).write_text(f'{digest}  {OUT.name}\n', encoding='ascii')
print(OUT)
print(digest)
