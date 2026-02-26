#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Resolve the directory containing this script and run the local Python file (prefer venv)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (-not $scriptDir) { $scriptDir = Get-Location }

$scriptPath = Join-Path $scriptDir 'guitar_client.py'
$venvDir = $env:VENV_DIR
if (-not $venvDir) { $venvDir = 'venv' }
$venvPy = Join-Path $scriptDir "$venvDir\Scripts\python.exe"

if (-not (Test-Path $scriptPath)) {
    Write-Error "Error: Python script not found at $scriptPath"
    exit 1
}

if (Test-Path $venvPy) {
    Write-Host "Using virtualenv python: $venvPy"
    & $venvPy $scriptPath
} else {
    Write-Host "Virtualenv not found at $venvPy; falling back to system python3 or python"
    if (Get-Command python3 -ErrorAction SilentlyContinue) {
        & python3 $scriptPath
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python $scriptPath
    } else {
        Write-Error "No system python found"
        exit 1
    }
}

$rc = $LASTEXITCODE
if ($rc -ne 0) {
    Write-Error "Error: drums_server.py failed (exit $rc)"
    exit $rc
}
