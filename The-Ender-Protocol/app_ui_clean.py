import streamlit as st
import boto3
import json
import uuid
from datetime import datetime
import time

st.set_page_config(
    page_title="The Ender Protocol",
    page_icon="⚔️",
    layout="wide"
)

def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Orbitron', monospace !important;
        background: linear-gradient(135deg, #0a0a1a 0%, #1a0a2e 50%, #16213e 100%) !important;
        color: #00ffff !important;
    }
    
    .main .block-container {
        max-width: 100% !important;
        padding: 1rem !important;
    }
    
    .stButton > button {
        width: 100% !important;
        font-family: 'Orbitron', monospace !important;
        background: linear-gradient(135deg, rgba(0, 255, 255, 0.1), rgba(0, 255, 255, 0.2)) !important;
        border: 2px solid #00ffff !important;
        color: #00ffff !important;
        border-radius: 10px !important;
        padding: 1rem !important;
    }
    
    .mission-card {
        background: linear-gradient(135deg, rgba(0, 20, 40, 0.9), rgba(0, 40, 80, 0.9));
        border: 2px solid #00ffff;
        border-radius: 15px;
        padding: 2rem;
        margin: 1rem 0;
        text-align: center;
    }
    
    #MainMenu, footer, header {
        visibility: hidden;
    }
    </style>
    """, unsafe_allow_html=True)

def invoke_lambda(function_name, payload):
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

# Initialize session state
if 'game_active' not in st.session_state:
    st.session_state.game_active = False
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'game_state' not in st.session_state:
    st.session_state.game_state = {}
if 'choices' not in st.session_state:
    st.session_state.choices = []

# Load CSS
load_css()

# Main title
st.markdown("# ⚔️ THE ENDER PROTOCOL")
st.markdown("### SITH INFILTRATOR vs JEDI CO-PILOT")

def display_mission_briefing():
    st.markdown("## 🏛️ JEDI ARCHIVES: TACTICAL TRAINING")
    
    st.markdown("""
    <div class="mission-card">
        <h3 style="color: #00ffff;">⚡ MISSION PARAMETERS ⚡</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; margin-top: 2rem;">
            <div>
                <h4 style="color: #00ff00;">🔵 JEDI VICTORY</h4>
                <div>Survive 10 turns</div>
            </div>
            <div>
                <h4 style="color: #ff4444;">🔴 SITH VICTORY</h4>
                <div>3 successful breaches</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="mission-card">
            <h3 style="color: #ff4444;">⚔️ MISSION I: BRUTE FORCE</h3>
            <p style="color: #ffaaaa;">
                <strong>THREAT:</strong> Credential attacks<br>
                <strong>DEFENSES:</strong> Block IPs, Lock Accounts
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 INITIATE MISSION I"):
            start_game('scenario_01_bruteforce')
    
    with col2:
        st.markdown("""
        <div class="mission-card">
            <h3 style="color: #8800ff;">🛡️ MISSION II: SQL INJECTION</h3>
            <p style="color: #ccaaff;">
                <strong>THREAT:</strong> Database exploitation<br>
                <strong>DEFENSES:</strong> Patch Server, Monitor DB
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 INITIATE MISSION II"):
            start_game('scenario_02_sqlinjection')

def start_game(scenario_id):
    session_id = f"game-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"
    
    payload = {
        'session_id': session_id,
        'scenario_id': scenario_id
    }
    
    with st.spinner('🌌 Initializing mission...'):
        time.sleep(1)
        response = invoke_lambda('ender-protocol-SupervisorMockFunction-LCCbxTfvJcCa', payload)
    
    if 'error' not in response:
        st.session_state.game_active = True
        st.session_state.session_id = session_id
        st.session_state.game_state = response.get('game_state', {})
        st.session_state.choices = response.get('choices', [])
        st.success("🎯 Mission initialized!")
        time.sleep(0.5)
        st.rerun()
    else:
        st.error(f"💥 Mission failed: {response['error']}")

def display_game_interface():
    game_state = st.session_state.get('game_state', {})
    status = game_state.get('status', 'active')
    
    st.markdown("## ⚔️ TACTICAL ENGAGEMENT")
    
    if status == 'active':
        st.markdown("### 🎯 AWAITING ORDERS")
        st.markdown("Select your tactical response below")
    
    # Mission log
    st.markdown("### 🏛️ MISSION LOG")
    
    scenario_id = game_state.get('scenario_id', '')
    if scenario_id == 'scenario_01_bruteforce':
        st.text("🚀 Mission I: Brute Force - Active")
    elif scenario_id == 'scenario_02_sqlinjection':
        st.text("🚀 Mission II: SQL Injection - Active")
    
    # Recent actions
    red_team = game_state.get('red_team', {})
    if 'last_action' in red_team:
        action = red_team['last_action']
        if action.get('success'):
            st.text(f"🔴 SITH: {action.get('message', 'Attack successful')}")
        else:
            st.text(f"🔴 SITH FAILED: {action.get('message', 'Repelled')}")
    
    blue_team = game_state.get('blue_team', {})
    if 'last_action' in blue_team:
        action = blue_team['last_action']
        st.text(f"🔵 JEDI: {action.get('message', 'Defense executed')}")
    
    # Action buttons
    if status == 'active':
        choices = st.session_state.get('choices', [])
        if choices:
            st.markdown("### ⚔️ TACTICAL OPTIONS")
            
            for choice in choices:
                if st.button(choice['label'], key=f"choice_{choice['action_id']}"):
                    execute_player_action(choice['action_id'])
    
    # Victory/Defeat screens
    if status in ['red_wins', 'blue_wins']:
        if status == 'blue_wins':
            st.success("🏆 VICTORY! The Jedi Co-Pilot has defended the archives!")
        else:
            st.error("💀 DEFEAT! The Sith Infiltrator has breached the archives!")
    
    # Reset button
    if st.button("🔄 ABORT MISSION"):
        for key in ['game_active', 'session_id', 'game_state', 'choices']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

def execute_player_action(action_id):
    payload = {
        'session_id': st.session_state.session_id,
        'player_action': action_id
    }
    
    with st.spinner('⚡ Executing maneuver...'):
        time.sleep(1)
        response = invoke_lambda('ender-protocol-SupervisorMockFunction-LCCbxTfvJcCa', payload)
    
    if 'error' not in response:
        st.session_state.game_state = response.get('game_state', {})
        st.session_state.choices = response.get('choices', [])
        st.success("🎯 Maneuver executed!")
        time.sleep(0.5)
        st.rerun()
    else:
        st.error(f"💥 Maneuver failed: {response['error']}")

# Main application logic
if st.session_state.game_active:
    display_game_interface()
else:
    display_mission_briefing()