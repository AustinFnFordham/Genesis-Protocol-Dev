# Fix AWS CLI and SAM CLI PATH Issues

## Option 1: Add to PATH Manually

1. Open System Environment Variables:
   - Press `Win + R`
   - Type `sysdm.cpl` and press Enter
   - Click "Environment Variables"

2. Edit PATH variable:
   - Under "System variables", find and select "Path"
   - Click "Edit"
   - Click "New" and add these paths:
     ```
     C:\Program Files\Amazon\AWSCLIV2
     C:\Program Files\Amazon\AWSSAMCLI\bin
     ```

3. Click OK on all dialogs

4. Restart PowerShell completely (close all windows)

## Option 2: Use Full Paths (Quick Fix)

Instead of `aws` and `sam`, use full paths:

```powershell
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" --version
& "C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd" --version
```

## Option 3: Install AWS CLI First

If AWS CLI isn't installed:
1. Download: https://awscli.amazonaws.com/AWSCLIV2.msi
2. Run installer
3. Restart terminal

## Verify Installation Locations

Check if files exist:
```powershell
Test-Path "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
Test-Path "C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd"
```

## After Fixing PATH

Test:
```powershell
aws --version
sam --version
```
