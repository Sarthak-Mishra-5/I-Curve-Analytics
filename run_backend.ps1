# Run backend (PowerShell). Pass -Mock for synthetic ticks.
param([switch]$Mock)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not (Test-Path 'backend\.venv')) {
    Write-Host 'Creating venv...' -ForegroundColor Cyan
    py -3.12 -m venv backend\.venv
}

& backend\.venv\Scripts\Activate.ps1
pip install -q -r backend\requirements.txt

if ($Mock) { $env:RV_MOCK = '1' } else { Remove-Item Env:RV_MOCK -ErrorAction SilentlyContinue }
python -m backend.main
