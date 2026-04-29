import requests
import pandas as pd
import time
import os

from recruit_sources import normalize_name, extract_player_rows

ROOT_DIR    = os.path.join(os.path.dirname(__file__), "..")
WIKI_PATH   = os.path.join(ROOT_DIR, "data/draft/ol_wikipedia_picks.csv")
OUTPUT_PATH = os.path.join(ROOT_DIR, "data/draft/ol_ucreport_data.csv")

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
    return set(range(draft_year - 5, draft_year - 2))


# Load existing UCReport data and build set of already-fetched names
if os.path.exists(OUTPUT_PATH):
    existing_df = pd.read_csv(OUTPUT_PATH)
    existing_names = {normalize_name(v) for v in existing_df["query_name"].dropna()}
else:
    existing_df = pd.DataFrame()
    existing_names = set()

print(f"Already have {len(existing_df)} players in {OUTPUT_PATH}.")

# Find picks not yet in the UCReport data
wiki_df = pd.read_csv(WIKI_PATH)
missing_rows = [
    row for _, row in wiki_df.iterrows()
    if normalize_name(str(row["player"])) not in existing_names
]
print(f"Found {len(missing_rows)} players missing from UCReport data.\n")

newly_found = []

for row in missing_rows:
    player_name = str(row["player"]).strip()
    player_name = player_name.replace("†", "").replace("*", "").split("[")[0].strip()
    draft_year  = int(row["year"])
    first, last = split_name(player_name)
    if not last:
        print(f"Skipping malformed name: {player_name}")
        continue

    valid_classes = expected_class_years(draft_year)
    print(f"Searching: {first} {last} (draft {draft_year}, class {min(valid_classes)}-{max(valid_classes)})...")

    payload = {
        "last":  {"value": last.lower()},
        "first": {"value": first.lower()[:5]},  # partial first to handle nicknames
        "col_names": COL_NAMES,
        "page_size": 200,
    }

    try:
        resp = session.post(
            "https://ucreport.us/database/get_players",
            json=payload,
            timeout=20,
        )
        if resp.status_code != 200:
            print(f"  -> Error {resp.status_code}")
            time.sleep(1)
            continue

        candidates = extract_player_rows(resp.json())

        matched = []
        for p in candidates:
            if not isinstance(p, dict):
                continue
            api_first = normalize_name(p.get("first", ""))
            if not any(part in api_first for part in normalize_name(first).split()):
                continue
            try:
                player_class = int(str(p.get("class_field", "")).strip())
            except (ValueError, TypeError):
                continue
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
            newly_found.append(best)
            print(f"  -> Found (ID: {best.get('player_id')}, class {best.get('class_field')})")
        else:
            print(f"  -> Not found.")

    except Exception as e:
        print(f"  -> Exception: {e}")

    time.sleep(0.5)

print(f"\nFound {len(newly_found)} new players.")

if newly_found:
    new_df   = pd.DataFrame(newly_found)
    combined = pd.concat([existing_df, new_df], ignore_index=True)
    combined.to_csv(OUTPUT_PATH, index=False)
    print(f"Appended {len(newly_found)} players → {OUTPUT_PATH} (total: {len(combined)})")
else:
    print("Nothing to append.")
