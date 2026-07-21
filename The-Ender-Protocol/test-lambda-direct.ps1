#!/usr/bin/env pwsh
# Test Lambda with Bedrock event format

$awsPath = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"

Write-Host "=== Testing Lambda with Bedrock Event Format ===" -ForegroundColor Cyan

# Simulate Bedrock agent event
$bedrockEvent = @{
    actionGroup = "Sith-Attack-Tools"
    apiPath = "/brute-force"
    httpMethod = "POST"
    parameters = @(
        @{ name = "username"; value = "admin" }
        @{ name = "password"; value = "password123" }
    )
} | ConvertTo-Json -Compress

Write-Host "`nSending Bedrock-formatted event..." -ForegroundColor Yellow
Write-Host "Event: $bedrockEvent" -ForegroundColor Gray

& $awsPath lambda invoke `
    --function-name ender-protocol-red-team-tools `
    --cli-binary-format raw-in-base64-out `
    --payload $bedrockEvent `
    response.json | Out-Null

Write-Host "`nResponse:" -ForegroundColor Green
Get-Content response.json | ConvertFrom-Json | ConvertTo-Json -Depth 10

Write-Host "`n=== Check CloudWatch Logs ===" -ForegroundColor Cyan
Write-Host "Run this to see Lambda logs:" -ForegroundColor Yellow
Write-Host "& `"$awsPath`" logs tail /aws/lambda/ender-protocol-red-team-tools --follow" -ForegroundColor White
