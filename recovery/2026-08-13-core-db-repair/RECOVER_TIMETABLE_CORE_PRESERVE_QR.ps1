$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = "D:\timetable-intelligence-platform"
$CoreDb = Join-Path $Root "services\api\data\timetable.db"
$QrDb = Join-Path $Root "data\timetable.db"
$ApiDir = Join-Path $Root "services\api"
$WebDir = Join-Path $Root "apps\web"
$Helper = Join-Path $PSScriptRoot "RECOVER_TIMETABLE_CORE_PRESERVE_QR.py"
$EnvLocal = Join-Path $Root ".env.local"
$PinnedDatabaseUrl = "sqlite:///D:/timetable-intelligence-platform/services/api/data/timetable.db"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Backup = Join-Path $Root "backups\CORE_DB_QR_MERGE_$Stamp"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Report = Join-Path $Desktop "TIMETABLE_CORE_RECOVERY_$Stamp.txt"

function Log([string]$Message = "") {
    $Message | Tee-Object -FilePath $Report -Append
}

function Resolve-Python {
    $candidates = @(
        (Join-Path $ApiDir ".venv\Scripts\python.exe"),
        (Join-Path $Root ".venv\Scripts\python.exe"),
        (Join-Path $Root "venv\Scripts\python.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    throw "Python executable not found."
}

function Stop-AppPort([int]$Port) {
    if ($Port -eq 3457) { throw "Protected port 3457 must never be stopped." }
    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
    foreach ($listener in $listeners) {
        $pidValue = [int]$listener.OwningProcess
        if ($pidValue -le 0) { continue }
        $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
        $name = if ($proc) { $proc.ProcessName } else { "unknown" }
        if ($Port -eq 3500 -and $name -notmatch '^node$') {
            throw "Port 3500 is owned by unexpected process $name PID $pidValue. Nothing killed."
        }
        if ($Port -eq 3550 -and $name -notmatch '^(python|python3)$') {
            throw "Port 3550 is owned by unexpected process $name PID $pidValue. Nothing killed."
        }
        Log "Stopping Timetable listener: port=$Port process=$name PID=$pidValue"
        Stop-Process -Id $pidValue -Force -ErrorAction Stop
        Start-Sleep -Seconds 2
    }
}

function Wait-Url([string]$Url, [int]$Seconds = 75) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    do {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) { return $true }
        } catch {}
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    return $false
}

function Pin-CoreDatabase {
    Log "Pinning DATABASE_URL to authoritative service/API DB: $PinnedDatabaseUrl"
    if (Test-Path -LiteralPath $EnvLocal -PathType Leaf) {
        Copy-Item -LiteralPath $EnvLocal -Destination (Join-Path $Backup "env.local.before_recovery") -Force
        $lines = @(Get-Content -LiteralPath $EnvLocal -ErrorAction Stop)
    } else {
        $lines = @()
    }
    $updated = @()
    $found = $false
    foreach ($line in $lines) {
        if ($line -match '^\s*DATABASE_URL\s*=') {
            if (-not $found) {
                $updated += "DATABASE_URL=$PinnedDatabaseUrl"
                $found = $true
            }
        } else {
            $updated += $line
        }
    }
    if (-not $found) { $updated += "DATABASE_URL=$PinnedDatabaseUrl" }
    $updated | Set-Content -LiteralPath $EnvLocal -Encoding UTF8
    Log "PASS .env.local DATABASE_URL pin applied; other lines preserved."
}

function Start-CorrectRuntime {
    Log "Starting API from CORRECT working directory: $ApiDir"
    $python = Resolve-Python
    $oldDbUrl = $env:DATABASE_URL
    try {
        $env:DATABASE_URL = $PinnedDatabaseUrl
        Start-Process -FilePath $python -ArgumentList @("-m","uvicorn","app.main:app","--host","0.0.0.0","--port","3550") -WorkingDirectory $ApiDir -WindowStyle Hidden | Out-Null
    } finally {
        $env:DATABASE_URL = $oldDbUrl
    }
    Log "Starting Web from: $WebDir"
    Start-Process -FilePath "npm.cmd" -ArgumentList @("run","start","--","-p","3500") -WorkingDirectory $WebDir -WindowStyle Hidden | Out-Null
}

try {
    if (Test-Path -LiteralPath $Report) { Remove-Item -LiteralPath $Report -Force }
    Log "============================================================================"
    Log "TIMETABLE CORE DB / GOOGLE SHEET RECOVERY - PRESERVE QR"
    Log "Stamp: $Stamp"
    Log "Root: $Root"
    Log "Protected port 3457 is NOT touched."
    Log "============================================================================"

    if (-not (Test-Path -LiteralPath $Root -PathType Container)) { throw "Application root missing: $Root" }
    if (-not (Test-Path -LiteralPath $ApiDir -PathType Container)) { throw "API directory missing: $ApiDir" }
    if (-not (Test-Path -LiteralPath $CoreDb -PathType Leaf)) { throw "Core service DB missing: $CoreDb" }
    if (-not (Test-Path -LiteralPath $QrDb -PathType Leaf)) { throw "Root/QR DB missing: $QrDb" }
    if (-not (Test-Path -LiteralPath $Helper -PathType Leaf)) { throw "Recovery helper missing: $Helper" }

    $python = Resolve-Python
    Log "Python: $python"
    Log "Core DB: $CoreDb"
    Log "Root QR DB: $QrDb"

    Log ""
    Log "[1/8] Read-only database inspection"
    & $python $Helper inspect --core-db $CoreDb --qr-db $QrDb --report $Report
    if ($LASTEXITCODE -ne 0) { throw "Database preflight inspection failed." }

    Log ""
    Log "[2/8] Stop only Timetable ports 3500 and 3550"
    Stop-AppPort 3500
    Stop-AppPort 3550

    Log ""
    Log "[3/8] Consistent safety backup of both databases and QR assets"
    New-Item -ItemType Directory -Path $Backup -Force | Out-Null
    & $python $Helper backup --core-db $CoreDb --qr-db $QrDb --backup-dir $Backup --report $Report
    if ($LASTEXITCODE -ne 0) { throw "Safety backup failed." }

    foreach ($assetRel in @("services\api\data\qr_assets", "data\qr_assets")) {
        $src = Join-Path $Root $assetRel
        if (Test-Path -LiteralPath $src -PathType Container) {
            $safeName = $assetRel.Replace("\", "_")
            Copy-Item -LiteralPath $src -Destination (Join-Path $Backup $safeName) -Recurse -Force
            Log "Backed up QR assets: $src"
        }
    }

    Log ""
    Log "[4/8] Merge QR-only data into the authoritative service/API DB"
    & $python $Helper merge --core-db $CoreDb --qr-db $QrDb --root $Root --report $Report
    if ($LASTEXITCODE -ne 0) { throw "QR-only merge failed. Safety backup is at $Backup" }

    Log ""
    Log "[5/8] Pin database path and start API from services\api"
    Pin-CoreDatabase
    Start-CorrectRuntime
    if (-not (Wait-Url "http://127.0.0.1:3550/api/v1/dashboard" 75)) { throw "API did not become healthy on 3550." }
    if (-not (Wait-Url "http://127.0.0.1:3500/" 75)) { throw "Web did not become healthy on 3500." }
    Log "PASS API and Web are responding."

    Log ""
    Log "[6/8] Verify API is using the service/API DB and QR data is visible"
    & $python $Helper verify-runtime --core-db $CoreDb --api http://127.0.0.1:3550 --report $Report
    if ($LASTEXITCODE -ne 0) { throw "Runtime database verification failed." }

    Log ""
    Log "[7/8] Sync enabled Google Sheet sources using existing application API"
    & $python $Helper sync --core-db $CoreDb --api http://127.0.0.1:3550 --report $Report
    if ($LASTEXITCODE -ne 0) { throw "Google Sheet sync/verification failed. See Desktop report." }

    Log ""
    Log "[8/8] Final application checks"
    foreach ($url in @(
        "http://127.0.0.1:3500/timetable?view=today",
        "http://127.0.0.1:3500/timetable?view=week",
        "http://127.0.0.1:3500/sources",
        "http://127.0.0.1:3500/changes",
        "http://127.0.0.1:3500/tests",
        "http://127.0.0.1:3500/qr/codes"
    )) {
        if (-not (Wait-Url $url 30)) { throw "Page check failed: $url" }
        Log "PASS page: $url"
    }

    Log ""
    Log "SUCCESS: Correct service/API database is active, QR data preserved, Google Sheets synced."
    Log "Backup: $Backup"
    Log "Report: $Report"
    Log "LAN: http://156.156.40.51:3500"
    Write-Host ""
    Write-Host "RECOVERY SUCCESS" -ForegroundColor Green
    Write-Host "Report: $Report" -ForegroundColor White
    exit 0
}
catch {
    try { Log ""; Log ("FAIL: " + $_.Exception.Message); Log ("Safety backup folder: " + $Backup) } catch {}
    Write-Host ""
    Write-Host ("RECOVERY FAILED: " + $_.Exception.Message) -ForegroundColor Red
    Write-Host "Do NOT install another release. Upload the Desktop report." -ForegroundColor Yellow
    Write-Host "Report: $Report" -ForegroundColor White
    exit 1
}
