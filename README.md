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

## ARMS Archive Export

`scripts/fetch_arms_archive.py` exports the private ARMS recruiting archive endpoint as raw JSON pages plus a flattened CSV. Keep the copied cookie local; `.secrets/` and `data/arms/` are ignored by git.

```bash
mkdir -p .secrets
printf '%s' 'PASTE_THE_FULL_CURL_B_COOKIE_VALUE_HERE' > .secrets/arms_cookie.txt
.venv/bin/python scripts/fetch_arms_archive.py --sport-id 6918 --grad-year 0
```

Outputs are written to `data/arms/recruiting_6918_archive_grad_0.json` and `data/arms/recruiting_6918_archive_grad_0.csv` by default.

To scrape the Athletic tab from each archived profile after the archive export:

```bash
.venv/bin/python scripts/fetch_arms_athletic_profiles.py --limit 10
```

That writes `data/arms/recruiting_6918_athletic.csv`. If ARMS returns `403` for profile pages, refresh `.secrets/arms_cookie.txt` from a browser session that can open the recruit profile.
