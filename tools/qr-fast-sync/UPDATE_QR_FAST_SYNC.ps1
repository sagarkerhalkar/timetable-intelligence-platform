<#
NextToppers QR - fast and clear Cloudflare sync (update 2026-10-14)

What changes
  Only one program file of the QR API:
    services\api\app\services\qr_edge_runtime.py
  Creating, editing, turning on/off and deleting a tracked QR now talks to
  Cloudflare directly (seconds) instead of starting Wrangler/npx several times
  (often minutes). Error messages are short and say how to fix them.
  Two test files are added/updated so tests never write to the real Cloudflare.

What does NOT change
  The database, any QR code, slug, destination, scan, Google Sheet, timetable,
  the web app on port 3500, Cloudflare KV data and the Cloudflare Worker.

Safety
  1. Stops if the live file is not the exact version that was reviewed.
  2. Tests the new code in a separate temporary copy first.
  3. Backs up the old files to <app>\backups\qr-fast-sync-<time>.
  4. Restarts only the QR API (port 3550) and checks health, number of QR codes
     and number of scans. If anything is wrong it puts the old file back.

Run in PowerShell opened with "Run as administrator":
  powershell -ExecutionPolicy Bypass -File .\UPDATE_QR_FAST_SYNC.ps1
  Add -CheckOnly to only check, without changing anything.
#>
param(
    [string]$AppRoot = "D:\timetable-intelligence-platform",
    [int]$ApiPort = 3550,
    [string]$TaskName = "NextToppers-AutoRecovery",
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Api = "http://127.0.0.1:$ApiPort"

# Live file -> SHA-256 of the reviewed old version (from the 14 Oct source review)
# and of the new version on GitHub main.
$Files = @(
    @{ Rel = "services\api\app\services\qr_edge_runtime.py"; Old = "27db4f569197da44a96bce290dd0f28af883d2b05a0b8e114b7dc7ccb7ffde42"; New = "eb1c423c283531c6b1558a9ea71467f9347d7d7fd301afb51596f8ea3b46ad15"; Required = $true },
    @{ Rel = "services\api\tests\conftest.py"; Old = "a65cdf5767f848ae71929bf074e7e26a43a00cd579cd266c8847dcfe77209334"; New = "db38e68aa25b280a5b9240189085f66e796b79e3d9d6952f229d3e195c2c852f"; Required = $false },
    @{ Rel = "services\api\tests\test_v130_qr_edge_rest.py"; Old = ""; New = "1330d0bd581c1b3c104e928b9ffd9d31551698ed887a303b7987961443e60731"; Required = $false }
)

function Say([string]$Text, [string]$Color = "Gray") { Write-Host $Text -ForegroundColor $Color }
function Hash([string]$Path) { if (Test-Path -LiteralPath $Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLower() } else { "" } }

# Windows PowerShell 5.1 turns any text a program writes to its error stream
# into a stopping error; run outside programs with that switched off.
function Invoke-Native([scriptblock]$Block) {
    $old = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { & $Block } finally { $ErrorActionPreference = $old }
}

function Get-ApiState {
    try {
        $health = Invoke-RestMethod -Uri "$Api/api/v1/health" -TimeoutSec 15
        $codes = Invoke-RestMethod -Uri "$Api/api/v1/qr-codes" -TimeoutSec 60
        $codes = @($codes | ForEach-Object { $_ })
        $scans = 0
        foreach ($c in $codes) { $scans += [int]$c.total_scans + [int]$c.legacy_scans }
        return [pscustomobject]@{ Ok = ($health.status -eq "ok"); Qr = $codes.Count; Scans = $scans }
    } catch {
        return [pscustomobject]@{ Ok = $false; Qr = -1; Scans = -1 }
    }
}

function Restart-QrApi {
    $watchdogs = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'" | Where-Object { $_.CommandLine -match 'WATCHDOG' -and $_.ProcessId -ne $PID })
    foreach ($w in $watchdogs) { Stop-Process -Id $w.ProcessId -Force -ErrorAction SilentlyContinue }
    $listen = Get-NetTCPConnection -LocalPort $ApiPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    $oldPid = $null
    if ($listen) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($listen.OwningProcess)"
        if ($proc.Name -notmatch '^python' -and $proc.CommandLine -notmatch 'uvicorn') {
            throw "Port $ApiPort belongs to $($proc.Name), not the Python QR API. Not stopping it."
        }
        $top = $proc
        while ($true) {
            $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($top.ParentProcessId)" -ErrorAction SilentlyContinue
            if ($parent -and $parent.Name -match '^python' -and $parent.CommandLine -match 'uvicorn|app\.main') { $top = $parent } else { break }
        }
        $oldPid = $listen.OwningProcess
        Invoke-Native { & taskkill.exe /PID $top.ProcessId /T /F 2>&1 | Out-Null }
    }
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) { Start-ScheduledTask -TaskName $TaskName }
    for ($i = 0; $i -lt 36; $i++) {
        Start-Sleep -Seconds 5
        $back = Get-NetTCPConnection -LocalPort $ApiPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($back -and $back.OwningProcess -ne $oldPid) {
            for ($j = 0; $j -lt 12; $j++) { if ((Get-ApiState).Ok) { return $true }; Start-Sleep -Seconds 5 }
            return $false
        }
        if ($task -and $i -eq 12) { Start-ScheduledTask -TaskName $TaskName }
    }
    return $false
}

Say ""
Say "=== NextToppers QR - fast Cloudflare sync update ===" "Cyan"
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin -and -not $CheckOnly) { throw "Open PowerShell with 'Run as administrator' and run again. Nothing was changed." }
if (-not (Test-Path -LiteralPath $AppRoot)) { throw "App folder $AppRoot not found. Nothing was changed." }

# ---------- 1. Check files ----------
Say ""
Say "1. Checking files" "Cyan"
$toCopy = @()
foreach ($f in $Files) {
    $src = Join-Path $RepoRoot $f.Rel
    $dst = Join-Path $AppRoot $f.Rel
    if ((Hash $src) -ne $f.New) { throw "The update file $src is not the expected version. Run 'git pull' in $RepoRoot and try again. Nothing was changed." }
    $live = Hash $dst
    if ($live -eq $f.New) { Say "  Already up to date: $($f.Rel)" "Green"; continue }
    if ($live -eq $f.Old) { Say "  Will update: $($f.Rel)"; $toCopy += $f; continue }
    if ($f.Required) { throw "Live file $dst is a different version than the one reviewed (SHA $live). Nothing was changed. Send this message to Claude." }
    Say "  Skipped (different local version kept): $($f.Rel)" "Yellow"
}

$before = Get-ApiState
if ($before.Ok) { Say "  QR API is healthy: $($before.Qr) QR codes, $($before.Scans) scans." "Green" }
else { Say "  QR API is not answering on port $ApiPort right now." "Yellow" }
$tokenSet = [bool][Environment]::GetEnvironmentVariable("CLOUDFLARE_API_TOKEN", "Machine")
Say ("  Cloudflare token for the computer: " + $(if ($tokenSet) { "set" } else { "NOT set - run FIX_QR_CLOUDFLARE_TOKEN.ps1 too" })) $(if ($tokenSet) { "Green" } else { "Yellow" })

if (-not $toCopy.Count) { Say ""; Say "Nothing to update." "Green"; return }
if ($CheckOnly) { Say ""; Say "Check only: nothing was changed." "Green"; return }

# ---------- 2. Test in a separate copy ----------
Say ""
Say "2. Testing the new code in a temporary copy (the live app is not touched)" "Cyan"
$listen = Get-NetTCPConnection -LocalPort $ApiPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
$py = $null
if ($listen) { $py = (Get-CimInstance Win32_Process -Filter "ProcessId=$($listen.OwningProcess)").ExecutablePath }
if (-not $py -or $py -notmatch 'python') {
    foreach ($cand in @("$AppRoot\services\api\.venv\Scripts\python.exe", "$AppRoot\.venv\Scripts\python.exe")) { if (Test-Path $cand) { $py = $cand; break } }
}
if (-not $py) { throw "Could not find the Python used by the QR API. Nothing was changed." }
Say "  Python: $py"
$stage = Join-Path $env:TEMP "ntqr-stage-$Stamp"
Invoke-Native { & robocopy.exe "$AppRoot\services\api" "$stage\services\api" /E /XD data .venv venv __pycache__ .pytest_cache node_modules backups /XF *.db *.db-wal *.db-shm *.log .env* /NFL /NDL /NJH /NJS /NP | Out-Null }
if ($LASTEXITCODE -ge 8) { throw "Could not make the temporary copy (robocopy $LASTEXITCODE). Nothing was changed." }
foreach ($f in $Files) { Copy-Item -LiteralPath (Join-Path $RepoRoot $f.Rel) -Destination (Join-Path $stage $f.Rel) -Force }
$env:NEXTTOPPERS_QR_EDGE_SYNC = "off"
$env:DATABASE_URL = "sqlite:///" + ((Join-Path $stage "stage-test.db") -replace '\\', '/')
Push-Location "$stage\services\api"
try {
    $out = Invoke-Native { & $py -c "import app.services.qr_edge_runtime as e, app.main; assert e.TOKEN_HELP; print('IMPORT OK')" 2>&1 }
    if (($out | Out-String) -notmatch 'IMPORT OK') { throw "The new code did not load: $out. Nothing was changed." }
    Say "  New code loads correctly." "Green"
    Invoke-Native { & $py -m pytest --version 2>&1 | Out-Null }
    if ($LASTEXITCODE -eq 0) {
        $testOut = Invoke-Native { & $py -m pytest -q -p no:cacheprovider tests/test_v130_qr_edge_rest.py tests/test_v116_qr_analytics.py tests/test_v121_url_update.py 2>&1 | Out-String }
        if ($LASTEXITCODE -ne 0) { throw "Tests failed in the temporary copy. Nothing was changed.`n$testOut" }
        Say ("  Tests passed: " + (($testOut -split "`n" | Where-Object { $_ -match 'passed' }) -join ' ').Trim()) "Green"
    } else { Say "  pytest is not installed for this Python; load check only." "Yellow" }
} finally {
    Pop-Location
    Remove-Item Env:\NEXTTOPPERS_QR_EDGE_SYNC -ErrorAction SilentlyContinue
    Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue
}

# ---------- 3. Backup and apply ----------
Say ""
Say "3. Backing up and updating" "Cyan"
$backup = Join-Path $AppRoot "backups\qr-fast-sync-$Stamp"
foreach ($f in $toCopy) {
    $dst = Join-Path $AppRoot $f.Rel
    if (Test-Path -LiteralPath $dst) {
        $bdst = Join-Path $backup $f.Rel
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $bdst) | Out-Null
        Copy-Item -LiteralPath $dst -Destination $bdst -Force
    }
}
Say "  Backup: $backup"
foreach ($f in $toCopy) {
    $dst = Join-Path $AppRoot $f.Rel
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
    Copy-Item -LiteralPath (Join-Path $RepoRoot $f.Rel) -Destination $dst -Force
    Say "  Updated $($f.Rel)" "Green"
}

# ---------- 4. Restart only the QR API and verify ----------
Say ""
Say "4. Restarting only the QR API and checking it" "Cyan"
$ok = $false
try { $ok = Restart-QrApi } catch { Say "  $_" "Red" }
$after = Get-ApiState
if ($ok -and $after.Ok -and ($before.Qr -lt 0 -or ($after.Qr -eq $before.Qr -and $after.Scans -ge $before.Scans))) {
    Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
    Say "  QR API healthy: $($after.Qr) QR codes (before $($before.Qr)), $($after.Scans) scans (before $($before.Scans))." "Green"
    Say ""
    Say "SUCCESS - QR FAST SYNC IS INSTALLED. No QR code, scan or database data was changed." "Green"
    if (-not $tokenSet) { Say "Next: run FIX_QR_CLOUDFLARE_TOKEN.ps1 so new QR codes can be created." "Yellow" }
    else { Say "Test: create one tracked QR. It should save in a few seconds." "Green" }
    return
}

Say "  Check failed (healthy=$($after.Ok), QR $($after.Qr) vs $($before.Qr), scans $($after.Scans) vs $($before.Scans)). Putting the old file back..." "Red"
foreach ($f in $toCopy) {
    $dst = Join-Path $AppRoot $f.Rel
    $bsrc = Join-Path $backup $f.Rel
    if (Test-Path -LiteralPath $bsrc) { Copy-Item -LiteralPath $bsrc -Destination $dst -Force } else { Remove-Item -LiteralPath $dst -Force -ErrorAction SilentlyContinue }
}
try { [void](Restart-QrApi) } catch { Say "  $_" "Red" }
$final = Get-ApiState
Say "ROLLED BACK. QR API healthy=$($final.Ok), $($final.Qr) QR codes. Send this whole window to Claude." "Red"
exit 1
