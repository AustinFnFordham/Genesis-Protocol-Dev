import json
import boto3
from botocore.config import Config
import os
from datetime import datetime

# AWS clients with retries disabled
config = Config(retries={'max_attempts': 0})
s3 = boto3.client('s3', config=config)
bedrock_agent = boto3.client('bedrock-agent-runtime', config=config)

def lambda_handler(event, context):
    """
    Supervisor Agent: Orchestrates The Ender Protocol game loop
    
    Expected event format:
    {
        "scenario_id": "scenario_01_bruteforce",
        "session_id": "optional-session-id"
    }
    """
    try:
        # Extract scenario ID
        scenario_id = event.get('scenario_id', 'scenario_01_bruteforce')
        session_id = event.get('session_id', f'session-{datetime.now().timestamp()}')
        
        print(f'Starting game for scenario: {scenario_id}, session: {session_id}')
        
        # Load scenario data from S3
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        if not bucket_name:
            raise ValueError('S3_BUCKET_NAME environment variable not set')
        
        # Load user accounts
        accounts_key = f'scenarios/{scenario_id}/user_accounts.json'
        accounts_response = s3.get_object(Bucket=bucket_name, Key=accounts_key)
        accounts_data = json.loads(accounts_response['Body'].read().decode('utf-8'))
        
        # Load password dictionary
        passwords_key = f'scenarios/{scenario_id}/password_dictionary.json'
        passwords_response = s3.get_object(Bucket=bucket_name, Key=passwords_key)
        passwords_data = json.loads(passwords_response['Body'].read().decode('utf-8'))
        
        # Initialize game state
        game_state = {
            'scenario_id': scenario_id,
            'session_id': session_id,
            'turn': 1,
            'status': 'active',
            'red_team': {
                'attempts': 0,
                'successes': 0,
                'failed_attempts': []
            },
            'blue_team': {
                'detections': 0,
                'blocks': 0
            },
            'target_accounts': [acc['username'] for acc in accounts_data.get('accounts', [])],
            'available_passwords': passwords_data.get('passwords', [])
        }
        
        print(f'Game state initialized: {json.dumps(game_state)}')
        
        # === RED TEAM TURN ===
        print('Starting Red Team turn...')
        
        # Get and validate Red Team agent ID
        red_team_agent_id = os.environ.get('RED_TEAM_AGENT_ID')
        print(f'DEBUG: Red Team Agent ID from env: {red_team_agent_id}')
        if not red_team_agent_id:
            raise ValueError('FATAL: RED_TEAM_AGENT_ID environment variable not found or empty!')
        
        red_team_alias_id = 'TSTALIASID'
        
        # Construct prompt for Red Team
        red_team_prompt = f"""Begin your infiltration mission. 
        
Target: Gain access to one of these accounts: {', '.join(game_state['target_accounts'])}

Available passwords to try: {', '.join(game_state['available_passwords'][:3])}

Use your brute-force tools to attempt access. Report your results."""
        
        print(f'Invoking Red Team agent {red_team_agent_id} with prompt: {red_team_prompt}')
        
        try:
            # Invoke Bedrock agent
            agent_response = bedrock_agent.invoke_agent(
                agentId=red_team_agent_id,
                agentAliasId=red_team_alias_id,
                sessionId=session_id,
                inputText=red_team_prompt
            )
            
            print(f'[RED TEAM] Agent response received, type: {type(agent_response)}')
            print(f'[RED TEAM] Response keys: {list(agent_response.keys())}')
            
            # Parse agent response
            red_team_result = parse_agent_response(agent_response)
            
            print(f'Red Team result: {json.dumps(red_team_result)}')
        except Exception as e:
            print(f'[RED TEAM] Error invoking agent: {str(e)}')
            import traceback
            traceback.print_exc()
            red_team_result = {'success': False, 'message': f'Agent invocation error: {str(e)}'}
        
        # Update game state with Red Team results
        game_state['red_team']['attempts'] += 1
        game_state['red_team']['last_action'] = red_team_result
        
        if red_team_result.get('success'):
            game_state['red_team']['successes'] += 1
            print(f'Red Team success! Total successes: {game_state["red_team"]["successes"]}')
        
        # === BLUE TEAM TURN ===
        print('Starting Blue Team turn...')
        
        # Get and validate Blue Team agent ID
        blue_team_agent_id = os.environ.get('BLUE_TEAM_AGENT_ID')
        print(f'DEBUG: Blue Team Agent ID from env: {blue_team_agent_id}')
        if not blue_team_agent_id:
            raise ValueError('FATAL: BLUE_TEAM_AGENT_ID environment variable not found or empty!')
        
        blue_team_alias_id = 'TSTALIASID'
        
        # Format threat report
        threat_report = {
            'type': 'brute_force_attack_success' if red_team_result.get('success') else 'brute_force_attack_attempt',
            'details': red_team_result.get('message', ''),
            'raw_data': red_team_result
        }
        
        blue_team_prompt = f"Threat report: {json.dumps(threat_report)}"
        
        print(f'Invoking Blue Team agent {blue_team_agent_id} with prompt: {blue_team_prompt}')
        
        try:
            blue_agent_response = bedrock_agent.invoke_agent(
                agentId=blue_team_agent_id,
                agentAliasId=blue_team_alias_id,
                sessionId=session_id,
                inputText=blue_team_prompt
            )
            
            print(f'[BLUE TEAM] Agent response received')
            
            # Parse Blue Team response
            blue_team_result = parse_agent_response(blue_agent_response)
            
            print(f'Blue Team result: {json.dumps(blue_team_result)}')
        except Exception as e:
            print(f'[BLUE TEAM] Error invoking agent: {str(e)}')
            import traceback
            traceback.print_exc()
            blue_team_result = {'success': False, 'message': f'Agent invocation error: {str(e)}'}
        
        game_state['blue_team']['last_action'] = blue_team_result
        
        # Check win/loss conditions
        if game_state['red_team']['successes'] >= 3:
            game_state['status'] = 'red_wins'
            print('[SUPERVISOR] RED TEAM WINS - 3 successes reached')
        elif game_state['turn'] > 10:
            game_state['status'] = 'blue_wins'
            print('[SUPERVISOR] BLUE TEAM WINS - survived 10 turns')
        
        # Update final game state
        game_state['turn'] += 1
        game_state['last_updated'] = datetime.now().isoformat()
        
        # Save game state to S3 for collaboration
        save_game_state(session_id, game_state)
        
        # Return Blue Team choices
        return blue_team_result
        
    except Exception as e:
        print(f'Error in supervisor agent: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Game orchestration failed'
            })
        }

# In src/lambdas/supervisor_agent/app.py
def parse_agent_response(response):
    """
    Parses the streaming response from Bedrock Agent's invoke_agent call.
    Searches for the action group output or a final answer.
    """
    try:
        # response['completion'] is a stream, we must iterate through its chunks
        for chunk in response.get('completion', {}):
            
            # 1. Check for the Action Group Output (The successful Lambda result)
            if 'invocationOutput' in chunk:
                # Extract JSON string from nested fields
                invocation_output = chunk['invocationOutput']
                output_text = invocation_output.get('actionGroupInvocationOutput', {}).get('text')
                
                if output_text:
                    # The Lambda response is a JSON string, which must be loaded again
                    lambda_response = json.loads(output_text)
                    
                    # Return the clean result from the Lambda
                    return lambda_response

            # 2. Check for the Final Text Answer (The agent failing to act)
            if 'finalResponse' in chunk:
                final_text = chunk['finalResponse'].get('text', 'Agent returned a final answer.')
                
                # If the agent returns a final text answer, it failed to take a discrete action.
                return {
                    'success': False,
                    'message': f'Agent failed to take action (Final Answer returned): {final_text}'
                }

        # If the stream ends without finding an action or final response
        return {'success': False, 'message': 'No tool output or final answer found in agent response stream'}

    except Exception as e:
        print(f"FATAL PARSING ERROR: {e}")
        return {'success': False, 'message': f'FATAL PARSING ERROR: {str(e)}'}

def save_game_state(session_id, game_state):
    """Save game state to S3 for agent collaboration"""
    try:
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        state_key = f'game_sessions/{session_id}/state.json'
        
        s3.put_object(
            Bucket=bucket_name,
            Key=state_key,
            Body=json.dumps(game_state, indent=2),
            ContentType='application/json'
        )
        
        print(f'Game state saved to {state_key}')
        return True
    except Exception as e:
        print(f'Error saving game state: {str(e)}')
        return False
