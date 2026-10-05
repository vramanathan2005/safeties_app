"""Connect draft records to unique UCReport identities within position and class window."""
from collections import defaultdict
from scripts.recruit_sources import normalize_name

MEASUREMENTS = ('HT','WT','WING','ARM','HAND','40','SHUT','VERT','BROAD','100M','200M','SHOT','DISCUS','HJ','LJ','TJ')


def reconcile(groups):
    linked = {}
    for code, group in groups.items():
        if code == 'all':
            continue
        candidates = defaultdict(list)
        for player in group['players']:
            if player.get('is_recruit'):
                candidates[normalize_name(player.get('NAME'))].append(player)
        remove = set()
        for draft in group['players']:
            if draft.get('is_recruit') or not draft.get('YEAR'):
                continue
            matches = [p for p in candidates[normalize_name(draft.get('NAME'))]
                       if p.get('class_field') and 2 <= float(draft['YEAR']) - float(p['class_field']) <= 8]
            # Never choose arbitrarily between namesakes.
            by_id = {p['player_id']: p for p in matches if p.get('player_id') is not None}
            if len(by_id) != 1:
                continue
            pid, source = next(iter(by_id.items()))
            # A drafted player is measured as the high school recruit he was: UCReport's numbers only, never the
            # draft export's (those mix in later testing), so he compares like for like with today's recruits.
            for field in MEASUREMENTS:
                draft[field] = source.get(field)
            draft['player_id'] = pid
            draft['class_field'] = source['class_field']
            draft['measurement_source'] = 'UCReport'
            merged = dict(source)
            merged.update(draft)
            linked[pid] = merged
            remove.add(pid)
        # Drafted players UCReport never measured keep their draft record but no measurements, so they drop out of
        # the charts instead of showing numbers from somewhere else.
        for draft in group['players']:
            if not draft.get('is_recruit') and draft.get('player_id') is None:
                for field in MEASUREMENTS:
                    draft[field] = None
        group['players'] = [p for p in group['players'] if not (p.get('is_recruit') and p.get('player_id') in remove)]
    # Carry the same identity and draft outcome into every other view.
    for group in groups.values():
        group['players'] = [dict(linked[p['player_id']]) if p.get('is_recruit') and p.get('player_id') in linked else p for p in group['players']]
    return len(linked)
