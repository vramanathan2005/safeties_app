import argparse
import json
import os
import time
from pathlib import Path

import pandas as pd
import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT_DIR / "data" / "arms"
DEFAULT_COOKIE_FILE = ROOT_DIR / ".secrets" / "arms_cookie.txt"
ENDPOINT = "https://sso.armssoftware.com/arms/api/private/recruiting/{sport_id}/archive/"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export paginated recruiting archive rows from the ARMS private JSON API."
    )
    parser.add_argument("--sport-id", type=int, default=6918)
    parser.add_argument("--grad-year", default="0", help="Use 0 for all grad years.")
    parser.add_argument("--order", choices=("asc", "desc"), default="asc")
    parser.add_argument("--start-page", type=int, default=0)
    parser.add_argument("--per-page", type=int, default=50)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=0.25)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--raw-output", type=Path, default=None)
    parser.add_argument("--csv-output", type=Path, default=None)
    parser.add_argument(
        "--cookie-file",
        type=Path,
        default=None,
        help=f"File containing the full Cookie header. Defaults to {DEFAULT_COOKIE_FILE}.",
    )
    return parser.parse_args()


def load_cookie(cookie_file):
    cookie = os.environ.get("ARMS_COOKIE", "").strip()
    if cookie:
        return cookie

    cookie_path = cookie_file or DEFAULT_COOKIE_FILE
    if cookie_path.exists():
        return cookie_path.read_text().strip()

    raise SystemExit(
        "Missing ARMS cookie. Set ARMS_COOKIE to the curl -b value, or save it in "
        f"{cookie_path}."
    )


def build_headers(cookie, sport_id):
    return {
        "accept": "application/json",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "no-cache",
        "content-type": "application/json",
        "cookie": cookie,
        "origin": "https://sso.armssoftware.com",
        "pragma": "no-cache",
        "referer": f"https://sso.armssoftware.com/arms/recruiting/{sport_id}/archive",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
        ),
    }


def describe_payload(data):
    if isinstance(data, dict):
        return f"dict keys={list(data.keys())[:10]}"
    if isinstance(data, list):
        return f"list len={len(data)}"
    return type(data).__name__


def find_first_row_list(value):
    if isinstance(value, list):
        return value
    if not isinstance(value, dict):
        return None

    preferred_keys = (
        "results",
        "players",
        "recruits",
        "archive",
        "items",
        "rows",
        "content",
        "data",
    )
    for key in preferred_keys:
        rows = find_first_row_list(value.get(key))
        if rows is not None:
            return rows

    for child in value.values():
        rows = find_first_row_list(child)
        if rows is not None:
            return rows
    return None


def extract_rows(data):
    rows = find_first_row_list(data) or []
    return [row if isinstance(row, dict) else {"value": row} for row in rows]


def detect_total_count(data):
    if not isinstance(data, dict):
        return None
    for key in ("total", "totalCount", "totalRecords", "recordsTotal", "count"):
        value = data.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    for value in data.values():
        nested = detect_total_count(value)
        if nested is not None:
            return nested
    return None


def fetch_page(session, sport_id, payload):
    url = ENDPOINT.format(sport_id=sport_id)
    response = session.post(url, json=payload, timeout=30)
    if response.status_code in (401, 403):
        raise SystemExit(
            f"ARMS returned {response.status_code}. The session cookie is probably expired."
        )
    response.raise_for_status()
    return response.json()


def output_paths(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"recruiting_{args.sport_id}_archive_grad_{args.grad_year}"
    raw_output = args.raw_output or args.output_dir / f"{stem}.json"
    csv_output = args.csv_output or args.output_dir / f"{stem}.csv"
    raw_output.parent.mkdir(parents=True, exist_ok=True)
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    return raw_output, csv_output


def main():
    args = parse_args()
    cookie = load_cookie(args.cookie_file)
    raw_output, csv_output = output_paths(args)

    session = requests.Session()
    session.headers.update(build_headers(cookie, args.sport_id))

    raw_pages = []
    all_rows = []
    total_count = None
    page = args.start_page
    pages_fetched = 0

    while True:
        if args.max_pages is not None and pages_fetched >= args.max_pages:
            break

        payload = {
            "sportId": args.sport_id,
            "gradYear": str(args.grad_year),
            "order": args.order,
            "page": page,
            "perPage": args.per_page,
        }
        data = fetch_page(session, args.sport_id, payload)
        rows = extract_rows(data)
        total_count = total_count or detect_total_count(data)

        raw_pages.append({"page": page, "payload": payload, "response": data})
        all_rows.extend(rows)
        pages_fetched += 1

        total_msg = f" / total {total_count}" if total_count is not None else ""
        print(f"page {page}: {len(rows)} rows{total_msg} ({describe_payload(data)})")

        if not rows or len(rows) < args.per_page:
            break
        if total_count is not None and len(all_rows) >= total_count:
            break

        page += 1
        time.sleep(args.sleep)

    raw_output.write_text(json.dumps(raw_pages, indent=2), encoding="utf-8")

    if all_rows:
        df = pd.json_normalize(all_rows)
        df.to_csv(csv_output, index=False)
    else:
        pd.DataFrame().to_csv(csv_output, index=False)

    print(f"\nSaved raw pages: {raw_output}")
    print(f"Saved flattened CSV: {csv_output}")
    print(f"Exported {len(all_rows)} rows from {pages_fetched} page(s).")


if __name__ == "__main__":
    main()
