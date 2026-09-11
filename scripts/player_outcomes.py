"""Classify verified season records; missing evidence remains unverified."""
import math


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def classify(row):
    grad_year = number(row.get('class_field'))
    if grad_year is not None and grad_year >= 2027:
        return 'HS Recruit'
    if number(row.get('draft_round')) is not None and number(row['draft_round']) > 0:
        return 'NFL drafted'
    snaps = number(row.get('nfl_snaps'))
    undrafted = str(row.get('undrafted', '')).lower() in ('true', '1')
    if undrafted and snaps is not None and snaps > 0:
        return 'NFL UDFA'
    if snaps is None:
        return 'Outcome unverified'
    if snaps > 0:
        return 'NFL — draft status unverified'
    starts = number(row.get('college_starts'))
    games = number(row.get('college_games'))
    conference = str(row.get('conference') or '').strip()
    season = number(row.get('season'))
    if not conference or season is None:
        return 'College — outcome unverified'
    suffix = f' · {int(season)}'
    team_games = number(row.get('team_games'))
    if starts is not None and starts >= 0 and team_games is not None and team_games > 0:
        if starts > team_games:
            return 'College — outcome unverified'
        if starts * 2 >= team_games:
            return f'{conference} Starter{suffix}'
        if games is not None and games > 0:
            return f'{conference} Backup{suffix}'
    if starts == 0 and games == 0:
        return f'{conference} No appearances{suffix}'
    return 'College — outcome unverified'
