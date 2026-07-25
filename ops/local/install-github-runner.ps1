param(
    [Parameter(Mandatory = $true)]
    [string]$RepositoryUrl,
    [Parameter(Mandatory = $true)]
    [string]$RegistrationToken
)

$ErrorActionPreference = 'Stop'
$runnerRoot = 'C:\PegasusRunner'
$archive = Join-Path $env:TEMP 'actions-runner-win-x64.zip'
New-Item -ItemType Directory -Force -Path $runnerRoot | Out-Null
$release = Invoke-RestMethod -Uri 'https://api.github.com/repos/actions/runner/releases/latest' -Headers @{ 'User-Agent' = 'PegasusLocalControl' }
$asset = @($release.assets | Where-Object { $_.name -match '^actions-runner-win-x64-.*\.zip$' }) | Select-Object -First 1
if ($null -eq $asset) { throw 'Could not locate the current Windows GitHub Actions runner package.' }
if (-not $asset.browser_download_url) { throw 'GitHub did not provide the runner download address.' }
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $archive
Expand-Archive -LiteralPath $archive -DestinationPath $runnerRoot -Force
Push-Location $runnerRoot
try {
    .\config.cmd --url $RepositoryUrl --token $RegistrationToken --labels pegasus --name ("pegasus-" + $env:COMPUTERNAME) --unattended
    .\run.cmd
} finally {
    Pop-Location
}