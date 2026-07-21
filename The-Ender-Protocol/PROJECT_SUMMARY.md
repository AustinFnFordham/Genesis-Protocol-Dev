# The Ender Protocol - Project Summary

## Overview
AI training platform where a human player with "Jedi Co-Pilot" agent plays against autonomous "Sith Infiltrator" agent on serverless AWS architecture.

## Architecture
- **AWS Lambda Functions**: Red Team, Blue Team, Supervisor (real + mock)
- **AWS Bedrock Agents**: Red Team (QFY4WQH3Q8), Blue Team (KAH6H3NHW1)
- **AWS S3**: Scenario data storage
- **Streamlit UI**: Interactive web interface

## Key Files
- `src/lambdas/red_team_tools/app.py` - Brute force & SQL injection attacks
- `src/lambdas/blue_team_tools/app.py` - IP blocking & server patching
- `src/lambdas/supervisor_agent/app.py` - Real Bedrock orchestration
- `src/lambdas/supervisor_agent/app_mock.py` - Mock orchestration (bypasses Bedrock)
- `app_ui.py` - Streamlit interface with Hextech Star Wars theme
- `template.yaml` - SAM deployment configuration
- `deploy-fullpath.ps1` - Deployment script

## Scenarios
1. **Brute Force**: Red Team tries username/password combos, Blue Team blocks IPs/locks accounts
2. **SQL Injection**: Red Team exploits vulnerable server, Blue Team patches it

## Win Conditions
- **Blue Team**: Survive 10 turns
- **Red Team**: 3 successful breaches

## Deployment
```powershell
.\deploy-fullpath.ps1
```

## Testing
```powershell
.\test-full-game.ps1  # Mock supervisor
.\test-bedrock-supervisor.ps1  # Real Bedrock agents
```

## Running UI
```powershell
streamlit run app_ui.py
```

## AWS Resources
- Account ID: 986341372503
- S3 Bucket: the-ender-protocol-data-austin-fordham
- Region: us-east-1

## Key Insights
- Bedrock rate limits required mock supervisor workaround
- Lambda response format: single 'response' key without 'messageVersion'
- Retry logic disabled (max_attempts: 0) to prevent cascading errors
- CloudFormation auto-generates function names (no explicit FunctionName)

## Status
✅ Fully functional mock game loop
✅ Streamlit UI with Star Wars theme
✅ Two playable scenarios
✅ Win/loss conditions working
⚠️ Bedrock agents functional but rate-limited
