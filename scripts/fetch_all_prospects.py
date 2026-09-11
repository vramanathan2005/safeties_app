"""Export all prospects visible to the configured API account, without board filters.

Fetches the full masterlist (no class-year filter) because scripts/reconcile_players.py
needs older class years to link already-drafted players back to their HS measurables.
The dashboard-facing 2027+ restriction is applied later in build_html.py, after
reconciliation has used the older records.
"""
import pandas as pd
from recruit_sources import RECRUIT_DATA_DIR
from ucreport_api import APIError, COLUMNS, UCReportClient
from ucreport_pipeline import save_rows


def main():
    client = UCReportClient.from_config()
    rows = {}
    for row in client.rows(cols=COLUMNS):
        if row.get('player_id') is None:
            raise APIError('Player missing player_id; export not replaced.')
        row['effective_school_name'] = row.get('juco_school_name') or row.get('school_name') or ''
        row['arm_length'] = row.get('arm_length_verified') or row.get('arm')
        row['query_name'] = f"{row.get('first') or ''} {row.get('last') or ''}".strip()
        rows[row['player_id']] = row
        if len(rows) % 500 == 0:
            print(f'Fetched {len(rows)} unique prospects', flush=True)
    output = RECRUIT_DATA_DIR / 'ucreport_all_prospects.csv'
    save_rows(list(rows.values()), pd.DataFrame(), output)
    print(f'Saved {len(rows)} unique prospects to {output}', flush=True)


if __name__ == '__main__':
    try:
        main()
    except APIError as exc:
        raise SystemExit(str(exc))
