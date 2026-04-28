import requests
import json
import time
import pandas as pd

from recruit_sources import (
    UCREPORT_PATH,
    attach_board_fields,
    load_recruit_board,
    normalize_name,
)

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
            if not isinstance(p, dict):
                continue
            # handle cases like "Kevin “KJ”" matching "Kevin"
            api_first = normalize_name(p.get('first', ''))
            query_first_parts = normalize_name(first_name).split()
            
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
recruit_board = load_recruit_board()

print(f"Starting scrape for {len(recruit_board)} players from 2027_recruits.csv...")
for _, board_row in recruit_board.iterrows():
    player_name = board_row["query_name"]
    first_name = board_row["query_first"]
    last_name = board_row["query_last"]
    if not first_name or not last_name:
        print(f"Skipping malformed name: {player_name}")
        continue
        
    print(f"Fetching: {first_name} {last_name}...")
    matched_players = fetch_player(first_name, last_name)
    
    if matched_players:
        # Take the most recently updated one if there are multiple matches
        # or just the first one
        best_match = matched_players[0]
        attach_board_fields(best_match, board_row)
        all_scraped_data.append(best_match)
        print(f"  -> Found! (ID: {best_match.get('player_id')})")
    else:
        print(f"  -> Not found.")
        
    time.sleep(0.5) # Be polite to the API

print(f"\nScraping complete. Found {len(all_scraped_data)} out of {len(recruit_board)} players.")

if all_scraped_data:
    df = pd.DataFrame(all_scraped_data)
    df.to_csv(UCREPORT_PATH, index=False)
    print(f"Saved data to {UCREPORT_PATH}")
