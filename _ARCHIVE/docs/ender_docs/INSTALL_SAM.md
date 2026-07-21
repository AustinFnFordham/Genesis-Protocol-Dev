# Installing AWS SAM CLI on Windows

## Prerequisites
1. **AWS CLI** - Must be installed first
2. **Python 3.11+** - Required for SAM CLI

## Installation Steps

### Option 1: Using MSI Installer (Recommended)

1. Download the AWS SAM CLI installer:
   - 64-bit: https://github.com/aws/aws-sam-cli/releases/latest/download/AWS_SAM_CLI_64_PY3.msi

2. Run the MSI installer and follow the prompts

3. Verify installation:
   ```cmd
   sam --version
   ```

### Option 2: Using pip

```cmd
pip install aws-sam-cli
```

### Option 3: Using Chocolatey

```cmd
choco install aws-sam-cli
```

## Verify Installation

```cmd
sam --version
aws --version
```

## Next Steps

After installation, deploy The Ender Protocol:

```cmd
cd b:\API_Cursor_SW5e\SW5e_Data_Hub\The-Ender-Protocol
sam build
sam deploy --guided
```
