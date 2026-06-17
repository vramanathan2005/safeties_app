import re
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
DRAFT_DIR = ROOT_DIR / "data" / "draft"
ARMS_DIR = ROOT_DIR / "data" / "arms"
ARCHIVE_CSV = ARMS_DIR / "recruiting_6918_archive_grad_0.csv"
OUTPUT_CSV = ARMS_DIR / "draft_archive_matches.csv"

SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}


def expected_class_years(draft_year):
    try:
        draft_year = int(float(draft_year))
    except (TypeError, ValueError):
        return None
    return set(range(draft_year - 5, draft_year - 2))


def parse_year(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def normalize_name(value):
    value = str(value or "").lower()
    value = value.replace("'", "").replace("’", "").replace("‘", "")
    value = value.replace('"', "").replace("“", "").replace("”", "")
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    parts = [part for part in value.split() if part not in SUFFIXES]
    return " ".join(parts)


def archive_name_to_full_name(value):
    value = str(value or "").strip()
    if "," not in value:
        return value
    last, first = value.split(",", 1)
    return f"{first.strip()} {last.strip()}".strip()


def iter_draft_players():
    seen = set()
    for path in sorted(DRAFT_DIR.glob("*_stats.csv")) + sorted(DRAFT_DIR.glob("*_combine.csv")):
        position = path.name.split("_", 1)[0]
        df = pd.read_csv(path, header=1)
        if "NAME" not in df.columns:
            continue
        year_col = df.columns[0]
        df[year_col] = df[year_col].replace("", pd.NA).ffill()
        for _, row in df.iterrows():
            name = str(row.get("NAME", "")).strip()
            if not name or name.lower() == "nan":
                continue
            key = (normalize_name(name), position)
            if key in seen:
                continue
            seen.add(key)
            yield {
                "draft_name": name,
                "draft_position": position.upper(),
                "draft_source": path.name,
                "draft_year": row.get(year_col),
                "draft_team": row.get("TEAM"),
                "draft_college": row.get("SCHOOL"),
            }

    ol_path = DRAFT_DIR / "ol_wikipedia_picks.csv"
    if ol_path.exists():
        df = pd.read_csv(ol_path)
        for _, row in df.iterrows():
            name = str(row.get("player", "")).strip()
            if not name or name.lower() == "nan":
                continue
            key = (normalize_name(name), "ol")
            if key in seen:
                continue
            seen.add(key)
            yield {
                "draft_name": name,
                "draft_position": "OL",
                "draft_source": ol_path.name,
                "draft_year": row.get("year"),
                "draft_team": row.get("team"),
                "draft_college": row.get("college"),
            }


def main():
    ARMS_DIR.mkdir(parents=True, exist_ok=True)
    archive = pd.read_csv(ARCHIVE_CSV)
    archive = archive.drop_duplicates(subset=["id"])
    archive["archive_full_name"] = archive["name"].map(archive_name_to_full_name)
    archive["match_name"] = archive["archive_full_name"].map(normalize_name)

    archive_by_name = {}
    for _, row in archive.iterrows():
        archive_by_name.setdefault(row["match_name"], []).append(row)

    matches = []
    for draft_player in iter_draft_players():
        match_name = normalize_name(draft_player["draft_name"])
        valid_classes = expected_class_years(draft_player.get("draft_year"))
        for archive_row in archive_by_name.get(match_name, []):
            archive_class = parse_year(archive_row.get("gradYear"))
            if valid_classes and archive_class and archive_class not in valid_classes:
                continue
            matches.append(
                {
                    **draft_player,
                    "id": int(archive_row["id"]),
                    "name": archive_row["name"],
                    "archive_full_name": archive_row["archive_full_name"],
                    "gradYear": archive_row.get("gradYear"),
                    "email": archive_row.get("email"),
                    "deletedOn": archive_row.get("deletedOn"),
                    "deletedBy": archive_row.get("deletedBy"),
                }
            )

    output = pd.DataFrame(matches)
    output.to_csv(OUTPUT_CSV, index=False)
    print(f"Matched {len(output)} archive rows to draft players.")
    print(f"Saved {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
