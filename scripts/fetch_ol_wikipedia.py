import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os

OL_POSITIONS = {"T", "G", "C", "OT", "OG", "OL", "LT", "RT", "LG", "RG"}
YEARS = [2022, 2023, 2024, 2025]
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "../data/draft/ol_wikipedia_picks.csv")

def fetch_ol_picks(year):
    url = f"https://en.wikipedia.org/wiki/{year}_NFL_draft"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Find the main picks table — it has columns Rnd., Pick, Team, Player, Pos., College
    picks_table = None
    for table in soup.find_all("table", class_="wikitable"):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if "Player" in headers and "Pos." in headers and "Pick" in headers:
            picks_table = table
            break

    if picks_table is None:
        print(f"  Could not find picks table for {year}")
        return []

    headers = [th.get_text(strip=True) for th in picks_table.find_all("th")]
    # Deduplicate header list (wikitables sometimes repeat headers mid-table)
    col_map = {}
    for i, h in enumerate(headers):
        if h not in col_map:
            col_map[h] = i

    rnd_idx   = col_map.get("Rnd.")
    pick_idx  = col_map.get("Pick")
    team_idx  = col_map.get("Team")
    player_idx = col_map.get("Player")
    pos_idx   = col_map.get("Pos.")
    college_idx = col_map.get("College")

    rows = []
    for tr in picks_table.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue
        texts = [c.get_text(strip=True) for c in cells]
        if len(texts) < 6:
            continue
        # Skip header rows
        if texts[0] in ("Rnd.", "Round"):
            continue

        try:
            pos = texts[pos_idx] if pos_idx is not None else ""
            # Strip footnotes like [a]
            pos = pos.split("[")[0].strip()
            if pos.upper() not in OL_POSITIONS:
                continue

            rows.append({
                "year": year,
                "round": texts[rnd_idx] if rnd_idx is not None else "",
                "pick":  texts[pick_idx] if pick_idx is not None else "",
                "team":  texts[team_idx] if team_idx is not None else "",
                "player": texts[player_idx] if player_idx is not None else "",
                "pos":   pos,
                "college": texts[college_idx] if college_idx is not None else "",
            })
        except IndexError:
            continue

    return rows

all_picks = []
for year in YEARS:
    print(f"Fetching {year}...")
    picks = fetch_ol_picks(year)
    print(f"  Found {len(picks)} OL picks")
    all_picks.extend(picks)
    time.sleep(1)

df = pd.DataFrame(all_picks)
df.to_csv(OUTPUT_PATH, index=False)
print(f"\nSaved {len(df)} total OL picks to {OUTPUT_PATH}")
print(df.groupby("year")["player"].count().to_string())
