$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
& "$Root\scripts\windows\Resolve-BackendDbEnv.ps1"
python backend/manage.py verify_static_v21
