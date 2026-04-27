import requests
import json
import pandas as pd
import time

missing_queries = [
    {"first": "gavin", "last": "williams", "query_name": "Gavin Williams"},
    {"first": "honor", "last": "johnson", "query_name": "Honor Fa’alave-Johnson"},
    {"first": "ta", "last": "poole", "query_name": "Ta’Shawn Poole"},
    {"first": "junior", "last": "tu", "query_name": "Junior Tu’upo"},
    {"first": "greedy", "last": "james", "query_name": "Greedy James"},
    {"first": "semaj", "last": "stanford", "query_name": "Semaj Stanford"}
]

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

for mq in missing_queries:
    payload = {
        "last": {"value": mq['last'].lower()},
        "first": {"value": mq['first'].lower()},
        "col_names": col_names,
        "page_size": 10
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
            
        if players_data:
            best_match = players_data[0]
            best_match['query_name'] = mq['query_name']
            all_scraped_data.append(best_match)
            print(f"Found {best_match['first']} {best_match['last']} for {mq['query_name']}")
        else:
            print(f"Still couldn't find {mq['query_name']}")
    else:
        print(f"Error fetching {mq['query_name']}: {response.status_code}")
        
    time.sleep(0.5)

if all_scraped_data:
    try:
        existing_df = pd.read_csv("ucreport_data.csv")
        new_df = pd.DataFrame(all_scraped_data)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df.to_csv("ucreport_data.csv", index=False)
        print(f"Successfully appended {len(all_scraped_data)} players to ucreport_data.csv. Total rows: {len(combined_df)}")
    except Exception as e:
        print(f"Error appending: {e}")
