#!/usr/bin/env pwsh
# Check Red Team Lambda CloudWatch logs

$awsPath = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"

Write-Host "=== Red Team Lambda CloudWatch Logs ===" -ForegroundColor Cyan

& $awsPath logs tail /aws/lambda/ender-protocol-RedTeamToolsFunction-vFDWIQfF4PQa --since 10m --format short
