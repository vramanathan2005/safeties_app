# NFL Draft Scouting Dashboard

Static scouting dashboard generated from local CSV data.

## Layout

- `index.html` - generated dashboard you can open in a browser.
- `build_html.py` - rebuilds `index.html` from the CSV files.
- `data/draft/` - position CSVs for drafted-player combine and high school stats.
- `data/recruits/` - 2027 recruit board export and MaxPreps data.
- `scripts/` - one-off data collection and maintenance scripts.
- `tests/` - small API/debug probes kept out of the app root.

## Rebuild

```bash
.venv/bin/python build_html.py
```

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

## API reference files

The retained API documentation and sanitized Postman collection are in `docs/ucreport/`.

## UCReport API pipeline

Enter the current key and assigned college name in `.secrets/ucreport_api.json`
(ignored by git). `college` selects the account's access package; the documentation's
Florida Atlantic value is an example, not an assumed account setting.

```json
{"api_key": "YOUR_API_KEY", "college": "YOUR_COLLEGE_NAME"}
```

Environment variables `UCREPORT_API_KEY`, `UCREPORT_COLLEGE`, and optionally
`UCREPORT_API_BASE_URL` override local configuration. Cookie credentials are not used.

```bash
.venv/bin/python scripts/debug_ucreport.py
.venv/bin/python scripts/fetch_players.py
.venv/bin/python scripts/fetch_ol_ucreport.py
.venv/bin/python scripts/fetch_maxpreps.py
.venv/bin/python build_html.py
```

Recruit exports default to class 2027 (`--class-year` overrides it). Drafted OL
searches use high-school classes three to five years before each draft year.
Both support `--append` and `--output`; the `append_missing_players.py` and
`append_missing_ol_players.py` wrappers enable append mode. API failures stop the
export before replacement; zero matches retain any existing CSV.

The API client supports all six documented routes with POST JSON, the `key` header,
a required college, and zero-based pagination. Player exports use master-list
measurements, map school and arm fields to the dashboard columns, and retain
`player_id` for MaxPreps joins (`dbkey` is a distinct API identifier).
The dashboard can load recruits before MaxPreps stats are available.

403 indicates rejected credentials. A 500 may indicate a college package or
server problem; the client reports it without changing the college or access scope.
The deleted historical CSVs are not restored: these commands regenerate them
from the API once valid credentials are configured.

```bash
.venv/bin/python -m unittest discover -s tests -p test_ucreport_api.py
```

## Full prospect database and career outcomes

Run `.venv/bin/python scripts/fetch_all_prospects.py` to retrieve every public
prospect visible to the configured college package. This saves a separate
`data/recruits/ucreport_all_prospects.csv`; the board export is preserved.
The dashboard prefers this complete export when present. Rebuild with
`.venv/bin/python build_html.py`. Use All prospects and the HS graduation-year
filter to browse; cards are paginated in batches of 100.

Optional verified outcomes go in `data/player_outcomes.csv`, with one selected
season per `player_id`: `season`, `conference`, `college_starts`, `college_games`,
`team_games`, `nfl_snaps`, `undrafted`, `draft_round`. Missing facts remain
unverified. Starter requires starts in at least half the team's games that
season, rounded up; the denominator is team games, not player appearances.
Conference must correspond to that season. College labels require verified zero
NFL snaps. NFL drafted takes precedence; NFL UDFA requires verified undrafted
status and positive NFL snaps. UCReport alone does not establish these facts.

Graduation classes 2027 and later always display `HS Recruit`. Career-outcome
classification applies to 2026 and earlier; unknown class years remain unverified
unless supported by outcome evidence.
