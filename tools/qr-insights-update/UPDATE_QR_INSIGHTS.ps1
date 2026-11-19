<#
NextToppers QR - QR Insights update (2026-11-19)

What changes
  QR API (port 3550)
    - New read-only "QR Insights" analytics (sources, states, cities, networks,
      hours, returning devices). Old scans are re-read with better labels:
      Google Lens vs Google Search vs YouTube vs Gmail, mobile networks, etc.
    - New scans: Instagram / Facebook / Snapchat / LinkedIn / X in-app browsers
      are recognised automatically from the one normal QR link.
    - Includes the earlier speed fixes and QR image cache if not installed yet.
  Website (port 3500)
    - New QR Analytics page, refreshed QR tab bar (light + dark), one-link
      Share window in My QR Codes, phones open My QR Codes as cards (the list
      was empty on phones), menu links no longer pre-render every page.

What does NOT change
  The database, any QR code, slug, destination, scan, Google Sheet, timetable
  data, Cloudflare KV and the Cloudflare Worker. Nothing is deleted.

Safety
  1. Stops if any live file is not a version that was reviewed.
  2. API: tests the new code in a temporary copy, backs up, restarts only the
     QR API, checks QR and scan counts, rolls back by itself on any problem.
  3. Website: builds the new website in a separate copy first. The live site is
     not touched unless that build succeeds. Then it swaps the build (old one
     kept as backup), restarts only the website and checks the pages. If a
     check fails it puts the old build and files back and restarts again.
  The website is offline for roughly 10-60 seconds during its restart.
  QR codes keep opening during both restarts (they are answered by Cloudflare).
  Run it at a quiet time.

Run in PowerShell opened with "Run as administrator":
  powershell -ExecutionPolicy Bypass -File .\UPDATE_QR_INSIGHTS.ps1 -CheckOnly
  powershell -ExecutionPolicy Bypass -File .\UPDATE_QR_INSIGHTS.ps1
  Optional: -SkipWebsite updates only the API.
#>
param(
    [string]$AppRoot = "D:\timetable-intelligence-platform",
    [int]$ApiPort = 3550,
    [int]$WebPort = 3500,
    [string]$TaskName = "NextToppers-AutoRecovery",
    [switch]$CheckOnly,
    [switch]$SkipWebsite
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Api = "http://127.0.0.1:$ApiPort"
$WebUrl = "http://127.0.0.1:$WebPort"

# Rel, accepted live versions (Old; "" = file may not exist yet), New, Required
$ApiFiles = @(
    @{ Rel = "services\api\app\api\qr_scale.py"; Old = @("2fcc1638b7d87ad55004d1795afcfa1b49b552b9ef57ff2616eda1e3e8b9e37f", "222ef05f367f2b2c0649436eaf605053076f70f494bef614a78907af6d363f7e"); New = "7809feebbed676823cf533c158f8e4aa856613f48f2cd4165e8cb5ff778836a1"; Required = $true },
    @{ Rel = "services\api\app\api\qr_fast.py"; Old = @("dc514559d5bd3768e776feb4c8eea08810373d74264750d667d465f3c62d9fe7", "c3dd239d061106081106ded711f1876cf4b286b605d6cb6ad5f77558d9ee08f4"); New = "3b89f66c7e908ee706edf18e06c87af28b1b87e9b64ae4731a9d948cdd8cf60e"; Required = $true },
    @{ Rel = "services\api\app\api\qr_reports.py"; Old = @("f95eb508988b78fdf11bd35a394457c8116c0b62e180adfb2b5d51485e14cedf"); New = "c7c6d09f7b3d25ebc12b9754266b62116564a3e7f2afc2b22e5c2f800e962525"; Required = $true },
    @{ Rel = "services\api\app\api\routes.py"; Old = @("d5975f2107a63a9bcc759608d2a61e3c7581985bc324b0c266c8fd8596d5485c"); New = "88d385d1347a665bbfc0d6c8b51bf6a9d72d98034614a9aeac914dd8c3368df9"; Required = $true },
    @{ Rel = "services\api\app\main.py"; Old = @("d4943af13e4730baee7bfc18e2d38ebc82b3ee4351840d6ef611e5a3a8a562d8"); New = "dc9b0b69c322fe40e65933e58f87fdd7d6d7b1ce57bfb7deb3970a07c06f29f8"; Required = $true },
    @{ Rel = "services\api\app\api\qr_insights.py"; Old = @(""); New = "ecdc8707abf806f8467ef25824376648f42333fe2d804e52e54cc8a91d31b8b6"; Required = $true },
    @{ Rel = "services\api\tests\test_v140_qr_speed.py"; Old = @("", "3c7958499c45dfd99327d6cbf893db4c4178600774fc1c1eddc2acd2a5cdeb70"); New = "ddd1a243c2357c8936d697a7030d0df5d9c377220f2aa2fab9a06bddb5331edf"; Required = $false },
    @{ Rel = "services\api\tests\test_v141_qr_insights.py"; Old = @(""); New = "76235b93669dd572fbdd3bee94c9b1d04aa085e46b12c8e0ea837af57bbc5abf"; Required = $false }
)
$WebFiles = @(
    @{ Rel = "apps\web\app\qr\stats\page.tsx"; Old = @("b301fa37f2f511cefcbd3c57cb62ea412377b066955089d17454cf69c1391240"); New = "1de6da23dc19a67bc3b5fd3bb90dc033e840a1b29836880f1bce1d4a826c1859"; Required = $true },
    @{ Rel = "apps\web\app\qr\stats\insights.css"; Old = @(""); New = "09b6922fc202f217e4b9c570a41cdefd20ca9fedf9977728536b90000db1ad71"; Required = $true },
    @{ Rel = "apps\web\app\qr\codes\page.tsx"; Old = @("4f29cffc2d5574339ccbc3b807976894f23349d3e187552ee4e4ff37d73d91e1"); New = "e680d751d01a5e2d4cea03a18bf9762b49710a18ec44e1aa004da45607a5f27c"; Required = $true },
    @{ Rel = "apps\web\app\globals.css"; Old = @("3c5903479e970f69177815b5a8f67ac83e62c375d7d0a04d35713b088df51eb9"); New = "112bb6b411a4fa8e6eaa78de0b2d8794258347a995e586d3f5354a71b959e85d"; Required = $true },
    @{ Rel = "apps\web\components\navigation-links.tsx"; Old = @("dc5594bc0e6e609456ae0001d70db78ad81892a3b72c9c801e9919441864c860"); New = "7b401ee4ac871c70683aaaf6fa0ac847d92a8d702bfd8514b993f830bfb03d54"; Required = $true },
    @{ Rel = "apps\web\components\qr-product-nav.tsx"; Old = @("ce34563642255d977c3c953c1416c2cb8b81b47a9c0b0fbf9ad0ab93893eaf31"); New = "c70b59ab58b905a0dadd53b18af41881ed4743a3b06237fcc701423247bf3f6b"; Required = $true }
)

function Say([string]$Text, [string]$Color = "Gray") { Write-Host $Text -ForegroundColor $Color }
function Hash([string]$Path) { if (Test-Path -LiteralPath $Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLower() } else { "" } }
function Invoke-Native([scriptblock]$Block) {
    $old = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { & $Block } finally { $ErrorActionPreference = $old }
}

function Test-Files($Files, [string]$Label) {
    $toCopy = @()
    foreach ($f in $Files) {
        $src = Join-Path $RepoRoot $f.Rel
        $dst = Join-Path $AppRoot $f.Rel
        if ((Hash $src) -ne $f.New) { throw "The update file $src is not the expected version. Run 'git pull' in $RepoRoot and try again. Nothing was changed." }
        $live = Hash $dst
        if ($live -eq $f.New) { Say "  Already up to date: $($f.Rel)" "Green"; continue }
        if ($f.Old -contains $live) { Say "  Will update: $($f.Rel)"; $toCopy += $f; continue }
        if ($f.Required) { throw "$Label file $dst is a version that was not reviewed (SHA $live). Nothing was changed. Send this message to Claude." }
        Say "  Skipped (different local version kept): $($f.Rel)" "Yellow"
    }
    return ,$toCopy
}

function Backup-Files($Files, [string]$Backup) {
    foreach ($f in $Files) {
        $dst = Join-Path $AppRoot $f.Rel
        if (Test-Path -LiteralPath $dst) {
            $bdst = Join-Path $Backup $f.Rel
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $bdst) | Out-Null
            Copy-Item -LiteralPath $dst -Destination $bdst -Force
        }
    }
}
function Apply-Files($Files) {
    foreach ($f in $Files) {
        $dst = Join-Path $AppRoot $f.Rel
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
        Copy-Item -LiteralPath (Join-Path $RepoRoot $f.Rel) -Destination $dst -Force
        Say "  Updated $($f.Rel)" "Green"
    }
}
function Restore-Files($Files, [string]$Backup) {
    foreach ($f in $Files) {
        $dst = Join-Path $AppRoot $f.Rel
        $bsrc = Join-Path $Backup $f.Rel
        if (Test-Path -LiteralPath $bsrc) { Copy-Item -LiteralPath $bsrc -Destination $dst -Force } else { Remove-Item -LiteralPath $dst -Force -ErrorAction SilentlyContinue }
    }
}

# ---------------------------------------------------------------- API helpers
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

function Stop-Watchdogs {
    $watchdogs = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'" | Where-Object { $_.CommandLine -match 'WATCHDOG' -and $_.ProcessId -ne $PID })
    foreach ($w in $watchdogs) { Stop-Process -Id $w.ProcessId -Force -ErrorAction SilentlyContinue }
}

function Restart-QrApi {
    Stop-Watchdogs
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

# ------------------------------------------------------------ website helpers
function Get-WebProcess {
    $listen = Get-NetTCPConnection -LocalPort $WebPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $listen) { return $null }
    return Get-CimInstance Win32_Process -Filter "ProcessId=$($listen.OwningProcess)"
}

function Get-WebPlan {
    $web = Join-Path $AppRoot "apps\web"
    $proc = Get-WebProcess
    if (-not $proc) { throw "Nothing is listening on port $WebPort, so the website start command is unknown. Nothing was changed. Send this message to Claude." }
    if ($proc.Name -notmatch '^node') { throw "Port $WebPort belongs to $($proc.Name), not Node.js. Nothing was changed. Send this message to Claude." }
    $cmd = [string]$proc.CommandLine
    $mode = $null
    $serverJs = $null
    if ($cmd -match '([A-Za-z]:\\[^"]*?server\.js)') {
        $serverJs = $Matches[1]
        $standaloneRoot = Join-Path $web ".next\standalone"
        if (-not $serverJs.StartsWith($standaloneRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "The website runs $serverJs, which is outside $standaloneRoot. Nothing was changed. Send this message to Claude."
        }
        $mode = "standalone"
    } elseif ($cmd -match 'server\.js') {
        $serverJs = Join-Path $web ".next\standalone\server.js"
        if (-not (Test-Path -LiteralPath $serverJs)) { throw "The website runs a relative server.js that was not found under $web\.next\standalone. Nothing was changed. Send this message to Claude." }
        $mode = "standalone"
    } elseif ($cmd -match 'next') {
        $mode = "next-start"
    } else {
        throw "Unrecognised website start command: $cmd. Nothing was changed. Send this message to Claude."
    }
    $nextBin = Join-Path $web "node_modules\next\dist\bin\next"
    if (-not (Test-Path -LiteralPath $nextBin)) { throw "Next.js is not installed in $web\node_modules, so the website cannot be rebuilt here. Nothing was changed. Send this message to Claude." }
    $top = $proc
    while ($true) {
        $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($top.ParentProcessId)" -ErrorAction SilentlyContinue
        if ($parent -and $parent.Name -match '^(node|cmd|npm)' -and $parent.CommandLine -match 'next|npm|server\.js|apps\\web') { $top = $parent } else { break }
    }
    return [pscustomobject]@{ Web = $web; Proc = $proc; Top = $top; Node = $proc.ExecutablePath; Cmd = $cmd; Mode = $mode; ServerJs = $serverJs; NextBin = $nextBin }
}

function Test-Website {
    $paths = @("/", "/timetable", "/qr", "/qr/codes", "/qr/stats", "/qr/reports")
    foreach ($p in $paths) {
        try {
            $r = Invoke-WebRequest -Uri "$WebUrl$p" -UseBasicParsing -TimeoutSec 30
            if ($r.StatusCode -ne 200) { Say "    $p -> HTTP $($r.StatusCode)" "Red"; return $false }
        } catch { Say "    $p -> $($_.Exception.Message)" "Red"; return $false }
    }
    try {
        $stats = Invoke-WebRequest -Uri "$WebUrl/qr/stats" -UseBasicParsing -TimeoutSec 30
        if ($stats.Content -notmatch 'Verified scan analytics') { Say "    /qr/stats is not the new page" "Red"; return $false }
        $o = Invoke-RestMethod -Uri "$WebUrl/backend/api/v1/qr-insights/overview?period=7d" -TimeoutSec 60
        if ($null -eq $o.totals) { Say "    QR Insights API answer is incomplete" "Red"; return $false }
    } catch { Say "    New analytics check failed: $($_.Exception.Message)" "Red"; return $false }
    return $true
}

function Start-Website($Plan) {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) { Start-ScheduledTask -TaskName $TaskName }
    for ($i = 0; $i -lt 18; $i++) {
        Start-Sleep -Seconds 5
        if (Get-WebProcess) { return $true }
    }
    # The recovery task did not start it: start it the same way it was running.
    Say "  Starting the website directly..." "Yellow"
    $env:PORT = "$WebPort"
    $env:NODE_ENV = "production"
    if ($Plan.Mode -eq "standalone") {
        $env:HOSTNAME = "0.0.0.0"
        Start-Process -FilePath $Plan.Node -ArgumentList "`"$($Plan.ServerJs)`"" -WorkingDirectory (Split-Path -Parent $Plan.ServerJs) -WindowStyle Hidden
    } else {
        Start-Process -FilePath $Plan.Node -ArgumentList "`"$($Plan.NextBin)`" start -p $WebPort" -WorkingDirectory $Plan.Web -WindowStyle Hidden
    }
    for ($i = 0; $i -lt 24; $i++) {
        Start-Sleep -Seconds 5
        if (Get-WebProcess) { return $true }
    }
    return $false
}

function Stop-Website($Plan) {
    Stop-Watchdogs
    $p = Get-WebProcess
    if ($p) {
        $top = $p
        while ($true) {
            $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($top.ParentProcessId)" -ErrorAction SilentlyContinue
            if ($parent -and $parent.Name -match '^(node|cmd|npm)' -and $parent.CommandLine -match 'next|npm|server\.js|apps\\web') { $top = $parent } else { break }
        }
        Invoke-Native { & taskkill.exe /PID $top.ProcessId /T /F 2>&1 | Out-Null }
    }
    for ($i = 0; $i -lt 20; $i++) { if (-not (Get-WebProcess)) { Start-Sleep -Seconds 2; return }; Start-Sleep -Seconds 1 }
    throw "The website did not stop. Nothing else was changed."
}

function Install-StandaloneAssets($Plan) {
    if ($Plan.Mode -ne "standalone") { return }
    $sdir = Split-Path -Parent $Plan.ServerJs
    $static = Join-Path $Plan.Web ".next\static"
    $public = Join-Path $Plan.Web "public"
    Invoke-Native { & robocopy.exe $static (Join-Path $sdir ".next\static") /E /NFL /NDL /NJH /NJS /NP | Out-Null }
    if (Test-Path -LiteralPath $public) { Invoke-Native { & robocopy.exe $public (Join-Path $sdir "public") /E /NFL /NDL /NJH /NJS /NP | Out-Null } }
}

# ======================================================================= run
Say ""
Say "=== NextToppers QR - QR Insights update ===" "Cyan"
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin -and -not $CheckOnly) { throw "Open PowerShell with 'Run as administrator' and run again. Nothing was changed." }
if (-not (Test-Path -LiteralPath $AppRoot)) { throw "App folder $AppRoot not found. Nothing was changed." }

Say ""
Say "1. Checking files" "Cyan"
$apiCopy = Test-Files $ApiFiles "Live API"
$webCopy = @()
$plan = $null
if (-not $SkipWebsite) {
    $webCopy = Test-Files $WebFiles "Live website"
    if ($webCopy.Count) {
        $plan = Get-WebPlan
        Say "  Website: $($plan.Mode) mode, Node $($plan.Node)" "Green"
        Say "  Start command: $($plan.Cmd)"
    }
}
$before = Get-ApiState
if ($before.Ok) { Say "  QR API is healthy: $($before.Qr) QR codes, $($before.Scans) scans." "Green" }
else { Say "  QR API is not answering on port $ApiPort right now." "Yellow" }

if (-not $apiCopy.Count -and -not $webCopy.Count) { Say ""; Say "Nothing to update." "Green"; return }
if ($CheckOnly) { Say ""; Say "Check only: nothing was changed." "Green"; return }

$backup = Join-Path $AppRoot "backups\qr-insights-$Stamp"

# ------------------------------------------------------------- API phase
if ($apiCopy.Count) {
    Say ""
    Say "2. QR API: testing the new code in a temporary copy (live app untouched)" "Cyan"
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
    foreach ($f in $ApiFiles) { $d = Join-Path $stage $f.Rel; New-Item -ItemType Directory -Force -Path (Split-Path -Parent $d) | Out-Null; Copy-Item -LiteralPath (Join-Path $RepoRoot $f.Rel) -Destination $d -Force }
    $env:NEXTTOPPERS_QR_EDGE_SYNC = "off"
    $env:DATABASE_URL = "sqlite:///" + ((Join-Path $stage "stage-test.db") -replace '\\', '/')
    Push-Location "$stage\services\api"
    try {
        $out = Invoke-Native { & $py -c "import app.main, app.api.qr_insights as i, app.api.qr_scale as s, app.api.qr_fast as f, app.api.routes as r; assert i.classify_source and s._schema_ready and f._in_app and r._render_qr_png_uncached; print('IMPORT OK')" 2>&1 }
        if (($out | Out-String) -notmatch 'IMPORT OK') { throw "The new code did not load: $out. Nothing was changed." }
        Say "  New code loads correctly." "Green"
        Invoke-Native { & $py -m pytest --version 2>&1 | Out-Null }
        if ($LASTEXITCODE -eq 0) {
            $testOut = Invoke-Native { & $py -m pytest -q -p no:cacheprovider tests/test_v141_qr_insights.py tests/test_v140_qr_speed.py tests/test_v116_qr_analytics.py tests/test_v121_url_update.py 2>&1 | Out-String }
            if ($LASTEXITCODE -ne 0) { throw "Tests failed in the temporary copy. Nothing was changed.`n$testOut" }
            Say ("  Tests passed: " + (($testOut -split "`n" | Where-Object { $_ -match 'passed' }) -join ' ').Trim()) "Green"
        } else { Say "  pytest is not installed for this Python; load check only." "Yellow" }
    } finally {
        Pop-Location
        Remove-Item Env:\NEXTTOPPERS_QR_EDGE_SYNC -ErrorAction SilentlyContinue
        Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue
    }

    Say ""
    Say "3. QR API: backing up, updating and restarting" "Cyan"
    Backup-Files $apiCopy $backup
    Say "  Backup: $backup"
    Apply-Files $apiCopy
    $ok = $false
    try { $ok = Restart-QrApi } catch { Say "  $_" "Red" }
    $after = Get-ApiState
    if ($ok -and $after.Ok -and ($before.Qr -lt 0 -or ($after.Qr -eq $before.Qr -and $after.Scans -ge $before.Scans))) {
        Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
        Say "  QR API healthy: $($after.Qr) QR codes (before $($before.Qr)), $($after.Scans) scans (before $($before.Scans))." "Green"
    } else {
        Say "  Check failed (healthy=$($after.Ok), QR $($after.Qr) vs $($before.Qr), scans $($after.Scans) vs $($before.Scans)). Putting the old API files back..." "Red"
        Restore-Files $apiCopy $backup
        try { [void](Restart-QrApi) } catch { Say "  $_" "Red" }
        $final = Get-ApiState
        Say "ROLLED BACK the API. Website not touched. QR API healthy=$($final.Ok), $($final.Qr) QR codes. Send this whole window to Claude." "Red"
        exit 1
    }
}

# --------------------------------------------------------- website phase
if ($webCopy.Count) {
    Say ""
    Say "4. Website: building the new version in a separate copy (live site untouched)" "Cyan"
    # Remove build copies left by an earlier failed run (only our own web-stage-* folders; they hold copies, never links).
    Get-ChildItem -LiteralPath (Join-Path $AppRoot "backups") -Directory -Filter "web-stage-*" -ErrorAction SilentlyContinue | ForEach-Object {
        Say "  Removing old build copy $($_.Name)"
        Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
    }
    $wstage = Join-Path $AppRoot "backups\web-stage-$Stamp"
    Invoke-Native { & robocopy.exe $plan.Web $wstage /E /XD node_modules .next .turbo coverage test-results playwright-report /XF *.log /NFL /NDL /NJH /NJS /NP | Out-Null }
    if ($LASTEXITCODE -ge 8) { throw "Could not copy the website for building (robocopy $LASTEXITCODE). The QR API update is installed; the website was not changed." }
    # A real copy (not a link): the build must never be able to touch the live node_modules.
    Invoke-Native { & robocopy.exe "$($plan.Web)\node_modules" "$wstage\node_modules" /E /MT:16 /NFL /NDL /NJH /NJS /NP | Out-Null }
    if ($LASTEXITCODE -ge 8) { throw "Could not copy node_modules for building (robocopy $LASTEXITCODE). The QR API update is installed; the website was not changed." }
    foreach ($f in $WebFiles) {
        $rel = $f.Rel.Substring("apps\web\".Length)
        $d = Join-Path $wstage $rel
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $d) | Out-Null
        Copy-Item -LiteralPath (Join-Path $RepoRoot $f.Rel) -Destination $d -Force
    }
    $env:NEXT_TELEMETRY_DISABLED = "1"
    if (-not $env:INTERNAL_API_URL) { $env:INTERNAL_API_URL = "http://127.0.0.1:$ApiPort" }
    # next build must run with NODE_ENV=production. Any other value (from this window,
    # Windows settings or an .env file) makes Next.js 16 fail on "/_global-error".
    $nodeEnvFiles = @(Get-ChildItem -LiteralPath $wstage -Filter ".env*" -File -Force -ErrorAction SilentlyContinue | Where-Object { Select-String -LiteralPath $_.FullName -Pattern '^\s*NODE_ENV\s*=' -Quiet } | ForEach-Object { $_.Name })
    Say ("  NODE_ENV before build: window='" + [string]$env:NODE_ENV + "', Windows machine='" + [string][Environment]::GetEnvironmentVariable("NODE_ENV", "Machine") + "', user='" + [string][Environment]::GetEnvironmentVariable("NODE_ENV", "User") + "', set in files: " + $(if ($nodeEnvFiles.Count) { $nodeEnvFiles -join ", " } else { "none" }))
    $env:NODE_ENV = "production"

    # How was the live site built? Use the same builder first (Turbopack is the Next.js 16
    # default; Webpack is the long-standing one). Each try happens only in the copy.
    $liveNextDir = Join-Path $plan.Web ".next"
    $liveBuilder = "unknown"
    if (Test-Path -LiteralPath (Join-Path $liveNextDir "server\webpack-runtime.js")) { $liveBuilder = "webpack" }
    elseif (Test-Path -LiteralPath (Join-Path $liveNextDir "server\chunks\ssr")) { $liveBuilder = "turbopack" }
    $liveBuiltAt = ""
    if (Test-Path -LiteralPath (Join-Path $liveNextDir "BUILD_ID")) { $liveBuiltAt = [string](Get-Item -LiteralPath (Join-Path $liveNextDir "BUILD_ID")).LastWriteTime }
    $ver = { param($pkg) try { (Get-Content -Raw -LiteralPath (Join-Path $plan.Web "node_modules\$pkg\package.json") | ConvertFrom-Json).version } catch { "?" } }
    $nodeVer = (Invoke-Native { & $plan.Node --version 2>&1 | Out-String }).Trim()
    Say "  Live site was built with: $liveBuilder ($liveBuiltAt). Node $nodeVer, next $(& $ver 'next'), react $(& $ver 'react'), react-dom $(& $ver 'react-dom')"
    $envNames = @()
    foreach ($ef in @(Get-ChildItem -LiteralPath $wstage -Filter ".env*" -File -Force -ErrorAction SilentlyContinue)) {
        $names = @(Get-Content -LiteralPath $ef.FullName | ForEach-Object { if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=') { $Matches[1] } })
        $envNames += "$($ef.Name): $($names -join ', ')"
    }
    Say ("  Settings files (names only): " + $(if ($envNames.Count) { $envNames -join ' | ' } else { "none" }))
    Say ("  NODE_OPTIONS set: " + $(if ($env:NODE_OPTIONS) { "yes" } else { "no" }))

    $attempts = @("turbopack", "webpack")
    if ($liveBuilder -eq "webpack") { $attempts = @("webpack", "turbopack") }
    $built = $false
    $buildOut = ""
    foreach ($builder in $attempts) {
        Remove-Item -LiteralPath (Join-Path $wstage ".next") -Recurse -Force -ErrorAction SilentlyContinue
        Say "  Building with $builder..."
        Push-Location $wstage
        try {
            if ($builder -eq "webpack") { $buildOut = Invoke-Native { & $plan.Node $plan.NextBin build --webpack 2>&1 | Out-String } }
            else { $buildOut = Invoke-Native { & $plan.Node $plan.NextBin build 2>&1 | Out-String } }
            $buildCode = $LASTEXITCODE
        } finally { Pop-Location }
        if ($buildCode -eq 0 -and (Test-Path -LiteralPath (Join-Path $wstage ".next\BUILD_ID"))) { $built = $true; Say "  Build with $builder succeeded." "Green"; break }
        $short = ($buildOut -split "`n" | Where-Object { $_ -match 'Error|error|Invariant|prerender|failed' } | Select-Object -First 6) -join "`n"
        Say "  Build with $builder failed:" "Yellow"
        Say $short "Yellow"
    }
    if (-not $built) {
        $tail = ($buildOut -split "`n" | Select-Object -Last 30) -join "`n"
        Say $tail "Yellow"
        Remove-Item -LiteralPath $wstage -Recurse -Force -ErrorAction SilentlyContinue
        throw "The new website did not build, so the live website was NOT changed (the QR API update is installed and working). Send this whole window to Claude."
    }
    Say "  New website built successfully." "Green"
    if ($plan.Mode -eq "standalone" -and -not (Test-Path -LiteralPath (Join-Path $wstage ".next\standalone"))) {
        throw "The new build has no standalone server, but the live site needs one. Live website NOT changed. Send this window to Claude."
    }

    Say ""
    Say "5. Website: swapping in the new build and restarting (about 10-60 seconds offline)" "Cyan"
    $webBackup = Join-Path $backup "web"
    Backup-Files $webCopy $backup
    $liveNext = Join-Path $plan.Web ".next"
    $oldNext = Join-Path $plan.Web ".next.before-$Stamp"
    Stop-Website $plan
    $swapped = $false
    try {
        if (Test-Path -LiteralPath $liveNext) { Rename-Item -LiteralPath $liveNext -NewName (Split-Path -Leaf $oldNext) }
        Move-Item -LiteralPath (Join-Path $wstage ".next") -Destination $liveNext
        $swapped = $true
        Apply-Files $webCopy
        Install-StandaloneAssets $plan
    } catch { Say "  Swap problem: $_" "Red" }

    $started = $false
    if ($swapped) { $started = Start-Website $plan }
    Start-Sleep -Seconds 3
    if ($swapped -and $started -and (Test-Website)) {
        Remove-Item -LiteralPath $wstage -Recurse -Force -ErrorAction SilentlyContinue
        if (Test-Path -LiteralPath $oldNext) {
            New-Item -ItemType Directory -Force -Path $webBackup | Out-Null
            Move-Item -LiteralPath $oldNext -Destination (Join-Path $webBackup ".next") -ErrorAction SilentlyContinue
        }
        Say "  Website healthy: home, timetable and all QR pages answer; new QR Analytics is live." "Green"
        Say ""
        Say "SUCCESS - QR INSIGHTS IS INSTALLED. No QR code, scan or database data was changed." "Green"
        Say "Backup of old files: $backup" "Gray"
        Say "Open QR Analytics and press Ctrl+F5 once to load the new design." "Green"
        return
    }

    Say "  Website check failed. Putting the old website back..." "Red"
    try { Stop-Website $plan } catch { Say "  $_" "Yellow" }
    if (Test-Path -LiteralPath $oldNext) {
        if (Test-Path -LiteralPath $liveNext) { Remove-Item -LiteralPath $liveNext -Recurse -Force -ErrorAction SilentlyContinue }
        Rename-Item -LiteralPath $oldNext -NewName ".next"
    }
    Restore-Files $webCopy $backup
    [void](Start-Website $plan)
    Start-Sleep -Seconds 3
    $siteUp = $false
    try { $siteUp = ((Invoke-WebRequest -Uri "$WebUrl/" -UseBasicParsing -TimeoutSec 30).StatusCode -eq 200) } catch {}
    Say "ROLLED BACK the website to the old version (website answering: $siteUp). The QR API update stays installed. Send this whole window to Claude." "Red"
    exit 1
}

Say ""
Say "SUCCESS - QR API part installed. No QR code, scan or database data was changed." "Green"
