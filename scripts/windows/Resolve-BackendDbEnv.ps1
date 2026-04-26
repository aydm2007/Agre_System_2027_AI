$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$backendEnv = Join-Path $Root "backend\.env"

if (Test-Path $backendEnv) {
    Get-Content $backendEnv | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            return
        }
        $key, $value = $line -split "=", 2
        $key = $key.Trim()
        $value = $value.Trim().Trim('"')
        switch -Regex ($key) {
            '^DATABASE_URL$' { $env:DATABASE_URL = $value }
            '^DB_HOST$' { $env:DB_HOST = $value }
            '^DB_PORT$' { $env:DB_PORT = $value }
            '^DB_NAME$' { $env:DB_NAME = $value }
            '^DB_USER$' { $env:DB_USER = $value }
            '^DB_PASSWORD$' { $env:DB_PASSWORD = $value }
            '^PGPASSWORD$' { $env:PGPASSWORD = $value }
        }
    }
    if ($env:DATABASE_URL) {
        Write-Host "[OK] Backend DB environment loaded from backend\.env via DATABASE_URL"
        return
    }
    if ($env:DB_PASSWORD) {
        if (-not $env:PGPASSWORD) {
            $env:PGPASSWORD = $env:DB_PASSWORD
        }
        Write-Host "[OK] Backend DB password loaded from backend\.env"
        return
    }
    Write-Host "[OK] Backend DB environment partially loaded from backend\.env"
}

if ($env:DATABASE_URL) {
    Write-Host "[OK] Backend DB environment available via DATABASE_URL"
    return
}

if (-not $env:DB_HOST) { $env:DB_HOST = "localhost" }
if (-not $env:DB_PORT) { $env:DB_PORT = "5432" }
if (-not $env:DB_NAME) { $env:DB_NAME = "agriasset" }
if (-not $env:DB_USER) { $env:DB_USER = "postgres" }

if ($env:DB_PASSWORD) {
    $env:PGPASSWORD = $env:DB_PASSWORD
    Write-Host "[OK] Backend DB password loaded from DB_PASSWORD"
    return
}

$pgpass = Join-Path $env:APPDATA "postgresql\pgpass.conf"
if (Test-Path $pgpass) {
    $line = Get-Content $pgpass | Where-Object {
        $_ -match '^(localhost|127\.0\.0\.1|\*):(5432|\*):(agriasset|postgres|\*):(postgres|agriasset|\*):'
    } | Select-Object -First 1
    if ($line) {
        $env:DB_PASSWORD = ($line -split ':', 5)[4]
        $env:PGPASSWORD = $env:DB_PASSWORD
        Write-Host "[OK] Backend DB password loaded from pgpass.conf"
        return
    }
}

Write-Warning "No backend DB password resolved from backend\.env, DATABASE_URL, DB_PASSWORD, or pgpass.conf."
