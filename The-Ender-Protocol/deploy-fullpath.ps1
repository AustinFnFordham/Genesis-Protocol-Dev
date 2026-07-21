#!/usr/bin/env pwsh
# The Ender Protocol - Deployment Script (Full Paths)

Write-Host "=== The Ender Protocol Deployment ===" -ForegroundColor Cyan

# Define full paths
$awsPath = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
$samPath = "C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd"

# Step 1: Check AWS credentials
Write-Host "`n[1/5] Checking AWS credentials..." -ForegroundColor Yellow
try {
    & $awsPath sts get-caller-identity | Out-Null
    Write-Host "✓ AWS credentials configured" -ForegroundColor Green
} catch {
    Write-Host "✗ AWS credentials not configured" -ForegroundColor Red
    Write-Host "Run this command to configure:" -ForegroundColor Yellow
    Write-Host "& `"$awsPath`" configure" -ForegroundColor White
    exit 1
}

# Step 2: Create S3 bucket if it doesn't exist
Write-Host "`n[2/5] Checking S3 bucket..." -ForegroundColor Yellow
$bucketName = "the-ender-protocol-data-austin-fordham"
$bucketExists = & $awsPath s3 ls "s3://$bucketName" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating S3 bucket: $bucketName" -ForegroundColor Yellow
    & $awsPath s3 mb "s3://$bucketName"
}
Write-Host "✓ S3 bucket ready" -ForegroundColor Green

# Step 3: Upload scenario data
Write-Host "`n[3/5] Uploading scenario data..." -ForegroundColor Yellow
& $awsPath s3 cp scenarios/scenario_01_bruteforce/user_accounts.json "s3://$bucketName/scenarios/scenario_01_bruteforce/user_accounts.json"
& $awsPath s3 cp scenarios/scenario_01_bruteforce/password_dictionary.json "s3://$bucketName/scenarios/scenario_01_bruteforce/password_dictionary.json"
& $awsPath s3 cp scenarios/scenario_02_sqlinjection/servers.json "s3://$bucketName/scenarios/scenario_02_sqlinjection/servers.json"
Write-Host "✓ Scenario data uploaded" -ForegroundColor Green

# Step 4: Build Lambda functions
Write-Host "`n[4/5] Building Lambda functions..." -ForegroundColor Yellow
& $samPath build
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Build failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Build complete" -ForegroundColor Green

# Step 5: Deploy
Write-Host "`n[5/5] Deploying to AWS..." -ForegroundColor Yellow
& $samPath deploy --s3-bucket $bucketName --no-confirm-changeset --no-fail-on-empty-changeset
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Deployment failed" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Deployment Complete ===" -ForegroundColor Green
Write-Host "`nTest the Red Team function:" -ForegroundColor Cyan
Write-Host "& `"$awsPath`" lambda invoke --function-name ender-protocol-red-team-tools --payload `"{\\`"username\\`":\\`"admin\\`",\\`"password\\`":\\`"password123\\`"}`" response.json" -ForegroundColor White
