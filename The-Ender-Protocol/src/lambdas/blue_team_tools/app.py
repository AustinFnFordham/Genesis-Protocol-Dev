import json
import boto3
import os

s3_client = boto3.client('s3')

def patch_server(parameters, bucket_name):
    """
    Blue Team Tool: Patch vulnerable server
    """
    scenario_id = next((p['value'] for p in parameters if p['name'] == 'scenario_id'), None)
    server_id = next((p['value'] for p in parameters if p['name'] == 'server_id'), None)
    
    if not scenario_id or not server_id:
        return {'status': 'error', 'message': 'Missing scenario_id or server_id'}
    
    file_key = f'scenarios/{scenario_id}/servers.json'
    
    # Get current servers
    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    servers_data = json.loads(response['Body'].read().decode('utf-8'))
    
    # Find and patch server
    for server in servers_data.get('servers', []):
        if server['id'] == server_id:
            server['patch_level'] = 'patched'
            break
    
    # Save updated servers
    s3_client.put_object(
        Bucket=bucket_name,
        Key=file_key,
        Body=json.dumps(servers_data, indent=2),
        ContentType='application/json'
    )
    
    return {'status': 'success', 'message': f'Server {server_id} patched successfully'}

def lambda_handler(event, context):
    """
    Blue Team Tools: Block malicious IP addresses and patch servers
    """
    print(f'Received event: {json.dumps(event)}')
    
    try:
        action_group = event.get('actionGroup', '')
        api_path = event.get('apiPath', '')
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        
        # Extract parameters from requestBody
        parameters = event.get('requestBody', {}).get('content', {}).get('application/json', {}).get('properties', [])
        
        # Route to correct tool
        if api_path == '/patch-server':
            response_body = patch_server(parameters, bucket_name)
        else:
            # Block IP
            scenario_id = next((p['value'] for p in parameters if p['name'] == 'scenario_id'), None)
            ip_address = next((p['value'] for p in parameters if p['name'] == 'ip_address'), None)
            
            if not scenario_id or not ip_address:
                raise ValueError('Missing scenario_id or ip_address')
            
            file_key = f'scenarios/{scenario_id}/firewall_rules.json'
            
            # Get current firewall rules
            response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
            firewall_rules = json.loads(response['Body'].read().decode('utf-8'))
            
            # Add IP to blocked list
            if ip_address not in firewall_rules['blocked_ips']:
                firewall_rules['blocked_ips'].append(ip_address)
            
            # Save updated rules
            s3_client.put_object(
                Bucket=bucket_name,
                Key=file_key,
                Body=json.dumps(firewall_rules)
            )
            
            response_body = {'status': 'success', 'message': f'IP {ip_address} blocked'}
    
    except Exception as e:
        print(f'Error: {e}')
        response_body = {'status': 'error', 'message': str(e)}
    
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
