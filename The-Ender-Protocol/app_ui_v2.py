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
    """Load custom CSS for Star Wars theme"""
    with open('style_v2.css', 'r') as f:
        css = f.read()
    st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)

def create_starfield():
    """Create animated starfield background"""
    starfield_html = """
    <div id="starfield">
        <div class="star" style="left: 10%; top: 20%; animation-delay: 0s;"></div>
        <div class="star" style="left: 20%; top: 80%; animation-delay: 1s;"></div>
        <div class="star" style="left: 30%; top: 40%; animation-delay: 2s;"></div>
        <div class="star" style="left: 40%; top: 90%; animation-delay: 0.5s;"></div>
        <div class="star" style="left: 50%; top: 10%; animation-delay: 1.5s;"></div>
        <div class="star" style="left: 60%; top: 70%; animation-delay: 2.5s;"></div>
        <div class="star" style="left: 70%; top: 30%; animation-delay: 0.8s;"></div>
        <div class="star" style="left: 80%; top: 60%; animation-delay: 1.8s;"></div>
        <div class="star" style="left: 90%; top: 15%; animation-delay: 2.2s;"></div>
    </div>
    
    <style>
    #starfield {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: -1;
    }
    
    .star {
        position: absolute;
        width: 2px;
        height: 2px;
        background: #ffffff;
        border-radius: 50%;
        animation: twinkle 3s ease-in-out infinite;
        box-shadow: 0 0 6px #ffffff;
    }
    
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
    """Display the initial mission briefing screen"""
    
    # Main title with epic styling
    st.markdown("""
    <div style="text-align: center; margin: 2rem 0;">
        <h1 class="stTitle">⚔️ THE ENDER PROTOCOL ⚔️</h1>
        <div class="subtitle">SITH INFILTRATOR vs JEDI CO-PILOT</div>
        <div style="color: #00ffff; font-size: 1.2rem; margin: 1rem 0; font-weight: 600;">
            🏛️ JEDI ARCHIVES: TACTICAL TRAINING SIMULATION 🏛️
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Create three-column layout
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Mission briefing container
        st.markdown("""
        <div class="center-panel hologram">
            <h2 style="text-align: center; color: #00ffff; font-size: 2rem; margin-bottom: 2rem;">
                📜 MISSION BRIEFING 📜
            </h2>
            
            <div style="background: rgba(0, 255, 255, 0.1); border: 1px solid #00ffff; border-radius: 10px; padding: 1.5rem; margin: 1rem 0;">
                <h3 style="color: #00ff00; margin-bottom: 1rem;">⚡ WIN CONDITIONS ⚡</h3>
                <div style="color: #00ffff; font-size: 1.1rem; line-height: 1.8;">
                    🔵 <strong>BLUE TEAM VICTORY:</strong> Survive 10 turns without system breach<br>
                    🔴 <strong>RED TEAM VICTORY:</strong> Achieve 3 successful breaches
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Scenario selection
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Create two columns for scenarios
        scen_col1, scen_col2 = st.columns(2)
        
        with scen_col1:
            st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(255, 0, 0, 0.2), rgba(255, 100, 0, 0.2)); 
                        border: 2px solid #ff4444; border-radius: 15px; padding: 1.5rem; height: 200px;">
                <h3 style="color: #ff4444; text-align: center; margin-bottom: 1rem;">
                    ⚔️ MISSION I: BRUTE FORCE
                </h3>
                <div style="color: #ffaaaa; font-size: 1rem; line-height: 1.6;">
                    <strong>THREAT:</strong> Sith Infiltrator attempts credential attacks<br><br>
                    <strong>DEFENSES:</strong><br>
                    • Block attacker IPs<br>
                    • Lockdown compromised accounts<br>
                    • Monitor attack patterns
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🚀 MISSION I: BRUTE FORCE ASSAULT", key="scenario1", help="Begin the credential attack simulation"):
                start_game('scenario_01_bruteforce')
        
        with scen_col2:
            st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(128, 0, 255, 0.2), rgba(255, 0, 128, 0.2)); 
                        border: 2px solid #8800ff; border-radius: 15px; padding: 1.5rem; height: 200px;">
                <h3 style="color: #8800ff; text-align: center; margin-bottom: 1rem;">
                    🛡️ MISSION II: SQL INJECTION BREACH
                </h3>
                <div style="color: #ccaaff; font-size: 1rem; line-height: 1.6;">
                    <strong>THREAT:</strong> Database exploitation via code injection<br><br>
                    <strong>KEY DEFENSE:</strong><br>
                    • 🔧 <strong>PATCH VULNERABLE SERVER</strong> (Critical!)<br>
                    • Monitor database access<br>
                    • Lockdown sensitive data
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🚀 MISSION II: SQL INJECTION BREACH", key="scenario2", help="Begin the database attack simulation"):
                start_game('scenario_02_sqlinjection')

def start_game(scenario_id):
    """Start a new game"""
    session_id = f"game-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"
    
    payload = {
        'session_id': session_id,
        'scenario_id': scenario_id
    }
    
    with st.spinner('🔄 Initializing tactical simulation...'):
        response = invoke_lambda('ender-protocol-SupervisorMockFunction-LCCbxTfvJcCa', payload)
    
    if 'error' not in response:
        st.session_state.game_active = True
        st.session_state.session_id = session_id
        st.session_state.game_state = response.get('game_state', {})
        st.session_state.choices = response.get('choices', [])
        st.session_state.current_turn = 'red'  # Red team goes first
        st.rerun()
    else:
        st.error(f"❌ Mission initialization failed: {response['error']}")

def display_game_interface():
    """Display the active game interface"""
    
    # Header
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 class="stTitle">⚔️ THE ENDER PROTOCOL ⚔️</h1>
        <div class="subtitle">TACTICAL ENGAGEMENT IN PROGRESS</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Create main game layout
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        # Game status panel
        game_state = st.session_state.get('game_state', {})
        
        st.markdown("""
        <div class="left-panel">
            <h3 style="color: #00ffff; text-align: center; margin-bottom: 1rem;">
                📊 TACTICAL STATUS
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Status metrics
        red_team = game_state.get('red_team', {})
        blue_team = game_state.get('blue_team', {})
        
        st.metric("🔴 Sith Breaches", red_team.get('successes', 0), delta=None)
        st.metric("🔵 Jedi Defenses", blue_team.get('blocks', 0), delta=None)
        st.metric("⏱️ Turn", game_state.get('turn', 1), delta=None)
        
        # Reset button
        if st.button("🔄 ABORT MISSION & RESET", key="reset"):
            for key in ['game_active', 'session_id', 'game_state', 'choices', 'current_turn']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    with col2:
        # Main game area
        game_state = st.session_state.get('game_state', {})
        status = game_state.get('status', 'active')
        
        # Check for game over
        if status in ['red_wins', 'blue_wins']:
            if status == 'blue_wins':
                st.markdown("""
                <div class="center-panel victory">
                    <h2 style="text-align: center; color: #00ff00; font-size: 3rem; margin: 2rem 0;">
                        🏆 VICTORY! 🏆
                    </h2>
                    <div style="text-align: center; color: #00ffff; font-size: 1.5rem;">
                        The Jedi Co-Pilot has successfully defended the archives!<br>
                        The Sith Infiltrator has been repelled!
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="center-panel defeat">
                    <h2 style="text-align: center; color: #ff0000; font-size: 3rem; margin: 2rem 0;">
                        💀 DEFEAT 💀
                    </h2>
                    <div style="text-align: center; color: #ffaaaa; font-size: 1.5rem;">
                        The Sith Infiltrator has breached the archives!<br>
                        The mission has failed!
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            # Active game interface
            turn_class = "red-turn" if st.session_state.get('current_turn') == 'red' else "blue-turn"
            
            st.markdown(f"""
            <div class="center-panel {turn_class}">
                <h2 style="text-align: center; color: #00ffff; margin-bottom: 2rem;">
                    🎯 COMMANDER, THE CO-PILOT AWAITS YOUR COMMAND 🎯
                </h2>
            </div>
            """, unsafe_allow_html=True)
            
            # Action buttons
            choices = st.session_state.get('choices', [])
            if choices:
                st.markdown("<div style='margin: 2rem 0;'>", unsafe_allow_html=True)
                
                for choice in choices:
                    if st.button(choice['label'], key=f"choice_{choice['action_id']}", help=f"Execute {choice['action_id']} protocol"):
                        execute_player_action(choice['action_id'])
                
                st.markdown("</div>", unsafe_allow_html=True)
    
    with col3:
        # Mission log
        st.markdown("""
        <div class="right-panel">
            <h3 style="color: #00ffff; text-align: center; margin-bottom: 1rem;">
                🏛️ MISSION HOLOCRON: TACTICAL READOUT 🏛️
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Display game log
        display_mission_log()

def display_mission_log():
    """Display the mission log with recent events"""
    game_state = st.session_state.get('game_state', {})
    
    log_entries = []
    
    # Add scenario start
    scenario_id = game_state.get('scenario_id', '')
    if scenario_id == 'scenario_01_bruteforce':
        log_entries.append("🚀 Starting scenario_01_bruteforce...")
    elif scenario_id == 'scenario_02_sqlinjection':
        log_entries.append("🚀 Starting scenario_02_sqlinjection...")
    
    # Add recent actions
    red_team = game_state.get('red_team', {})
    if 'last_action' in red_team:
        action = red_team['last_action']
        if action.get('success'):
            log_entries.append(f"🔴 RED TEAM: {action.get('message', 'Attack successful')}")
            if 'access_level' in action:
                log_entries.append(f"   ⚠️ Access Level: {action['access_level']}")
        else:
            log_entries.append(f"🔴 RED TEAM: {action.get('message', 'Attack failed')}")
    
    blue_team = game_state.get('blue_team', {})
    if 'last_action' in blue_team:
        action = blue_team['last_action']
        log_entries.append(f"🔵 YOU: {action.get('message', 'Defense executed')}")
    
    # Display in scrollable container
    log_html = "<div class='mission-log'>"
    for entry in log_entries[-10:]:  # Show last 10 entries
        log_html += f"<div style='margin: 0.5rem 0; padding: 0.5rem; background: rgba(0, 255, 255, 0.05); border-left: 3px solid #00ffff;'>{entry}</div>"
    log_html += "</div>"
    
    st.markdown(log_html, unsafe_allow_html=True)

def execute_player_action(action_id):
    """Execute a player action"""
    payload = {
        'session_id': st.session_state.session_id,
        'player_action': action_id
    }
    
    with st.spinner('🔄 Executing tactical maneuver...'):
        time.sleep(1)  # Add dramatic pause
        response = invoke_lambda('ender-protocol-SupervisorMockFunction-LCCbxTfvJcCa', payload)
    
    if 'error' not in response:
        st.session_state.game_state = response.get('game_state', {})
        st.session_state.choices = response.get('choices', [])
        st.session_state.current_turn = 'blue'  # Player's turn after action
        st.rerun()
    else:
        st.error(f"❌ Tactical maneuver failed: {response['error']}")

def main():
    """Main application"""
    # Load custom CSS
    load_css()
    
    # Create starfield background
    create_starfield()
    
    # Initialize session state
    if 'game_active' not in st.session_state:
        st.session_state.game_active = False
    
    # Display appropriate interface
    if st.session_state.game_active:
        display_game_interface()
    else:
        display_mission_briefing()

if __name__ == "__main__":
    main()