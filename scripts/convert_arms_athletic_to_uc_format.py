import argparse
import math
import re
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT_DIR / "data/arms/draft_arms_athletic.csv"
DEFAULT_OUTPUT = ROOT_DIR / "data/arms/draft_arms_athletic_uc_format.csv"
DEFAULT_MATCH_CSV = ROOT_DIR / "data/arms/draft_archive_matches.csv"

UC_COLUMNS = [
    "player_id",
    "class_field",
    "college_level_projection",
    "uc_score",
    "last",
    "first",
    "effective_school_name",
    "college_enrolled",
    "school_city",
    "state",
    "county",
    "position_played",
    "position_projected",
    "height",
    "weight",
    "wingspan",
    "forty",
    "shuttle",
    "vertical",
    "track60m",
    "track100m",
    "track200m",
    "broad",
    "trackLJ",
    "highJump",
    "trackSP",
    "discus",
    "updated",
    "head_coach",
    "player_head_shot",
    "camp_event_videos",
    "hudl_video_link",
    "college_offers",
    "commit",
    "max_speed_video",
    "query_name",
    "wiki_year",
    "wiki_round",
    "wiki_pick",
    "wiki_team",
    "wiki_pos",
    "wiki_college",
    "arm_length",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert ARMS Athletic scrape output into UCReport-style draft columns."
    )
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--match-csv",
        type=Path,
        default=DEFAULT_MATCH_CSV,
        help="Optional cleaned match CSV used to filter stale/ambiguous raw scrape rows.",
    )
    return parser.parse_args()


def clean_text(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()


def parse_number(value):
    text = clean_text(value)
    if not text:
        return None
    text = text.replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    number = float(match.group(0))
    if number == 0:
        return None
    return number


def parse_height(value):
    text = clean_text(value)
    if not text:
        return None
    text = (
        text.replace("’", "'")
        .replace("′", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("″", '"')
    )
    match = re.search(r"(\d+)\s*'\s*(\d+(?:\.\d+)?)?", text)
    if match:
        feet = float(match.group(1))
        inches = float(match.group(2) or 0)
        total = feet * 12 + inches
        return total if total else None
    number = parse_number(text)
    if number and number < 9:
        return number * 12
    return number


def parse_compact_eighths(text):
    """ARMS sometimes stores 30 7/8 as 3078 and 8 6/8 as 0868."""
    if not re.fullmatch(r"\d{4}", text):
        return None
    whole = int(text[:2])
    numerator = int(text[2])
    denominator = int(text[3])
    if denominator == 0 or numerator >= denominator:
        return None
    return whole + numerator / denominator


def parse_inches(value):
    text = clean_text(value)
    if not text:
        return None
    text = (
        text.replace("’", "'")
        .replace("′", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("″", '"')
    )

    compact = parse_compact_eighths(text)
    if compact is not None:
        return compact

    match = re.search(r"(\d+)\s+(\d+)\s*/\s*(\d+)", text)
    if match:
        whole = float(match.group(1))
        numerator = float(match.group(2))
        denominator = float(match.group(3))
        return whole + numerator / denominator if denominator else whole

    match = re.search(r"(\d+)\s*'\s*(\d+(?:\.\d+)?)", text)
    if match:
        feet = float(match.group(1))
        inches = float(match.group(2) or 0)
        return feet * 12 + inches

    return parse_number(text)


def parse_time(value):
    text = clean_text(value)
    if not text:
        return None
    minute_match = re.search(r"(\d+)\s*:\s*(\d+(?:\.\d+)?)", text)
    if minute_match:
        return int(minute_match.group(1)) * 60 + float(minute_match.group(2))
    return parse_number(text)


def unique_text(text):
    text = clean_text(text)
    if not text:
        return ""
    midpoint = len(text) // 2
    if len(text) % 2 == 0 and text[:midpoint].strip() == text[midpoint:].strip():
        return text[:midpoint].strip()
    return text


EVENT_ALIASES = {
    "55m": "track55m",
    "55 meter dash": "track55m",
    "60m": "track60m",
    "60 meter dash": "track60m",
    "100m": "track100m",
    "100 meter dash": "track100m",
    "110mh": "track110mh",
    "110hh": "track110mh",
    "110 hurdles": "track110mh",
    "200m": "track200m",
    "200 meter dash": "track200m",
    "300m": "track300m",
    "300 meter dash": "track300m",
    "300ih": "track300ih",
    "400m": "track400m",
    "400 meter dash": "track400m",
    "400r": "track400r",
    "400 relay": "track400r",
    "800r": "track800r",
    "800 meter run": "track800m",
    "lj": "trackLJ",
    "long jump": "trackLJ",
    "tj": "tripleJump",
    "triple jump": "tripleJump",
    "hj": "highJump",
    "high jump": "highJump",
    "shot put": "trackSP",
    "sp": "trackSP",
    "discus": "discus",
    "javelin": "javelin",
}

EVENT_PATTERN = (
    r"55\s*meter\s*dash|55m|60\s*meter\s*dash|60m|100\s*meter\s*dash|100m|"
    r"110mh|110hh|110\s*hurdles|200\s*meter\s*dash|200m|300ih|300m|"
    r"400\s*meter\s*dash|400m|400r|400\s*relay|800\s*meter\s*run|800r|"
    r"long\s*jump|triple\s*jump|high\s*jump|shot\s*put|discus|javelin|lj|tj|hj|sp"
)
PERF_PATTERN = r"\d+(?:\.\d+)?(?::\d+(?:\.\d+)?)?(?:\s*'\s*\d*(?:\.\d+)?\"?)?"


def event_key(label):
    label = " ".join(clean_text(label).lower().split())
    label = re.sub(r"\s+", " ", label)
    return EVENT_ALIASES.get(label)


def parse_track_value(key, value):
    if key in {"trackLJ", "tripleJump", "highJump", "trackSP", "discus", "javelin"}:
        return parse_inches(value)
    return parse_time(value)


def parse_verified_track_results(value):
    text = unique_text(value)
    if not text:
        return {}

    results = {}
    patterns = [
        re.compile(
            rf"(?P<event>{EVENT_PATTERN})\s*(?:-|:)\s*(?P<value>{PERF_PATTERN})",
            re.IGNORECASE,
        ),
        re.compile(
            rf"(?P<value>{PERF_PATTERN})\s*(?:-|:)\s*(?P<event>{EVENT_PATTERN})",
            re.IGNORECASE,
        ),
    ]

    for pattern in patterns:
        for match in pattern.finditer(text):
            key = event_key(match.group("event"))
            if not key or key in results:
                continue
            parsed = parse_track_value(key, match.group("value"))
            if parsed is not None:
                results[key] = parsed

    return results


def split_arms_name(value):
    text = clean_text(value)
    if "," in text:
        last, first = [part.strip() for part in text.split(",", 1)]
        return first, last
    parts = text.split()
    if len(parts) < 2:
        return text, ""
    return " ".join(parts[:-1]), parts[-1]


def first_non_empty(*values):
    for value in values:
        text = clean_text(value)
        if text:
            return text
    return ""


def selected_position(value):
    text = clean_text(value)
    if not text:
        return ""
    option_tail = " ATH CB Db De DL Dt EDGE Fb Fs H ILB K Lb Ls Mlb Nt Oc Og OL Olb Ot P Pk Pt QB RB SAF Ss TE WR"
    if option_tail in text:
        return text.split(option_tail, 1)[0].strip()
    parts = text.split()
    return parts[0] if parts else ""


POSITION_COMPATIBILITY = {
    "QB": {"QB", "ATH"},
    "RB": {"RB", "FB", "ATH"},
    "WR": {"WR", "TE", "ATH"},
    "TE": {"TE", "WR", "DE", "ATH"},
    "CB": {"CB", "DB", "SAF", "S", "FS", "SS", "ATH", "WR"},
    "SAFETY": {"SAF", "S", "FS", "SS", "DB", "CB", "ATH", "WR"},
    "S": {"SAF", "S", "FS", "SS", "DB", "CB", "ATH", "WR"},
    "LB": {"LB", "ILB", "OLB", "MLB", "EDGE", "DE", "ATH"},
    "DE": {"DE", "EDGE", "DL", "OLB", "LB", "ATH"},
    "DT": {"DT", "DL", "NT", "DE", "OL", "OG", "OT", "ATH"},
    "OL": {"OL", "OT", "OG", "OC", "C", "G", "T", "DL", "DT", "ATH"},
}


def position_ok(draft_position, arms_position):
    draft_position = clean_text(draft_position).upper()
    arms_parts = {
        part.upper()
        for part in re.split(r"[^A-Za-z0-9]+", clean_text(arms_position))
        if part
    }
    if not draft_position or not arms_parts:
        return ""
    allowed = POSITION_COMPATIBILITY.get(draft_position, {draft_position, "ATH"})
    return bool(arms_parts & allowed)


def filter_to_matches(raw, match_csv):
    if not match_csv or not match_csv.exists():
        return raw

    matches = pd.read_csv(match_csv)
    key_cols = ["draft_name", "draft_position", "draft_source", "id"]
    if any(column not in raw.columns for column in key_cols):
        return raw
    if any(column not in matches.columns for column in key_cols):
        return raw

    filtered = raw.merge(matches[key_cols].drop_duplicates(), on=key_cols, how="inner")
    filtered = filtered.drop_duplicates(subset=key_cols)
    return filtered


def convert(input_csv, output_csv, match_csv=None):
    raw = pd.read_csv(input_csv)
    raw = filter_to_matches(raw, match_csv)
    rows = []

    for _, row in raw.iterrows():
        first, last = split_arms_name(row.get("name"))
        position = first_non_empty(row.get("position"), row.get("draft_position"))

        out = {column: "" for column in UC_COLUMNS}
        out.update(
            {
                "player_id": row.get("profile_id"),
                "class_field": row.get("gradYear"),
                "last": last,
                "first": first,
                "college_enrolled": row.get("draft_college"),
                "position_played": position,
                "position_projected": position,
                "height": parse_height(row.get("height")),
                "weight": parse_number(row.get("weight")),
                "wingspan": parse_inches(row.get("wingspan")),
                "forty": parse_number(row.get("40_time")),
                "shuttle": parse_number(row.get("shuttle")),
                "vertical": parse_inches(row.get("vertical")),
                "broad": parse_inches(row.get("broad_jump")),
                "query_name": row.get("draft_name"),
                "wiki_year": row.get("draft_year"),
                "wiki_team": row.get("draft_team"),
                "wiki_pos": row.get("draft_position"),
                "wiki_college": row.get("draft_college"),
                "arm_length": parse_inches(row.get("arm_length")),
            }
        )

        track_results = parse_verified_track_results(row.get("verified_track_results"))
        for key, value in track_results.items():
            if key not in out or clean_text(out.get(key)) == "":
                out[key] = value

        out["arms_archive_id"] = row.get("id")
        out["arms_profile_id"] = row.get("profile_id")
        out["arms_positions"] = row.get("positions")
        arms_position = selected_position(row.get("positions"))
        out["arms_primary_position"] = arms_position
        out["arms_position_ok"] = position_ok(row.get("draft_position"), arms_position)
        out["hand_size"] = parse_inches(row.get("hand_size"))
        out["other_sports_played"] = row.get("other_sports_played")
        out["verified_track_results"] = row.get("verified_track_results")
        out["draft_source"] = row.get("draft_source")
        rows.append(out)

    output = pd.DataFrame(rows).replace("", pd.NA)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_csv, index=False)
    return output


def main():
    args = parse_args()
    output = convert(args.input_csv, args.output_csv, args.match_csv)
    measure_cols = [
        "height",
        "weight",
        "wingspan",
        "forty",
        "shuttle",
        "vertical",
        "broad",
        "arm_length",
        "hand_size",
        "track55m",
        "track60m",
        "track100m",
        "track110mh",
        "track200m",
        "track300m",
        "track300ih",
        "track400m",
        "track400r",
        "track800m",
        "track800r",
        "trackLJ",
        "tripleJump",
        "highJump",
        "trackSP",
        "discus",
        "javelin",
    ]
    measure_cols = [column for column in measure_cols if column in output.columns]
    counts = output[measure_cols].notna().sum()
    print(f"Saved {len(output)} rows to {args.output_csv}")
    print(counts.to_string())


if __name__ == "__main__":
    main()
