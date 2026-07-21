#!/usr/bin/env pwsh
# Test Supervisor Agent

$awsPath = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"

Write-Host "=== Testing Supervisor Agent ===" -ForegroundColor Cyan

$payload = @{
    scenario_id = "scenario_01_bruteforce"
} | ConvertTo-Json -Compress

Write-Host "`nStarting game session..." -ForegroundColor Yellow
Write-Host "Payload: $payload" -ForegroundColor Gray

& $awsPath lambda invoke `
    --function-name ender-protocol-supervisor-agent `
    --cli-binary-format raw-in-base64-out `
    --payload $payload `
    game-result.json | Out-Null

Write-Host "`nGame Result:" -ForegroundColor Green
Get-Content game-result.json | ConvertFrom-Json | ConvertTo-Json -Depth 10

Write-Host "`n=== Check Logs ===" -ForegroundColor Cyan
Write-Host "& `"$awsPath`" logs tail /aws/lambda/ender-protocol-supervisor-agent --follow" -ForegroundColor White
