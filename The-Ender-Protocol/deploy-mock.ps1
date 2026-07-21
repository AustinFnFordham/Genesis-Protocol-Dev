#!/usr/bin/env pwsh
# Deploy Mock Supervisor (bypasses Bedrock agents)

$awsPath = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
$samPath = "C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd"

Write-Host "=== Deploying Mock Supervisor ===" -ForegroundColor Cyan

Write-Host "`n[1/2] Building..." -ForegroundColor Yellow
& $samPath build --template template-mock.yaml

Write-Host "`n[2/2] Deploying..." -ForegroundColor Yellow
& $samPath deploy --template-file .aws-sam/build/template.yaml --stack-name ender-protocol-mock --s3-bucket the-ender-protocol-data-austin-fordham --capabilities CAPABILITY_IAM --no-confirm-changeset --no-fail-on-empty-changeset

Write-Host "`n=== Mock Deployment Complete ===" -ForegroundColor Green
