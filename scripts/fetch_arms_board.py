"""Export an ARMS Recruiting Board (the drag-and-drop board UI, not the archive
endpoint) as a CSV matching data/recruits/2027_recruits.csv's shape.

The board page (GET /arms/recruiting/{sportId}/board/v2/{boardId}) is server-rendered
HTML with every player card embedded inline — no separate JSON API call needed. Each
category column on the board (e.g. "SAF (IS)", "QB") becomes one or more rows; the
board switcher menu embedded in that same HTML lists every other board's id, which
--list-boards prints out.

Usage:
    .venv/bin/python scripts/fetch_arms_board.py --list-boards
    .venv/bin/python scripts/fetch_arms_board.py --board-id 238649 --board-id 238650 \
        --output data/recruits/2027_recruits.csv
"""
import argparse
import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

from fetch_arms_archive import DEFAULT_COOKIE_FILE, load_cookie

ROOT_DIR = Path(__file__).resolve().parents[1]
BASE_URL = "https://sso.armssoftware.com"

# Known irregular category -> position_group mappings, taken from the existing
# 2027_recruits.csv export. Anything not listed here falls back to stripping the
# " (IS)"/" (OOS)"/" IS"/" OOS"/" - H"/" - Y" suffix and using what's left.
CATEGORY_OVERRIDES = {
    "COMBO -> CB": "CB",
    "COMBO -> SAF": "SAF",
    "JACK/SAM": "LB",
    "DT/NOSE": "DT",
    "SAF/STAR": "SAF",
}


def position_group_for(category):
    if category in CATEGORY_OVERRIDES:
        return CATEGORY_OVERRIDES[category]
    stripped = re.sub(r"\s*(\(IS\)|\(OOS\)|-\s*H|-\s*Y|\bIS\b|\bOOS\b)\s*$", "", category).strip()
    if stripped in CATEGORY_OVERRIDES:
        return CATEGORY_OVERRIDES[stripped]
    return stripped or category


def build_session(cookie):
    session = requests.Session()
    session.headers.update({
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
        "accept": "application/json, text/plain, */*",
    })
    return session


def fetch_board_html(session, sport_id, board_id):
    url = f"{BASE_URL}/arms/recruiting/{sport_id}/board/v2/{board_id}"
    response = session.get(url, headers={"referer": url}, timeout=30)
    if response.status_code in (401, 403):
        raise RuntimeError(
            f"ARMS returned {response.status_code} for board {board_id}. "
            "Refresh .secrets/arms_cookie.txt from a browser session that can open the board."
        )
    response.raise_for_status()
    return response.text


def list_boards(html):
    """Board switcher menu embedded in every board page: <a class="switch_board"
    data-board-id="...">Name</a>. Returns [(board_id, name), ...]."""
    soup = BeautifulSoup(html, "html.parser")
    boards = []
    for a in soup.select("a.switch_board[data-board-id]"):
        boards.append((a["data-board-id"], a.get_text(strip=True)))
    return boards


def field_text(profile, suffix):
    el = profile.select_one(f'span[id*="{suffix}_"]')
    return el.get_text(strip=True) if el else None


def parse_board(html, board_name):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for category_div in soup.select('div[id^="category"][data-id]'):
        label_a = category_div.select_one('.header a.tooltipMe[onclick*="arms.std.load"]')
        category = label_a.get_text(strip=True) if label_a else category_div["data-id"]

        for profile in category_div.select("div.board_profile"):
            img = profile.select_one("img.headshot")
            name = img.get("title", "").strip() if img else ""
            if not name:
                continue

            rank_headers = [h.get_text(strip=True) for h in profile.select(".viewFieldHeader")]
            rank_values = [v.get_text(strip=True) for v in profile.select(".viewFieldValue")]
            rank_type = rank_headers[0] if rank_headers else None
            rank_value = rank_values[0] if rank_values else None

            rows.append({
                "board": board_name,
                "position_group": position_group_for(category),
                "category": category,
                "name": name,
                "school": field_text(profile, "highSchool"),
                "city": field_text(profile, "primaryAddress.city"),
                "state": field_text(profile, "primaryAddress.state"),
                "height": field_text(profile, "recruit.height"),
                "weight": field_text(profile, "recruit.weight"),
                "rank_type": rank_type,
                "rank_value": rank_value,
                "contact_id": profile.get("data-contact"),
                "recruit_id": profile.get("data-recruit"),
            })
    return rows


def main():
    parser = argparse.ArgumentParser(description="Export ARMS Recruiting Board(s) to CSV.")
    parser.add_argument("--sport-id", type=int, default=6918)
    parser.add_argument("--board-id", action="append", default=[],
                         help="Board id to export. Repeat for multiple boards (e.g. Offense + Defense).")
    parser.add_argument("--output", type=Path, default=None,
                         help="CSV output path. Required unless --list-boards.")
    parser.add_argument("--cookie-file", type=Path, default=None)
    parser.add_argument("--list-boards", action="store_true",
                         help="Fetch one board (the first --board-id, or a board id you know) "
                              "and print every board id/name found in its board-switcher menu, then exit.")
    args = parser.parse_args()

    cookie = load_cookie(args.cookie_file or DEFAULT_COOKIE_FILE)
    session = build_session(cookie)

    if args.list_boards:
        if not args.board_id:
            raise SystemExit("--list-boards needs at least one --board-id to fetch the switcher menu from.")
        html = fetch_board_html(session, args.sport_id, args.board_id[0])
        for board_id, name in list_boards(html):
            print(f"{board_id}\t{name}")
        return

    if not args.board_id:
        raise SystemExit("Provide at least one --board-id (or use --list-boards to find one).")
    if not args.output:
        raise SystemExit("--output is required when exporting boards.")

    all_rows = []
    for board_id in args.board_id:
        html = fetch_board_html(session, args.sport_id, board_id)
        boards = dict(list_boards(html))
        board_name = boards.get(board_id, board_id)
        rows = parse_board(html, board_name)
        print(f"Board {board_id} ({board_name}): {len(rows)} players")
        all_rows.extend(rows)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(all_rows).to_csv(args.output, index=False)
    print(f"Saved {len(all_rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
