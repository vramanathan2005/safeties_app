"""Export the full pick list for an NFL draft year from Wikipedia.

Writes data/draft/wikipedia_picks_{year}.csv with columns matching the existing
data/draft/ol_wikipedia_picks.csv convention (year, round, pick, team, player,
pos, college), but covering every position, not just OL. That file feeds
fetch_wikipedia_ucreport_matches.py, which looks up each pick's HS measurables
in UCReport the same way the existing OL pipeline already does.
"""
import argparse
import io
import re

import pandas as pd
import requests
from recruit_sources import ROOT_DIR

WIKI_API = "https://en.wikipedia.org/w/api.php"
DRAFT_TABLE_COLUMNS = {"Rnd.", "Pick", "Team", "Player", "Pos.", "College"}


def fetch_draft_table(year):
    response = requests.get(WIKI_API, params={
        "action": "parse",
        "page": f"{year} NFL draft",
        "prop": "text",
        "format": "json",
    }, headers={"User-Agent": "safeties-app-draft-import/1.0"}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise SystemExit(f"Wikipedia API error: {payload['error']}")
    html = payload["parse"]["text"]["*"]

    tables = pd.read_html(io.StringIO(html))
    for table in tables:
        if DRAFT_TABLE_COLUMNS.issubset(set(table.columns.astype(str))):
            return table
    raise SystemExit(
        f"Could not find the main draft-order table on the '{year} NFL draft' Wikipedia "
        "page (expected columns Rnd./Pick/Team/Player/Pos./College)."
    )


def clean_round(value):
    digits = re.sub(r"\D", "", str(value))
    return int(digits) if digits else None


def main():
    parser = argparse.ArgumentParser(description="Export an NFL draft year's picks from Wikipedia.")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    table = fetch_draft_table(args.year)
    picks = pd.DataFrame({
        "year": args.year,
        "round": table["Rnd."].map(clean_round),
        "pick": pd.to_numeric(table["Pick"], errors="coerce"),
        "team": table["Team"].astype(str).str.strip(),
        "player": table["Player"].astype(str).str.strip(),
        "pos": table["Pos."].astype(str).str.strip(),
        "college": table["College"].astype(str).str.strip(),
    })
    picks = picks[picks["player"].notna() & (picks["player"] != "nan")]

    output = args.output or ROOT_DIR / "data" / "draft" / f"wikipedia_picks_{args.year}.csv"
    picks.to_csv(output, index=False)
    print(f"Saved {len(picks)} picks to {output}")
    print(picks["pos"].value_counts().to_string())


if __name__ == "__main__":
    main()
