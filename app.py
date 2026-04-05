import streamlit as st
import pandas as pd
import requests
import gspread
from google.oauth2.service_account import Credentials

# --- 1. CONFIG & TIERS ---
st.set_page_config(page_title="MSBA Masters Pool 2026", layout="wide")

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

SHEET_ID = "1JuPu9bQG3tSNPvPb8DikqSTvZK4GxNoZPKSB6qvTs28"

# --- 2. GOOGLE SHEETS CONNECTION ---
@st.cache_resource
def get_sheet():
    import json
    creds_dict = json.loads(st.secrets["gcp_service_account_json"])
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet("Picks")

def get_db():
    try:
        sheet = get_sheet()
        data = sheet.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame(columns=["Name", "PIN", "T1", "T2", "T3", "T4", "T5", "T6"])
    except:
        return pd.DataFrame(columns=["Name", "PIN", "T1", "T2", "T3", "T4", "T5", "T6"])

def save_db(df):
    sheet = get_sheet()
    sheet.clear()
    sheet.update([df.columns.tolist()] + df.values.tolist())

# --- 3. LIVE DATA ENGINE ---
@st.cache_data(ttl=300)
def get_live_data():
    url = "https://www.masters.com/en_US/scores/feeds/2026/scores.json"
    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        is_started = any(p.get('thru') not in [None, '', '0', '-', 'Not Started'] for p in data['player'])
        players = {}
        for p in data['player']:
            name = p.get('full_name')
            score_str = str(p.get('topar', '0'))
            if score_str == 'E': val = 0
            elif "cut" in score_str.lower() or p.get('status') in ['C', 'W', 'WD']: val = 80
            else:
                try: val = int(score_str)
                except: val = 0
            players[name] = val
        return players, is_started
    except:
        all_names = [n for t in TIERS.values() for n in t]
        return {name: 0 for name in all_names}, False

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
            db = get_db()
            if not db.empty and not db[(db['Name'] == l_name) & (db['PIN'].astype(str) == str(l_pin))].empty:
                st.session_state.auth, st.session_state.user = True, l_name
                st.rerun()
            else: st.error("Invalid Name or PIN.")
    with col2:
        st.write("### New Entry")
        s_name = st.text_input("Full Name")
        s_pin = st.text_input("4-Digit PIN", type="password", max_chars=4)
        if st.button("Sign Up"):
            if s_name and s_pin:
                db = get_db()
                if not db.empty and s_name in db['Name'].values: st.error("Name taken.")
                else:
                    st.session_state.auth, st.session_state.user, st.session_state.new_pin = True, s_name, str(s_pin)
                    st.rerun()
    st.stop()

# --- 5. LOGGED IN UI ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Leaderboard", "Select / Manage Team"])
if st.sidebar.button("Logout"):
    st.session_state.auth, st.session_state.user = False, None
    st.rerun()

with st.container():
    st.markdown("### 📝 Rules\n**Best 4 of 6 count.** Tiebreaker: Best individual score. **Cuts/WD = 80.**")
st.write("---")

# --- 6. LEADERBOARD ---
if page == "Leaderboard":
    st.header("🏆 Live Leaderboard")
    db = get_db()
    if not tournament_started:
        st.info("Tournament hasn't started. Showing entries.")
        if not db.empty: st.table(db[['Name']].rename(columns={'Name': 'Confirmed Entrants'}))
    else:
        results = []
        if not db.empty:
            for _, row in db.iterrows():
                picks = [row['T1'], row['T2'], row['T3'], row['T4'], row['T5'], row['T6']]
                player_data = sorted([(live_map.get(p, 0), p) for p in picks])
                best_4_total = sum(d[0] for d in player_data[:4])
                score_cells = []
                for i, (score, name) in enumerate(player_data):
                    fmt = f"{score:+}" if score != 0 else "E"
                    if i >= 4: score_cells.append(f'<span style="color: #A9A9A9;">{name} ({fmt})</span>')
                    else: score_cells.append(f"<b>{name} ({fmt})</b>" if i == 0 else f"{name} ({fmt})")
                results.append({"Team Name": f"<b>{row['Name']}</b>", "Cumulative": f"<b>{best_4_total:+}</b>", "Players": " | ".join(score_cells), "sort_key": (best_4_total, *[d[0] for d in player_data])})
            leaderboard_df = pd.DataFrame(results).sort_values("sort_key")
            st.write(leaderboard_df[['Team Name', 'Cumulative', 'Players']].to_html(escape=False, index=False), unsafe_allow_html=True)

# --- 7. SELECT / MANAGE TEAM ---
else:
    st.header("🏌️ Select / Manage Team")
    db = get_db()
    if tournament_started:
        st.error("🔒 Entries locked.")
        u_picks = db[db['Name'] == st.session_state.user].iloc[0]
        for i in range(1, 7): st.write(f"**Tier {i}:** {u_picks[f'T{i}']}")
    else:
        existing = db[db['Name'] == st.session_state.user].iloc[0] if (not db.empty and st.session_state.user in db['Name'].values) else None
        with st.form("team_selection"):
            picks = []
            for i in range(1, 7):
                t_key = f"Tier {i}"
                idx = TIERS[t_key].index(existing[f'T{i}']) if existing is not None else 0
                picks.append(st.radio(f"### {t_key}", TIERS[t_key], index=idx))
            if st.form_submit_button("Lock in My Team"):
                current_db = get_db()
                pin = existing['PIN'] if existing is not None else st.session_state.get('new_pin', '0000')
                new_row = pd.DataFrame([[st.session_state.user, str(pin)] + picks],
                                       columns=["Name", "PIN", "T1", "T2", "T3", "T4", "T5", "T6"])
                if not current_db.empty:
                    current_db = current_db[current_db['Name'] != st.session_state.user]
                updated_db = pd.concat([current_db, new_row], ignore_index=True)
                save_db(updated_db)
                st.success("Team saved!")
                st.cache_data.clear()
                st.rerun()
