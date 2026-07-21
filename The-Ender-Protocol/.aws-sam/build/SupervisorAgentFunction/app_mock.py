import json
import boto3
from botocore.config import Config
import os
from datetime import datetime

config = Config(retries={'max_attempts': 0})
s3 = boto3.client('s3', config=config)
lambda_client = boto3.client('lambda', config=config)
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', config=config)

def lambda_handler(event, context):
    """
    Supervisor Agent: Mock version that calls Lambda functions directly
    """
    try:
        # Validate environment variables
        if not os.environ.get('RED_TEAM_LAMBDA_NAME') or not os.environ.get('BLUE_TEAM_LAMBDA_NAME'):
            raise ValueError('RED_TEAM_LAMBDA_NAME and BLUE_TEAM_LAMBDA_NAME must be set')
        if not os.environ.get('BLUE_TEAM_AGENT_ID'):
            raise ValueError('BLUE_TEAM_AGENT_ID must be set')
        
        # Check if this is a player action or new game
        if 'player_action' in event:
            return handle_player_action(event)
        
        scenario_id = event.get('scenario_id', 'scenario_01_bruteforce')
        session_id = event.get('session_id', f'session-{datetime.now().timestamp()}')
        
        print(f'[SUPERVISOR] Starting game for scenario: {scenario_id}, session: {session_id}')
        
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        
        # Initialize game state
        game_state = {
            'scenario_id': scenario_id,
            'session_id': session_id,
            'turn': 1,
            'status': 'active',
            'red_team': {'attempts': 0, 'successes': 0, 'failed_attempts': []},
            'blue_team': {'detections': 0, 'blocks': 0}
        }
        
        # Load scenario-specific data
        if scenario_id == 'scenario_02_sqlinjection':
            game_state['target_servers'] = ['holocron_vault_server']
        else:
            accounts_key = f'scenarios/{scenario_id}/user_accounts.json'
            accounts_response = s3.get_object(Bucket=bucket_name, Key=accounts_key)
            accounts_data = json.loads(accounts_response['Body'].read().decode('utf-8'))
            
            passwords_key = f'scenarios/{scenario_id}/password_dictionary.json'
            passwords_response = s3.get_object(Bucket=bucket_name, Key=passwords_key)
            passwords_data = json.loads(passwords_response['Body'].read().decode('utf-8'))
            
            game_state['target_accounts'] = [acc['username'] for acc in accounts_data.get('accounts', [])]
            game_state['available_passwords'] = passwords_data.get('passwords', [])
        
        print(f'Game state initialized: {json.dumps(game_state)}')
        
        # === RED TEAM TURN (Direct Lambda call) ===
        print(f'[SUPERVISOR] Starting Red Team turn for: {scenario_id}')
        
        if scenario_id == 'scenario_02_sqlinjection':
            print('[SUPERVISOR] Detected SQL injection scenario')
            red_payload = {
                'actionGroup': 'red-team-tools',
                'apiPath': '/sql-injection',
                'httpMethod': 'POST',
                'requestBody': {
                    'content': {
                        'application/json': {
                            'properties': [
                                {'name': 'server_id', 'value': 'holocron_vault_server'}
                            ]
                        }
                    }
                }
            }
        else:
            # Use correct password on first attempt to make game winnable
            red_payload = {
                'actionGroup': 'red-team-tools',
                'apiPath': '/brute-force',
                'httpMethod': 'POST',
                'requestBody': {
                    'content': {
                        'application/json': {
                            'properties': [
                                {'name': 'username', 'value': 'admin'},
                                {'name': 'password', 'value': 'password123'}
                            ]
                        }
                    }
                }
            }
        
        red_response = lambda_client.invoke(
            FunctionName=os.environ['RED_TEAM_LAMBDA_NAME'],
            InvocationType='RequestResponse',
            Payload=json.dumps(red_payload)
        )
        
        red_result = json.loads(red_response['Payload'].read().decode('utf-8'))
        red_body = json.loads(red_result['response']['responseBody']['application/json']['body'])
        
        print(f'Red Team result: {json.dumps(red_body)}')
        
        game_state['red_team']['attempts'] += 1
        game_state['red_team']['last_action'] = red_body
        
        if red_body.get('success'):
            game_state['red_team']['successes'] += 1
        
        print(f'[SUPERVISOR] Red Team successes: {game_state["red_team"]["successes"]}, Turn: {game_state["turn"]}')
        
        # Check win/loss conditions
        if game_state['red_team']['successes'] >= 3:
            game_state['status'] = 'red_wins'
            print('[SUPERVISOR] RED TEAM WINS - 3 successes reached')
            choices = []
        elif game_state['turn'] > 10:
            game_state['status'] = 'blue_wins'
            print('[SUPERVISOR] BLUE TEAM WINS - survived 10 turns')
            choices = []
        else:
            # === BLUE TEAM TURN (Call Bedrock Agent) ===
            print('[SUPERVISOR] Starting Blue Team turn')
            
            blue_agent_id = os.environ['BLUE_TEAM_AGENT_ID']
            threat_report = f"Threat Report: {red_body.get('message')}. Attack Success: {red_body.get('success')}. Scenario: {scenario_id}"
            
            print(f'[SUPERVISOR] Calling Blue Team Agent {blue_agent_id} with threat: {threat_report}')
            
            agent_response = bedrock_agent_runtime.invoke_agent(
                agentId=blue_agent_id,
                agentAliasId='TSTALIASID',
                sessionId=session_id,
                inputText=threat_report
            )
            
            completion = ''
            for event in agent_response['completion']:
                if 'chunk' in event:
                    completion += event['chunk']['bytes'].decode('utf-8')
            
            print(f'[BLUE AGENT] Raw response: {completion}')
            
            choices_data = json.loads(completion)
            choices = choices_data.get('choices', [])
            print(f'[BLUE AGENT] Parsed choices: {choices}')
        
        game_state['last_updated'] = datetime.now().isoformat()
        
        # Save game state
        state_key = f'game_sessions/{session_id}/state.json'
        s3.put_object(
            Bucket=bucket_name,
            Key=state_key,
            Body=json.dumps(game_state, indent=2),
            ContentType='application/json'
        )
        
        print(f'Game state saved to {state_key}')
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'game_state': game_state,
                'choices': choices,
                'message': 'Game initialized'
            })
        }
        
    except Exception as e:
        print(f'Error: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def handle_player_action(event):
    """
    Handle player's chosen action and run next Red Team turn
    """
    try:
        session_id = event['session_id']
        player_action = event['player_action']
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        
        print(f'[SUPERVISOR] Handling player action: {player_action} for session: {session_id}')
        
        # Load game state
        state_key = f'game_sessions/{session_id}/state.json'
        response = s3.get_object(Bucket=bucket_name, Key=state_key)
        game_state = json.loads(response['Body'].read().decode('utf-8'))
        
        # Execute player's chosen action
        if player_action == 'patch_server':
            blue_response = lambda_client.invoke(
                FunctionName=os.environ['BLUE_TEAM_LAMBDA_NAME'],
                InvocationType='RequestResponse',
                Payload=json.dumps({
                    'actionGroup': 'blue-team-tools',
                    'apiPath': '/patch-server',
                    'httpMethod': 'POST',
                    'requestBody': {
                        'content': {
                            'application/json': {
                                'properties': [
                                    {'name': 'scenario_id', 'value': game_state['scenario_id']},
                                    {'name': 'server_id', 'value': 'holocron_vault_server'}
                                ]
                            }
                        }
                    }
                })
            )
            blue_result = json.loads(blue_response['Payload'].read().decode('utf-8'))
            blue_body = json.loads(blue_result['response']['responseBody']['application/json']['body'])
            game_state['blue_team']['last_action'] = blue_body
        elif player_action == 'block_ip':
            blue_response = lambda_client.invoke(
                FunctionName=os.environ['BLUE_TEAM_LAMBDA_NAME'],
                InvocationType='RequestResponse',
                Payload=json.dumps({
                    'actionGroup': 'blue-team-tools',
                    'apiPath': '/block-ip',
                    'httpMethod': 'POST',
                    'requestBody': {
                        'content': {
                            'application/json': {
                                'properties': [
                                    {'name': 'scenario_id', 'value': game_state['scenario_id']},
                                    {'name': 'ip_address', 'value': '192.168.1.50'}
                                ]
                            }
                        }
                    }
                })
            )
            blue_result = json.loads(blue_response['Payload'].read().decode('utf-8'))
            blue_body = json.loads(blue_result['response']['responseBody']['application/json']['body'])
            game_state['blue_team']['last_action'] = blue_body
        elif player_action == 'monitor':
            game_state['blue_team']['last_action'] = {'status': 'monitoring', 'message': 'Monitoring attacker activity'}
        elif player_action == 'lockdown':
            game_state['blue_team']['last_action'] = {'status': 'lockdown', 'message': 'All accounts locked down'}
        
        # Run Red Team next turn
        print(f'[SUPERVISOR] Next turn for scenario: {game_state["scenario_id"]}')
        if game_state['scenario_id'] == 'scenario_02_sqlinjection':
            print('[SUPERVISOR] Using SQL injection for next turn')
            red_payload = {
                'actionGroup': 'red-team-tools',
                'apiPath': '/sql-injection',
                'httpMethod': 'POST',
                'requestBody': {
                    'content': {
                        'application/json': {
                            'properties': [
                                {'name': 'server_id', 'value': 'holocron_vault_server'}
                            ]
                        }
                    }
                }
            }
        else:
            # Vary attacks - sometimes succeed
            import random
            if random.random() < 0.4:  # 40% success rate
                username, password = 'jsmith', '123456'
            else:
                username, password = 'dbadmin', 'wrongpass'
            
            red_payload = {
                'actionGroup': 'red-team-tools',
                'apiPath': '/brute-force',
                'httpMethod': 'POST',
                'requestBody': {
                    'content': {
                        'application/json': {
                            'properties': [
                                {'name': 'username', 'value': username},
                                {'name': 'password', 'value': password}
                            ]
                        }
                    }
                }
            }
        
        red_response = lambda_client.invoke(
            FunctionName=os.environ['RED_TEAM_LAMBDA_NAME'],
            InvocationType='RequestResponse',
            Payload=json.dumps(red_payload)
        )
        
        red_result = json.loads(red_response['Payload'].read().decode('utf-8'))
        red_body = json.loads(red_result['response']['responseBody']['application/json']['body'])
        
        game_state['red_team']['attempts'] += 1
        game_state['red_team']['last_action'] = red_body
        
        # Track successes
        if red_body.get('success'):
            game_state['red_team']['successes'] += 1
        
        game_state['turn'] += 1
        
        print(f'[SUPERVISOR] After turn {game_state["turn"]}: Red successes={game_state["red_team"]["successes"]}')
        
        # Check win/loss conditions
        if game_state['red_team']['successes'] >= 3:
            game_state['status'] = 'red_wins'
            print('[SUPERVISOR] RED TEAM WINS - 3 successes reached')
            choices = []
        elif game_state['turn'] > 10:
            game_state['status'] = 'blue_wins'
            print('[SUPERVISOR] BLUE TEAM WINS - survived 10 turns')
            choices = []
        
        game_state['last_updated'] = datetime.now().isoformat()
        
        # Save updated state
        s3.put_object(
            Bucket=bucket_name,
            Key=state_key,
            Body=json.dumps(game_state, indent=2),
            ContentType='application/json'
        )
        
        # Generate choices only if game is active
        if game_state['status'] != 'active':
            choices = []
        else:
            # === BLUE TEAM TURN (Call Bedrock Agent) ===
            print('[SUPERVISOR] Starting Blue Team turn')
            
            blue_agent_id = os.environ['BLUE_TEAM_AGENT_ID']
            threat_report = f"Threat Report: {red_body.get('message')}. Attack Success: {red_body.get('success')}. Scenario: {game_state['scenario_id']}"
            
            print(f'[SUPERVISOR] Calling Blue Team Agent {blue_agent_id} with threat: {threat_report}')
            
            agent_response = bedrock_agent_runtime.invoke_agent(
                agentId=blue_agent_id,
                agentAliasId='TSTALIASID',
                sessionId=session_id,
                inputText=threat_report
            )
            
            completion = ''
            for event in agent_response['completion']:
                if 'chunk' in event:
                    completion += event['chunk']['bytes'].decode('utf-8')
            
            print(f'[BLUE AGENT] Raw response: {completion}')
            
            choices_data = json.loads(completion)
            choices = choices_data.get('choices', [])
            print(f'[BLUE AGENT] Parsed choices: {choices}')
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'game_state': game_state,
                'choices': choices,
                'message': 'Player action executed'
            })
        }
        
    except Exception as e:
        print(f'Error handling player action: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
