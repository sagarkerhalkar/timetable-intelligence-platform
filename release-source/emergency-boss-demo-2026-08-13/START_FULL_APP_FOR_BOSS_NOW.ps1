$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = "D:\timetable-intelligence-platform"
$WebDir = Join-Path $Root "apps\web"
$CoreDb = Join-Path $Root "services\api\data\timetable.db"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Report = Join-Path $Desktop "BOSS_DEMO_START_$Stamp.txt"
$WebLog = Join-Path $Desktop "BOSS_DEMO_WEB_$Stamp.log"
$WebErr = Join-Path $Desktop "BOSS_DEMO_WEB_$Stamp.err.log"

function Log([string]$Message = "") {
    Write-Host $Message
    Add-Content -LiteralPath $Report -Value $Message -Encoding UTF8
}

function Resolve-Python {
    foreach ($candidate in @(
        (Join-Path $Root "services\api\.venv\Scripts\python.exe"),
        (Join-Path $Root ".venv\Scripts\python.exe"),
        (Join-Path $Root "venv\Scripts\python.exe")
    )) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    throw "Python executable not found."
}

function Resolve-Node {
    $cmd = Get-Command node.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $cmd = Get-Command node -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    throw "Node executable not found."
}

function Stop-Web3500 {
    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort 3500 -ErrorAction SilentlyContinue)
    foreach ($listener in $listeners) {
        $pidValue = [int]$listener.OwningProcess
        if ($pidValue -le 0) { continue }
        $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
        $name = if ($proc) { $proc.ProcessName } else { "unknown" }
        if ($name -notmatch '^node$') {
            throw "Port 3500 is owned by unexpected process $name PID $pidValue. Nothing killed."
        }
        Log "Stopping existing web process PID=$pidValue on 3500"
        Stop-Process -Id $pidValue -Force -ErrorAction Stop
        Start-Sleep -Seconds 2
    }
}

function Wait-Url([string]$Url, [int]$Seconds = 45) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    do {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 400) { return $true }
        } catch {}
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    return $false
}

function Start-NextDevDirect([string]$Node) {
    $nextBin = Join-Path $WebDir "node_modules\next\dist\bin\next"
    if (-not (Test-Path -LiteralPath $nextBin -PathType Leaf)) {
        throw "Next.js executable not found: $nextBin"
    }

    if (Test-Path -LiteralPath $WebLog) { Remove-Item -LiteralPath $WebLog -Force }
    if (Test-Path -LiteralPath $WebErr) { Remove-Item -LiteralPath $WebErr -Force }

    Log "Starting current web SOURCE directly in Next dev mode on 0.0.0.0:3500"
    Log "This bypasses the stale/failed production .next startup only."
    $p = Start-Process -FilePath $Node `
        -ArgumentList @($nextBin, "dev", "-H", "0.0.0.0", "-p", "3500") `
        -WorkingDirectory $WebDir `
        -RedirectStandardOutput $WebLog `
        -RedirectStandardError $WebErr `
        -PassThru `
        -WindowStyle Hidden
    Log "Started node PID=$($p.Id)"
    return $p
}

try {
    if (Test-Path -LiteralPath $Report) { Remove-Item -LiteralPath $Report -Force }
    Log "===================================================================="
    Log "START FULL CURRENT APP NOW - BOSS DEMO"
    Log "NO DATABASE CHANGE / NO QR CHANGE / NO SHEET DATA CHANGE"
    Log "===================================================================="

    $python = Resolve-Python
    $node = Resolve-Node
    $verify = Join-Path $PSScriptRoot "verify_demo.py"

    Log ""
    Log "[1/4] Prove recovered data is still present before touching web"
    & $python $verify pre --db $CoreDb --api "http://127.0.0.1:3550"
    if ($LASTEXITCODE -ne 0) { throw "Recovered database/API verification failed. Web was not touched." }

    Log ""
    Log "[2/4] Stop ONLY web port 3500"
    Stop-Web3500

    Log ""
    Log "[3/4] Start current app source directly (bypass npm start problem)"
    $proc = Start-NextDevDirect $node

    if (-not (Wait-Url "http://127.0.0.1:3500/" 60)) {
        Log "Web did not answer. Last startup error lines:"
        if (Test-Path -LiteralPath $WebErr) { Get-Content -LiteralPath $WebErr -Tail 40 | ForEach-Object { Log $_ } }
        if (Test-Path -LiteralPath $WebLog) { Get-Content -LiteralPath $WebLog -Tail 40 | ForEach-Object { Log $_ } }
        throw "Direct current-source web startup failed."
    }

    Log ""
    Log "[4/4] Verify boss-demo pages + data"
    & $python $verify post --db $CoreDb --api "http://127.0.0.1:3550" --web "http://127.0.0.1:3500"
    if ($LASTEXITCODE -ne 0) { throw "Boss-demo verification failed. See report." }

    Log ""
    Log "===================================================================="
    Log "SUCCESS - FULL APP IS OPEN FOR DEMO"
    Log "===================================================================="
    Log "LAN URL: http://156.156.40.51:3500"
    Log "Data verified: timetable/tests/changes/QR still present."
    Log "Web mode: current source via Next dev on port 3500."
    Log "API 3550 was NOT restarted."
    Log "Port 3457 was NOT touched."
    Log ""
    Log "Open the LAN URL and press Ctrl+F5 once."
    Write-Host ""
    Write-Host "SUCCESS - OPEN http://156.156.40.51:3500 NOW" -ForegroundColor Green
    Write-Host "Press Ctrl+F5 once." -ForegroundColor Yellow
    Write-Host "Report: $Report" -ForegroundColor White
    exit 0
}
catch {
    $msg = $_.Exception.Message
    try { Log ""; Log ("FAIL: " + $msg) } catch {}
    Write-Host ""
    Write-Host ("FAILED: " + $msg) -ForegroundColor Red
    Write-Host "No database was modified." -ForegroundColor Yellow
    Write-Host "Report: $Report" -ForegroundColor White
    Write-Host "Web stdout: $WebLog" -ForegroundColor White
    Write-Host "Web stderr: $WebErr" -ForegroundColor White
    exit 1
}
