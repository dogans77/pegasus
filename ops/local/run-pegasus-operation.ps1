param(
    [ValidateSet('health', 'daily-refresh', 'reconcile-results', 'model-report')]
    [string]$Operation = 'health'
)

$ErrorActionPreference = 'Stop'
$repo = 'C:\Projects\pegasus'
$apiRoot = Join-Path $repo 'apps\api'
$python = Join-Path $apiRoot '.venv\Scripts\python.exe'
$reportDir = Join-Path $repo 'deploy\reports'
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$reportPath = Join-Path $reportDir ("mobile-operation-$Operation-$stamp.txt")

function Write-Report([string]$Text) {
    $Text | Tee-Object -FilePath $reportPath -Append
}

if (-not (Test-Path -LiteralPath $python)) { throw "Pegasus Python environment was not found: $python" }

switch ($Operation) {
    'health' {
        try {
            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8042/health' -TimeoutSec 20
            Write-Report ("API health: " + ($health | ConvertTo-Json -Compress))
        } catch {
            Write-Report ('API health check failed: ' + $_.Exception.Message)
            throw
        }
    }
    'daily-refresh' {
        $scriptPath = Join-Path $repo 'deploy\run-pegasus-daily-refresh.ps1'
        if (-not (Test-Path -LiteralPath $scriptPath)) { throw "Daily refresh script was not found: $scriptPath" }
        & powershell -NoProfile -ExecutionPolicy Bypass -File $scriptPath
        if ($LASTEXITCODE -ne 0) { throw 'Daily refresh returned a failure exit code.' }
        Write-Report 'Daily refresh completed.'
    }
    'reconcile-results' {
        $helper = Join-Path $apiRoot 'scripts\reconcile_tjk_history.py'
        if (-not (Test-Path -LiteralPath $helper)) { throw 'Historical reconciliation helper is not installed yet.' }
        Push-Location $apiRoot
        try {
            & $python -m scripts.reconcile_tjk_history --max-dates 0
            if ($LASTEXITCODE -ne 0) { throw 'Historical result reconciliation returned a failure exit code.' }
        } finally {
            Pop-Location
        }
        Write-Report 'Historical result reconciliation completed or checkpointed.'
    }
    'model-report' {
        $safety = Invoke-RestMethod -Uri 'http://127.0.0.1:8042/api/v1/analytics/model-safety?refresh=true' -TimeoutSec 60
        Write-Report ($safety | ConvertTo-Json -Depth 8)
    }
}

Write-Host "Pegasus operation complete. Report: $reportPath"