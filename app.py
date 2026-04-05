import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime

# --- 1. CONFIG & TIERS ---
st.set_page_config(page_title="MSBA Masters Pool 2026", layout="wide")

# Transcribed exactly from your screenshots
TIERS = {
    "Tier 1": ["Scottie Scheffler", "Rory McIlroy", "Bryson DeChambeau", "Jon Rahm", "Ludvig Aberg", "Tommy Fleetwood", "Xander Schauffele", "Collin Morikawa", "Cameron Young", "Matt Fitzpatrick"],
    "Tier 2": ["Justin Rose", "Patrick Reed", "Chris Gotterup", "Hideki Matsuyama", "Viktor Hovland", "Brooks Koepka", "Robert MacIntyre", "Justin Thomas", "Tyrrell Hatton", "Jordan Spieth"],
    "Tier 3": ["Shane Lowry", "Patrick Cantlay", "Ben Griffin", "Akshay Bhatia", "Si Woo Kim", "Jake Knapp", "Corey Conners", "Russell Henley", "Min Woo Lee", "Jason Day"],
    "Tier 4": ["Adam Scott", "Max Homa", "Cameron Smith", "Sepp Straka", "Sam Burns", "Daniel Berger", "Marco Penge", "Gary Woodland", "Sungjae Im", "Wyndham Clark"],
    "Tier 5": ["J.J. Spaun", "Jacob Bridgeman", "Harris English", "Dustin Johnson", "Alexander Noren", "Matthew McCarty", "Sergio Garcia", "Maverick McNealy", "Ryan Gerard", "Keegan Bradley"],
    "Tier 6": [
        "Kurt Kitayama", "Nicolai Hojgaard", "Ryan Fox", "Aaron Rai", "Harry Hall", "John Keefer", 
        "Rasmus Neergaard-Petersen", "Tom McKibbin", "Sam Stevens", "Brian Harman", "Rasmus Hojgaard", 
        "Carlos Ortiz", "Nicolas Echavarria", "Andrew Novak", "Michael Kim", "Casey Jarvis", 
        "Aldrich Potgieter", "Max Greyserman", "Nick Taylor", "Hao-Tong Li", "Bubba Watson", 
        "Kristoffer Reitan", "Sami Valimaki", "Davis Riley", "Charl Schwartzel", "Michael Brennan", 
        "Brian Campbell", "Zach Johnson", "Angel Cabrera", "Danny Willett", "Fred Couples", 
        "Mike Weir", "Vijay Singh", "Jose Maria Olazabal", "Naoyuki Kataoka", "Brandon Holtz", 
        "Ethan Fang", "Fifa Laopakdee", "Jackson Herrington", "Mason Howell", "Mateo Pulcini",
        "WITHDRAWN - Phil Mickelson"
    ]
}

DB_FILE = "users_db.csv"
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=["Name", "PIN", "T1", "T2", "T3", "T4", "T5", "T6"]).to_csv(DB_FILE, index=False)

# --- 2. LIVE DATA & AUTO-START CHECK ---
@st.cache_data(ttl=300) # Updates every 5 minutes
def get_live_data():
    url = "https://www.masters.com/en_US/scores/feeds/2026/scores.json"
    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        
        # AUTOMATION: Check if any player has teed off
        is_started = any(p.get('thru') not in [None, '', '0', '-', 'Not Started'] for p in data['player'])
        
        players = {}
        for p in data['player']:
            name = p.get('full_name')
            score_str = str(p.get('topar', '0'))
            
            if score_str == 'E': val = 0
            elif "cut" in score_str.lower() or p.get('status') in ['C', 'W', 'WD']: 
                val = 80 # Penalty for Cut/WD
            else:
                try: val = int(score_str)
                except: val = 0
            players[name] = val
        return players, is_started
    except:
        # Fallback if feed isn't live yet
        all_names = [n for t in TIERS.values() for n in t]
        return {name: 0 for name in all_names}, False

# --- 3. SESSION STATE & NAVIGATION ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'user' not in st.session_state: st.session_state.user = None

live_map, tournament_started = get_live_data()


# --- 4. ENTRANCE GATE ---
if not st.session_state.auth:
    st.title("⛳️ MSBA Masters Pool 470511")
    col1, col2 = st.columns(2)
    with col1:
        st.write("### Login")
        l_name = st.text_input("Name")
        l_pin = st.text_input("PIN", type="password")
        if st.button("Login"):
            db = pd.read_csv(DB_FILE)
            if not db[(db['Name'] == l_name) & (db['PIN'].astype(str) == l_pin)].empty:
                st.session_state.auth, st.session_state.user = True, l_name
                st.rerun()
    with col2:
        st.write("### New Entry")
        s_name = st.text_input("Full Name")
        s_pin = st.text_input("4-Digit PIN", type="password", max_chars=4)
        if st.button("Sign Up"):
            if s_name and s_pin:
                db = pd.read_csv(DB_FILE)
                if s_name in db['Name'].values: st.error("Name taken.")
                else:
                    st.session_state.auth, st.session_state.user, st.session_state.new_pin = True, s_name, s_pin
                    st.rerun()
    st.stop()

# --- 5. LOGGED IN UI ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Leaderboard", "Select / Manage Team"])
if st.sidebar.button("Logout"):
    st.session_state.auth, st.session_state.user = False, None
    st.rerun()

# RULES AT THE TOP
with st.container():
    st.markdown("""
    ### 📝 Rules
    **Best 4 of 6 scores count.** Lowest total wins. 
    **Tiebreaker:** Best individual score on team, then 2nd best, etc.
    **Cuts:** Anyone who misses the cut or withdraws is assigned a score of **80**.
    """)
st.write("---")

# --- 6. WINDOW: LEADERBOARD ---
if page == "Leaderboard":
    st.header("🏆 Live Leaderboard")
    db = pd.read_csv(DB_FILE)
    
    if not tournament_started:
        st.info("Tournament has not started. Showing confirmed participants.")
        st.table(db[['Name']].rename(columns={'Name': 'Confirmed Entrants'}))
    else:
        results = []
        for _, row in db.iterrows():
            picks = [row['T1'], row['T2'], row['T3'], row['T4'], row['T5'], row['T6']]
            # Sort scores to identify Best 4 and Tiebreakers
            # Data format: (score, name)
            player_data = sorted([(live_map.get(p, 0), p) for p in picks])
            
            best_4_total = sum(d[0] for d in player_data[:4])
            
            # Formatting the grey-out logic
            score_cells = []
            for i, (score, name) in enumerate(player_data):
                fmt_score = f"{score:+}" if score != 0 else "E"
                if i >= 4: # Worst two scores
                    score_cells.append(f'<span style="color: #A9A9A9;">{name} ({fmt_score})</span>')
                else:
                    score_cells.append(f"<b>{name} ({fmt_score})</b>" if i == 0 else f"{name} ({fmt_score})")
            
            results.append({
                "Team Name": f"<b>{row['Name']}</b>",
                "Cumulative": f"<b>{best_4_total:+}</b>" if best_4_total != 0 else "<b>E</b>",
                "Players (Best 4 Bolded / Worst 2 Greyed)": " | ".join(score_cells),
                "sort_key": (best_4_total, *[d[0] for d in player_data])
            })
        
        leaderboard_df = pd.DataFrame(results).sort_values("sort_key")
        st.write(leaderboard_df[['Team Name', 'Cumulative', 'Players (Best 4 Bolded / Worst 2 Greyed)']].to_html(escape=False, index=False), unsafe_allow_html=True)

# --- 7. WINDOW: SELECT / MANAGE TEAM ---
else:
    st.header("🏌️ Select / Manage Team")
    if tournament_started:
        st.error("🔒 Entries are locked. The tournament has started.")
        # Display their current team as read-only
        db = pd.read_csv(DB_FILE)
        u_picks = db[db['Name'] == st.session_state.user].iloc[0]
        for i in range(1, 7): st.write(f"**Tier {i}:** {u_picks[f'T{i}']}")
    else:
        st.success("🔓 Edits are open until the first tee ball is hit.")
        db = pd.read_csv(DB_FILE)
        existing = db[db['Name'] == st.session_state.user].iloc[0] if st.session_state.user in db['Name'].values else None
        
        with st.form("team_selection"):
            picks = []
            for i in range(1, 7):
                t_key = f"Tier {i}"
                idx = TIERS[t_key].index(existing[f'T{i}']) if existing is not None else 0
                picks.append(st.radio(f"### {t_key}", TIERS[t_key], index=idx))
            
            if st.form_submit_button("Lock in My Team"):
                db = db[db['Name'] != st.session_state.user] # Remove old
                pin = existing['PIN'] if existing is not None else st.session_state.get('new_pin', '0000')
                db.loc[len(db)] = [st.session_state.user, pin] + picks
                db.to_csv(DB_FILE, index=False)
                st.success("Team saved successfully!")
                st.rerun()
