$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot\frontend

if (-not (Test-Path 'node_modules')) {
    Write-Host 'Installing dependencies...' -ForegroundColor Cyan
    & 'C:\Program Files\nodejs\npm.cmd' install
}

# Avoid `npm run ...` here because the workspace path contains `&`,
# which breaks npm/cmd script execution on Windows.
& 'C:\Program Files\nodejs\node.exe' '.\node_modules\vite\bin\vite.js'
