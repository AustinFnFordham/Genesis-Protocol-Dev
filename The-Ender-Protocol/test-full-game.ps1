#!/usr/bin/env pwsh
# Test the mock supervisor (no Bedrock)

$awsPath = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"

Write-Host "=== Testing Mock Supervisor ===" -ForegroundColor Cyan

# Create test payload
$payload = @{
    scenario_id = "scenario_02_sqlinjection"
    session_id = "test-game-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
} | ConvertTo-Json -Compress

Write-Host "`nInvoking Mock Supervisor..." -ForegroundColor Yellow
Write-Host "Payload: $payload" -ForegroundColor Gray

# Invoke the mock supervisor
& $awsPath lambda invoke `
    --function-name ender-protocol-SupervisorMockFunction-LCCbxTfvJcCa `
    --payload $payload `
    --cli-binary-format raw-in-base64-out `
    game-response.json

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n=== Game Response ===" -ForegroundColor Green
    Get-Content game-response.json | ConvertFrom-Json | ConvertTo-Json -Depth 10
    
    Write-Host "`n=== CloudWatch Logs ===" -ForegroundColor Cyan
    Start-Sleep -Seconds 2
    & $awsPath logs tail /aws/lambda/ender-protocol-SupervisorMockFunction-LCCbxTfvJcCa --since 2m --format short | Select-Object -Last 100
} else {
    Write-Host "`nInvocation failed!" -ForegroundColor Red
}
