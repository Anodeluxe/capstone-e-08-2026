<#
.SYNOPSIS
  Database Environment Switcher for Capstone E-08 (Toren Monitoring)
.DESCRIPTION
  Usage:
    .\scripts\switch_db.ps1 test   -> Switch backend to isolated toren_ml_test
    .\scripts\switch_db.ps1 prod   -> Switch backend to production toren_db
#>

param (
    [Parameter(Mandatory=$true)]
    [ValidateSet("test", "prod")]
    [string]$Target
)

$rootDir = Split-Path -Parent $PSScriptRoot
Set-Location $rootDir

$envFile = Join-Path $rootDir "backend\.env"

if ($Target -eq "test") {
    Write-Host "==================================================" -ForegroundColor Cyan
    Write-Host "  SWITCHING BACKEND TO: toren_ml_test (TEST DB)   " -ForegroundColor Cyan
    Write-Host "==================================================" -ForegroundColor Cyan

    if (Test-Path $envFile) {
        $content = Get-Content $envFile -Raw
        if ($content -match "POSTGRES_DB=") {
            $content = $content -replace "POSTGRES_DB=.*", "POSTGRES_DB=toren_ml_test"
        } else {
            $content += "`nPOSTGRES_DB=toren_ml_test`n"
        }
        Set-Content -Path $envFile -Value $content -NoNewline
    }

    Write-Host "Restarting backend container..."
    docker compose --profile app up -d backend
    Start-Sleep -Seconds 3

    Write-Host "`n✅ SUCCESS: Backend is now connected to 'toren_ml_test'." -ForegroundColor Green
    Write-Host "👉 Open https://amin-u.vercel.app to preview the 9-day trend and XGBoost prediction live!"
    Write-Host "👉 When finished, switch back using: .\scripts\switch_db.ps1 prod"
}
elseif ($Target -eq "prod") {
    Write-Host "==================================================" -ForegroundColor Cyan
    Write-Host "  RESTORING BACKEND TO: toren_db (PRODUCTION DB)  " -ForegroundColor Cyan
    Write-Host "==================================================" -ForegroundColor Cyan

    if (Test-Path $envFile) {
        $content = Get-Content $envFile -Raw
        if ($content -match "POSTGRES_DB=") {
            $content = $content -replace "POSTGRES_DB=.*", "POSTGRES_DB=toren_db"
        } else {
            $content += "`nPOSTGRES_DB=toren_db`n"
        }
        Set-Content -Path $envFile -Value $content -NoNewline
    }

    Write-Host "Restarting backend container..."
    docker compose --profile app up -d backend
    Start-Sleep -Seconds 3

    Write-Host "`n✅ SUCCESS: Backend is now safely restored to PRODUCTION 'toren_db'." -ForegroundColor Green
}
