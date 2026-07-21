import streamlit as st
import boto3
import json
import uuid
from datetime import datetime
import time

# Page config for full-width layout
st.set_page_config(
    page_title="The Ender Protocol",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def load_css():
    """Load CSS with proper escaping"""
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
    
    * {
        margin: 0 !important;
        padding: 0 !important;
        box-sizing: border-box !important;
    }
    
    html, body, [class*="css"] {
        font-family: 'Orbitron', monospace !important;
        background: linear-gradient(135deg, #0a0a1a 0%, #1a0a2e 50%, #16213e 100%) !important;
        color: #00ffff !important;
        overflow-x: hidden !important;
    }
    
    .main .block-container {
        max-width: 100% !important;
        padding: 1rem !important;
        margin: 0 !important;
    }
    
    .main-header {
        background: linear-gradient(135deg, rgba(0, 0, 0, 0.9), rgba(0, 20, 40, 0.9));
        border: 3px solid #00ffff;
        border-radius: 20px;
        padding: 2rem !important;
        margin: 1rem 0 2rem 0 !important;
        text-align: center;
        box-shadow: 0 0 30px rgba(0, 255, 255, 0.5);
        position: relative;
        overflow: hidden;
    }
    
    .epic-title {
        font-family: 'Orbitron', monospace !important;
        font-weight: 900 !important;
        font-size: 3.5rem !important;
        background: linear-gradient(45deg, #00ffff, #ff0080, #00ffff) !important;
        background-size: 200% 200% !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        background-clip: text !important;
        animation: titleGlow 3s ease-in-out infinite !important;
        text-shadow: 0 0 30px rgba(0, 255, 255, 0.8) !important;
        margin: 1rem 0 !important;
        letter-spacing: 0.2em !important;
    }
    
    @keyframes titleGlow {
        0%, 100% { filter: drop-shadow(0 0 20px #00ffff); }
        50% { filter: drop-shadow(0 0 30px #ff0080); }
    }
    
    .epic-subtitle {
        color: #ff4444 !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        text-shadow: 0 0 10px #ff4444 !important;
        margin: 1rem 0 !important;
    }
    
    .mission-parameters {
        background: linear-gradient(135deg, rgba(0, 20, 40, 0.9), rgba(0, 40, 80, 0.9));
        border: 2px solid #00ffff;
        border-radius: 15px;
        padding: 2rem !important;
        margin: 2rem 0 !important;
        text-align: center;
    }
    
    .victory-conditions {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 2rem;
        margin-top: 2rem;
    }
    
    .stButton > button {
        width: 100% !important;
        height: 70px !important;
        background: linear-gradient(135deg, rgba(0, 255, 255, 0.1), rgba(0, 255, 255, 0.2)) !important;
        border: 2px solid #00ffff !important;
        border-radius: 10px !important;
        color: #00ffff !important;
        font-family: 'Orbitron', monospace !important;
        font-weight: 600 !important;
        font-size: 1.2rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        transition: all 0.3s ease !important;
        margin: 0.5rem 0 !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, rgba(0, 255, 255, 0.3), rgba(0, 255, 255, 0.4)) !important;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.6) !important;
        transform: translateY(-2px) !important;
        border-color: #ffffff !important;
    }
    
    .game-panel {
        background: linear-gradient(135deg, rgba(0, 10, 30, 0.95), rgba(0, 30, 60, 0.95));
        border: 3px solid #00ffff;
        border-radius: 20px;
        padding: 2rem !important;
        margin: 1rem 0 !important;
        min-height: 400px;
    }
    
    .status-panel {
        background: linear-gradient(135deg, rgba(0, 20, 40, 0.9), rgba(0, 40, 80, 0.9));
        border: 2px solid #00ffff;
        border-radius: 15px;
        padding: 1.5rem !important;
        margin: 1rem 0 !important;
    }
    
    .log-panel {
        background: rgba(0, 0, 0, 0.8);
        border: 2px solid #00ffff;
        border-radius: 15px;
        padding: 1.5rem !important;
        height: 400px;
        overflow-y: auto;
        font-family: 'Orbitron', monospace;
        font-size: 1.1rem;
        line-height: 1.6;
        margin: 1rem 0 !important;
    }
    
    .red-turn {
        border-color: #ff4444 !important;
        box-shadow: 0 0 30px rgba(255, 68, 68, 0.8) !important;
        animation: redPulse 2s ease-in-out infinite;
    }
    
    .blue-turn {
        border-color: #00ffff !important;
        box-shadow: 0 0 30px rgba(0, 255, 255, 0.8) !important;
        animation: bluePulse 2s ease-in-out infinite;
    }
    
    @keyframes redPulse {
        0%, 100% { box-shadow: 0 0 20px rgba(255, 68, 68, 0.6); }
        50% { box-shadow: 0 0 40px rgba(255, 68, 68, 1); }
    }
    
    @keyframes bluePulse {
        0%, 100% { box-shadow: 0 0 20px rgba(0, 255, 255, 0.6); }
        50% { box-shadow: 0 0 40px rgba(0, 255, 255, 1); }
    }
    
    .victory-screen {
        background: linear-gradient(135deg, rgba(0, 255, 0, 0.2), rgba(0, 255, 255, 0.2));
        border: 3px solid #00ff00;
        animation: victoryGlow 1s ease-in-out infinite;
        text-align: center;
        padding: 3rem !important;
        border-radius: 20px;
        margin: 2rem 0 !important;
    }
    
    .defeat-screen {
        background: linear-gradient(135deg, rgba(255, 0, 0, 0.2), rgba(255, 0, 128, 0.2));
        border: 3px solid #ff0000;
        animation: defeatGlow 1s ease-in-out infinite;
        text-align: center;
        padding: 3rem !important;
        border-radius: 20px;
        margin: 2rem 0 !important;
    }
    
    @keyframes victoryGlow {
        0%, 100% { box-shadow: 0 0 20px rgba(0, 255, 0, 0.8); }
        50% { box-shadow: 0 0 40px rgba(0, 255, 0, 1); }
    }
    
    @keyframes defeatGlow {
        0%, 100% { box-shadow: 0 0 20px rgba(255, 0, 0, 0.8); }
        50% { box-shadow: 0 0 40px rgba(255, 0, 0, 1); }
    }
    
    .css-1rs6os, .css-17ziqus, #MainMenu, footer, header {
        visibility: hidden !important;
        height: 0 !important;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def create_starfield():
    """Create animated starfield background"""
    starfield_html = """
    <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: -1;">
        <div style="position: absolute; left: 10%; top: 20%; width: 2px; height: 2px; background: #ffffff; border-radius: 50%; animation: twinkle 3s ease-in-out infinite; box-shadow: 0 0 6px #ffffff;"></div>
        <div style="position: absolute; left: 20%; top: 80%; width: 2px; height: 2px; background: #ffffff; border-radius: 50%; animation: twinkle 3s ease-in-out infinite 1s; box-shadow: 0 0 6px #ffffff;"></div>
        <div style="position: absolute; left: 30%; top: 40%; width: 2px; height: 2px; background: #ffffff; border-radius: 50%; animation: twinkle 3s ease-in-out infinite 2s; box-shadow: 0 0 6px #ffffff;"></div>
        <div style="position: absolute; left: 70%; top: 30%; width: 2px; height: 2px; background: #ffffff; border-radius: 50%; animation: twinkle 3s ease-in-out infinite 0.5s; box-shadow: 0 0 6px #ffffff;"></div>
        <div style="position: absolute; left: 80%; top: 60%; width: 2px; height: 2px; background: #ffffff; border-radius: 50%; animation: twinkle 3s ease-in-out infinite 1.5s; box-shadow: 0 0 6px #ffffff;"></div>
        <div style="position: absolute; left: 90%; top: 15%; width: 2px; height: 2px; background: #ffffff; border-radius: 50%; animation: twinkle 3s ease-in-out infinite 2.5s; box-shadow: 0 0 6px #ffffff;"></div>
    </div>
    
    <style>
    @keyframes twinkle {
        0%, 100% { opacity: 0.3; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.5); }
    }
    </style>
    """
    st.markdown(starfield_html, unsafe_allow_html=True)

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
    """Display the mission briefing screen"""
    
    create_starfield()
    
    # Epic header
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
    
    # Mission selection using clickable cards
    col1, col2 = st.columns(2)
    
    with col1:
        # Mission I Clickable Card
        if st.button("", key="mission1_card", help="Click to start Mission I: Brute Force"):
            start_game('scenario_01_bruteforce')
        
        # Use the button's container to style it as a card
        st.markdown("""
        <style>
        div[data-testid="stButton"]:has(button[kind="secondary"]) button {
            background: linear-gradient(135deg, rgba(40, 0, 0, 0.9), rgba(80, 0, 0, 0.9)) !important;
            border: 2px solid #ff4444 !important;
            border-radius: 15px !important;
            padding: 2rem !important;
            height: 300px !important;
            width: 100% !important;
            color: #ffaaaa !important;
            font-family: 'Orbitron', monospace !important;
            transition: all 0.3s ease !important;
            cursor: pointer !important;
        }
        
        div[data-testid="stButton"]:has(button[kind="secondary"]) button:hover {
            transform: translateY(-5px) scale(1.02) !important;
            box-shadow: 0 10px 30px rgba(255, 68, 68, 0.4), 0 0 40px rgba(255, 68, 68, 0.6) !important;
            border-color: #ffffff !important;
        }
        </style>
        
        <div style="position: relative; margin-top: -300px; pointer-events: none; z-index: 10;">
            <h3 style="color: #ff4444; text-align: center; font-size: 1.6rem; margin-bottom: 1.5rem; margin-top: 2rem;">
                ⚔️ MISSION I: BRUTE FORCE
            </h3>
            <div style="color: #ffaaaa; font-size: 1rem; line-height: 1.6; padding: 0 2rem;">
                <div style="margin-bottom: 1rem;">
                    <strong style="color: #ff6666;">THREAT:</strong><br>
                    Sith Infiltrator deploying credential attacks
                </div>
                <div>
                    <strong style="color: #ff6666;">DEFENSES:</strong><br>
                    • Force Barrier (Block IPs)<br>
                    • Stasis Field (Lock Accounts)<br>
                    • Battle Meditation (Monitor)
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Mission II Clickable Card
        if st.button("", key="mission2_card", help="Click to start Mission II: SQL Injection"):
            start_game('scenario_02_sqlinjection')
        
        st.markdown("""
        <style>
        div[data-testid="stButton"]:has(button[kind="secondary"]):nth-of-type(2) button {
            background: linear-gradient(135deg, rgba(20, 0, 40, 0.9), rgba(40, 0, 80, 0.9)) !important;
            border: 2px solid #8800ff !important;
            border-radius: 15px !important;
            padding: 2rem !important;
            height: 300px !important;
            width: 100% !important;
            color: #ccaaff !important;
            font-family: 'Orbitron', monospace !important;
            transition: all 0.3s ease !important;
            cursor: pointer !important;
        }
        
        div[data-testid="stButton"]:has(button[kind="secondary"]):nth-of-type(2) button:hover {
            transform: translateY(-5px) scale(1.02) !important;
            box-shadow: 0 10px 30px rgba(136, 0, 255, 0.4), 0 0 40px rgba(136, 0, 255, 0.6) !important;
            border-color: #ffffff !important;
        }
        </style>
        
        <div style="position: relative; margin-top: -300px; pointer-events: none; z-index: 10;">
            <h3 style="color: #8800ff; text-align: center; font-size: 1.6rem; margin-bottom: 1.5rem; margin-top: 2rem;">
                🛡️ MISSION II: SQL INJECTION
            </h3>
            <div style="color: #ccaaff; font-size: 1rem; line-height: 1.6; padding: 0 2rem;">
                <div style="margin-bottom: 1rem;">
                    <strong style="color: #aa66ff;">THREAT:</strong><br>
                    Database exploitation via code injection
                </div>
                <div>
                    <strong style="color: #aa66ff;">CRITICAL DEFENSE:</strong><br>
                    • 🔧 <strong>PATCH SERVER</strong> (Priority!)<br>
                    • Monitor database access<br>
                    • Secure data repositories
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

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
    """Display the game interface"""
    
    create_starfield()
    
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
        if st.button("🔄 ABORT MISSION", key="reset", help="Emergency abort"):
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
            <div class="game-panel {turn_class}">
                <h2 style="text-align: center; color: #00ffff; font-size: 1.8rem; margin-bottom: 2rem;">
                    🎯 COMMANDER, AWAITING YOUR ORDERS 🎯
                </h2>
            </div>
            """, unsafe_allow_html=True)
            
            # Action buttons
            choices = st.session_state.get('choices', [])
            if choices:
                for choice in choices:
                    if st.button(choice['label'], key=f"choice_{choice['action_id']}", help=f"Execute {choice['action_id']}"):
                        execute_player_action(choice['action_id'])
    
    with col3:
        # Mission log
        st.markdown("""
        <div class="status-panel">
            <h3 style="color: #00ffff; text-align: center; font-size: 1.4rem; margin-bottom: 1.5rem;">
                🏛️ MISSION HOLOCRON
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        display_mission_log()

def display_mission_log():
    """Display mission log"""
    game_state = st.session_state.get('game_state', {})
    
    log_entries = []
    
    # Scenario info
    scenario_id = game_state.get('scenario_id', '')
    if scenario_id == 'scenario_01_bruteforce':
        log_entries.append("🚀 Mission I: Brute Force Active")
    elif scenario_id == 'scenario_02_sqlinjection':
        log_entries.append("🚀 Mission II: SQL Injection Active")
    
    # Recent actions
    red_team = game_state.get('red_team', {})
    if 'last_action' in red_team:
        action = red_team['last_action']
        if action.get('success'):
            log_entries.append(f"🔴 SITH: {action.get('message', 'Attack successful')}")
            if 'access_level' in action:
                log_entries.append(f"   ⚠️ Access: {action['access_level']}")
        else:
            log_entries.append(f"🔴 SITH FAILED: {action.get('message', 'Repelled')}")
    
    blue_team = game_state.get('blue_team', {})
    if 'last_action' in blue_team:
        action = blue_team['last_action']
        log_entries.append(f"🔵 JEDI: {action.get('message', 'Defense executed')}")
    
    # Display log
    log_html = '<div class="log-panel">'
    for entry in log_entries[-6:]:
        log_html += f"""
        <div style="margin: 1rem 0; padding: 1rem; 
                    background: linear-gradient(90deg, rgba(0, 255, 255, 0.1), rgba(0, 255, 255, 0.05)); 
                    border-left: 3px solid #00ffff; border-radius: 5px;">
            {entry}
        </div>
        """
    log_html += '</div>'
    
    st.markdown(log_html, unsafe_allow_html=True)

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
    load_css()
    
    if 'game_active' not in st.session_state:
        st.session_state.game_active = False
    
    if st.session_state.game_active:
        display_game_interface()
    else:
        display_mission_briefing()

if __name__ == "__main__":
    main()