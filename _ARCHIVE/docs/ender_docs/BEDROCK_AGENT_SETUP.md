# Bedrock Agent Setup Guide

## Configure Red Team Agent Action Group

1. **Go to Bedrock Console**
   - Navigate to: https://console.aws.amazon.com/bedrock/
   - Click "Agents" in left sidebar
   - Select your Red Team agent (QFY4WQH3Q8)

2. **Add Action Group**
   - Click "Add action group"
   - Name: `Sith-Attack-Tools`
   - Description: `Red Team brute-force attack tools`

3. **Configure Action Group**
   - Action group type: **Define with API schemas**
   - Action group invocation: **Select an existing Lambda function**
   - Lambda function: `ender-protocol-red-team-tools`

4. **Upload API Schema**
   - Click "Browse S3" or "Upload file"
   - Upload: `red-team-action-schema.json`
   - Or paste the schema directly

5. **Save and Prepare**
   - Click "Save and exit"
   - Click "Prepare" to update the agent

## Upload Schema to S3 (Alternative)

```powershell
aws s3 cp red-team-action-schema.json s3://the-ender-protocol-data-austin-fordham/schemas/red-team-action-schema.json
```

Then in Bedrock console, select "Browse S3" and choose the uploaded file.

## Test the Agent

After preparing, test with:
```
Begin your infiltration. Your mission is to gain access to the 'admin' account. 
Try the password 'password123'.
```

Expected response:
```
Access granted to admin with administrator level access.
```

## Schema Summary

The schema defines one endpoint:
- **POST /brute-force**
  - Parameters: `username` (string), `password` (string)
  - Returns: `success` (boolean), `message` (string), `access_level` (string)
