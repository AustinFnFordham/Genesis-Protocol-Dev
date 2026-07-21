# -*- coding: utf-8 -*-
import streamlit as st
import boto3
import json
import uuid
from datetime import datetime
import time

# Page config
st.set_page_config(
    page_title="The Ender Protocol",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def load_clean_css():
    """Simple, clean CSS without conflicts"""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
    
    /* Base */
    html, body, [class*="css"] {
        font-family: 'Orbitron', monospace !important;
        background: linear-gradient(135deg, #0a0a1a 0%, #1a0a2e 50%, #16213e 100%) !important;
        color: #00ffff !important;
    }
    
    .main .block-container {
        max-width: 100% !important;
        padding: 1rem !important;
    }
    
    /* Header */
    .main-header {
        background: linear-gradient(135deg, rgba(0, 0, 0, 0.9), rgba(0, 20, 40, 0.9));
        border: 3px solid #00ffff;
        border-radius: 20px;
        padding: 2rem;
        margin: 1rem 0 2rem 0;
        text-align: center;
        box-shadow: 0 0 30px rgba(0, 255, 255, 0.5);
    }
    
    .epic-title {
        font-weight: 900;
        font-size: 3.5rem;
        background: linear-gradient(45deg, #00ffff, #ff0080, #00ffff);
        background-size: 200% 200%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 1rem 0;
        letter-spacing: 0.2em;
    }
    
    .epic-subtitle {
        color: #ff4444;
        font-size: 1.5rem;
        font-weight: 700;
        text-shadow: 0 0 10px #ff4444;
        margin: 1rem 0;
    }
    
    /* Mission parameters */
    .mission-parameters {
        background: linear-gradient(135deg, rgba(0, 20, 40, 0.9), rgba(0, 40, 80, 0.9));
        border: 2px solid #00ffff;
        border-radius: 15px;
        padding: 2rem;
        margin: 2rem 0;
        text-align: center;
    }
    
    .victory-conditions {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 2rem;
        margin-top: 2rem;
    }
    
    /* Mission buttons - clean approach */
    .stButton > button {
        width: 100% !important;
        height: 300px !important;
        font-family: 'Orbitron', monospace !important;
        font-size: 0.9rem !important;
        white-space: pre-line !important;
        text-align: left !important;
        padding: 1.5rem !important;
        border-radius: 15px !important;
        border: 3px solid !important;
        transition: all 0.3s ease !important;
        margin: 0.5rem 0 !important;
    }
    
    /* Mission I - Red */
    div[data-testid="column"]:first-child .stButton > button {
        background: linear-gradient(135deg, rgba(40, 0, 0, 0.9), rgba(80, 0, 0, 0.9)) !important;
        border-color: #ff4444 !important;
        color: #ffaaaa !important;
    }
    
    /* Mission II - Purple */
    div[data-testid="column"]:last-child .stButton > button {
        background: linear-gradient(135deg, rgba(20, 0, 40, 0.9), rgba(40, 0, 80, 0.9)) !important;
        border-color: #8800ff !important;
        color: #ccaaff !important;
    }
    
    /* Hover effects */
    div[data-testid="column"]:first-child .stButton > button:hover {
        transform: translateY(-5px) !important;
        box-shadow: 0 10px 30px rgba(255, 68, 68, 0.5) !important;
        border-color: #ffffff !important;
    }
    
    div[data-testid="column"]:last-child .stButton > button:hover {
        transform: translateY(-5px) !important;
        box-shadow: 0 10px 30px rgba(136, 0, 255, 0.5) !important;
        border-color: #ffffff !important;
    }
    
    /* Game interface */
    .status-panel, .game-panel {
        background: linear-gradient(135deg, rgba(0, 20, 40, 0.9), rgba(0, 40, 80, 0.9));
        border: 2px solid #00ffff;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    .game-panel {
        min-height: 400px;
        border: 3px solid #00ffff;
    }
    
    .red-turn {
        border-color: #ff4444 !important;
        box-shadow: 0 0 30px rgba(255, 68, 68, 0.8) !important;
    }
    
    .blue-turn {
        border-color: #00ffff !important;
        box-shadow: 0 0 30px rgba(0, 255, 255, 0.8) !important;
    }
    
    .victory-screen {
        background: linear-gradient(135deg, rgba(0, 255, 0, 0.2), rgba(0, 255, 255, 0.2));
        border: 3px solid #00ff00;
        text-align: center;
        padding: 3rem;
        border-radius: 20px;
        margin: 2rem 0;
    }
    
    .defeat-screen {
        background: linear-gradient(135deg, rgba(255, 0, 0, 0.2), rgba(255, 0, 128, 0.2));
        border: 3px solid #ff0000;
        text-align: center;
        padding: 3rem;
        border-radius: 20px;
        margin: 2rem 0;
    }
    
    /* Hide Streamlit elements */
    #MainMenu, footer, header {
        visibility: hidden;
    }
    </style>
    """, unsafe_allow_html=True)

def invoke_lambda(function_name, payload):
    """Invoke Lambda function"""
    try:
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        if 'body' in result:
            return json.loads(result['body'])
        return result
    except Exception as e:
        return {'error': str(e)}

def display_mission_briefing():
    """Display mission briefing with clean card buttons"""
    
    # Header
    st.markdown("""
    <div class="main-header">
        <div class="epic-title">⚔️ THE ENDER PROTOCOL ⚔️</div>
        <div class="epic-subtitle">SITH INFILTRATOR vs JEDI CO-PILOT</div>
        <div style="color: #00ffff; font-size: 1.3rem; font-weight: 600; margin: 1rem 0;">
            🏛️ JEDI ARCHIVES: TACTICAL TRAINING SIMULATION 🏛️
        </div>
        <div style="color: #ffaa00; font-size: 1rem; margin-top: 1rem;">
            ⚡ Powered by AWS Lambda • Amazon Bedrock • Amazon S3 ⚡
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Mission parameters
    st.markdown("""
    <div class="mission-parameters">
        <h2 style="color: #00ffff; font-size: 2rem; margin-bottom: 2rem;">⚡ MISSION PARAMETERS ⚡</h2>
        <div class="victory-conditions">
            <div>
                <h3 style="color: #00ff00; font-size: 1.3rem; margin-bottom: 1rem;">🔵 JEDI VICTORY</h3>
                <div style="color: #00ffff; font-size: 1.1rem;">Survive 10 turns without system breach</div>
            </div>
            <div>
                <h3 style="color: #ff4444; font-size: 1.3rem; margin-bottom: 1rem;">🔴 SITH VICTORY</h3>
                <div style="color: #ffaaaa; font-size: 1.1rem;">Achieve 3 successful breaches</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Mission cards as buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("""⚔️ MISSION I: BRUTE FORCE

THREAT:
Sith Infiltrator deploying credential attacks

DEFENSES:
• Force Barrier (Block IPs)
• Stasis Field (Lock Accounts)
• Battle Meditation (Monitor)

CLICK TO INITIATE MISSION""", key="mission1"):
            start_game('scenario_01_bruteforce')
    
    with col2:
        if st.button("""🛡️ MISSION II: SQL INJECTION

THREAT:
Database exploitation via code injection

CRITICAL DEFENSE:
• 🔧 PATCH SERVER (Priority!)
• Monitor database access
• Secure data repositories

CLICK TO INITIATE MISSION""", key="mission2"):
            start_game('scenario_02_sqlinjection')

def start_game(scenario_id):
    """Start a new game"""
    session_id = f"game-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"
    
    payload = {
        'session_id': session_id,
        'scenario_id': scenario_id
    }
    
    with st.spinner('🌌 Initializing tactical simulation... 🌌'):
        time.sleep(1)
        response = invoke_lambda('ender-protocol-SupervisorMockFunction-LCCbxTfvJcCa', payload)
    
    if 'error' not in response:
        st.session_state.game_active = True
        st.session_state.session_id = session_id
        st.session_state.game_state = response.get('game_state', {})
        st.session_state.choices = response.get('choices', [])
        st.session_state.current_turn = 'red'
        st.success("🎯 Mission initialized! Engaging enemy...")
        time.sleep(0.5)
        st.rerun()
    else:
        st.error(f"💥 Mission failed to initialize: {response['error']}")

def display_game_interface():
    """Display game interface"""
    
    # Game header
    st.markdown("""
    <div class="main-header">
        <div class="epic-title" style="font-size: 3rem;">⚔️ TACTICAL ENGAGEMENT ⚔️</div>
        <div class="epic-subtitle">BATTLE IN PROGRESS</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Game layout
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        # Status panel
        game_state = st.session_state.get('game_state', {})
        red_team = game_state.get('red_team', {})
        blue_team = game_state.get('blue_team', {})
        
        st.markdown("""
        <div class="status-panel">
            <h3 style="color: #00ffff; text-align: center; font-size: 1.4rem; margin-bottom: 1.5rem;">
                📊 TACTICAL STATUS
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Status metrics
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem;">
            <div style="color: #ff4444; font-size: 1.2rem; margin: 1rem 0; padding: 0.5rem; 
                        background: rgba(255, 68, 68, 0.1); border-radius: 8px;">
                🔴 Sith Breaches: <strong>{red_team.get('successes', 0)}</strong>
            </div>
            <div style="color: #00ffff; font-size: 1.2rem; margin: 1rem 0; padding: 0.5rem; 
                        background: rgba(0, 255, 255, 0.1); border-radius: 8px;">
                🔵 Jedi Defenses: <strong>{blue_team.get('blocks', 0)}</strong>
            </div>
            <div style="color: #ffaa00; font-size: 1.2rem; margin: 1rem 0; padding: 0.5rem; 
                        background: rgba(255, 170, 0, 0.1); border-radius: 8px;">
                ⏱️ Turn: <strong>{game_state.get('turn', 1)}</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Reset button
        if st.button("🔄 ABORT MISSION", key="reset"):
            for key in ['game_active', 'session_id', 'game_state', 'choices', 'current_turn']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    with col2:
        # Main game area
        game_state = st.session_state.get('game_state', {})
        status = game_state.get('status', 'active')
        
        if status in ['red_wins', 'blue_wins']:
            if status == 'blue_wins':
                st.markdown("""
                <div class="victory-screen">
                    <h1 style="color: #00ff00; font-size: 3.5rem; margin: 2rem 0;">
                        🏆 VICTORY! 🏆
                    </h1>
                    <div style="color: #00ffff; font-size: 1.6rem; line-height: 1.6;">
                        The Jedi Co-Pilot has defended the archives!<br>
                        The Sith Infiltrator has been repelled!<br><br>
                        <span style="color: #ffaa00;">The Force is strong with this one...</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="defeat-screen">
                    <h1 style="color: #ff0000; font-size: 3.5rem; margin: 2rem 0;">
                        💀 DEFEAT 💀
                    </h1>
                    <div style="color: #ffaaaa; font-size: 1.6rem; line-height: 1.6;">
                        The Sith Infiltrator has breached the archives!<br>
                        The mission has failed!<br><br>
                        <span style="color: #ff6666;">The dark side grows stronger...</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            # Active game
            turn_class = "red-turn" if st.session_state.get('current_turn') == 'red' else "blue-turn"
            
            st.markdown(f"""
            <div class="game-panel {turn_class}" style="display: flex; align-items: center; justify-content: center;">
                <div style="text-align: center;">
                    <h2 style="color: #00ffff; font-size: 2rem; margin-bottom: 2rem;">
                        🎯 COMMANDER, AWAITING YOUR ORDERS 🎯
                    </h2>
                    <div style="font-size: 1.2rem; color: #ffaa00; margin-top: 2rem;">
                        Select your tactical response below
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        # Mission log
        st.markdown("""
        <div class="status-panel">
            <h3 style="color: #00ffff; text-align: center; font-size: 1.4rem; margin-bottom: 1.5rem;">
                🏛️ MISSION HOLOCRON
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Simple log display
        game_state = st.session_state.get('game_state', {})
        
        # Show scenario
        scenario_id = game_state.get('scenario_id', '')
        if scenario_id == 'scenario_01_bruteforce':
            st.text("🚀 Mission I: Brute Force Active")
        elif scenario_id == 'scenario_02_sqlinjection':
            st.text("🚀 Mission II: SQL Injection Active")
        
        # Show recent actions
        red_team = game_state.get('red_team', {})
        if 'last_action' in red_team:
            action = red_team['last_action']
            if action.get('success'):
                st.text(f"🔴 SITH: {action.get('message', 'Attack successful')}")
                if 'access_level' in action:
                    st.text(f"   ⚠️ Access: {action['access_level']}")
            else:
                st.text(f"🔴 SITH FAILED: {action.get('message', 'Repelled')}")
        
        blue_team = game_state.get('blue_team', {})
        if 'last_action' in blue_team:
            action = blue_team['last_action']
            st.text(f"🔵 JEDI: {action.get('message', 'Defense executed')}")
    
    # Bottom row: Action buttons
    game_state = st.session_state.get('game_state', {})
    status = game_state.get('status', 'active')
    
    if status == 'active':
        choices = st.session_state.get('choices', [])
        if choices:
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Create columns for action buttons
            if len(choices) == 3:
                btn_col1, btn_col2, btn_col3 = st.columns(3)
                cols = [btn_col1, btn_col2, btn_col3]
            elif len(choices) == 2:
                btn_col1, btn_col2 = st.columns(2)
                cols = [btn_col1, btn_col2]
            else:
                cols = [st.container()]
            
            # Display action buttons
            for i, choice in enumerate(choices):
                with cols[i % len(cols)]:
                    if st.button(choice['label'], key=f"choice_{choice['action_id']}"):
                        execute_player_action(choice['action_id'])

def execute_player_action(action_id):
    """Execute player action"""
    payload = {
        'session_id': st.session_state.session_id,
        'player_action': action_id
    }
    
    with st.spinner('⚡ Executing maneuver... ⚡'):
        time.sleep(1)
        response = invoke_lambda('ender-protocol-SupervisorMockFunction-LCCbxTfvJcCa', payload)
    
    if 'error' not in response:
        st.session_state.game_state = response.get('game_state', {})
        st.session_state.choices = response.get('choices', [])
        st.session_state.current_turn = 'blue'
        st.success("🎯 Maneuver executed!")
        time.sleep(0.5)
        st.rerun()
    else:
        st.error(f"💥 Maneuver failed: {response['error']}")

def main():
    """Main application"""
    load_clean_css()
    
    if 'game_active' not in st.session_state:
        st.session_state.game_active = False
    
    if st.session_state.game_active:
        display_game_interface()
    else:
        display_mission_briefing()

if __name__ == "__main__":
    main()