$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $projectDirectory 'backend')
& (Join-Path $projectDirectory '.venv/Scripts/python.exe') -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& (Join-Path $projectDirectory '.venv/Scripts/python.exe') -m uvicorn app.main:app --host 127.0.0.1 --port 8000
