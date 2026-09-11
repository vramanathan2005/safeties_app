"""Documented UCReport API transport and dashboard field adapter."""
import json
import os
from pathlib import Path

import requests
from recruit_sources import normalize_name

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = 'https://football-api-dot-football-344319.uc.r.appspot.com'
ENDPOINTS = {'get_masterlist', 'get_measurable', 'get_measurablecamp',
             'get_measurabletrack', 'get_measurablespeed', 'get_collegeoffers'}
COLUMNS = '''dbkey player_id first last nickname class_field school_name juco_school_name
college_enrolled school_city state county position_played position_projected
college_level_projection uc_score height weight wingspan hand arm arm_length_verified
forty shuttle vertical broad track60m track100m track200m trackLJ highJump trackSP discus
updated head_coach player_head_shot camp_event_videos hudl_video_link college_offers commit
max_speed_video'''.split()


class APIError(RuntimeError):
    pass


class UCReportClient:
    def __init__(self, key, college, base_url=BASE_URL, session=None):
        if not isinstance(key, str) or not key.strip() or key == 'YOUR_API_KEY':
            raise APIError('Add your API key to .secrets/ucreport_api.json or UCREPORT_API_KEY.')
        if not isinstance(college, str) or not college.strip() or college == 'YOUR_COLLEGE_NAME':
            raise APIError('Set the assigned college in .secrets/ucreport_api.json or UCREPORT_COLLEGE.')
        self.college = college.strip()
        self.key = key.strip()
        self.base_url = base_url.rstrip('/')
        self.session = session or requests.Session()
        self.session.headers.update({'key': self.key, 'Accept': 'application/json'})

    @classmethod
    def from_config(cls):
        path = ROOT / '.secrets/ucreport_api.json'
        try:
            config = json.loads(path.read_text()) if path.exists() else {}
        except (ValueError, OSError) as exc:
            raise APIError('Cannot read .secrets/ucreport_api.json; check its JSON format.') from exc
        return cls(os.environ.get('UCREPORT_API_KEY', config.get('api_key')),
                   os.environ.get('UCREPORT_COLLEGE', config.get('college')),
                   os.environ.get('UCREPORT_API_BASE_URL', config.get('base_url', BASE_URL)))

    def rows(self, endpoint='get_masterlist', filters=None, cols=None, limit=500):
        if endpoint not in ENDPOINTS:
            raise ValueError('Unknown UCReport endpoint')
        if not 0 < limit < 1000:
            raise ValueError('limit must be between 1 and 999')
        page = 0
        while True:
            body = {'college': self.college, 'page': page, 'limit': limit, 'filter': filters or {}}
            if cols is not None:
                body['cols'] = cols
            try:
                response = self.session.post(f'{self.base_url}/api/{endpoint}', json=body, timeout=30)
            except requests.RequestException as exc:
                raise APIError('UCReport request failed; check the network and API availability.') from exc
            try:
                payload = response.json()
            except ValueError as exc:
                raise APIError(f'UCReport HTTP {response.status_code}: response is not JSON.') from exc
            if response.status_code != 200 or not isinstance(payload, dict) or 'error' in payload:
                detail = str(payload.get('error', 'invalid response')) if isinstance(payload, dict) else 'invalid response'
                raise APIError(f'UCReport HTTP {response.status_code}: {detail.replace(self.key, "[redacted]")[:300]}')
            rows = payload.get('data')
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise APIError('UCReport returned malformed rows.')
            if not isinstance(payload.get('has_next'), bool):
                raise APIError('UCReport returned malformed pagination.')
            if payload['has_next'] and not rows:
                raise APIError('UCReport returned an empty page with has_next=true.')
            yield from rows
            if not payload['has_next']:
                return
            page += 1
            if page >= 10000:
                raise APIError('UCReport exceeded the pagination safety limit.')

    def find_players(self, first, last, classes):
        filters = {'last__iexact': last, 'class_field__in': sorted(classes)}
        matches = []
        for row in self.rows(filters=filters, cols=COLUMNS):
            tokens = normalize_name(first).split()
            names = normalize_name(f"{row.get('first') or ''} {row.get('nickname') or ''}").split()
            if not any(token in names for token in tokens):
                continue
            player = {column: row.get(column) for column in COLUMNS}
            player['effective_school_name'] = row.get('juco_school_name') or row.get('school_name') or ''
            player['arm_length'] = row.get('arm_length_verified') or row.get('arm')
            if player['player_id'] is None:
                raise APIError('Matched player lacks player_id; refusing an invalid CSV join.')
            matches.append(player)
        matches.sort(key=lambda p: (normalize_name(p['first']) == normalize_name(first), str(p['updated'] or '')), reverse=True)
        return matches
