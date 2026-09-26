$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Version = "v1.0.25"
$Root = "D:\timetable-intelligence-platform"
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PayloadRoot = Join-Path $PackageRoot "payload"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupRoot = Join-Path $Root "_release_backups\v1.0.25_$Stamp"
$LogRoot = Join-Path $Root "_release_logs"
$LogFile = Join-Path $LogRoot "v1.0.25_$Stamp.log"
$Applied = $false
$RestartAttempted = $false

$RelativeFiles = @(
  "apps\web\app\qr\codes\page.tsx",
  "apps\web\app\qr\templates\page.tsx",
  "apps\web\app\qr\bulk\page.tsx",
  "apps\web\app\qr\stats\page.tsx",
  "apps\web\components\pagination-controls.tsx",
  "apps\web\lib\pagination.ts",
  "apps\web\lib\pagination.test.ts"
)
$GlobalsRelative = "apps\web\app\globals.css"
$GlobalsPatchRelative = "apps\web\app\globals.v1.0.25.append.css"

function Log([string]$Message, [string]$Level = "INFO") {
  $line = "[{0}] [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level, $Message
  Write-Host $line
  Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
}

function Assert-LastExit([string]$Step) {
  if ($LASTEXITCODE -ne 0) { throw "$Step failed with exit code $LASTEXITCODE" }
}

function Resolve-Python {
  $candidates = @(
    (Join-Path $Root ".venv\Scripts\python.exe"),
    (Join-Path $Root "venv\Scripts\python.exe")
  )
  foreach ($candidate in $candidates) { if (Test-Path -LiteralPath $candidate) { return $candidate } }
  $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  $cmd = Get-Command python -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  throw "Python executable not found."
}

function Stop-Port([int]$Port) {
  if ($Port -eq 3457) { throw "Protected port 3457 must never be touched." }
  $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
  foreach ($listener in $listeners) {
    $pidValue = [int]$listener.OwningProcess
    if ($pidValue -le 0) { continue }
    try {
      $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$pidValue" -ErrorAction SilentlyContinue
      Log "Stopping app listener on port ${Port}: PID $pidValue $($proc.Name)"
      Stop-Process -Id $pidValue -Force -ErrorAction Stop
    } catch {
      throw "Could not stop listener PID $pidValue on port ${Port}: $($_.Exception.Message)"
    }
  }
}

function Wait-Url([string]$Url, [int]$Seconds = 75) {
  $deadline = (Get-Date).AddSeconds($Seconds)
  do {
    try {
      $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
      if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 400) { return $true }
    } catch { }
    Start-Sleep -Seconds 2
  } while ((Get-Date) -lt $deadline)
  return $false
}

function Assert-RuntimeJson([string]$Url, [string]$Name) {
  try {
    $null = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 20
    Log "PASS runtime API $Name"
  } catch {
    throw "Runtime API check failed for $Name at ${Url}: $($_.Exception.Message)"
  }
}

function Test-QrRuntimeLifecycle {
  $templateId = $null
  $codeIds = @()
  $probe = "V1_0_25_ACCEPTANCE_$Stamp"
  try {
    Log "Running temporary QR template/bulk/independent-analytics lifecycle probe."
    $templatePayload = @{
      name = "$probe Template"
      description = "Temporary v1.0.25 acceptance template"
      tracking_mode = "tracked"
      identity_mode = "anonymous"
      design = @{
        foreground_color = "#173EA5"
        background_color = "#FFFFFF"
        dot_style = "dots"
        marker_border_style = "circle"
        marker_center_style = "rounded"
        frame_style = "badge"
        frame_text = "SCAN NOW"
        logo_scale_percent = 20
      }
      experience = @{
        mode = "page"
        title = "Opening"
        message = "Please wait"
        accent_color = "#2455FF"
        background_color = "#F8FAFC"
        redirect_delay_ms = 900
        image_fit = "cover"
        image_scale_percent = 100
      }
    } | ConvertTo-Json -Depth 10
    $template = Invoke-RestMethod -Uri "http://127.0.0.1:3550/api/v1/qr-templates" -Method Post -ContentType "application/json" -Body $templatePayload -TimeoutSec 20
    $templateId = [string]$template.id
    if ([string]::IsNullOrWhiteSpace($templateId)) { throw "Temporary QR template did not return an id." }

    $bulkPayload = @{
      template_id = $templateId
      items = @(
        @{ name = "$probe A"; url = "https://example.com/v1-0-25-a" },
        @{ name = "$probe B"; url = "https://example.com/v1-0-25-b" }
      )
    } | ConvertTo-Json -Depth 10
    $bulk = Invoke-RestMethod -Uri "http://127.0.0.1:3550/api/v1/qr-bulk" -Method Post -ContentType "application/json" -Body $bulkPayload -TimeoutSec 30
    $created = @($bulk.created)
    if ($created.Count -ne 2) { throw "Bulk lifecycle probe expected 2 QR codes but received $($created.Count)." }
    $first = $created[0]
    $second = $created[1]
    $codeIds = @([string]($first.id), [string]($second.id))
    if ($codeIds[0] -eq $codeIds[1] -or [string]($first.slug) -eq [string]($second.slug)) { throw "Bulk QR IDs/slugs are not independent." }

    $image = Invoke-WebRequest -Uri ("http://127.0.0.1:3550/api/v1/qr-codes/{0}/image?format=png" -f $codeIds[0]) -UseBasicParsing -TimeoutSec 20
    if ($image.StatusCode -ne 200) { throw "Temporary QR PNG endpoint did not return HTTP 200." }

    $confirmPayload = @{ visitor_id = "$probe-device-a"; event_id = "$probe-event-a" } | ConvertTo-Json
    $null = Invoke-RestMethod -Uri ("http://127.0.0.1:3550/api/v1/qr/confirm/{0}" -f [string]($first.slug)) -Method Post -ContentType "application/json" -Body $confirmPayload -Headers @{ "cf-ipcountry" = "IN" } -UserAgent "Mozilla/5.0 Chrome/151 Safari/537.36" -TimeoutSec 20

    $firstStats = Invoke-RestMethod -Uri ("http://127.0.0.1:3550/api/v1/qr-analytics?qr_id={0}" -f $codeIds[0]) -Method Get -TimeoutSec 20
    $secondStats = Invoke-RestMethod -Uri ("http://127.0.0.1:3550/api/v1/qr-analytics?qr_id={0}" -f $codeIds[1]) -Method Get -TimeoutSec 20
    if ([int]$firstStats.total_scans -ne 1) { throw "Independent analytics probe expected QR A total_scans=1 but got $($firstStats.total_scans)." }
    if ([int]$secondStats.total_scans -ne 0) { throw "Independent analytics probe expected QR B total_scans=0 but got $($secondStats.total_scans)." }

    Invoke-RestMethod -Uri ("http://127.0.0.1:3550/api/v1/qr-templates/{0}" -f $templateId) -Method Delete -TimeoutSec 20 | Out-Null
    $templateId = $null
    $persisted = Invoke-RestMethod -Uri ("http://127.0.0.1:3550/api/v1/qr-codes/{0}" -f $codeIds[0]) -Method Get -TimeoutSec 20
    if ($null -ne $persisted.template_id -and -not [string]::IsNullOrWhiteSpace([string]$persisted.template_id)) { throw "Deleting template did not detach provenance from existing QR." }
    Log "PASS QR template/bulk/image/independent-analytics/template-delete lifecycle probe."
  } finally {
    foreach ($codeId in $codeIds) {
      if ([string]::IsNullOrWhiteSpace($codeId)) { continue }
      try { Invoke-RestMethod -Uri ("http://127.0.0.1:3550/api/v1/qr-codes/{0}" -f $codeId) -Method Delete -TimeoutSec 20 | Out-Null } catch { Log "Temporary QR cleanup warning for ${codeId}: $($_.Exception.Message)" "WARN" }
    }
    if (-not [string]::IsNullOrWhiteSpace([string]$templateId)) {
      try { Invoke-RestMethod -Uri ("http://127.0.0.1:3550/api/v1/qr-templates/{0}" -f $templateId) -Method Delete -TimeoutSec 20 | Out-Null } catch { Log "Temporary template cleanup warning: $($_.Exception.Message)" "WARN" }
    }
  }
}

function Start-App {
  $python = Resolve-Python
  $apiDir = Join-Path $Root "services\api"
  $webDir = Join-Path $Root "apps\web"
  Log "Starting API on 3550."
  Start-Process -FilePath $python -ArgumentList @("-m","uvicorn","app.main:app","--host","0.0.0.0","--port","3550") -WorkingDirectory $apiDir -WindowStyle Hidden | Out-Null
  Log "Starting Web on 3500."
  Start-Process -FilePath "npm.cmd" -ArgumentList @("run","start","--","-p","3500") -WorkingDirectory $webDir -WindowStyle Hidden | Out-Null
}

function Restore-Backup {
  Log "ROLLBACK STARTED" "ROLLBACK"
  Stop-Port 3500
  Stop-Port 3550
  foreach ($rel in $RelativeFiles) {
    $backup = Join-Path $BackupRoot $rel
    $dest = Join-Path $Root $rel
    if (Test-Path -LiteralPath $backup) {
      New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force | Out-Null
      Copy-Item -LiteralPath $backup -Destination $dest -Force
    } else {
      if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Force }
    }
  }
  $globalsBackup = Join-Path $BackupRoot $GlobalsRelative
  $globalsDest = Join-Path $Root $GlobalsRelative
  if (Test-Path -LiteralPath $globalsBackup) { Copy-Item -LiteralPath $globalsBackup -Destination $globalsDest -Force }
  $nextBackup = Join-Path $BackupRoot ".next"
  $nextDest = Join-Path $Root "apps\web\.next"
  if (Test-Path -LiteralPath $nextDest) { Remove-Item -LiteralPath $nextDest -Recurse -Force }
  if (Test-Path -LiteralPath $nextBackup) { Copy-Item -LiteralPath $nextBackup -Destination $nextDest -Recurse -Force }
  Start-App
  $webOk = Wait-Url "http://127.0.0.1:3500/qr/codes" 75
  $apiOk = Wait-Url "http://127.0.0.1:3550/api/v1/dashboard" 75
  Log "ROLLBACK COMPLETE. Web=$webOk API=$apiOk" "ROLLBACK"
}

try {
  if (-not (Test-Path -LiteralPath $Root)) { throw "Application root not found: $Root" }
  if (-not (Test-Path -LiteralPath $PayloadRoot)) { throw "Payload folder missing: $PayloadRoot" }
  New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null
  New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
  Log "$Version acceptance started."
  Log "Protected port 3457 will not be touched."

  foreach ($rel in $RelativeFiles) {
    $src = Join-Path $PayloadRoot $rel
    if (-not (Test-Path -LiteralPath $src -PathType Leaf)) { throw "Payload file missing: $rel" }
    $dest = Join-Path $Root $rel
    $backup = Join-Path $BackupRoot $rel
    if (Test-Path -LiteralPath $dest -PathType Leaf) {
      New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
      Copy-Item -LiteralPath $dest -Destination $backup -Force
    }
  }
  $globalsDest = Join-Path $Root $GlobalsRelative
  $globalsBackup = Join-Path $BackupRoot $GlobalsRelative
  $globalsPatch = Join-Path $PayloadRoot $GlobalsPatchRelative
  if (-not (Test-Path -LiteralPath $globalsDest -PathType Leaf)) { throw "Runtime CSS missing: $GlobalsRelative" }
  if (-not (Test-Path -LiteralPath $globalsPatch -PathType Leaf)) { throw "Payload CSS patch missing: $GlobalsPatchRelative" }
  New-Item -ItemType Directory -Path (Split-Path -Parent $globalsBackup) -Force | Out-Null
  Copy-Item -LiteralPath $globalsDest -Destination $globalsBackup -Force
  $nextDest = Join-Path $Root "apps\web\.next"
  if (Test-Path -LiteralPath $nextDest) {
    Log "Backing up current Next.js .next build."
    Copy-Item -LiteralPath $nextDest -Destination (Join-Path $BackupRoot ".next") -Recurse -Force
  }

  foreach ($rel in $RelativeFiles) {
    $src = Join-Path $PayloadRoot $rel
    $dest = Join-Path $Root $rel
    New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force | Out-Null
    Copy-Item -LiteralPath $src -Destination $dest -Force
    Log "Applied $rel"
  }
  $css = Get-Content -LiteralPath $globalsDest -Raw
  $marker = "/* ================================================================`n   v1.0.25 — shared pagination + larger QR library"
  $markerIndex = $css.IndexOf($marker)
  if ($markerIndex -ge 0) { $css = $css.Substring(0, $markerIndex) }
  $css = $css.TrimEnd()
  $patchCss = (Get-Content -LiteralPath $globalsPatch -Raw).TrimStart()
  Set-Content -LiteralPath $globalsDest -Value ($css + "`r`n`r`n" + $patchCss) -Encoding UTF8
  Log "Applied $GlobalsRelative from deterministic v1.0.25 append patch."
  $Applied = $true

  $codesText = Get-Content -LiteralPath (Join-Path $Root "apps\web\app\qr\codes\page.tsx") -Raw
  $bulkText = Get-Content -LiteralPath (Join-Path $Root "apps\web\app\qr\bulk\page.tsx") -Raw
  $statsText = Get-Content -LiteralPath (Join-Path $Root "apps\web\app\qr\stats\page.tsx") -Raw
  foreach ($needle in @("Delete Selected","Copy Source Link","Copy QR Link","Show QR","paginateItems(filtered, page, 8)")) { if (-not $codesText.Contains($needle)) { throw "v1.0.25 QR Library source contract missing: $needle" } }
  foreach ($needle in @("paginateItems(templates,templatePage,6)","paginateItems(rows,rowPage,10)","paginateItems(created,resultPage,10)")) { if (-not $bulkText.Contains($needle)) { throw "v1.0.25 Bulk source contract missing: $needle" } }
  foreach ($needle in @("paginateItems(analytics.top_devices, devicePage, 6)","paginateItems(analytics.recent_scans, recentPage, 15)")) { if (-not $statsText.Contains($needle)) { throw "v1.0.25 Analytics source contract missing: $needle" } }
  Log "PASS v1.0.25 source contract."

  $python = Resolve-Python
  Push-Location $Root
  try {
    Log "Running complete backend test suite."
    & $python -m pytest "services\api\tests" -q
    Assert-LastExit "Backend tests"
    Log "PASS backend tests."
  } finally { Pop-Location }

  $webDir = Join-Path $Root "apps\web"
  Push-Location $webDir
  try {
    Log "Running complete functional web regression suite (coverage disabled for release gate)."
    $vitest = Join-Path $webDir "node_modules\.bin\vitest.cmd"
    if (-not (Test-Path -LiteralPath $vitest)) { throw "Local Vitest executable not found: $vitest" }
    & $vitest run
    Assert-LastExit "Web regression tests"
    Log "PASS web regression tests."

    Log "Running real project TypeScript typecheck."
    & npm.cmd run typecheck
    Assert-LastExit "TypeScript typecheck"
    Log "PASS TypeScript typecheck."

    Log "Stopping only web port 3500 before replacing the production .next build."
    Stop-Port 3500
    $RestartAttempted = $true
    Log "Building production Next.js output."
    & npm.cmd run build
    Assert-LastExit "Next.js production build"
    Log "PASS Next.js production build."
  } finally { Pop-Location }

  Log "Restarting only timetable app ports 3500 and 3550."
  Stop-Port 3500
  Stop-Port 3550
  $RestartAttempted = $true
  Start-App

  if (-not (Wait-Url "http://127.0.0.1:3550/api/v1/dashboard" 75)) { throw "API smoke check failed on 3550." }
  Assert-RuntimeJson "http://127.0.0.1:3550/api/v1/dashboard" "Dashboard"
  Assert-RuntimeJson "http://127.0.0.1:3550/api/v1/timetable?page=1&page_size=1" "Timetable"
  Assert-RuntimeJson "http://127.0.0.1:3550/api/v1/changes?page=1&page_size=1&period=today&view=cells" "Sheet Updates"
  Assert-RuntimeJson "http://127.0.0.1:3550/api/v1/test-monitor?compact=true" "Test Monitor"
  foreach ($path in @("/qr","/qr/templates","/qr/bulk","/qr/codes","/qr/stats")) {
    if (-not (Wait-Url ("http://127.0.0.1:3500" + $path) 75)) { throw "Web smoke check failed: $path" }
    Log "PASS page smoke $path"
  }
  Test-QrRuntimeLifecycle

  Log "ACCEPTED $Version. Backup retained at $BackupRoot" "PASS"
  Write-Host ""
  Write-Host "SUCCESS: v1.0.25 accepted." -ForegroundColor Green
  Write-Host "Log: $LogFile"
  exit 0
}
catch {
  $message = $_.Exception.Message
  try { Log "FAIL: $message" "FAIL" } catch { Write-Host "FAIL: $message" }
  if ($Applied) {
    try { Restore-Backup } catch { try { Log "ROLLBACK ERROR: $($_.Exception.Message)" "FAIL" } catch {} }
  }
  Write-Host ""
  Write-Host "v1.0.25 NOT ACCEPTED: $message" -ForegroundColor Red
  if (Test-Path -LiteralPath $LogFile) { Write-Host "Log: $LogFile" }
  exit 1
}
