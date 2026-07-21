#!/usr/bin/env pwsh
$awsPath = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
& $awsPath lambda list-functions --query "Functions[?contains(FunctionName, 'ender-protocol')].FunctionName" --output table
