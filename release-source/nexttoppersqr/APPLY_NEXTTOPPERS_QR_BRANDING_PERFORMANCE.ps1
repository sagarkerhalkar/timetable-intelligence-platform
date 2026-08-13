$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Root = 'D:\timetable-intelligence-platform'
$Web = Join-Path $Root 'apps\web'
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$Backup = Join-Path $Root "backups\NEXTTOPPERS_QR_$Stamp"
$Log = Join-Path ([Environment]::GetFolderPath('Desktop')) "NEXTTOPPERS_QR_$Stamp.txt"

function Write-Log([string]$Message='') {
    $Message | Tee-Object -FilePath $Log -Append
}

function Replace-Required([string]$Path,[string]$Old,[string]$New) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing file: $Path" }
    $text = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    if ($text.Contains($Old)) {
        $text = $text.Replace($Old,$New)
        Set-Content -LiteralPath $Path -Value $text -Encoding UTF8
        Write-Log "PASS patched: $Path"
        return
    }
    if ($text.Contains($New)) {
        Write-Log "PASS already patched: $Path"
        return
    }
    throw "Expected source contract not found in $Path"
}

function Stop-Web3500 {
    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort 3500 -ErrorAction SilentlyContinue)
    foreach ($listener in $listeners) {
        $pidValue = [int]$listener.OwningProcess
        if ($pidValue -le 0) { continue }
        $p = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
        if ($p -and $p.ProcessName -notmatch '^node$') { throw "Unexpected owner on port 3500: $($p.ProcessName) PID $pidValue" }
        Stop-Process -Id $pidValue -Force -ErrorAction Stop
        Start-Sleep -Seconds 2
    }
}

function Wait-Web {
    $deadline = (Get-Date).AddSeconds(60)
    do {
        try {
            $r = Invoke-WebRequest -Uri 'http://127.0.0.1:3500/' -UseBasicParsing -TimeoutSec 5
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 400) { return $true }
        } catch {}
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    return $false
}

try {
    Write-Log 'NEXTTOPPERS QR - BRANDING + PRODUCTION WEB RUNTIME'
    Write-Log 'Database is not modified. API 3550 and protected port 3457 are not stopped.'

    if (-not (Test-Path -LiteralPath $Web -PathType Container)) { throw "Missing web root: $Web" }
    New-Item -ItemType Directory -Path $Backup -Force | Out-Null

    $nav = Join-Path $Web 'components\qr-product-nav.tsx'
    $builder = Join-Path $Web 'app\qr\page.tsx'
    $codes = Join-Path $Web 'app\qr\codes\page.tsx'
    foreach ($file in @($nav,$builder,$codes)) {
        if (Test-Path -LiteralPath $file -PathType Leaf) {
            $rel = $file.Substring($Web.Length).TrimStart('\').Replace('\','_')
            Copy-Item -LiteralPath $file -Destination (Join-Path $Backup $rel) -Force
        }
    }
    if (Test-Path -LiteralPath (Join-Path $Web '.next')) {
        Copy-Item -LiteralPath (Join-Path $Web '.next') -Destination (Join-Path $Backup '.next') -Recurse -Force
    }
    Write-Log "PASS web safety backup: $Backup"

    Replace-Required $nav '<div><strong>QR Studio</strong><small>Dynamic QR & verified scan intelligence</small></div>' '<div><strong>NextToppers QR</strong><small>Fast, secure QR & verified scan intelligence</small></div>'
    Replace-Required $builder 'title:"Opening…",message:"Preparing your QR action"' 'title:"NextToppers",message:"Opening your content…"'

    $codesText = Get-Content -LiteralPath $codes -Raw -Encoding UTF8
    $oldVisible = '<small title={absoluteUrl(code.public_url)}>{absoluteUrl(code.public_url)}</small>'
    $newVisible = '<small title="Public tracked QR">NextToppers QR</small>'
    if ($codesText.Contains($oldVisible)) { $codesText = $codesText.Replace($oldVisible,$newVisible) }
    if ($codesText.Contains('>Open public QR link ↗</a>')) { $codesText = $codesText.Replace('>Open public QR link ↗</a>','>Open NextToppers QR ↗</a>') }
    Set-Content -LiteralPath $codes -Value $codesText -Encoding UTF8
    Write-Log "PASS public hostname hidden from normal QR library display; real Copy/Open URL preserved."

    $layout = Join-Path $Web 'app\qr\layout.tsx'
    @'
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "NextToppers QR",
  description: "NextToppers dynamic QR and verified scan intelligence",
  applicationName: "NextToppers",
};

export default function QrLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
'@ | Set-Content -LiteralPath $layout -Encoding UTF8
    Write-Log 'PASS QR metadata branding created.'

    $manifest = Join-Path $Web 'app\manifest.ts'
    @'
import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "NextToppers",
    short_name: "NextToppers",
    description: "NextToppers QR and timetable intelligence",
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#111827",
  };
}
'@ | Set-Content -LiteralPath $manifest -Encoding UTF8
    Write-Log 'PASS NextToppers web-app manifest created.'

    Push-Location $Web
    try {
        Write-Log 'Running production build...'
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw "npm run build failed with exit code $LASTEXITCODE" }
    } finally { Pop-Location }

    Stop-Web3500
    $next = Join-Path $Web 'node_modules\next\dist\bin\next'
    $node = (Get-Command node.exe -ErrorAction Stop).Source
    Start-Process -FilePath $node -ArgumentList @($next,'start','-H','0.0.0.0','-p','3500','--keepAliveTimeout','70000') -WorkingDirectory $Web -WindowStyle Hidden | Out-Null
    if (-not (Wait-Web)) { throw 'Production Next.js web did not become healthy on 3500.' }

    Write-Log 'SUCCESS: NextToppers QR branding is active and web 3500 is running in Next.js production mode.'
    Write-Log 'Public hostname remains technically unchanged: https://nexttoppers.sagarkerhalkar.com'
    Write-Log 'The hostname can still appear in the browser address bar; normal QR UI branding now uses NextToppers.'
    exit 0
}
catch {
    try { Write-Log ('FAIL: ' + $_.Exception.Message) } catch {}
    Write-Host ('FAILED: ' + $_.Exception.Message) -ForegroundColor Red
    Write-Host "Backup: $Backup" -ForegroundColor Yellow
    Write-Host "Log: $Log" -ForegroundColor White
    exit 1
}
