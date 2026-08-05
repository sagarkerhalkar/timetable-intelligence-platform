param(
    [string]$TargetRoot = 'D:\timetable-intelligence-platform'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Write-Step([string]$Message) {
    Write-Host "`n$Message" -ForegroundColor Cyan
}

function Convert-SecureToText([Security.SecureString]$SecureValue) {
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}

function Read-KeyValues([string]$Path) {
    $values = @{}
    if (-not (Test-Path $Path)) { return $values }
    foreach ($raw in Get-Content $Path) {
        $line = $raw.Trim()
        if (-not $line -or $line.StartsWith('#') -or -not $line.Contains('=')) { continue }
        $parts = $line.Split('=', 2)
        $values[$parts[0].Trim()] = $parts[1].Trim()
    }
    return $values
}

function Prompt-Value([string]$Label, [string]$Current = '') {
    $suffix = if ($Current) { ' [press Enter to keep current value]' } else { '' }
    $value = Read-Host "$Label$suffix"
    if (-not $value -and $Current) { return $Current }
    return $value.Trim()
}

if (-not (Test-Path $TargetRoot)) { throw "Application folder not found: $TargetRoot" }
$configPath = Join-Path $TargetRoot '.env.notifications'
$values = Read-KeyValues $configPath

$defaults = @{
    AUTO_SYNC_ENABLED = 'true'
    SYNC_INTERVAL_MINUTES = '30'
    PAGE_REFRESH_MINUTES = '5'
    NOTIFICATION_INTERVAL_SECONDS = '60'
    SMTP_HOST = ''
    SMTP_PORT = '587'
    SMTP_USERNAME = ''
    SMTP_PASSWORD = ''
    SMTP_FROM = ''
    SMTP_USE_TLS = 'true'
    GOOGLE_CHAT_WEBHOOK_URL = ''
    TELEGRAM_BOT_TOKEN = ''
    WHATSAPP_WEBHOOK_URL = ''
    PUSH_WEBHOOK_URL = ''
}
foreach ($key in $defaults.Keys) {
    if (-not $values.ContainsKey($key)) { $values[$key] = $defaults[$key] }
}

Write-Host 'Timetable Intelligence - Notification Channel Setup' -ForegroundColor Green
Write-Host 'This runs only on the local timetable server and does not change port 3457.' -ForegroundColor Yellow

$done = $false
while (-not $done) {
    Write-Host "`nChoose a channel to configure:" -ForegroundColor White
    Write-Host '  1. Email (Gmail / Microsoft 365 / custom SMTP)'
    Write-Host '  2. Google Chat webhook'
    Write-Host '  3. Telegram bot'
    Write-Host '  4. WhatsApp provider webhook'
    Write-Host '  5. Push webhook'
    Write-Host '  6. Save and restart app'
    Write-Host '  7. Exit without saving'
    $choice = Read-Host 'Enter 1-7'

    switch ($choice) {
        '1' {
            Write-Step 'Email setup'
            Write-Host 'For Gmail, use an App Password. Do not use your normal Gmail password.' -ForegroundColor Yellow
            Write-Host 'Choose provider: 1 Gmail, 2 Microsoft 365, 3 Custom SMTP'
            $provider = Read-Host 'Provider'
            if ($provider -eq '1') {
                $values['SMTP_HOST'] = 'smtp.gmail.com'
                $values['SMTP_PORT'] = '587'
                $values['SMTP_USE_TLS'] = 'true'
            }
            elseif ($provider -eq '2') {
                $values['SMTP_HOST'] = 'smtp.office365.com'
                $values['SMTP_PORT'] = '587'
                $values['SMTP_USE_TLS'] = 'true'
            }
            else {
                $values['SMTP_HOST'] = Prompt-Value 'SMTP host' $values['SMTP_HOST']
                $values['SMTP_PORT'] = Prompt-Value 'SMTP port' $values['SMTP_PORT']
                $values['SMTP_USE_TLS'] = Prompt-Value 'Use TLS? true/false' $values['SMTP_USE_TLS']
            }
            $values['SMTP_USERNAME'] = Prompt-Value 'SMTP username/email' $values['SMTP_USERNAME']
            $defaultFrom = if ($values['SMTP_FROM']) { $values['SMTP_FROM'] } else { $values['SMTP_USERNAME'] }
            $values['SMTP_FROM'] = Prompt-Value 'From email address' $defaultFrom
            $secure = Read-Host 'SMTP app password' -AsSecureString
            $password = Convert-SecureToText $secure
            if ($password) { $values['SMTP_PASSWORD'] = $password }
            Write-Host 'Email settings recorded. Save and restart when finished.' -ForegroundColor Green
        }
        '2' {
            Write-Step 'Google Chat setup'
            Write-Host 'In Google Chat: open the target Space > Apps & integrations > Webhooks > Add webhook.' -ForegroundColor Yellow
            $values['GOOGLE_CHAT_WEBHOOK_URL'] = Prompt-Value 'Google Chat webhook URL' $values['GOOGLE_CHAT_WEBHOOK_URL']
        }
        '3' {
            Write-Step 'Telegram setup'
            Write-Host 'Create a bot with @BotFather and paste the bot token. Put the chat ID in the rule Recipient field.' -ForegroundColor Yellow
            $values['TELEGRAM_BOT_TOKEN'] = Prompt-Value 'Telegram bot token' $values['TELEGRAM_BOT_TOKEN']
        }
        '4' {
            Write-Step 'WhatsApp webhook setup'
            Write-Host 'This requires a WhatsApp Business/provider API webhook. Personal WhatsApp alone cannot send automatically.' -ForegroundColor Yellow
            $values['WHATSAPP_WEBHOOK_URL'] = Prompt-Value 'WhatsApp provider webhook URL' $values['WHATSAPP_WEBHOOK_URL']
        }
        '5' {
            Write-Step 'Push webhook setup'
            $values['PUSH_WEBHOOK_URL'] = Prompt-Value 'Push service webhook URL' $values['PUSH_WEBHOOK_URL']
        }
        '6' { $done = $true }
        '7' {
            Write-Host 'No changes were saved.' -ForegroundColor Yellow
            exit 0
        }
        default { Write-Host 'Please enter a number from 1 to 7.' -ForegroundColor Yellow }
    }
}

$lines = @(
    '# Timetable Intelligence notification channels',
    '# Updated by SETUP_NOTIFICATION_CHANNELS_WINDOWS.ps1',
    "AUTO_SYNC_ENABLED=$($values['AUTO_SYNC_ENABLED'])",
    "SYNC_INTERVAL_MINUTES=$($values['SYNC_INTERVAL_MINUTES'])",
    "PAGE_REFRESH_MINUTES=$($values['PAGE_REFRESH_MINUTES'])",
    "NOTIFICATION_INTERVAL_SECONDS=$($values['NOTIFICATION_INTERVAL_SECONDS'])",
    '',
    "SMTP_HOST=$($values['SMTP_HOST'])",
    "SMTP_PORT=$($values['SMTP_PORT'])",
    "SMTP_USERNAME=$($values['SMTP_USERNAME'])",
    "SMTP_PASSWORD=$($values['SMTP_PASSWORD'])",
    "SMTP_FROM=$($values['SMTP_FROM'])",
    "SMTP_USE_TLS=$($values['SMTP_USE_TLS'])",
    '',
    "GOOGLE_CHAT_WEBHOOK_URL=$($values['GOOGLE_CHAT_WEBHOOK_URL'])",
    "TELEGRAM_BOT_TOKEN=$($values['TELEGRAM_BOT_TOKEN'])",
    "WHATSAPP_WEBHOOK_URL=$($values['WHATSAPP_WEBHOOK_URL'])",
    "PUSH_WEBHOOK_URL=$($values['PUSH_WEBHOOK_URL'])"
)
$lines | Set-Content -Path $configPath -Encoding UTF8

Write-Step 'Restarting only Timetable Intelligence.'
$stopScript = Join-Path $TargetRoot 'STOP_LOCAL_WINDOWS.ps1'
$startScript = Join-Path $TargetRoot 'START_LOCAL_WINDOWS.ps1'
if (Test-Path $stopScript) { & $stopScript }
Start-Sleep -Seconds 2
if (Test-Path $startScript) { & $startScript -NoBrowser }

Write-Host "`nChannel configuration saved: $configPath" -ForegroundColor Green
Write-Host 'Open Notifications and press Test now on a rule using the configured channel.' -ForegroundColor Green
