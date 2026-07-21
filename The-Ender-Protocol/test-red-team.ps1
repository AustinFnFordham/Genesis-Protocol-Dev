#!/usr/bin/env pwsh
# Test Red Team Brute Force Function

$awsPath = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"

Write-Host "=== Testing Red Team Brute Force Attack ===" -ForegroundColor Cyan

# Test 1: Valid credentials
Write-Host "`nTest 1: Valid credentials (admin/password123)" -ForegroundColor Yellow
$payload1 = '{"username":"admin","password":"password123"}'
& $awsPath lambda invoke --function-name ender-protocol-red-team-tools --cli-binary-format raw-in-base64-out --payload $payload1 response.json | Out-Null
$result = Get-Content response.json | ConvertFrom-Json
Write-Host "Result: $($result.success)" -ForegroundColor $(if($result.success){"Green"}else{"Red"})

# Test 2: Invalid password
Write-Host "`nTest 2: Invalid password (admin/wrongpass)" -ForegroundColor Yellow
$payload2 = '{"username":"admin","password":"wrongpass"}'
& $awsPath lambda invoke --function-name ender-protocol-red-team-tools --cli-binary-format raw-in-base64-out --payload $payload2 response.json | Out-Null
$result = Get-Content response.json | ConvertFrom-Json
Write-Host "Result: $($result.success)" -ForegroundColor $(if($result.success){"Green"}else{"Red"})

# Test 3: Invalid username
Write-Host "`nTest 3: Invalid username (hacker/password123)" -ForegroundColor Yellow
$payload3 = '{"username":"hacker","password":"password123"}'
& $awsPath lambda invoke --function-name ender-protocol-red-team-tools --cli-binary-format raw-in-base64-out --payload $payload3 response.json | Out-Null
$result = Get-Content response.json | ConvertFrom-Json
Write-Host "Result: $($result.success)" -ForegroundColor $(if($result.success){"Green"}else{"Red"})

Write-Host "`n=== Tests Complete ===" -ForegroundColor Green
Write-Host "`nResponse file: response.json" -ForegroundColor Cyan
