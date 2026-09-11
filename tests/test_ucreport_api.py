import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ucreport_api import APIError, UCReportClient
from ucreport_pipeline import save_rows


class APITests(unittest.TestCase):
    def client(self, pages, status=200):
        session = Mock()
        session.headers = {}
        session.post.side_effect = [Mock(status_code=status, json=Mock(return_value=p)) for p in pages]
        return UCReportClient('test-key', 'Test College', session=session), session

    def test_pagination_mapping_and_name_matching(self):
        c, s = self.client([
            {'data': [{'dbkey': 2, 'player_id': 9, 'first': 'John', 'last': 'Smith', 'school_name': 'Central', 'arm_length_verified': 33}], 'has_next': True},
            {'data': [{'player_id': 10, 'first': 'Johnny', 'last': 'Smith'}], 'has_next': False},
        ])
        rows = c.find_players('John', 'Smith', {2027})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['player_id'], 9)
        self.assertEqual(rows[0]['arm_length'], 33)
        self.assertEqual(rows[0]['effective_school_name'], 'Central')
        self.assertIn('track100m', rows[0])
        self.assertEqual(s.headers['key'], 'test-key')
        self.assertEqual(s.post.call_args.kwargs['json']['page'], 1)
        self.assertEqual(s.post.call_args.kwargs['json']['filter'], {'last__iexact': 'Smith', 'class_field__in': [2027]})

    def test_error_and_key_redaction(self):
        c, _ = self.client([{'error': 'access denied test-key'}], 403)
        with self.assertRaises(APIError) as caught:
            list(c.rows())
        self.assertNotIn('test-key', str(caught.exception))
        self.assertIn('403', str(caught.exception))

    def test_malformed_responses(self):
        for payload in [{'data': [], 'has_next': True}, {'data': []}, {'data': [None], 'has_next': False}]:
            with self.subTest(payload=payload):
                c, _ = self.client([payload])
                with self.assertRaises(APIError):
                    list(c.rows())

    def test_all_documented_endpoints(self):
        for endpoint in ('get_masterlist','get_measurable','get_measurablecamp','get_measurabletrack','get_measurablespeed','get_collegeoffers'):
            c, s = self.client([{'data': [], 'has_next': False}])
            self.assertEqual(list(c.rows(endpoint)), [])
            self.assertTrue(s.post.call_args.args[0].endswith('/api/' + endpoint))
            self.assertEqual(s.post.call_args.kwargs['json']['college'], 'Test College')

    def test_config_requires_real_values(self):
        for key,college in [('YOUR_API_KEY','College'),('key','YOUR_COLLEGE_NAME'),('key',None)]:
            with self.assertRaises(APIError):
                UCReportClient(key,college)

    def test_empty_export_retains_file_and_append_preserves_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'players.csv'
            path.write_text('player_id\n1\n')
            existing = pd.read_csv(path)
            self.assertFalse(save_rows([],existing,path))
            self.assertEqual(path.read_text(),'player_id\n1\n')
            self.assertTrue(save_rows([{'player_id':2}],existing,path))
            self.assertEqual(pd.read_csv(path).player_id.tolist(),[1,2])


if __name__ == '__main__':
    unittest.main()
