$projectDirectory = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $projectDirectory 'frontend')
& npm.cmd run dev
