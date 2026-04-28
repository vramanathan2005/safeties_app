import requests
import pandas as pd
import time

from recruit_sources import (
    UCREPORT_PATH,
    attach_board_fields,
    extract_player_rows,
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
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "x-csrftoken": "TPwxt7v2mFUyUWWdL7WynvkChRYdgC2K1xwiLcKSnWxhK4gh3pilnXXFTSE4YRnL",
})
session.cookies.update({"sessionid": "xqy7lkm7ztv1ar6b7nqifinoebhhu19t"})

col_names = [
    "player_id","class_field","college_level_projection","uc_score","last","first","effective_school_name",
    "college_enrolled","school_city","state","county","position_played","position_projected","height",
    "weight","wingspan","forty","shuttle","vertical","track60m","track100m","track200m","broad",
    "trackLJ","highJump","trackSP","discus","updated","head_coach","player_head_shot","camp_event_videos",
    "hudl_video_link","college_offers","commit","max_speed_video"
]

all_scraped_data = []

existing_df = pd.read_csv(UCREPORT_PATH) if UCREPORT_PATH.exists() else pd.DataFrame()
if "source_recruit_id" in existing_df.columns:
    existing_keys = set(existing_df["source_recruit_id"].dropna().astype(str))
else:
    existing_keys = set()

if "query_name" in existing_df.columns:
    existing_names = {normalize_name(v) for v in existing_df["query_name"].dropna()}
else:
    existing_names = {
        normalize_name(f"{row.get('first', '')} {row.get('last', '')}")
        for _, row in existing_df.iterrows()
    }

recruit_board = load_recruit_board()
missing_board_rows = []
for _, board_row in recruit_board.iterrows():
    recruit_id = str(board_row.get("recruit_id"))
    name_key = normalize_name(board_row["query_name"])
    if recruit_id not in existing_keys and name_key not in existing_names:
        missing_board_rows.append(board_row)

print(f"Found {len(missing_board_rows)} board players missing from {UCREPORT_PATH}.")

for board_row in missing_board_rows:
    payload = {
        "last": {"value": board_row["query_last"].lower()},
        "first": {"value": board_row["query_first"].lower()},
        "col_names": col_names,
        "page_size": 10
    }
    
    response = session.post(
        "https://ucreport.us/database/get_players",
        json=payload,
        timeout=20,
    )
    if response.status_code == 200:
        data = response.json()
        players_data = extract_player_rows(data)
            
        if players_data:
            best_match = players_data[0]
            attach_board_fields(best_match, board_row)
            all_scraped_data.append(best_match)
            print(f"Found {best_match['first']} {best_match['last']} for {board_row['query_name']}")
        else:
            print(f"Still couldn't find {board_row['query_name']}")
    else:
        print(f"Error fetching {board_row['query_name']}: {response.status_code}")
        
    time.sleep(0.5)

if all_scraped_data:
    try:
        new_df = pd.DataFrame(all_scraped_data)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df.to_csv(UCREPORT_PATH, index=False)
        print(f"Successfully appended {len(all_scraped_data)} players to {UCREPORT_PATH}. Total rows: {len(combined_df)}")
    except Exception as e:
        print(f"Error appending: {e}")
