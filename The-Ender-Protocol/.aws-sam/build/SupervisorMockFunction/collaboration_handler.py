import json
import boto3
import os

s3 = boto3.client('s3')

def handle_collaboration_request(event, context):
    """
    Handle collaboration requests from Blue Team agent
    
    Expected event format from Bedrock agent collaboration:
    {
        "messageVersion": "1.0",
        "agent": {...},
        "inputText": "...",
        "sessionId": "...",
        "sessionAttributes": {...},
        "promptSessionAttributes": {...}
    }
    """
    try:
        print(f'Collaboration request: {json.dumps(event)}')
        
        # Extract session info
        session_id = event.get('sessionId')
        input_text = event.get('inputText', '')
        agent_info = event.get('agent', {})
        
        # Load current game state from S3
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        state_key = f'game_sessions/{session_id}/state.json'
        
        try:
            response = s3.get_object(Bucket=bucket_name, Key=state_key)
            game_state = json.loads(response['Body'].read().decode('utf-8'))
        except:
            # No existing state, return basic info
            game_state = {
                'session_id': session_id,
                'status': 'active',
                'message': 'Game state not found'
            }
        
        # Prepare response for Blue Team
        collaboration_response = {
            'game_state': game_state,
            'red_team_activity': game_state.get('red_team', {}).get('last_action', {}),
            'recommendations': [
                'Monitor for brute-force patterns',
                'Consider blocking suspicious IPs',
                'Review failed login attempts'
            ]
        }
        
        # Return collaboration response
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': 'supervisor-collaboration',
                'functionResponse': {
                    'responseBody': {
                        'TEXT': {
                            'body': json.dumps(collaboration_response)
                        }
                    }
                }
            }
        }
    
    except Exception as e:
        print(f'Collaboration error: {str(e)}')
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': 'supervisor-collaboration',
                'functionResponse': {
                    'responseBody': {
                        'TEXT': {
                            'body': json.dumps({'error': str(e)})
                        }
                    }
                }
            }
        }

def save_game_state(session_id, game_state):
    """Save game state to S3"""
    try:
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        state_key = f'game_sessions/{session_id}/state.json'
        
        s3.put_object(
            Bucket=bucket_name,
            Key=state_key,
            Body=json.dumps(game_state, indent=2),
            ContentType='application/json'
        )
        
        return True
    except Exception as e:
        print(f'Error saving state: {str(e)}')
        return False
