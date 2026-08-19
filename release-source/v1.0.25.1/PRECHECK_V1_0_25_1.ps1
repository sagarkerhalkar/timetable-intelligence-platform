$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Installer = Join-Path $PSScriptRoot "INSTALL_V1_0_25_1.ps1"
if (-not (Test-Path -LiteralPath $Installer -PathType Leaf)) {
  Write-Host "FAIL: Installer file not found: $Installer" -ForegroundColor Red
  exit 90
}

$text = [System.IO.File]::ReadAllText($Installer)
$nonAscii = @($text.ToCharArray() | Where-Object { [int]$_ -gt 127 })
if ($nonAscii.Count -gt 0) {
  Write-Host "FAIL: Installer contains non-ASCII characters. This package is not safe for Windows PowerShell 5.1." -ForegroundColor Red
  exit 91
}

$tokens = $null
$errors = $null
[System.Management.Automation.Language.Parser]::ParseInput($text, [ref]$tokens, [ref]$errors) | Out-Null
if (@($errors).Count -gt 0) {
  Write-Host "FAIL: PowerShell parser found errors before installation:" -ForegroundColor Red
  foreach ($err in @($errors)) {
    Write-Host ("  Line {0}, Column {1}: {2}" -f $err.Extent.StartLineNumber, $err.Extent.StartColumnNumber, $err.Message) -ForegroundColor Red
  }
  exit 92
}

Write-Host "PASS: Windows PowerShell parser precheck completed with zero errors." -ForegroundColor Green
exit 0
