$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkerDir = Join-Path $Here "worker"
$Fixer = Join-Path $Here "SET_NEXTTOPPERS_QR_PUBLIC_URL.ps1"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Log = Join-Path ([Environment]::GetFolderPath("Desktop")) "NEXTTOPPERS_QR_WORKER_DEPLOY_$Stamp.txt"

function Log([string]$Level,[string]$Message) {
    $line = "[$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))] [$Level] $Message"
    Write-Host $line
    Add-Content -LiteralPath $Log -Value $line -Encoding UTF8
}

function Run-Wrangler([string[]]$Args) {
    $allArgs = @("--yes","wrangler@latest") + $Args
    $lines = @()
    & npx.cmd @allArgs 2>&1 | ForEach-Object {
        $line = "$_"
        $lines += $line
        Write-Host $line
        Add-Content -LiteralPath $Log -Value $line -Encoding UTF8
    }
    return [pscustomobject]@{ExitCode=$LASTEXITCODE;Lines=$lines;Text=($lines -join "`n")}
}

try {
    Log "INFO" "NextToppers QR Worker deployment + live public URL correction"
    Log "INFO" "Port 3457 is protected. Production QR rows are not migrated/deleted."

    if (-not (Get-Command node.exe -ErrorAction SilentlyContinue)) { throw "Node.js is not available in PATH." }
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw "npm is not available in PATH." }
    if (-not (Get-Command npx.cmd -ErrorAction SilentlyContinue)) { throw "npx is not available in PATH." }

    Push-Location $WorkerDir
    try {
        $who = Run-Wrangler @("whoami")
        if ($who.ExitCode -ne 0 -or $who.Text -match "(?i)(not authenticated|not logged|login required|you are not authenticated)") {
            Log "INFO" "Cloudflare sign-in is required. Sign in to the account-owner browser page and click Allow."
            $login = Run-Wrangler @("login")
            if ($login.ExitCode -ne 0) { throw "Cloudflare Wrangler login failed or was cancelled." }
            $who = Run-Wrangler @("whoami")
            if ($who.ExitCode -ne 0) { throw "Cloudflare authentication still not available after login." }
        }
        Log "PASS" "Cloudflare authentication is available."

        $deploy = Run-Wrangler @("deploy","--config","wrangler.jsonc")
        if ($deploy.ExitCode -ne 0) { throw "Cloudflare Worker deployment failed." }

        $matches = [regex]::Matches($deploy.Text,'https://[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\.workers\.dev')
        if ($matches.Count -lt 1) { throw "Worker deployed but Wrangler output did not contain the assigned workers.dev URL." }
        $PublicQrBase = $matches[$matches.Count - 1].Value.TrimEnd("/")
        Log "PASS" "Cloudflare assigned live QR hostname: $PublicQrBase"
    }
    finally { Pop-Location }

    $health = Invoke-RestMethod -Uri ($PublicQrBase + "/__nexttoppers_health") -Method GET -TimeoutSec 20
    if (-not $health.ok) { throw "Worker health endpoint did not return ok=true." }
    Log "PASS" "Worker health endpoint is live."

    try {
        $originCheck = Invoke-RestMethod -Uri ($PublicQrBase + "/__nexttoppers_origin_check") -Method GET -TimeoutSec 20
        if ($originCheck.ok) { Log "PASS" "Worker can reach the current QR origin." }
        else { Log "WARN" "Worker deployed, but current QR origin did not report healthy through gateway." }
    } catch { Log "WARN" "Worker live but origin check failed; current origin/tunnel must remain online for scans." }

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Fixer -PublicQrBase $PublicQrBase
    if ($LASTEXITCODE -ne 0) { throw "Worker deployed successfully, but application public-QR-base update failed." }

    Log "SUCCESS" "NEXTTOPPERS QR WORKER IS DEPLOYED AND NEW QR PUBLIC URL IS UPDATED"
    Log "PASS" "Actual Worker URL: $PublicQrBase"
    exit 0
}
catch {
    try { Log "FAIL" $_.Exception.Message } catch {}
    Write-Host "NOT ACCEPTED: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "No guessed Worker hostname is being applied." -ForegroundColor Yellow
    exit 1
}
