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
    # Combine both CSS files
    css_content = ""
    try:
        with open('style_v2.css', 'r') as f:
            css_content += f.read()
    except:
        pass
    
    try:
        with open('enhanced_effects.css', 'r') as f:
            css_content += f.read()
    except:
        pass
    
    # Add inline CSS for immediate effects
    css_content += """
    /* Immediate visual enhancements */
    .main-header {
        background: linear-gradient(135deg, rgba(0, 0, 0, 0.9), rgba(0, 20, 40, 0.9));
        border: 3px solid #00ffff;
        border-radius: 20px;
        padding: 2rem;
        margin: 2rem 0;
        text-align: center;
        box-shadow: 
            0 0 30px rgba(0, 255, 255, 0.5),
            inset 0 0 30px rgba(0, 255, 255, 0.1);
        position: relative;
        overflow: hidden;
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: -2px;
        left: -2px;
        right: -2px;
        bottom: -2px;
        background: linear-gradient(45deg, #00ffff, #ff0080, #00ffff, #ff0080);
        background-size: 400% 400%;
        border-radius: 20px;
        z-index: -1;
        animation: borderGlow 3s ease-in-out infinite;
    }
    
    .epic-title {
        font-family: 'Orbitron', monospace;
        font-weight: 900;
        font-size: 4rem;
        background: linear-gradient(45deg, #00ffff, #ff0080, #00ffff);
        background-size: 200% 200%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: titleGlow 3s ease-in-out infinite, gradientShift 4s ease-in-out infinite;
        text-shadow: 0 0 30px rgba(0, 255, 255, 0.8);
        margin: 1rem 0;
        letter-spacing: 0.2em;
    }
    
    .epic-subtitle {
        color: #ff4444;
        font-size: 1.5rem;
        font-weight: 700;
        text-shadow: 0 0 10px #ff4444;
        animation: redPulse 2s ease-in-out infinite;
        margin: 1rem 0;
    }
    
    .mission-card {
        background: linear-gradient(135deg, rgba(0, 20, 40, 0.9), rgba(0, 40, 80, 0.9));
        border: 2px solid #00ffff;
        border-radius: 15px;
        padding: 2rem;
        margin: 1rem;
        height: 300px;
        position: relative;
        overflow: hidden;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .mission-card:hover {
        transform: translateY(-10px) scale(1.02);
        box-shadow: 
            0 20px 40px rgba(0, 255, 255, 0.3),
            0 0 50px rgba(0, 255, 255, 0.5);
        border-color: #ffffff;
    }
    
    .clickable-card {
        cursor: pointer;
        pointer-events: auto !important;
    }
    
    /* Hide default streamlit button styling */
    .stButton > button {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        height: 0 !important;
        width: 0 !important;
        opacity: 0 !important;
    }
    
    /* Ensure single page layout */
    .main .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-height: 100vh !important;
        overflow: hidden !important;
    }
    
    /* Fixed height containers */
    .single-page-container {
        height: calc(100vh - 2rem);
        overflow: hidden;
        display: flex;
        flex-direction: column;
    }
    
    .mission-card.red {
        border-color: #ff4444;
        background: linear-gradient(135deg, rgba(40, 0, 0, 0.9), rgba(80, 0, 0, 0.9));
    }
    
    .mission-card.red:hover {
        box-shadow: 
            0 20px 40px rgba(255, 68, 68, 0.3),
            0 0 50px rgba(255, 68, 68, 0.5);
    }
    
    .mission-card.purple {
        border-color: #8800ff;
        background: linear-gradient(135deg, rgba(20, 0, 40, 0.9), rgba(40, 0, 80, 0.9));
    }
    
    .mission-card.purple:hover {
        box-shadow: 
            0 20px 40px rgba(136, 0, 255, 0.3),
            0 0 50px rgba(136, 0, 255, 0.5);
    }
    
    .game-panel {
        background: linear-gradient(135deg, rgba(0, 10, 30, 0.95), rgba(0, 30, 60, 0.95));
        border: 3px solid #00ffff;
        border-radius: 20px;
        padding: 2rem;
        margin: 1rem 0;
        position: relative;
        overflow: hidden;
        min-height: 500px;
    }
    
    .status-panel {
        background: linear-gradient(135deg, rgba(0, 20, 40, 0.9), rgba(0, 40, 80, 0.9));
        border: 2px solid #00ffff;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    .log-panel {
        background: rgba(0, 0, 0, 0.8);
        border: 2px solid #00ffff;
        border-radius: 15px;
        padding: 1.5rem;
        height: 400px;
        overflow-y: auto;
        font-family: 'Rajdhani', monospace;
        font-size: 1.1rem;
        line-height: 1.6;
    }
    
    .action-button {
        width: 100%;
        height: 70px;
        background: linear-gradient(135deg, rgba(0, 255, 255, 0.1), rgba(0, 255, 255, 0.2));
        border: 2px solid #00ffff;
        border-radius: 10px;
        color: #00ffff;
        font-family: 'Orbitron', monospace;
        font-weight: 600;
        font-size: 1.2rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin: 0.5rem 0;
        cursor: pointer;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .action-button:hover {
        background: linear-gradient(135deg, rgba(0, 255, 255, 0.3), rgba(0, 255, 255, 0.4));
        box-shadow: 
            0 0 20px rgba(0, 255, 255, 0.6),
            inset 0 0 20px rgba(0, 255, 255, 0.2);
        transform: translateY(-2px);
        border-color: #ffffff;
    }
    
    .victory-screen {
        background: linear-gradient(135deg, rgba(0, 255, 0, 0.2), rgba(0, 255, 255, 0.2));
        border: 3px solid #00ff00;
        animation: victoryGlow 1s ease-in-out infinite;
        text-align: center;
        padding: 3rem;
        border-radius: 20px;
    }
    
    .defeat-screen {
        background: linear-gradient(135deg, rgba(255, 0, 0, 0.2), rgba(255, 0, 128, 0.2));
        border: 3px solid #ff0000;
        animation: defeatGlow 1s ease-in-out infinite;
        text-align: center;
        padding: 3rem;
        border-radius: 20px;
    }
    """
    
    st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)

def create_particles():
    """Create floating particle effects"""
    particles_html = """
    <div class="particles">
        <div class="particle" style="left: 10%; animation-delay: 0s;"></div>
        <div class="particle" style="left: 20%; animation-delay: 1s;"></div>
        <div class="particle" style="left: 30%; animation-delay: 2s;"></div>
        <div class="particle" style="left: 40%; animation-delay: 3s;"></div>
        <div class="particle" style="left: 50%; animation-delay: 4s;"></div>
        <div class="particle" style="left: 60%; animation-delay: 5s;"></div>
        <div class="particle" style="left: 70%; animation-delay: 1.5s;"></div>
        <div class="particle" style="left: 80%; animation-delay: 2.5s;"></div>
        <div class="particle" style="left: 90%; animation-delay: 3.5s;"></div>
    </div>
    """
    st.markdown(particles_html, unsafe_allow_html=True)

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
    """Display the epic mission briefing screen"""
    
    # Create particles
    create_particles()
    
    # Single page container
    st.markdown('<div class="single-page-container">', unsafe_allow_html=True)
    
    # Compact header
    st.markdown("""
    <div style="text-align: center; margin: 0.5rem 0;">
        <div class="epic-title" style="font-size: 2.8rem; margin: 0.3rem 0;">THE ENDER PROTOCOL</div>
        <div class="epic-subtitle" style="font-size: 1.1rem;">SITH INFILTRATOR vs JEDI CO-PILOT</div>
        <div style="color: #ffaa00; font-size: 0.8rem; margin: 0.3rem 0;">
            Powered by AWS Lambda • Amazon Bedrock • Amazon S3
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Single row layout with win conditions and missions
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        # Win conditions
        st.markdown("""
        <div class="mission-card" style="height: 350px;">
            <h3 style="color: #00ffff; text-align: center; font-size: 1.5rem; margin-bottom: 1rem;">
                MISSION PARAMETERS
            </h3>
            <div style="margin-bottom: 2rem;">
                <h4 style="color: #00ff00; font-size: 1.2rem; margin-bottom: 0.5rem;">JEDI VICTORY</h4>
                <div style="color: #00ffff; font-size: 1rem;">Survive 10 turns without system breach</div>
            </div>
            <div>
                <h4 style="color: #ff4444; font-size: 1.2rem; margin-bottom: 0.5rem;">SITH VICTORY</h4>
                <div style="color: #ffaaaa; font-size: 1rem;">Achieve 3 successful breaches</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Mission I - Clickable card
        if st.button("", key="scenario1_card", help="Begin Mission I"):
            start_game('scenario_01_bruteforce')
        
        st.markdown("""
        <div class="mission-card red lightsaber-glow scanlines clickable-card" style="height: 350px; margin-top: -58px; pointer-events: none;">
            <h3 style="color: #ff4444; text-align: center; font-size: 1.4rem; margin-bottom: 1rem;">
                MISSION I: BRUTE FORCE ASSAULT
            </h3>
            <div style="color: #ffaaaa; font-size: 1rem; line-height: 1.6;">
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
            <div style="position: absolute; bottom: 1rem; left: 50%; transform: translateX(-50%); color: #ffffff; font-weight: bold;">
                CLICK TO INITIATE
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Mission II - Clickable card
        if st.button("", key="scenario2_card", help="Begin Mission II"):
            start_game('scenario_02_sqlinjection')
        
        st.markdown("""
        <div class="mission-card purple lightsaber-glow scanlines clickable-card" style="height: 350px; margin-top: -58px; pointer-events: none;">
            <h3 style="color: #8800ff; text-align: center; font-size: 1.4rem; margin-bottom: 1rem;">
                MISSION II: SQL INJECTION BREACH
            </h3>
            <div style="color: #ccaaff; font-size: 1rem; line-height: 1.6;">
                <div style="margin-bottom: 1rem;">
                    <strong style="color: #aa66ff;">THREAT:</strong><br>
                    Database exploitation via code injection
                </div>
                <div>
                    <strong style="color: #aa66ff;">CRITICAL DEFENSE:</strong><br>
                    • PATCH VULNERABLE SERVER<br>
                    • Monitor database access<br>
                    • Secure data repositories
                </div>
            </div>
            <div style="position: absolute; bottom: 1rem; left: 50%; transform: translateX(-50%); color: #ffffff; font-weight: bold;">
                CLICK TO INITIATE
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Close container
    st.markdown('</div>', unsafe_allow_html=True)

def start_game(scenario_id):
    """Start a new game with epic loading"""
    session_id = f"game-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"
    
    payload = {
        'session_id': session_id,
        'scenario_id': scenario_id
    }
    
    # Epic loading message
    with st.spinner('🌌 Initializing hyperspace tactical simulation... 🌌'):
        time.sleep(2)  # Dramatic pause
        response = invoke_lambda('ender-protocol-SupervisorMockFunction-LCCbxTfvJcCa', payload)
    
    if 'error' not in response:
        st.session_state.game_active = True
        st.session_state.session_id = session_id
        st.session_state.game_state = response.get('game_state', {})
        st.session_state.choices = response.get('choices', [])
        st.session_state.current_turn = 'red'
        st.success("🎯 Tactical simulation initialized! The battle begins...")
        time.sleep(1)
        st.rerun()
    else:
        st.error(f"💥 Mission initialization failed: {response['error']}")

def display_game_interface():
    """Display the epic game interface"""
    
    # Create particles
    create_particles()
    
    # Single page container
    st.markdown('<div class="single-page-container">', unsafe_allow_html=True)
    
    # Compact game header
    st.markdown("""
    <div style="text-align: center; margin: 0.3rem 0;">
        <div class="epic-title" style="font-size: 2.2rem; margin: 0;">TACTICAL ENGAGEMENT</div>
        <div class="epic-subtitle" style="font-size: 0.9rem;">BATTLE IN PROGRESS</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Single row layout
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        # Status panel
        game_state = st.session_state.get('game_state', {})
        red_team = game_state.get('red_team', {})
        blue_team = game_state.get('blue_team', {})
        
        st.markdown(f"""
        <div class="status-panel energy-shield" style="height: 400px;">
            <h3 style="color: #00ffff; text-align: center; font-size: 1.3rem; margin-bottom: 1rem;">
                TACTICAL STATUS
            </h3>
            <div style="text-align: center; margin: 2rem 0;">
                <div style="color: #ff4444; font-size: 1.2rem; margin: 1rem 0;">
                    Sith Breaches: <strong>{red_team.get('successes', 0)}</strong>
                </div>
                <div style="color: #00ffff; font-size: 1.2rem; margin: 1rem 0;">
                    Jedi Defenses: <strong>{blue_team.get('blocks', 0)}</strong>
                </div>
                <div style="color: #ffaa00; font-size: 1.2rem; margin: 1rem 0;">
                    Turn: <strong>{game_state.get('turn', 1)}</strong>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Reset button
        if st.button("ABORT MISSION", key="reset", help="Emergency mission abort"):
            for key in ['game_active', 'session_id', 'game_state', 'choices', 'current_turn']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    with col2:
        # Main game panel
        game_state = st.session_state.get('game_state', {})
        status = game_state.get('status', 'active')
        
        if status in ['red_wins', 'blue_wins']:
            if status == 'blue_wins':
                st.markdown("""
                <div class="victory-screen hologram-flicker" style="height: 400px; display: flex; flex-direction: column; justify-content: center;">
                    <h1 style="color: #00ff00; font-size: 3rem; margin: 1rem 0;">
                        VICTORY ACHIEVED!
                    </h1>
                    <div style="color: #00ffff; font-size: 1.4rem; line-height: 1.6;">
                        The Jedi Co-Pilot has successfully defended the archives!<br>
                        The Sith Infiltrator has been repelled!<br><br>
                        <span style="color: #ffaa00;">The Force is strong with this one...</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="defeat-screen glitch" style="height: 400px; display: flex; flex-direction: column; justify-content: center;">
                    <h1 style="color: #ff0000; font-size: 3rem; margin: 1rem 0;">
                        MISSION FAILED
                    </h1>
                    <div style="color: #ffaaaa; font-size: 1.4rem; line-height: 1.6;">
                        The Sith Infiltrator has breached the archives!<br>
                        The Republic systems have fallen!<br><br>
                        <span style="color: #ff6666;">The dark side grows stronger...</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            # Active game with turn results
            turn_class = "red-turn" if st.session_state.get('current_turn') == 'red' else "blue-turn"
            
            # Display turn results
            turn_results = get_turn_results()
            
            st.markdown(f"""
            <div class="game-panel {turn_class} trench-run" style="height: 400px;">
                <h2 style="text-align: center; color: #00ffff; font-size: 1.5rem; margin-bottom: 1rem;">
                    COMMANDER, THE CO-PILOT AWAITS YOUR COMMAND
                </h2>
                <div style="background: rgba(0, 0, 0, 0.6); border: 1px solid #00ffff; border-radius: 10px; padding: 1rem; margin: 1rem 0; min-height: 120px;">
                    {turn_results}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Action buttons as clickable cards
            choices = st.session_state.get('choices', [])
            if choices:
                for i, choice in enumerate(choices):
                    if st.button("", key=f"choice_btn_{choice['action_id']}", help=f"Execute {choice['action_id']} protocol"):
                        execute_player_action(choice['action_id'])
                    
                    # Clean up the label text
                    clean_label = choice['label'].replace('🛡️', '').replace('🔍', '').replace('🔒', '').replace('🔧', '').strip()
                    
                    st.markdown(f"""
                    <div class="action-button hyperspace" style="margin-top: -58px; pointer-events: none; height: 50px; display: flex; align-items: center; justify-content: center; font-size: 1rem;">
                        {clean_label}
                    </div>
                    """, unsafe_allow_html=True)
    
    with col3:
        # Mission log
        st.markdown("""
        <div class="status-panel" style="height: 400px;">
            <h3 style="color: #00ffff; text-align: center; font-size: 1.3rem; margin-bottom: 1rem;">
                MISSION HOLOCRON
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        display_mission_log()
    
    # Close container
    st.markdown('</div>', unsafe_allow_html=True)

def get_turn_results():
    """Get formatted turn results for display"""
    game_state = st.session_state.get('game_state', {})
    
    if not game_state:
        return "<div style='color: #00ffff; text-align: center; padding: 2rem;'>Initializing tactical systems...</div>"
    
    results = []
    
    # Recent Sith action
    red_team = game_state.get('red_team', {})
    if 'last_action' in red_team:
        action = red_team['last_action']
        if action.get('success'):
            results.append(f"<div style='color: #ff4444; margin: 0.5rem 0;'><strong>SITH ATTACK:</strong> {action.get('message', 'Attack successful')}</div>")
            if 'access_level' in action:
                results.append(f"<div style='color: #ffaa00; margin: 0.5rem 0; padding-left: 1rem;'>Access Level: {action['access_level']}</div>")
        else:
            results.append(f"<div style='color: #ff8888; margin: 0.5rem 0;'><strong>SITH FAILED:</strong> {action.get('message', 'Attack repelled')}</div>")
    
    # Recent Jedi response
    blue_team = game_state.get('blue_team', {})
    if 'last_action' in blue_team:
        action = blue_team['last_action']
        results.append(f"<div style='color: #00ffff; margin: 0.5rem 0;'><strong>JEDI RESPONSE:</strong> {action.get('message', 'Defense executed')}</div>")
    
    if not results:
        scenario_id = game_state.get('scenario_id', '')
        if scenario_id == 'scenario_01_bruteforce':
            results.append("<div style='color: #00ffff; text-align: center;'>Mission I: Brute Force Assault initiated</div>")
        elif scenario_id == 'scenario_02_sqlinjection':
            results.append("<div style='color: #8800ff; text-align: center;'>Mission II: SQL Injection Breach initiated</div>")
    
    return "".join(results) if results else "<div style='color: #00ffff; text-align: center;'>Awaiting tactical data...</div>"

def display_mission_log():
    """Display compact mission log"""
    game_state = st.session_state.get('game_state', {})
    
    log_entries = []
    
    # Scenario info
    scenario_id = game_state.get('scenario_id', '')
    if scenario_id == 'scenario_01_bruteforce':
        log_entries.append("<span style='color: #00ffff;'>Mission I: Brute Force</span>")
    elif scenario_id == 'scenario_02_sqlinjection':
        log_entries.append("<span style='color: #8800ff;'>Mission II: SQL Injection</span>")
    
    # Turn summary
    turn = game_state.get('turn', 1)
    red_successes = game_state.get('red_team', {}).get('successes', 0)
    log_entries.append(f"<span style='color: #ffaa00;'>Turn {turn} | Breaches: {red_successes}/3</span>")
    
    # Recent events (last 4)
    red_team = game_state.get('red_team', {})
    if 'last_action' in red_team:
        action = red_team['last_action']
        status = "SUCCESS" if action.get('success') else "FAILED"
        color = "#ff4444" if action.get('success') else "#ff8888"
        log_entries.append(f"<span style='color: {color};'>Sith: {status}</span>")
    
    blue_team = game_state.get('blue_team', {})
    if 'last_action' in blue_team:
        log_entries.append("<span style='color: #00ffff;'>Jedi: Defense Active</span>")
    
    # Display compact log
    log_html = f'<div style="height: 320px; overflow-y: auto; padding: 1rem; background: rgba(0, 0, 0, 0.6); border-radius: 10px;">'
    for entry in log_entries[-6:]:
        log_html += f"""
        <div style="margin: 0.8rem 0; padding: 0.8rem; 
                    background: rgba(0, 255, 255, 0.05); 
                    border-left: 2px solid #00ffff; border-radius: 3px; 
                    font-size: 1rem;">
            {entry}
        </div>
        """
    log_html += '</div>'
    
    st.markdown(log_html, unsafe_allow_html=True)

def execute_player_action(action_id):
    """Execute player action with epic effects"""
    payload = {
        'session_id': st.session_state.session_id,
        'player_action': action_id
    }
    
    with st.spinner('⚡ Executing tactical maneuver through the Force... ⚡'):
        time.sleep(1.5)  # Dramatic pause
        response = invoke_lambda('ender-protocol-SupervisorMockFunction-LCCbxTfvJcCa', payload)
    
    if 'error' not in response:
        st.session_state.game_state = response.get('game_state', {})
        st.session_state.choices = response.get('choices', [])
        st.session_state.current_turn = 'blue'
        st.success("🎯 Tactical maneuver executed successfully!")
        time.sleep(0.5)
        st.rerun()
    else:
        st.error(f"💥 Tactical maneuver failed: {response['error']}")

def main():
    """Main application with epic styling"""
    # Load all CSS
    load_css()
    
    # Initialize session state
    if 'game_active' not in st.session_state:
        st.session_state.game_active = False
    
    # Display interface
    if st.session_state.game_active:
        display_game_interface()
    else:
        display_mission_briefing()

if __name__ == "__main__":
    main()