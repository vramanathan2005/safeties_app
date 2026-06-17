import argparse
import json
import re
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

from fetch_arms_archive import DEFAULT_COOKIE_FILE, DEFAULT_OUTPUT_DIR, load_cookie


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE_CSV = DEFAULT_OUTPUT_DIR / "recruiting_6918_archive_grad_0.csv"
DEFAULT_OUTPUT_CSV = DEFAULT_OUTPUT_DIR / "recruiting_6918_athletic.csv"
BASE_URL = "https://sso.armssoftware.com"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape the Athletic section from ARMS recruit profile pages."
    )
    parser.add_argument("--sport-id", type=int, default=6918)
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_ARCHIVE_CSV)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--cookie-file", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=0.25)
    parser.add_argument(
        "--ids",
        default=None,
        help="Optional comma-separated recruit ids to fetch instead of the full input CSV.",
    )
    parser.add_argument(
        "--save-html-dir",
        type=Path,
        default=None,
        help="Optional ignored directory for raw fetched profile HTML snapshots.",
    )
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument(
        "--max-errors",
        type=int,
        default=5,
        help="Stop after this many consecutive fetch errors. Use 0 to disable.",
    )
    parser.add_argument(
        "--resolve-profile-ids",
        action="store_true",
        help="Resolve archive/list ids through /profile/recruits/{id} before fetching Athletic data.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Keep existing output rows and continue with the next input row.",
    )
    return parser.parse_args()


def build_session(cookie):
    session = requests.Session()
    session.headers.update(
        {
            "cookie": cookie,
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
            ),
            "content-type": "text/plain; charset=utf-8",
            "cache-control": "no-cache, no-store, must-revalidate, post-check=0, pre-check=0",
            "pragma": "no-cache",
            "expires": "0",
            "x-ajax-request": "true",
            "x-redirect-on-error": "true",
            "accept": "text/plain, */*",
        }
    )
    return session


def normalize_text(value):
    return " ".join(str(value or "").replace("\xa0", " ").split())


def field_key(label):
    label = normalize_text(label).lower()
    label = label.replace("#", "number")
    label = re.sub(r"[^a-z0-9]+", "_", label)
    return label.strip("_")


def is_section_heading(text):
    text = normalize_text(text)
    if not text or len(text) > 60:
        return False
    return text.upper() == text and any(char.isalpha() for char in text)


def parse_athletic_section(html):
    soup = BeautifulSoup(html, "html.parser")
    athletic_node = soup.find(string=lambda value: normalize_text(value).upper() == "ATHLETIC")

    rows = {}
    found_rows = False
    if athletic_node:
        elements = athletic_node.parent.find_all_next(["tr", "h1", "h2", "h3", "h4", "h5"])
    else:
        elements = soup.find_all("tr")

    for element in elements:
        text = normalize_text(element.get_text(" ", strip=True))
        if found_rows and element.name in {"h1", "h2", "h3", "h4", "h5"} and is_section_heading(text):
            break

        if element.name != "tr":
            continue

        cells = [normalize_text(cell.get_text(" ", strip=True)) for cell in element.find_all(["td", "th"])]
        cells = [cell for cell in cells if cell]
        if len(cells) < 2:
            continue

        label, value = cells[0], cells[1]
        if not label:
            continue
        rows[field_key(label)] = value
        found_rows = True

    return rows


def flatten_json(value, prefix=""):
    rows = {}
    if isinstance(value, dict):
        for key, child in value.items():
            child_key = f"{prefix}_{field_key(key)}" if prefix else field_key(key)
            rows.update(flatten_json(child, child_key))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            child_key = f"{prefix}_{idx}" if prefix else str(idx)
            rows.update(flatten_json(child, child_key))
    elif prefix:
        rows[prefix] = value
    return rows


def parse_athletic_payload(text):
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return parse_athletic_section(text)
    return flatten_json(data)


def fetch_athletic_payload(session, sport_id, recruit_id):
    cache_buster = int(time.time() * 1000)
    path = f"/arms/recruiting/{sport_id}/profile/{recruit_id}/athletic?_={cache_buster}"
    url = BASE_URL + path
    response = session.get(url, headers={"referer": url}, timeout=30, allow_redirects=False)
    if response.status_code in (401, 403):
        raise RuntimeError(
            f"ARMS returned {response.status_code} for recruit {recruit_id}. "
            "Refresh the cookie from a browser session that can open the Athletic tab."
        )
    response.raise_for_status()
    return response.text


def resolve_profile_id(session, sport_id, recruit_id):
    url = f"{BASE_URL}/arms/recruiting/-1/profile/recruits/{recruit_id}"
    response = session.get(url, headers={"referer": url}, timeout=30, allow_redirects=True)
    if response.status_code in (401, 403):
        raise RuntimeError(
            f"ARMS returned {response.status_code} while resolving recruit {recruit_id}."
        )
    response.raise_for_status()

    match = re.search(r"/arms/recruiting/(\d+)/profile/(\d+)", response.url)
    if match:
        return int(match.group(2)), int(match.group(1))

    match = re.search(r"/arms/recruiting/(\d+)/profile/(\d+)", response.text or "")
    if match:
        return int(match.group(2)), int(match.group(1))

    return int(recruit_id), sport_id


def load_targets(args):
    if args.ids:
        ids = [int(value.strip()) for value in args.ids.split(",") if value.strip()]
        return pd.DataFrame({"id": ids})

    df = pd.read_csv(args.input_csv)
    df = df[df["id"].notna()].copy()
    if args.limit:
        df = df.head(args.limit)
    return df


def main():
    args = parse_args()
    cookie = load_cookie(args.cookie_file or DEFAULT_COOKIE_FILE)
    targets = load_targets(args)
    session = build_session(cookie)

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    if args.save_html_dir:
        args.save_html_dir.mkdir(parents=True, exist_ok=True)

    output_rows = []
    completed_rows = 0
    if args.resume and args.output_csv.exists():
        existing = pd.read_csv(args.output_csv)
        output_rows = existing.to_dict("records")
        completed_rows = len(existing)
        targets = targets.iloc[completed_rows:].copy()
        print(
            f"Resuming from {args.output_csv}: {completed_rows} rows already saved, "
            f"{len(targets)} rows remaining.",
            flush=True,
        )

    consecutive_errors = 0

    def save_progress():
        pd.DataFrame(output_rows).to_csv(args.output_csv, index=False)

    for offset, (_, row) in enumerate(targets.iterrows(), start=completed_rows + 1):
        recruit_id = int(row["id"])
        base = row.to_dict()
        print(
            f"Fetching athletic profile {offset}/{completed_rows + len(targets)}: "
            f"{recruit_id} {base.get('name', '')}",
            flush=True,
        )
        try:
            profile_id = recruit_id
            sport_id = args.sport_id
            if args.resolve_profile_ids:
                profile_id, sport_id = resolve_profile_id(session, args.sport_id, recruit_id)
                print(f"  -> resolved to profile {profile_id} sport {sport_id}", flush=True)

            html = fetch_athletic_payload(session, sport_id, profile_id)
            if args.save_html_dir:
                (args.save_html_dir / f"{profile_id}.html").write_text(html, encoding="utf-8")
            athletic = parse_athletic_payload(html)
            output_rows.append(
                {
                    **base,
                    "profile_id": profile_id,
                    "profile_sport_id": sport_id,
                    **athletic,
                    "athletic_field_count": len(athletic),
                    "error": "",
                }
            )
            consecutive_errors = 0
        except Exception as exc:
            if args.stop_on_error:
                raise
            output_rows.append({**base, "profile_id": "", "profile_sport_id": "", "athletic_field_count": 0, "error": str(exc)})
            consecutive_errors += 1
            print(f"  -> {exc}", flush=True)
            if args.max_errors and consecutive_errors >= args.max_errors:
                print(
                    f"\nStopping after {consecutive_errors} consecutive errors. "
                    "Refresh the cookie or capture the Athletic tab request from DevTools.",
                    flush=True,
                )
                break

        save_progress()
        time.sleep(args.sleep)

    save_progress()
    print(f"\nSaved {len(output_rows)} rows to {args.output_csv}", flush=True)


if __name__ == "__main__":
    main()
