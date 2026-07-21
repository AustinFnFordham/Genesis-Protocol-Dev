#!/usr/bin/env pwsh
# Fix SAM CLI permissions issue

$metadataPath = "$env:APPDATA\AWS SAM\metadata.json"

Write-Host "Fixing SAM CLI permissions..." -ForegroundColor Yellow

if (Test-Path $metadataPath) {
    Write-Host "Removing locked metadata file..." -ForegroundColor Cyan
    Remove-Item $metadataPath -Force
    Write-Host "✓ File removed" -ForegroundColor Green
} else {
    Write-Host "Metadata file not found, creating directory..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path "$env:APPDATA\AWS SAM" -Force | Out-Null
    Write-Host "✓ Directory created" -ForegroundColor Green
}

Write-Host "`nTry running deploy-fullpath.ps1 again" -ForegroundColor Yellow
