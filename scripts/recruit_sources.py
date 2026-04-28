from pathlib import Path
import re

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
RECRUIT_DATA_DIR = DATA_DIR / "recruits"
RECRUIT_BOARD_PATH = RECRUIT_DATA_DIR / "2027_recruits.csv"
UCREPORT_PATH = RECRUIT_DATA_DIR / "ucreport_data.csv"
MAXPREPS_PATH = RECRUIT_DATA_DIR / "maxpreps_data.csv"

SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}


def normalize_name(value):
    value = str(value or "").lower()
    value = value.replace("'", "").replace("’", "").replace("‘", "")
    value = value.replace('"', "").replace("“", "").replace("”", "")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def split_player_name(name):
    parts = str(name).strip().split()
    if len(parts) < 2:
        return "", ""
    if parts[-1].lower() in SUFFIXES and len(parts) >= 3:
        return " ".join(parts[:-2]), parts[-2]
    return " ".join(parts[:-1]), parts[-1]


def load_recruit_board():
    df = pd.read_csv(RECRUIT_BOARD_PATH)
    df["name"] = df["name"].astype(str).str.strip()
    df = df[df["name"].str.len() > 0].copy()
    df["query_name"] = df["name"]
    df["query_first"] = ""
    df["query_last"] = ""
    for idx, row in df.iterrows():
        first, last = split_player_name(row["name"])
        df.at[idx, "query_first"] = first
        df.at[idx, "query_last"] = last
    return df


def attach_board_fields(player, board_row):
    player["query_name"] = board_row["query_name"]
    player["source_recruit_id"] = board_row.get("recruit_id")
    player["source_contact_id"] = board_row.get("contact_id")
    player["board"] = board_row.get("board")
    player["board_position_group"] = board_row.get("position_group")
    player["board_category"] = board_row.get("category")
    player["board_rank_type"] = board_row.get("rank_type")
    player["board_rank_value"] = board_row.get("rank_value")
    return player


def extract_player_rows(data):
    def find_rows(value):
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            for key in ("results", "players", "data", "content"):
                rows = find_rows(value.get(key))
                if rows is not None:
                    return rows
        return None

    rows = find_rows(data) or []
    return [row for row in rows if isinstance(row, dict)]


def describe_payload(data):
    if isinstance(data, dict):
        return f"dict keys={list(data.keys())[:8]}"
    if isinstance(data, list):
        item_types = sorted({type(item).__name__ for item in data[:5]})
        return f"list len={len(data)} item_types={item_types}"
    return type(data).__name__
