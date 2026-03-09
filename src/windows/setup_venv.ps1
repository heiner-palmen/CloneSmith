#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Creates a virtual environment in ./venv and installs requirements.txt
# Usage: .\setup_venv.ps1
# Optional env vars: PYTHON (defaults to 'python'), VENV_DIR (defaults to 'venv')

$python = $env:PYTHON
if (-not $python) { $python = 'python' }

$venvDir = $env:VENV_DIR
if (-not $venvDir) { $venvDir = 'venv' }

Write-Host "Creating virtual environment in $venvDir using $python..."
& $python -m venv $venvDir

Write-Host "Upgrading pip and installing requirements..."
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    Write-Error "venv python not found at $venvPython"
    exit 1
}

& $venvPython -m pip install --upgrade pip setuptools wheel

# Install requirements.txt from the current working directory (same behavior as the Linux script)
$reqPath = Join-Path (Get-Location) 'requirements.txt'
if (Test-Path $reqPath) {
    & $venvPython -m pip install -r $reqPath
} else {
    Write-Error "requirements.txt not found in $(Get-Location)"
    exit 1
}

Write-Host ""
Write-Host "Done. To activate the venv in PowerShell run: .\$venvDir\Scripts\Activate.ps1"
Write-Host "Or in cmd.exe run: $venvDir\Scripts\activate.bat"
