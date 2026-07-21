# Next Steps After SAM CLI Installation

## 1. Restart Your Terminal
Close and reopen your terminal/command prompt for PATH changes to take effect.

## 2. Verify Installation
```cmd
sam --version
aws --version
```

## 3. Upload Scenario Data to S3
```cmd
aws s3 cp scenarios/scenario_01_bruteforce/user_accounts.json s3://the-ender-protocol-data-austin-fordham/scenarios/scenario_01_bruteforce/user_accounts.json
aws s3 cp scenarios/scenario_01_bruteforce/password_dictionary.json s3://the-ender-protocol-data-austin-fordham/scenarios/scenario_01_bruteforce/password_dictionary.json
```

## 4. Build Lambda Functions
```cmd
cd b:\API_Cursor_SW5e\SW5e_Data_Hub\The-Ender-Protocol
sam build
```

## 5. Deploy to AWS
```cmd
sam deploy --guided
```

During deployment, you'll be prompted for:
- Stack name: `ender-protocol`
- AWS Region: `us-east-1` (or your preferred region)
- Confirm changes: `Y`
- Allow SAM CLI IAM role creation: `Y`
- Save arguments to config: `Y`

## 6. Test Red Team Function
```cmd
aws lambda invoke --function-name ender-protocol-red-team-tools --payload "{\"username\":\"admin\",\"password\":\"password123\"}" response.json
type response.json
```

Expected output: `{"success": true}`
