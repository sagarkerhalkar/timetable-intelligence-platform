<#
Fixes: "Cloudflare QR sync failed; QR creation was rolled back ...
        CLOUDFLARE_API_TOKEN ... / Invalid access token [code: 9109]"

Why it happens
  Since 9 Oct 2026 the QR API (port 3550) is started in the background by the
  scheduled task NextToppers-AutoRecovery, which runs as Local SYSTEM.
  SYSTEM cannot use the Cloudflare login (wrangler login) of your own Windows
  user, so every QR sync needs a Cloudflare API token in CLOUDFLARE_API_TOKEN.
  The token set on the server now is rejected by Cloudflare (Invalid access token).

What this script does
  1. Shows whether a token is set (it never prints a token).
  2. Asks for a NEW token and tests it with Cloudflare using READ-ONLY calls.
  3. Saves it for the whole computer, so SYSTEM can use it, and checks that a
     SYSTEM scheduled task really sees it.
  4. Restarts ONLY the QR API on port 3550 so it picks up the token.

What it never does
  It does not create, edit or delete any QR code, scan, database row,
  Cloudflare KV value, Worker code or Worker deployment.
  Web 3500, Sheets and timetables are not touched.

Run in PowerShell opened with "Run as administrator":
  powershell -ExecutionPolicy Bypass -File .\FIX_QR_CLOUDFLARE_TOKEN.ps1
  Add -CheckOnly to only look, without changing anything.
#>
param(
    [string]$AccountId = "7568b005c1ad536426ee8a2af8ba43f4",
    [string]$WorkerName = "q",
    [int]$ApiPort = 3550,
    [string]$TaskName = "NextToppers-AutoRecovery",
    [string]$AppRoot = "D:\timetable-intelligence-platform",
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch { }
$CfApi = "https://api.cloudflare.com/client/v4"

function Say([string]$Text, [string]$Color = "Gray") { Write-Host $Text -ForegroundColor $Color }

function Invoke-CF([string]$Path, [string]$Token) {
    try {
        $r = Invoke-RestMethod -Uri ($CfApi + $Path) -Headers @{ Authorization = "Bearer $Token" } -Method Get -TimeoutSec 30
        return @{ ok = [bool]$r.success; result = $r.result; error = "" }
    } catch {
        $msg = $_.Exception.Message
        $body = $null
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) { $body = $_.ErrorDetails.Message }
        elseif ($_.Exception.Response) {
            try { $sr = New-Object IO.StreamReader($_.Exception.Response.GetResponseStream()); $body = $sr.ReadToEnd() } catch { }
        }
        if ($body) {
            try {
                $j = $body | ConvertFrom-Json
                if ($j.errors) { $msg = (@($j.errors) | ForEach-Object { "$($_.message) [code $($_.code)]" }) -join "; " }
            } catch { }
        }
        return @{ ok = $false; result = $null; error = $msg }
    }
}

function Test-Token([string]$Token) {
    $checks = @()
    $v = Invoke-CF "/user/tokens/verify" $Token
    if (-not $v.ok) { $v2 = Invoke-CF "/accounts/$AccountId/tokens/verify" $Token; if ($v2.ok) { $v = $v2 } }
    $active = [bool]($v.ok -and $v.result -and $v.result.status -eq "active")
    $checks += [pscustomobject]@{ Name = "Token is valid and active"; Pass = $active; Needed = $true; Detail = $(if ($active) { "" } else { $v.error }) }
    $d = Invoke-CF "/accounts/$AccountId/workers/scripts/$WorkerName/deployments" $Token
    $checks += [pscustomobject]@{ Name = "Reads Worker '$WorkerName' deployments (Workers Scripts: Read)"; Pass = $d.ok; Needed = $true; Detail = $d.error }
    $k = Invoke-CF "/accounts/$AccountId/storage/kv/namespaces?per_page=50" $Token
    $checks += [pscustomobject]@{ Name = "Sees KV namespaces (Workers KV Storage: Edit)"; Pass = $k.ok; Needed = $true; Detail = $(if ($k.ok) { "$(@($k.result).Count) namespace(s)" } else { $k.error }) }
    $a = Invoke-CF "/accounts/$AccountId" $Token
    $checks += [pscustomobject]@{ Name = "Reads the account (Account Settings: Read)"; Pass = $a.ok; Needed = $false; Detail = $a.error }
    return $checks
}

function Show-Checks($Checks) {
    $allNeeded = $true
    foreach ($c in $Checks) {
        if ($c.Pass) { Say ("  PASS  " + $c.Name + $(if ($c.Detail) { " - " + $c.Detail } else { "" })) "Green" }
        elseif ($c.Needed) { Say ("  FAIL  " + $c.Name + " - " + $c.Detail) "Red"; $allNeeded = $false }
        else { Say ("  WARN  " + $c.Name + " - " + $c.Detail) "Yellow" }
    }
    return $allNeeded
}

# The app can also carry its own token in a .env file; that one wins over the
# computer setting, so an old wrong token there must be replaced too.
$TokenLine = '(?m)^([ \t]*(?:export[ \t]+)?CLOUDFLARE_API_TOKEN[ \t]*=[ \t]*)([^\r\n]*?)([ \t]*\r?)$'
function Find-AppTokenFiles {
    if (-not (Test-Path -LiteralPath $AppRoot)) { return @() }
    $skip = '\\(node_modules|\.next|\.git|\.venv|venv|__pycache__|backups)(\\|$)'
    return @(Get-ChildItem -LiteralPath $AppRoot -Recurse -Depth 5 -Force -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch $skip -and $_.Length -lt 1MB -and
            ($_.Name -like ".env*" -or $_.Name -like "*.env" -or $_.Extension -in ".ps1", ".cmd", ".bat", ".json", ".jsonc", ".toml", ".py", ".ini", ".xml") } |
        Where-Object { $_.Name -notlike "*.bak-token-fix-*" -and (Select-String -LiteralPath $_.FullName -Pattern "CLOUDFLARE_API_TOKEN" -SimpleMatch -Quiet) })
}
function Get-EnvFileToken([string]$Path) {
    $m = [regex]::Match([IO.File]::ReadAllText($Path), $TokenLine)
    if ($m.Success) { return $m.Groups[2].Value.Trim().Trim('"').Trim("'") }
    return $null
}

function Get-Sha256([string]$Text) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return (-join ($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Text)) | ForEach-Object { $_.ToString("x2") })) } finally { $sha.Dispose() }
}

# A brand-new SYSTEM scheduled task reports a fingerprint (SHA-256) of the token it
# sees. This proves the watchdog (also SYSTEM) will get the same token. No secret is written.
function Test-SystemSeesToken([string]$Token) {
    $probeName = "NextToppers-TokenProbe"
    $probeFile = Join-Path $env:ProgramData ("nexttoppers-token-probe-" + [Guid]::NewGuid().ToString("N") + ".txt")
    $cmd = "`$t=[Environment]::GetEnvironmentVariable('CLOUDFLARE_API_TOKEN'); `$h='MISSING'; if (`$t) { `$s=[Security.Cryptography.SHA256]::Create(); `$h=-join (`$s.ComputeHash([Text.Encoding]::UTF8.GetBytes(`$t)) | ForEach-Object { `$_.ToString('x2') }) }; Set-Content -LiteralPath '$probeFile' -Value `$h -Encoding ASCII"
    $enc = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($cmd))
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -EncodedCommand $enc"
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    Register-ScheduledTask -TaskName $probeName -Action $action -Principal $principal -Force | Out-Null
    try {
        Start-ScheduledTask -TaskName $probeName
        for ($i = 0; $i -lt 30 -and -not (Test-Path $probeFile); $i++) { Start-Sleep -Seconds 1 }
        if (-not (Test-Path $probeFile)) { return "no answer" }
        $seen = (Get-Content -LiteralPath $probeFile -Raw).Trim()
        if ($seen -eq (Get-Sha256 $Token)) { return "same" }
        if ($seen -eq "MISSING") { return "missing" }
        return "different"
    } finally {
        Unregister-ScheduledTask -TaskName $probeName -Confirm:$false -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $probeFile -Force -ErrorAction SilentlyContinue
    }
}

Say ""
Say "=== NextToppers QR - Cloudflare token fix ===" "Cyan"
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin -and -not $CheckOnly) { throw "Open PowerShell with 'Run as administrator' and run this script again. Nothing was changed." }

# ---------- 1. What is there now (read-only) ----------
Say ""
Say "1. Current state (read-only)" "Cyan"
foreach ($scope in "Machine", "User") {
    $val = [Environment]::GetEnvironmentVariable("CLOUDFLARE_API_TOKEN", $scope)
    Say ("  CLOUDFLARE_API_TOKEN for {0}: {1}" -f $(if ($scope -eq "Machine") { "the whole computer" } else { "your user" }), $(if ($val) { "set (" + $val.Length + " characters)" } else { "not set" }))
}
$machineToken = [Environment]::GetEnvironmentVariable("CLOUDFLARE_API_TOKEN", "Machine")
if ($machineToken) {
    Say "  Testing the saved token with Cloudflare:"
    [void](Show-Checks (Test-Token $machineToken.Trim()))
}
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($task) { Say ("  Scheduled task {0}: {1}, runs as {2}" -f $TaskName, $task.State, $task.Principal.UserId) }
else { Say "  Scheduled task $TaskName was not found." "Yellow" }
$listen = Get-NetTCPConnection -LocalPort $ApiPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listen) { Say "  QR API port ${ApiPort}: running (PID $($listen.OwningProcess))" } else { Say "  QR API port ${ApiPort}: not running" "Yellow" }

$appFiles = Find-AppTokenFiles
if ($appFiles.Count) {
    Say "  Files in the app that mention CLOUDFLARE_API_TOKEN:"
    foreach ($f in $appFiles) {
        $isEnv = ($f.Name -like ".env*" -or $f.Name -like "*.env")
        $val = if ($isEnv) { Get-EnvFileToken $f.FullName } else { $null }
        if ($val) {
            $ok = (Invoke-CF "/user/tokens/verify" $val).ok -or (Invoke-CF "/accounts/$AccountId/tokens/verify" $val).ok
            Say ("    {0}  (token set, {1})" -f $f.FullName, $(if ($ok) { "Cloudflare accepts it" } else { "Cloudflare REJECTS it" })) $(if ($ok) { "Gray" } else { "Yellow" })
        } else { Say ("    {0}  (mentions the name only)" -f $f.FullName) }
    }
} else { Say "  No app file under $AppRoot sets CLOUDFLARE_API_TOKEN." }

if ($CheckOnly) { Say ""; Say "Check only: nothing was changed." "Green"; return }

# ---------- 2. New token ----------
Say ""
Say "2. Create a new Cloudflare API token (about 2 minutes)" "Cyan"
Say "  a. On this server open Chrome or Edge and go to:"
Say "       https://dash.cloudflare.com/profile/api-tokens"
Say "     Sign in with the Cloudflare account that has the QR Worker (nexttoppers.workers.dev)."
Say "  b. Click the blue 'Create Token' button."
Say "  c. In the list, find 'Edit Cloudflare Workers' and click 'Use template'."
Say "  d. Account Resources: Include > choose your account."
Say "     Zone Resources: Include > All zones."
Say "  e. Click 'Continue to summary', then 'Create Token'."
Say "  f. Cloudflare shows the token ONCE. Click 'Copy'."
Say "  g. Come back here, right-click to paste (nothing shows; that is normal), press Enter."
Say ""
$secure = Read-Host "  Paste the new token here (it stays hidden) and press Enter" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try { $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
$token = ($token -replace '^\s*Bearer\s+', '').Trim()
if (-not $token) { throw "No token was pasted. Nothing was changed." }
if ($token -match '^[0-9a-fA-F]{37}$') { throw "This looks like the Global API Key, not an API token. Create an API token as shown above. Nothing was changed." }
if ($token -match '\s') { throw "The token contains spaces or line breaks. Copy it again. Nothing was changed." }

Say ""
Say "  Testing the new token with Cloudflare (read-only):"
if (-not (Show-Checks (Test-Token $token))) {
    throw "Cloudflare did not accept this token for the checks marked FAIL. Nothing was changed. Fix the token permissions and run again."
}

# ---------- 3. Save for the whole computer ----------
Say ""
Say "3. Saving the token for the whole computer" "Cyan"
[Environment]::SetEnvironmentVariable("CLOUDFLARE_API_TOKEN", $token, "Machine")
$env:CLOUDFLARE_API_TOKEN = $token
$acct = [Environment]::GetEnvironmentVariable("CLOUDFLARE_ACCOUNT_ID", "Machine")
if (-not $acct) { [Environment]::SetEnvironmentVariable("CLOUDFLARE_ACCOUNT_ID", $AccountId, "Machine"); Say "  CLOUDFLARE_ACCOUNT_ID saved." }
elseif ($acct -ne $AccountId) { Say "  CLOUDFLARE_ACCOUNT_ID is already set to a different account; left unchanged." "Yellow" }
if ([Environment]::GetEnvironmentVariable("CLOUDFLARE_API_TOKEN", "User")) {
    [Environment]::SetEnvironmentVariable("CLOUDFLARE_API_TOKEN", $token, "User")
    Say "  Your user had an old token too; it now has the new one."
}
Say "  Saved." "Green"
foreach ($f in $appFiles) {
    if (-not ($f.Name -like ".env*" -or $f.Name -like "*.env")) { continue }
    $text = [IO.File]::ReadAllText($f.FullName)
    $m = [regex]::Match($text, $TokenLine)
    if (-not $m.Success -or -not $m.Groups[2].Value.Trim()) { continue }
    $bak = $f.FullName + ".bak-token-fix-" + (Get-Date -Format "yyyyMMdd-HHmmss")
    Copy-Item -LiteralPath $f.FullName -Destination $bak
    $text = [regex]::Replace($text, $TokenLine, { param($x) $x.Groups[1].Value + $token + $x.Groups[3].Value })
    [IO.File]::WriteAllText($f.FullName, $text, (New-Object Text.UTF8Encoding($false)))
    Say "  Replaced the old token in $($f.FullName) (copy kept: $bak)" "Green"
}

$seen = Test-SystemSeesToken $token
if ($seen -ne "same") {
    Say "  A SYSTEM task does not see the new token yet ($seen)." "Yellow"
    Say "  The token is saved. Restart the server once at a quiet time; the" "Yellow"
    Say "  auto-recovery task then starts the QR API with the new token." "Yellow"
    Say "  The QR API was NOT restarted now." "Yellow"
    return
}
Say "  A SYSTEM task sees the new token." "Green"

# ---------- 4. Restart only the QR API ----------
Say ""
Say "4. Restarting only the QR API on port $ApiPort" "Cyan"
# A long-running watchdog would start the API again with its old settings, so it
# is stopped first; the scheduled task starts a fresh one. The watchdog never
# stops servers, so stopping it is safe.
$watchdogs = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'" | Where-Object { $_.CommandLine -match 'WATCHDOG' -and $_.ProcessId -ne $PID })
foreach ($w in $watchdogs) { Stop-Process -Id $w.ProcessId -Force -ErrorAction SilentlyContinue }
if ($watchdogs.Count) { Say "  Stopped $($watchdogs.Count) old watchdog process(es); the task starts a new one." }

$listen = Get-NetTCPConnection -LocalPort $ApiPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
$oldPid = $null
if ($listen) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($listen.OwningProcess)"
    if ($proc.Name -notmatch '^python' -and $proc.CommandLine -notmatch 'uvicorn') {
        Say "  Port $ApiPort belongs to $($proc.Name), not the Python QR API. It was NOT stopped." "Yellow"
        Say "  The token is saved; restart the QR API the way you normally do." "Yellow"
        return
    }
    # If a Python parent (uvicorn reloader) started this process, stop the parent too,
    # otherwise it would start a new child with the old settings.
    $top = $proc
    while ($true) {
        $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($top.ParentProcessId)" -ErrorAction SilentlyContinue
        if ($parent -and $parent.Name -match '^python' -and $parent.CommandLine -match 'uvicorn|app\.main') { $top = $parent } else { break }
    }
    $oldPid = $listen.OwningProcess
    & taskkill.exe /PID $top.ProcessId /T /F | Out-Null
    Say "  Stopped the QR API (PID $($top.ProcessId))."
}
if ($task) { Start-ScheduledTask -TaskName $TaskName }

$back = $null
for ($i = 0; $i -lt 36; $i++) {
    Start-Sleep -Seconds 5
    $back = Get-NetTCPConnection -LocalPort $ApiPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($back -and $back.OwningProcess -ne $oldPid) { break }
    if ($task -and $i -eq 12) { Start-ScheduledTask -TaskName $TaskName }
    $back = $null
}
if (-not $back) {
    Say "  The QR API did not come back within 3 minutes." "Red"
    Say "  Run: Start-ScheduledTask -TaskName $TaskName   then check port $ApiPort again." "Red"
    exit 1
}
Say "  QR API is running again (PID $($back.OwningProcess)) with the new token." "Green"

Say ""
Say "DONE. Existing QR codes, scans and the database were not changed." "Green"
Say "Test: open the QR page and create one tracked QR. It should save without the Cloudflare error." "Green"
