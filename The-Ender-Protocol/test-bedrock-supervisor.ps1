#!/usr/bin/env pwsh
# Test the real Bedrock supervisor with retry logic disabled

$awsPath = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"

Write-Host "=== Testing Bedrock Supervisor (Retries Disabled) ===" -ForegroundColor Cyan

$payload = @{
    scenario_id = "scenario_01_bruteforce"
    session_id = "bedrock-test-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
} | ConvertTo-Json -Compress

Write-Host "`nInvoking Bedrock Supervisor..." -ForegroundColor Yellow
Write-Host "Payload: $payload" -ForegroundColor Gray

& $awsPath lambda invoke `
    --function-name ender-protocol-SupervisorAgentFunction-hQhlW8aLjwVR `
    --payload $payload `
    --cli-binary-format raw-in-base64-out `
    bedrock-response.json

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n=== Game Response ===" -ForegroundColor Green
    Get-Content bedrock-response.json | ConvertFrom-Json | ConvertTo-Json -Depth 10
    
    Write-Host "`n=== CloudWatch Logs ===" -ForegroundColor Cyan
    Start-Sleep -Seconds 2
    & $awsPath logs tail /aws/lambda/ender-protocol-SupervisorAgentFunction-hQhlW8aLjwVR --since 2m --format short | Select-Object -Last 100
} else {
    Write-Host "`nInvocation failed!" -ForegroundColor Red
}
