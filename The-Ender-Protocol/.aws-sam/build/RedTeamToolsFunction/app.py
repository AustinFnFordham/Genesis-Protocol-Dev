import json
import boto3
import hashlib
import os

s3 = boto3.client('s3')

def exploit_sql_injection(event, bucket_name):
    """
    Red Team Tool: Exploit SQL injection vulnerability
    """
    print(f'[SQL INJECTION] Starting exploit attempt')
    parameters = event.get('requestBody', {}).get('content', {}).get('application/json', {}).get('properties', [])
    server_id = next((p['value'] for p in parameters if p['name'] == 'server_id'), None)
    print(f'[SQL INJECTION] Received server_id: {server_id}')
    
    if not server_id:
        return {'success': False, 'message': 'Missing server_id'}
    
    s3_key = 'scenarios/scenario_02_sqlinjection/servers.json'
    print(f'[SQL INJECTION] Reading from S3: {s3_key}')
    response = s3.get_object(Bucket=bucket_name, Key=s3_key)
    servers_data = json.loads(response['Body'].read().decode('utf-8'))
    print(f'[SQL INJECTION] Servers data: {json.dumps(servers_data)}')
    
    server = next((s for s in servers_data.get('servers', []) if s['id'] == server_id), None)
    print(f'[SQL INJECTION] Found server: {json.dumps(server)}')
    
    if not server:
        return {'success': False, 'message': f'Server {server_id} not found'}
    
    patch_level = server.get('patch_level')
    print(f'[SQL INJECTION] Patch level: {patch_level}')
    
    if patch_level == 'outdated':
        return {'success': True, 'message': f'SQL injection successful on {server["hostname"]}', 'server_id': server_id}
    else:
        return {'success': False, 'message': f'Server {server["hostname"]} is patched'}

def lambda_handler(event, context):
    """
    Red Team Tools: Attempt single login for brute-force attack
    """
    print(f'Received event: {json.dumps(event)}')
    
    try:
        action_group = event.get('actionGroup', '')
        api_path = event.get('apiPath', '')
        
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        if not bucket_name:
            raise ValueError('S3_BUCKET_NAME environment variable not set')
        
        # Route to correct tool based on API path
        if api_path == '/sql-injection':
            print(f'[RED TEAM] Routing to SQL injection tool')
            result = exploit_sql_injection(event, bucket_name)
            print(f'[RED TEAM] SQL injection result: {json.dumps(result)}')
            response_body = result
        else:
            # Extract parameters from requestBody
            print('[BRUTE FORCE] Starting login attempt')
            parameters = event.get('requestBody', {}).get('content', {}).get('application/json', {}).get('properties', [])
            print(f'[BRUTE FORCE] Parameters: {parameters}')
            
            username = next((p['value'] for p in parameters if p['name'] == 'username'), None)
            password = next((p['value'] for p in parameters if p['name'] == 'password'), None)
            print(f'[BRUTE FORCE] Attempting login - Username: {username}, Password: {password}')
            
            if not username or not password:
                raise ValueError('Missing username or password')
            
            # Fetch user_accounts.json from S3
            s3_key = 'scenarios/scenario_01_bruteforce/user_accounts.json'
            print(f'[BRUTE FORCE] Reading from S3: {s3_key}')
            response = s3.get_object(Bucket=bucket_name, Key=s3_key)
            raw_json = response['Body'].read().decode('utf-8')
            print(f'[BRUTE FORCE] Raw JSON from S3: {raw_json}')
            
            accounts_data = json.loads(raw_json)
            print(f'[BRUTE FORCE] Parsed accounts_data: {json.dumps(accounts_data)}')
            print(f'[BRUTE FORCE] Structure type: {type(accounts_data)}')
            print(f'[BRUTE FORCE] Keys in accounts_data: {accounts_data.keys() if isinstance(accounts_data, dict) else "Not a dict"}')
        
            # Find matching user account
            user_account = None
            accounts_list = accounts_data.get('accounts', [])
            print(f'[BRUTE FORCE] Number of accounts found: {len(accounts_list)}')
            
            for account in accounts_list:
                account_username = account.get('username')
                print(f'[BRUTE FORCE] Checking account: {account_username} == {username}? {account_username == username}')
                if account_username == username:
                    user_account = account
                    print(f'[BRUTE FORCE] Match found! Account: {json.dumps(user_account)}')
                    break
            
            if not user_account:
                print(f'[BRUTE FORCE] No matching account found for username: {username}')
                result = {'success': False, 'message': f'User {username} not found'}
            else:
                # Hash the provided password using MD5
                password_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
                stored_hash = user_account.get('password_hash')
                print(f'[BRUTE FORCE] Password hash comparison - Provided: {password_hash}, Stored: {stored_hash}')
                
                # Compare hashes
                if password_hash == stored_hash:
                    print(f'[BRUTE FORCE] Password match! Access granted')
                    result = {'success': True, 'message': f'Access granted to {username}', 'access_level': user_account.get('access_level')}
                else:
                    print(f'[BRUTE FORCE] Password mismatch')
                    result = {'success': False, 'message': 'Invalid password'}
            
            response_body = result
    
    except Exception as e:
        print(f'Error: {e}')
        response_body = {'success': False, 'message': str(e)}
    
    return {
        'response': {
            'actionGroup': action_group,
            'apiPath': api_path,
            'httpMethod': event.get('httpMethod', 'POST'),
            'httpStatusCode': 200,
            'responseBody': {
                'application/json': {
                    'body': json.dumps(response_body)
                }
            }
        }
    }
