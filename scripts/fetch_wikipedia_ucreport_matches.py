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

RECRUIT_MATCH = {
    'qb': ['QB'],
    'rb': ['RB'],
    'wr': ['WR'],
    'te': ['TE'],
    'ol': ['OT', 'OG', 'OL', 'C', 'G', 'T', 'LT', 'RT', 'LG', 'RG'],
    'safety': ['S', 'FS', 'SS', 'Safety'],
    'cb': ['CB'],
    'lb': ['LB', 'OLB', 'ILB'],
    'de': ['DE', 'EDGE', 'DL'],
    'dt': ['DT', 'DL', 'NT'],
}

COLLEGE_ALIASES = {
    'lsu': ['louisiana state', 'lsu'],
    'usc': ['southern california', 'usc'],
    'uconn': ['connecticut', 'uconn'],
    'byu': ['brigham young', 'byu'],
    'tcu': ['texas christian', 'tcu'],
    'smu': ['southern methodist', 'smu'],
    'ucf': ['central florida', 'ucf'],
    'ole miss': ['mississippi', 'ole miss'],
    'pitt': ['pittsburgh', 'pitt'],
    'unc': ['north carolina', 'unc'],
    'utep': ['texas el paso', 'texas-el paso', 'utep'],
    'utsa': ['texas san antonio', 'texas-san antonio', 'utsa'],
    'miami (fl)': ['miami (fl)', 'miami (florida)', 'miami'],
    'miami (oh)': ['miami (oh)', 'miami (ohio)', 'miami'],
}

NAME_OVERRIDES = {
    'T. J. Parker': ('Tomarrion', 'Parker'),
    'JC Davis': ('JC', 'Davis'),
    'J. C. Davis': ('JC', 'Davis'),
    'Chris Bell': ('Christopher', 'Bell'),
}

def college_matches(wiki_college, candidate):
    if not wiki_college or pd.isna(wiki_college):
        return True
    w = str(wiki_college).lower().strip()
    c_text = f"{candidate.get('commit', '')} {candidate.get('college_enrolled', '')} {candidate.get('college_offers', '')}".lower()
    for k, aliases in COLLEGE_ALIASES.items():
        if k in w:
            for a in aliases:
                if a in c_text:
                    return True
    words = [x.strip('()') for x in w.split() if len(x.strip('()')) > 2]
    return any(word in c_text for word in words)

def score_candidate(candidate, match_positions, wiki_college):
    score = 0
    c_pos_played = str(candidate.get('position_played', ''))
    c_pos_proj = str(candidate.get('position_projected', ''))
    
    if any(p in match_positions for p in [c_pos_played, c_pos_proj]):
        score += 50
    elif 'ATH' in [c_pos_played, c_pos_proj]:
        score += 20
    else:
        score -= 50  # Penalize contradictory position (e.g. DE when matching WR)
        
    if college_matches(wiki_college, candidate):
        score += 100
        
    return score

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

    classes = set(range(args.year - 6, args.year - 1))

    for pos_code in args.positions:
        match_positions = RECRUIT_MATCH[pos_code]
        pos_picks = picks[picks["pos"].isin(match_positions)]
        if pos_picks.empty:
            print(f"{pos_code}: no {args.year} picks at {match_positions}")
            continue

        results = []
        for _, row in pos_picks.iterrows():
            name = str(row["player"]).strip()
            if name in NAME_OVERRIDES:
                first, last = NAME_OVERRIDES[name]
            else:
                first, last = split_player_name(name)
            if not first or not last:
                print(f"  {name}: could not split name, skipping")
                continue
            try:
                matches = client.find_players(first, last, classes)
            except APIError as exc:
                print(f"  {name}: {exc}")
                continue
            
            if matches:
                # Rank candidates by position and college match
                ranked = sorted(matches, key=lambda c: score_candidate(c, match_positions, row["college"]), reverse=True)
                best = ranked[0]
                best_score = score_candidate(best, match_positions, row["college"])
                
                # If the best candidate is heavily penalized (contradictory position & unrelated college), reject
                if best_score < 0:
                    print(f"  {name}: candidate mismatch (best={best.get('first')} {best.get('last')} {best.get('position_played')}, score={best_score}), skipping")
                    continue
                    
                player = best
                player["query_name"] = name
                player["wiki_year"] = row["year"]
                player["wiki_round"] = row["round"]
                player["wiki_pick"] = row["pick"]
                player["wiki_team"] = row["team"]
                player["wiki_college"] = row["college"]
                results.append(player)
                print(f"  {name}: matched ({player.get('school_name')}, score={best_score})")
            else:
                print(f"  {name}: not found")

        output = ROOT_DIR / "data" / "draft" / f"{pos_code}_{args.year}_ucreport.csv"
        pd.DataFrame(results).to_csv(output, index=False)
        print(f"{pos_code}: matched {len(results)}/{len(pos_picks)} picks -> {output}")


if __name__ == "__main__":
    main()
