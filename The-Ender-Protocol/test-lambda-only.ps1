#!/usr/bin/env pwsh
# Test Lambda functions directly (no Bedrock agents)

$awsPath = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"

Write-Host "=== Testing Lambda Functions Directly ===" -ForegroundColor Cyan

# Test Red Team Lambda with requestBody format
Write-Host "`n[1/2] Testing Red Team Lambda..." -ForegroundColor Yellow
$redPayload = @{
    actionGroup = "red-team-tools"
    apiPath = "/brute-force"
    httpMethod = "POST"
    requestBody = @{
        content = @{
            "application/json" = @{
                properties = @(
                    @{ name = "username"; value = "admin" }
                    @{ name = "password"; value = "password123" }
                )
            }
        }
    }
} | ConvertTo-Json -Depth 10 -Compress

& $awsPath lambda invoke `
    --function-name ender-protocol-red-team-tools `
    --payload $redPayload `
    --cli-binary-format raw-in-base64-out `
    red-response.json

Write-Host "Red Team Response:" -ForegroundColor Green
Get-Content red-response.json | ConvertFrom-Json | ConvertTo-Json -Depth 10

# Test Blue Team Lambda with requestBody format
Write-Host "`n[2/2] Testing Blue Team Lambda..." -ForegroundColor Yellow
$bluePayload = @{
    actionGroup = "blue-team-tools"
    apiPath = "/block-ip"
    httpMethod = "POST"
    requestBody = @{
        content = @{
            "application/json" = @{
                properties = @(
                    @{ name = "scenario_id"; value = "scenario_01_bruteforce" }
                    @{ name = "ip_address"; value = "192.168.1.100" }
                )
            }
        }
    }
} | ConvertTo-Json -Depth 10 -Compress

& $awsPath lambda invoke `
    --function-name ender-protocol-blue-team-tools `
    --payload $bluePayload `
    --cli-binary-format raw-in-base64-out `
    blue-response.json

Write-Host "Blue Team Response:" -ForegroundColor Green
Get-Content blue-response.json | ConvertFrom-Json | ConvertTo-Json -Depth 10

Write-Host "`n=== Lambda Tests Complete ===" -ForegroundColor Cyan
