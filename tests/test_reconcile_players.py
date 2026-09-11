import unittest
from scripts.reconcile_players import reconcile

class ReconcileTests(unittest.TestCase):
    def test_fill_preserve_and_deduplicate(self):
        draft = dict(NAME='Drake Maye', YEAR=2024, ROUND=1, is_recruit=False, HT=None, VERT=28.7)
        uc = dict(NAME='Drake Maye', player_id=123, class_field=2021, is_recruit=True, HT=76.5, WT=210, WING=77, VERT=30)
        groups={'qb':{'players':[draft,uc]},'all':{'players':[uc]}}
        self.assertEqual(reconcile(groups),1)
        self.assertEqual(len(groups['qb']['players']),1)
        self.assertEqual(draft['HT'],76.5)
        self.assertEqual(draft['VERT'],28.7)
        self.assertEqual(groups['all']['players'][0]['ROUND'],1)

    def test_namesakes_are_not_guessed(self):
        draft=dict(NAME='John Smith',YEAR=2024,is_recruit=False,HT=None)
        groups={'qb':{'players':[draft]+[dict(NAME='John Smith',player_id=i,class_field=2020,is_recruit=True,HT=74) for i in (1,2)]}}
        self.assertEqual(reconcile(groups),0)
        self.assertIsNone(draft['HT'])

if __name__ == '__main__': unittest.main()
