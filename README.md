# NFL Draft Scouting Dashboard

Static scouting dashboard generated from local CSV data.

## Layout

- `index.html` - generated dashboard you can open in a browser.
- `build_html.py` - rebuilds `index.html` from the CSV files.
- `data/draft/` - position CSVs for drafted-player combine and high school stats.
- `data/recruits/` - 2027 recruit board export plus enriched UC Report/MaxPreps data.
- `scripts/` - one-off data collection and maintenance scripts.
- `tests/` - small API/debug probes kept out of the app root.

## Rebuild

```bash
.venv/bin/python build_html.py
```

## Recruit Data Pipeline

```bash
.venv/bin/python scripts/fetch_players.py
.venv/bin/python scripts/append_missing_players.py
.venv/bin/python scripts/fetch_maxpreps.py
```

The fetch scripts use `data/recruits/2027_recruits.csv` as the source player board, write enriched UC Report rows to `data/recruits/ucreport_data.csv`, then write MaxPreps stats to `data/recruits/maxpreps_data.csv`.
