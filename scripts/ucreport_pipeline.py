"""Recruit and drafted-OL exports using the UCReport API."""
import argparse
from pathlib import Path
import tempfile

import pandas as pd
from recruit_sources import ROOT_DIR, attach_board_fields, load_recruit_board, normalize_name, split_player_name
from ucreport_api import APIError, UCReportClient


def save_rows(rows, existing, output):
    if not rows:
        return False
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.concat([existing, pd.DataFrame(rows)], ignore_index=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tmp', dir=output.parent, delete=False) as handle:
            temporary = Path(handle.name)
            frame.to_csv(handle, index=False)
        temporary.replace(output)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return True


def main(kind='recruits', append=False):
    parser = argparse.ArgumentParser(description=f'Fetch UCReport {kind} via the documented API.')
    parser.add_argument('--append', action='store_true', default=append)
    parser.add_argument('--output', type=Path, default=ROOT_DIR / ('data/recruits/ucreport_data.csv' if kind == 'recruits' else 'data/draft/ol_ucreport_data.csv'))
    parser.add_argument('--class-year', type=int, default=2027)
    args = parser.parse_args()
    try:
        client = UCReportClient.from_config()
        existing = pd.read_csv(args.output) if args.append and args.output.exists() else pd.DataFrame()
        names = {normalize_name(n) for n in existing.get('query_name', [])}
        board = load_recruit_board() if kind == 'recruits' else pd.read_csv(ROOT_DIR / 'data/draft/ol_wikipedia_picks.csv')
        results = []
        for _, row in board.iterrows():
            if kind == 'recruits':
                name, first, last = row['query_name'], row['query_first'], row['query_last']
                classes = {args.class_year}
            else:
                name = str(row['player']).replace('†', '').replace('*', '').split('[')[0].strip()
                first, last = split_player_name(name)
                year = int(row['year'])
                classes = set(range(year - 5, year - 2))
            if not first or not last or normalize_name(name) in names:
                continue
            matches = client.find_players(first, last, classes)
            if matches:
                player = matches[0]
                if kind == 'recruits':
                    attach_board_fields(player, row)
                else:
                    player['query_name'] = name
                    for field in ('year', 'round', 'pick', 'team', 'pos', 'college'):
                        player[f'wiki_{field}'] = row[field]
                results.append(player)
            print(f"{name}: {'found' if matches else 'not found'}")
        saved = save_rows(results, existing, args.output)
        print(f'Saved {len(results)} players to {args.output}' if saved else 'No matches; existing output retained.')
    except APIError as exc:
        parser.exit(1, f'{exc}\nNo export was replaced.\n')
