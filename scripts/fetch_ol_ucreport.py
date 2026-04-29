import requests
import time
import os
import pandas as pd

from recruit_sources import normalize_name

ROOT_DIR    = os.path.join(os.path.dirname(__file__), "..")
INPUT_PATH  = os.path.join(ROOT_DIR, "data/draft/ol_wikipedia_picks.csv")
OUTPUT_PATH = os.path.join(ROOT_DIR, "data/draft/ol_ucreport_data.csv")

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

COL_NAMES = [
    "player_id", "class_field", "college_level_projection", "uc_score", "last", "first",
    "effective_school_name", "college_enrolled", "school_city", "state", "county",
    "position_played", "position_projected", "height", "weight", "wingspan",
    "forty", "shuttle", "vertical", "track60m", "track100m", "track200m", "broad",
    "trackLJ", "highJump", "trackSP", "discus", "updated", "head_coach",
    "player_head_shot", "camp_event_videos", "hudl_video_link", "college_offers",
    "commit", "max_speed_video",
]

SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}


def split_name(full_name):
    parts = str(full_name).strip().split()
    if len(parts) < 2:
        return full_name, ""
    if parts[-1].lower() in SUFFIXES and len(parts) >= 3:
        return " ".join(parts[:-2]), parts[-2]
    return " ".join(parts[:-1]), parts[-1]


def expected_class_years(draft_year):
    """Players spend 3-5 years in college, so HS class is 3-5 years before draft year."""
    return set(range(draft_year - 5, draft_year - 2))  # e.g. 2022 → {2017, 2018, 2019}


def fetch_by_name(first_name, last_name):
    payload = {
        "last":  {"value": last_name.lower()},
        "first": {"value": first_name.lower()[:5]},  # partial first to handle nicknames
        "col_names": COL_NAMES,
        "page_size": 200,
    }
    resp = session.post("https://ucreport.us/database/get_players", json=payload)
    if resp.status_code != 200:
        return []
    data = resp.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("content", data.get("results", []))
    return []


picks = pd.read_csv(INPUT_PATH)
print(f"Loaded {len(picks)} OL picks from {INPUT_PATH}")

all_results = []

for _, row in picks.iterrows():
    # Strip Wikipedia footnote markers (†, *, [a], etc.)
    player_name = str(row["player"]).strip()
    player_name = player_name.replace("†", "").replace("*", "").split("[")[0].strip()
    draft_year  = int(row["year"])
    first, last = split_name(player_name)
    if not last:
        print(f"  Skipping malformed name: {player_name}")
        continue

    valid_classes = expected_class_years(draft_year)
    print(f"Fetching UCReport: {first} {last} (draft {draft_year}, class {min(valid_classes)}-{max(valid_classes)})...")

    candidates = fetch_by_name(first, last)

    # Filter: first-name match AND class_field strictly within expected window
    matched = []
    for p in candidates:
        if not isinstance(p, dict):
            continue
        api_first = normalize_name(p.get("first", ""))
        first_match = any(part in api_first for part in normalize_name(first).split())
        if not first_match:
            continue

        try:
            player_class = int(str(p.get("class_field", "")).strip())
        except (ValueError, TypeError):
            continue  # skip entries with no parseable class year

        if player_class in valid_classes and player_class <= 2022:
            matched.append(p)

    if matched:
        best = matched[0]
        best["query_name"]   = player_name
        best["wiki_year"]    = draft_year
        best["wiki_round"]   = row["round"]
        best["wiki_pick"]    = row["pick"]
        best["wiki_team"]    = row["team"]
        best["wiki_pos"]     = row["pos"]
        best["wiki_college"] = row["college"]
        all_results.append(best)
        print(f"  -> Found (ID: {best.get('player_id')}, class {best.get('class_field')})")
    else:
        print(f"  -> Not found.")

    time.sleep(0.5)

print(f"\nFound {len(all_results)} / {len(picks)} players.")

if all_results:
    df = pd.DataFrame(all_results)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved to {OUTPUT_PATH}")
