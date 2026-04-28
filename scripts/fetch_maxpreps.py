import pandas as pd
import requests
import json
import re
import time

from recruit_sources import (
    MAXPREPS_PATH,
    UCREPORT_PATH,
    load_recruit_board,
    normalize_name,
)

if not UCREPORT_PATH.exists():
    print(f"Error: {UCREPORT_PATH} not found.")
    exit(1)

df = pd.read_csv(UCREPORT_PATH)
recruit_board = load_recruit_board()
board_by_name = {
    normalize_name(row["query_name"]): row
    for _, row in recruit_board.iterrows()
}

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
}

maxpreps_results = []

STATE_ABBR = {
    "alabama": "al", "alaska": "ak", "arizona": "az", "arkansas": "ar", "california": "ca",
    "colorado": "co", "connecticut": "ct", "delaware": "de", "florida": "fl", "georgia": "ga",
    "hawaii": "hi", "idaho": "id", "illinois": "il", "indiana": "in", "iowa": "ia",
    "kansas": "ks", "kentucky": "ky", "louisiana": "la", "maine": "me", "maryland": "md",
    "massachusetts": "ma", "michigan": "mi", "minnesota": "mn", "mississippi": "ms",
    "missouri": "mo", "montana": "mt", "nebraska": "ne", "nevada": "nv", "new hampshire": "nh",
    "new jersey": "nj", "new mexico": "nm", "new york": "ny", "north carolina": "nc",
    "north dakota": "nd", "ohio": "oh", "oklahoma": "ok", "oregon": "or", "pennsylvania": "pa",
    "rhode island": "ri", "south carolina": "sc", "south dakota": "sd", "tennessee": "tn",
    "texas": "tx", "utah": "ut", "vermont": "vt", "virginia": "va", "washington": "wa",
    "west virginia": "wv", "wisconsin": "wi", "wyoming": "wy",
}

SCHOOL_STOPWORDS = {"high", "school", "hs", "academy", "prep", "preparatory", "the"}


def clean_value(value):
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def row_value(row, column):
    if column in row and pd.notna(row.get(column)):
        return str(row.get(column)).strip()
    return ""


def board_value(board_row, column):
    if board_row is not None and column in board_row and pd.notna(board_row.get(column)):
        return str(board_row.get(column)).strip()
    return ""


def state_variants(value):
    normalized = normalize_name(value)
    if not normalized:
        return set()
    variants = {normalized}
    if normalized in STATE_ABBR:
        variants.add(STATE_ABBR[normalized])
    for state_name, abbr in STATE_ABBR.items():
        if normalized == abbr:
            variants.add(state_name)
    return variants


def significant_school_tokens(value):
    return [
        token for token in normalize_name(value).split()
        if len(token) > 2 and token not in SCHOOL_STOPWORDS
    ]


def flatten_strings(value):
    strings = []
    if isinstance(value, dict):
        for item in value.values():
            strings.extend(flatten_strings(item))
    elif isinstance(value, list):
        for item in value:
            strings.extend(flatten_strings(item))
    elif isinstance(value, str):
        strings.append(value)
    return strings


def expected_school_info(row, board_row):
    school = (
        board_value(board_row, "school")
        or row_value(row, "effective_school_name")
    )
    city = (
        board_value(board_row, "city")
        or row_value(row, "school_city")
    )
    state = (
        board_value(board_row, "state")
        or row_value(row, "state")
    )
    return school, city, state


def score_career_school_match(career, school, city, state):
    text = normalize_name(" ".join(flatten_strings(career)))
    school_norm = normalize_name(school)
    city_norm = normalize_name(city)
    state_options = state_variants(state)
    score = 0
    reasons = []

    if school_norm and (school_norm in text or text in school_norm):
        score += 100
        reasons.append("school")
    else:
        tokens = significant_school_tokens(school)
        matched_tokens = [token for token in tokens if token in text]
        if tokens and len(matched_tokens) == len(tokens):
            score += 80
            reasons.append("school tokens")
        elif len(matched_tokens) >= 2:
            score += 45
            reasons.append("partial school")

    if city_norm and city_norm in text:
        score += 25
        reasons.append("city")

    matched_state = [option for option in state_options if option in text]
    if matched_state:
        score += 15
        reasons.append("state")

    return score, reasons


def select_best_career(careers, row, board_row):
    football_careers = [c for c in careers if "Boys Football" in c.get("sports", [])]
    candidates = football_careers or careers
    school, city, state = expected_school_info(row, board_row)

    if not school:
        return candidates[0] if candidates else None, "no expected school available"

    scored = []
    for career in candidates:
        score, reasons = score_career_school_match(career, school, city, state)
        scored.append((score, reasons, career))

    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored:
        return None, f"no career results for expected school {school}"

    best_score, reasons, best_career = scored[0]
    if best_score < 45:
        return None, f"no career matched {school} ({city}, {state}); best score {best_score}"

    return best_career, f"matched {school} ({', '.join(reasons)})"


def recent_subgroup_stats(groups):
    stats_by_subgroup = {}
    for group in groups:
        for subgroup in group.get("subgroups", []):
            subgroup_name = str(subgroup.get("name", "")).strip()
            seasons = subgroup.get("stats", [])
            if not subgroup_name or not seasons:
                continue
            recent_season = seasons[0].get("stats", [])
            stat_lookup = {}
            for stat in recent_season:
                value = ""
                for value_key in ("value", "displayValue", "formattedValue"):
                    if stat.get(value_key) not in (None, ""):
                        value = stat.get(value_key)
                        break
                for key in (
                    "name",
                    "label",
                    "displayName",
                    "header",
                    "shortName",
                    "abbreviation",
                    "abbr",
                    "key",
                    "statName",
                    "title",
                ):
                    stat_key = stat.get(key)
                    if stat_key:
                        stat_lookup[str(stat_key)] = value
                        stat_lookup[normalize_name(stat_key)] = value
            stats_by_subgroup[subgroup_name] = stat_lookup
    return stats_by_subgroup


def find_subgroup(stats_by_subgroup, *needles):
    for name, stats in stats_by_subgroup.items():
        normalized = name.lower()
        if any(needle.lower() in normalized for needle in needles):
            return stats
    return {}


def stat_value(stats, *names):
    for name in names:
        if name in stats and stats[name] not in (None, ""):
            return stats[name]
        normalized = normalize_name(name)
        if normalized in stats and stats[normalized] not in (None, ""):
            return stats[normalized]
    return ""


def projected_position(row, board_row):
    for column in ("board_position_group", "board_category", "position_projected", "position_played"):
        if column in row and pd.notna(row.get(column)) and str(row.get(column)).strip():
            return str(row.get(column)).strip().upper()
    if board_row is not None:
        for column in ("position_group", "category"):
            if column in board_row and pd.notna(board_row.get(column)) and str(board_row.get(column)).strip():
                return str(board_row.get(column)).strip().upper()
    return ""


def classify_position(position):
    pos = position.upper().strip()
    if pos == "QB":
        return "qb"
    if pos == "RB":
        return "rb"
    if pos == "WR":
        return "wr"
    if pos == "TE":
        return "te"
    if pos in {"CB", "DB"}:
        return "cb"
    if pos in {"S", "SS", "FS", "SAFETY"}:
        return "safety"
    if pos in {"LB", "ILB", "OLB"}:
        return "lb"
    if pos in {"DE", "EDGE"}:
        return "de"
    if pos in {"DT", "DL", "NT"}:
        return "dt"
    return "defense"


def build_stat_row(stats_by_subgroup, position):
    pos_type = classify_position(position)

    passing = find_subgroup(stats_by_subgroup, "passing")
    rushing = find_subgroup(stats_by_subgroup, "rushing")
    receiving = find_subgroup(stats_by_subgroup, "receiving")
    tackles = find_subgroup(stats_by_subgroup, "tackles")
    defensive = find_subgroup(stats_by_subgroup, "defensive")
    sacks = find_subgroup(stats_by_subgroup, "sacks")

    if pos_type == "qb":
        return {
            "maxpreps_pass_gp": stat_value(passing, "GamesPlayed", "GP"),
            "maxpreps_c": stat_value(passing, "PassingComp", "Completions", "PassingCompletions", "C", "Cmp"),
            "maxpreps_att": stat_value(passing, "PassingAtt", "PassingAttempts", "Attempts", "Att"),
            "maxpreps_pass_yds": stat_value(passing, "PassingYards", "Yards", "Yds"),
            "maxpreps_c_pct": stat_value(passing, "CompletionPercentage", "C%"),
            "maxpreps_pass_avg": stat_value(passing, "YardsPerCompletion", "Average", "Avg"),
            "maxpreps_pass_y_g": stat_value(passing, "PassingYardsPerGame", "YardsPerGame", "Y/G"),
            "maxpreps_c_g": stat_value(passing, "CompletionsPerGame", "C/G"),
            "maxpreps_pass_td": stat_value(passing, "PassingTD", "PassingTouchdowns", "TouchdownPasses", "TD Passes", "Touchdowns", "TD"),
            "maxpreps_td_g": stat_value(passing, "PassingTDsPerGame", "PassingTouchdownsPerGame", "TD/G"),
            "maxpreps_int": stat_value(passing, "PassingInt", "Interceptions", "INTs", "Int"),
            "maxpreps_pass_lng": stat_value(passing, "PassingLong", "LongestPass", "Long", "Lng"),
            "maxpreps_qbr": stat_value(passing, "QbRating", "QuarterbackRating", "QB Rate", "QBR"),
            "maxpreps_rush_gp": stat_value(rushing, "GamesPlayed", "GP"),
            "maxpreps_car": stat_value(rushing, "Carries", "RushingAttempts", "Car"),
            "maxpreps_rush_yds": stat_value(rushing, "RushingYards", "Yards", "Yds"),
            "maxpreps_rush_avg": stat_value(rushing, "YardsPerCarry", "Average", "Avg"),
            "maxpreps_rush_y_g": stat_value(rushing, "RushingYardsPerGame", "YardsPerGame", "Y/G"),
            "maxpreps_rush_lng": stat_value(rushing, "LongestRush", "Long", "Lng"),
            "maxpreps_rush_100_plus": stat_value(rushing, "Rushing100YardGames", "OneHundredYardGames", "100+"),
            "maxpreps_rush_td": stat_value(rushing, "RushingTouchdowns", "Touchdowns", "TD"),
        }

    if pos_type == "rb":
        return {
            "maxpreps_rush_gp": stat_value(rushing, "GamesPlayed", "GP"),
            "maxpreps_car": stat_value(rushing, "Carries", "RushingAttempts", "Car"),
            "maxpreps_rush_yds": stat_value(rushing, "RushingYards", "Yards", "Yds"),
            "maxpreps_rush_avg": stat_value(rushing, "YardsPerCarry", "Average", "Avg"),
            "maxpreps_rush_y_g": stat_value(rushing, "RushingYardsPerGame", "YardsPerGame", "Y/G"),
            "maxpreps_rush_lng": stat_value(rushing, "LongestRush", "Long", "Lng"),
            "maxpreps_rush_100_plus": stat_value(rushing, "Rushing100YardGames", "OneHundredYardGames", "100+"),
            "maxpreps_rush_td": stat_value(rushing, "RushingTouchdowns", "Touchdowns", "TD"),
            "maxpreps_rec_gp": stat_value(receiving, "GamesPlayed", "GP"),
            "maxpreps_rec": stat_value(receiving, "Receptions", "Rec"),
            "maxpreps_rec_yds": stat_value(receiving, "ReceivingYards", "Yards", "Yds"),
            "maxpreps_rec_avg": stat_value(receiving, "YardsPerReception", "Average", "Avg"),
            "maxpreps_rec_y_g": stat_value(receiving, "ReceivingYardsPerGame", "YardsPerGame", "Y/G"),
            "maxpreps_rec_lng": stat_value(receiving, "LongestReception", "Long", "Lng"),
            "maxpreps_rec_td": stat_value(receiving, "ReceivingTouchdowns", "Touchdowns", "TD"),
        }

    if pos_type in {"wr", "te"}:
        return {
            "maxpreps_rec_gp": stat_value(receiving, "GamesPlayed", "GP"),
            "maxpreps_rec": stat_value(receiving, "Receptions", "Rec"),
            "maxpreps_rec_yds": stat_value(receiving, "ReceivingYards", "Yards", "Yds"),
            "maxpreps_rec_avg": stat_value(receiving, "YardsPerReception", "Average", "Avg"),
            "maxpreps_rec_y_g": stat_value(receiving, "ReceivingYardsPerGame", "YardsPerGame", "Y/G"),
            "maxpreps_rec_lng": stat_value(receiving, "LongestReception", "Long", "Lng"),
            "maxpreps_rec_td": stat_value(receiving, "ReceivingTouchdowns", "Touchdowns", "TD"),
            "maxpreps_rush_gp": stat_value(rushing, "GamesPlayed", "GP"),
            "maxpreps_car": stat_value(rushing, "Carries", "RushingAttempts", "Car"),
            "maxpreps_rush_yds": stat_value(rushing, "RushingYards", "Yards", "Yds"),
            "maxpreps_rush_avg": stat_value(rushing, "YardsPerCarry", "Average", "Avg"),
            "maxpreps_rush_y_g": stat_value(rushing, "RushingYardsPerGame", "YardsPerGame", "Y/G"),
            "maxpreps_rush_lng": stat_value(rushing, "LongestRush", "Long", "Lng"),
            "maxpreps_rush_100_plus": stat_value(rushing, "Rushing100YardGames", "OneHundredYardGames", "100+"),
            "maxpreps_rush_td": stat_value(rushing, "RushingTouchdowns", "Touchdowns", "TD"),
        }

    if pos_type in {"cb", "safety"}:
        return {
            "maxpreps_gp": stat_value(tackles, "GamesPlayed", "GP") or stat_value(defensive, "GamesPlayed", "GP"),
            "maxpreps_solo": stat_value(tackles, "Tackles", "Solo", "SOLO"),
            "maxpreps_asst": stat_value(tackles, "Assists", "ASST"),
            "maxpreps_total_tackles": stat_value(tackles, "TotalTackles", "TKLS"),
            "maxpreps_t_g": stat_value(tackles, "TacklesPerGame", "T/G"),
            "maxpreps_tfl": stat_value(tackles, "TacklesForLoss", "TFL"),
            "maxpreps_ints": stat_value(defensive, "INTs", "Interceptions", "INT"),
            "maxpreps_pd": stat_value(defensive, "PassesDefensed", "PD"),
        }

    # LB, DE, DT, and generic defense fallback
    return {
        "maxpreps_tackle_gp": stat_value(tackles, "GamesPlayed", "GP") or stat_value(defensive, "GamesPlayed", "GP"),
        "maxpreps_solo": stat_value(tackles, "Tackles", "Solo", "SOLO"),
        "maxpreps_asst": stat_value(tackles, "Assists", "ASST"),
        "maxpreps_total_tackles": stat_value(tackles, "TotalTackles", "TKLS"),
        "maxpreps_t_g": stat_value(tackles, "TacklesPerGame", "T/G"),
        "maxpreps_tfl": stat_value(tackles, "TacklesForLoss", "TFL"),
        "maxpreps_sack_gp": stat_value(sacks, "GamesPlayed", "GP"),
        "maxpreps_sacks": stat_value(sacks, "Sacks") or stat_value(defensive, "Sacks"),
        "maxpreps_ydl": stat_value(sacks, "YardsLost", "YDL") or stat_value(defensive, "YardsLost", "YDL"),
        "maxpreps_s_g": stat_value(sacks, "SacksPerGame", "S/G") or stat_value(defensive, "SacksPerGame", "S/G"),
        "maxpreps_hurs": stat_value(defensive, "Hurries", "QuarterbackHurries", "HURS"),
    }


for index, row in df.iterrows():
    query_name = str(row.get('query_name', '')).strip()
    first = str(row.get('first', '')).strip()
    last = str(row.get('last', '')).strip()
    player_id = row.get('player_id')
    board_row = board_by_name.get(normalize_name(query_name or f"{first} {last}"))
    position = projected_position(row, board_row)
    search_name = query_name or f"{first} {last}".strip()
    
    print(f"\n[{index+1}/{len(df)}] Searching MaxPreps for: {search_name}...")
    
    search_url = f"https://www.maxpreps.com/search/?q={'+'.join(search_name.split())}"
    
    try:
        r = requests.get(search_url, headers=headers)
        if r.status_code != 200:
            print(f"  -> Search failed with status {r.status_code}")
            time.sleep(1)
            continue
            
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text)
        if not match:
            print(f"  -> Could not find __NEXT_DATA__ in search results.")
            time.sleep(1)
            continue
            
        data = json.loads(match.group(1))
        props = data.get("props", {}).get("pageProps", {})
        careers = props.get("initialCareerResults", [])
        
        if not careers:
            print(f"  -> No career results found.")
            time.sleep(1)
            continue
            
        best_career, match_reason = select_best_career(careers, row, board_row)
        if not best_career:
            print(f"  -> Skipping: {match_reason}")
            time.sleep(1)
            continue
        print(f"  -> Career match: {match_reason}")
        
        canonical_url = best_career.get('careerCanonicalUrl')
        if not canonical_url:
            print(f"  -> No canonical URL found for the best career match.")
            time.sleep(1)
            continue
            
        if '?' in canonical_url:
            base, query = canonical_url.split('?', 1)
            stats_url = f"https://www.maxpreps.com{base}football/stats/?{query}"
        else:
            stats_url = f"https://www.maxpreps.com{canonical_url}football/stats/"
            
        print(f"  -> Fetching stats from: {stats_url}")
        
        time.sleep(0.5) 
        
        r_stats = requests.get(stats_url, headers=headers)
        if r_stats.status_code != 200:
            print(f"  -> Stats fetch failed with status {r_stats.status_code}")
            continue
            
        match_stats = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r_stats.text)
        if not match_stats:
            print(f"  -> Could not find __NEXT_DATA__ in stats page.")
            continue
            
        stats_data = json.loads(match_stats.group(1))
        stats_props = stats_data.get("props", {}).get("pageProps", {})
        
        card_props = stats_props.get("statsCardProps", {})
        career_rollup = card_props.get("careerRollup", {})
        groups = career_rollup.get("groups", [])
        
        stats_by_subgroup = recent_subgroup_stats(groups)
        extracted_stats = build_stat_row(stats_by_subgroup, position)

        stat_summary = ", ".join(
            f"{k.replace('maxpreps_', '')}={v}"
            for k, v in extracted_stats.items()
            if v not in (None, "")
        )
        print(f"  -> Extracted {position or 'UNK'}: {stat_summary}")
        
        result = {
            'player_id': player_id,
            'query_name': query_name or search_name,
            'source_recruit_id': row.get('source_recruit_id') if 'source_recruit_id' in row else (board_row.get('recruit_id') if board_row is not None else ""),
            'board_position_group': row.get('board_position_group') if 'board_position_group' in row else (board_row.get('position_group') if board_row is not None else ""),
            'board_category': row.get('board_category') if 'board_category' in row else (board_row.get('category') if board_row is not None else ""),
            'maxpreps_url': stats_url
        }
        result.update(extracted_stats)
        maxpreps_results.append(result)
        
    except Exception as e:
        print(f"  -> Exception: {e}")
        
    time.sleep(1) 

df_maxpreps = pd.DataFrame(maxpreps_results)
df_maxpreps.to_csv(MAXPREPS_PATH, index=False)
print(f"\nDone! Saved to {MAXPREPS_PATH}")
