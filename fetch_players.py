import requests
import json
import time
import pandas as pd

players_list = [
    "Danny Lang", "Braylon Deal", "JayQuan Snell", "Eli Johnson", "Adryan Cole",
    "Isala Wily-Ava", "Omarii Sanders", "Gavin Williams", "Jamarquis Hudson", "Isaiah Udom",
    "Aiden Evans", "Peyton Shaw", "Elijajuan Houston", "Chance Gilbert", "Jeremiah Proctor",
    "Myles Baker", "Mikyal Davis", "Honor Fa’alave-Johnson", "Greedy James", "Jayden Aparicio-Bailey",
    "Dillon Davis", "James Roberson", "Kamarui Dorsey", "Semai Stanford", "Jaylen Scott",
    "Aaryn Washington", "Davontrae Kirkland", "Bode Sparrow", "Tory Pittman III", "Malakai Taufoou",
    "Khalil Terry", "Ta’Shawn Poole", "Jaylyn Jones", "Davion Jones", "Corey Hadley Jr.",
    "Kevin “KJ” Caldwell Jr.", "Karon Eugene", "Jernard Albright", "Alex Scott", "Tavon Bolden",
    "Junior Tu’upo", "Quincy Carter", "Braiden Graves", "Kailib Dillard", "Hakim Frampton",
    "Aiden Martin", "Jaiden ‘JJ’ Fields", "Joshua Vilmael", "Pole Moala", "Jeovanni Henley"
]

session = requests.Session()
session.headers.update({
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "origin": "https://ucreport.us",
    "referer": "https://ucreport.us/dashboard/",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "x-csrftoken": "TPwxt7v2mFUyUWWdL7WynvkChRYdgC2K1xwiLcKSnWxhK4gh3pilnXXFTSE4YRnL",
})

session.cookies.update({
    "sessionid": "xqy7lkm7ztv1ar6b7nqifinoebhhu19t",
})

col_names = [
    "player_id","class_field","college_level_projection","uc_score","last","first","effective_school_name",
    "college_enrolled","school_city","state","county","position_played","position_projected","height",
    "weight","wingspan","forty","shuttle","vertical","track60m","track100m","track200m","broad",
    "trackLJ","highJump","trackSP","discus","updated","head_coach","player_head_shot","camp_event_videos",
    "hudl_video_link","college_offers","commit","max_speed_video"
]

results = []

def fetch_player(first_name, last_name):
    payload = {
        "last": {"value": last_name.lower()},
        "col_names": col_names,
        "page_size": 200
    }
    
    response = session.post("https://ucreport.us/database/get_players", json=payload)
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list):
            players_data = data
        elif isinstance(data, dict):
            players_data = data.get('content', data.get('results', []))
        else:
            players_data = []
        
        # We need to filter based on first name since the API just searches last name
        matched = []
        for p in players_data:
            # handle cases like "Kevin “KJ”" matching "Kevin"
            api_first = p.get('first', '').lower()
            query_first_parts = first_name.lower().replace('“', '').replace('”', '').replace('‘', '').replace('’', '').split()
            
            # If any part of the requested first name is in the API first name, consider it a match
            for part in query_first_parts:
                if part in api_first:
                    matched.append(p)
                    break
                    
        return matched
    else:
        print(f"Error fetching {first_name} {last_name}: {response.status_code}")
        return []

all_scraped_data = []

print(f"Starting scrape for {len(players_list)} players...")
for player_name in players_list:
    parts = player_name.split()
    if len(parts) >= 2:
        # Simple split, might need refining for "Jr." or multi-word last names
        # e.g. "Corey Hadley Jr." -> First: Corey, Last: Hadley Jr.
        if parts[-1].lower() in ['jr.', 'jr', 'iii', 'ii']:
            last_name = parts[-2]
            first_name = " ".join(parts[:-2])
        else:
            last_name = parts[-1]
            first_name = " ".join(parts[:-1])
    else:
        continue
        
    print(f"Fetching: {first_name} {last_name}...")
    matched_players = fetch_player(first_name, last_name)
    
    if matched_players:
        # Take the most recently updated one if there are multiple matches
        # or just the first one
        best_match = matched_players[0]
        # Add the original query name for reference
        best_match['query_name'] = player_name
        all_scraped_data.append(best_match)
        print(f"  -> Found! (ID: {best_match.get('player_id')})")
    else:
        print(f"  -> Not found.")
        
    time.sleep(0.5) # Be polite to the API

print(f"\nScraping complete. Found {len(all_scraped_data)} out of {len(players_list)} players.")

if all_scraped_data:
    df = pd.DataFrame(all_scraped_data)
    output_file = "ucreport_data.csv"
    df.to_csv(output_file, index=False)
    print(f"Saved data to {output_file}")
