"""Match a Wikipedia draft-picks export (see fetch_wikipedia_draft.py) against
UCReport to pull each drafted player's HS measurables, the same way the existing
OL pipeline (ucreport_pipeline.py --kind ol) already does for offensive linemen.

Writes one CSV per dashboard position group: data/draft/{pos_code}_{year}_ucreport.csv,
with wiki_year/wiki_round/wiki_pick/wiki_team/wiki_college columns attached so
build_html.py can merge them in next to the position's existing combine/stats data.
"""
import argparse
from pathlib import Path

import pandas as pd
from recruit_sources import ROOT_DIR, split_player_name
from ucreport_api import APIError, UCReportClient

# Mirrors build_html.py's POSITIONS dict — kept local rather than imported since
# build_html.py lives at the repo root and these scripts run with scripts/ on
# sys.path, not the root.
RECRUIT_MATCH = {
    'qb': ['QB'],
    'rb': ['RB'],
    'wr': ['WR'],
    'te': ['TE'],
    'ol': ['OT', 'OG', 'OL', 'C', 'G', 'T', 'LT', 'RT', 'LG', 'RG'],
    'safety': ['S', 'FS', 'SS', 'Safety'],
    'cb': ['CB'],
    'lb': ['LB', 'OLB', 'ILB'],
    'de': ['DE'],
    'dt': ['DT'],
}


def main():
    parser = argparse.ArgumentParser(description="Match Wikipedia draft picks against UCReport.")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--picks-csv", type=Path, default=None,
                         help="Defaults to data/draft/wikipedia_picks_{year}.csv")
    parser.add_argument("--positions", nargs="*", default=list(RECRUIT_MATCH.keys()),
                         help="Position codes to process (default: all).")
    args = parser.parse_args()

    picks_csv = args.picks_csv or ROOT_DIR / "data" / "draft" / f"wikipedia_picks_{args.year}.csv"
    picks = pd.read_csv(picks_csv)

    try:
        client = UCReportClient.from_config()
    except APIError as exc:
        raise SystemExit(str(exc))

    classes = set(range(args.year - 5, args.year - 2))

    for pos_code in args.positions:
        match_positions = RECRUIT_MATCH[pos_code]
        pos_picks = picks[picks["pos"].isin(match_positions)]
        if pos_picks.empty:
            print(f"{pos_code}: no {args.year} picks at {match_positions}")
            continue

        results = []
        for _, row in pos_picks.iterrows():
            name = str(row["player"]).strip()
            first, last = split_player_name(name)
            if not first or not last:
                print(f"  {name}: could not split name, skipping")
                continue
            try:
                matches = client.find_players(first, last, classes)
            except APIError as exc:
                print(f"  {name}: {exc}")
                continue
            print(f"  {name}: {'found' if matches else 'not found'}")
            if matches:
                player = matches[0]
                player["query_name"] = name
                player["wiki_year"] = row["year"]
                player["wiki_round"] = row["round"]
                player["wiki_pick"] = row["pick"]
                player["wiki_team"] = row["team"]
                player["wiki_college"] = row["college"]
                results.append(player)

        output = ROOT_DIR / "data" / "draft" / f"{pos_code}_{args.year}_ucreport.csv"
        pd.DataFrame(results).to_csv(output, index=False)
        print(f"{pos_code}: matched {len(results)}/{len(pos_picks)} picks -> {output}")


if __name__ == "__main__":
    main()
