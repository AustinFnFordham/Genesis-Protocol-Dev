# Bedrock Rate Limit Issues

## Problem
The real supervisor (app.py) that calls Bedrock agents is experiencing persistent rate limiting and timeout issues.

## Evidence
- CloudWatch logs show invoke_agent is called but EventStream never yields events
- Lambda times out waiting for Bedrock response
- AWS free tier has very low Bedrock quotas that don't reset quickly

## Current Status
- ✅ **Mock Supervisor (app_mock.py)**: WORKING - Calls Lambda functions directly, bypasses Bedrock agents
- ❌ **Real Supervisor (app.py)**: NOT WORKING - Bedrock rate limits prevent agent responses

## Solution Options

### Option 1: Use Mock Supervisor (Current)
- Function: `ender-protocol-SupervisorMockFunction-LCCbxTfvJcCa`
- Calls Red/Blue Team Lambdas directly
- No Bedrock agent overhead
- Works reliably for testing

### Option 2: Request Bedrock Quota Increase
1. Go to AWS Service Quotas console
2. Request increase for:
   - Bedrock Agent invocations per minute
   - Bedrock model invocations per minute
3. Wait for approval (can take days)

### Option 3: Add Exponential Backoff
- Implement retry logic with exponential backoff
- May help with transient rate limits
- Won't solve persistent quota exhaustion

## Recommendation
**Use the mock supervisor for development and testing.** The real supervisor with Bedrock agents requires higher AWS quotas that aren't available on free tier.

## Files
- Mock Supervisor: `src/lambdas/supervisor_agent/app_mock.py`
- Real Supervisor: `src/lambdas/supervisor_agent/app.py`
- UI uses mock: Function name in `app_ui.py` line 132
