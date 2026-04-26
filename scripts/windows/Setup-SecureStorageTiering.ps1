param(
    [string]$RootPath = "C:\AgriAsset_Data",
    [bool]$UpdateEnvFile = $true
)

Write-Host "AgriAsset Secure Storage Initializer" -ForegroundColor Cyan
Write-Host "===================================="
Write-Host "[*] Active Root Path: $RootPath" -ForegroundColor Magenta

# 1. Path Resolution
$PSScriptRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
$RepoPath = (Resolve-Path "$PSScriptRoot\..\..").Path
$EnvFile = "$RepoPath\backend\.env"
$EnvScript = "$RepoPath\scripts\windows\Resolve-BackendDbEnv.ps1"
$BackendDir = "$RepoPath\backend"

$ArchivePath = "$RootPath\Archive"
$QuarantinePath = "$RootPath\Quarantine"
$SanitizedPath = "$RootPath\Sanitized"

# 2. Storage Tier Directories
$Paths = @($RootPath, $ArchivePath, $QuarantinePath, $SanitizedPath)
foreach ($Path in $Paths) {
    if (-Not (Test-Path $Path)) {
        try {
            New-Item -ItemType Directory -Force -Path $Path | Out-Null
            Write-Host "[+] Created directory: $Path" -ForegroundColor Green
        } catch {
            Write-Host "[-] Failed to create directory $Path (Check if drive/path is accessible)" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "[x] Directory exists: $Path" -ForegroundColor Yellow
    }
}

# 3. Strict OS-Level Permissions (icacls)
Write-Host "`n[*] Applying strict OS-level permissions via icacls..." -ForegroundColor Cyan
icacls $RootPath "/inheritance:d" | Out-Null
icacls $RootPath "/grant" "SYSTEM:(OI)(CI)F" | Out-Null
icacls $RootPath "/grant" "Administrators:(OI)(CI)F" | Out-Null
Write-Host "[+] Secured permissions for $RootPath." -ForegroundColor Green


# 4. Schedule Nightly Workers (schtasks)
Write-Host "`n[*] Registering AgriAsset Nightly Workers (schtasks)..." -ForegroundColor Cyan
if (-Not (Test-Path $EnvScript)) {
    Write-Host "[!] Warning: Resolve-BackendDbEnv.ps1 not found at $EnvScript." -ForegroundColor Yellow
}

$ActionCommand = "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -Command `". '$EnvScript'; cd '$BackendDir'; python manage.py"

$Tasks = @(
    @{ Name = "AgriAsset-ScanAttachments"; Script = "scan_pending_attachments"; Time = "01:00" },
    @{ Name = "AgriAsset-ArchiveAttachments"; Script = "archive_due_attachments"; Time = "02:00" },
    @{ Name = "AgriAsset-PurgeTransient"; Script = "purge_expired_transient_attachments"; Time = "03:00" }
)

foreach ($Task in $Tasks) {
    $TaskName = $Task.Name
    $TaskCmd = "$ActionCommand $($Task.Script)`""
    
    schtasks /delete /tn $TaskName /f 2>$null | Out-Null
    schtasks /create /tn $TaskName /tr "$TaskCmd" /sc daily /st $Task.Time /ru "SYSTEM" /f | Out-Null
    if ($?) {
        Write-Host "[+] Scheduled $TaskName at $($Task.Time)" -ForegroundColor Green
    } else {
        Write-Host "[-] Failed to schedule $TaskName. (Run script as Administrator)" -ForegroundColor Red
    }
}

# 5. Environment Configuration Management (.env)
if ($UpdateEnvFile) {
    Write-Host "`n[*] Updating Backend .env configuration..." -ForegroundColor Cyan
    $EnvParams = @{
        "AGRIASSET_ATTACHMENT_ARCHIVE_ROOT" = $ArchivePath
        "AGRIASSET_ATTACHMENT_QUARANTINE_ROOT" = $QuarantinePath
        "AGRIASSET_ATTACHMENT_SANITIZED_ROOT" = $SanitizedPath
        "AGRIASSET_ATTACHMENT_SCAN_MODE" = "clamav"
        "AGRIASSET_CLAMSCAN_BINARY" = "C:\Program Files\ClamAV\clamscan.exe"
    }

    if (-Not (Test-Path $EnvFile)) {
        New-Item -ItemType File -Force -Path $EnvFile | Out-Null
    }

    $CurrentEnv = Get-Content $EnvFile -ErrorAction SilentlyContinue
    foreach ($Key in $EnvParams.Keys) {
        $Val = $EnvParams[$Key]
        $Pattern = "^$Key=.*$"
        $Match = $CurrentEnv | Select-String -Pattern $Pattern
        if ($Match) {
            $CurrentEnv = $CurrentEnv -replace $Pattern, "$Key=$Val"
            Write-Host "  ~ Updated $Key" -ForegroundColor Yellow
        } else {
            $CurrentEnv += "$Key=$Val"
            Write-Host "  + Added $Key" -ForegroundColor Green
        }
    }
    
    $CurrentEnv | Set-Content $EnvFile
    Write-Host "[+] Successfully synced configuration to $EnvFile" -ForegroundColor Green
}

Write-Host "`n==============================================="
Write-Host "SETUP COMPLETE. The system is fully operational using root: $RootPath" -ForegroundColor Green
Write-Host "To change this later, edit the .env file or run this script with -RootPath `"X:\Your_Path`""
Write-Host "==============================================="
