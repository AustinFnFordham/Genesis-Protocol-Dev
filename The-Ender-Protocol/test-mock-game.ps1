#!/usr/bin/env pwsh
# Test mock game loop (no Bedrock agents)

$awsPath = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"

Write-Host "=== Testing Mock Game Loop ===" -ForegroundColor Cyan

$payload = @{
    scenario_id = "scenario_01_bruteforce"
    session_id = "mock-game-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
} | ConvertTo-Json -Compress

Write-Host "`nInvoking Mock Supervisor..." -ForegroundColor Yellow
Write-Host "Payload: $payload" -ForegroundColor Gray

& $awsPath lambda invoke `
    --function-name ender-protocol-supervisor-mock `
    --payload $payload `
    --cli-binary-format raw-in-base64-out `
    mock-response.json

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n=== Game Response ===" -ForegroundColor Green
    Get-Content mock-response.json | ConvertFrom-Json | ConvertTo-Json -Depth 10
    
    Write-Host "`n=== CloudWatch Logs ===" -ForegroundColor Cyan
    Start-Sleep -Seconds 2
    & $awsPath logs tail /aws/lambda/ender-protocol-supervisor-mock --since 2m --format short | Select-Object -Last 100
} else {
    Write-Host "`nInvocation failed!" -ForegroundColor Red
}
