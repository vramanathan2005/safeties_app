import unittest
from scripts.player_outcomes import classify

class OutcomeTests(unittest.TestCase):
    def label(self, starts, total=12, **changes):
        row = dict(nfl_snaps=0, college_starts=starts, college_games=12,
                   team_games=total, conference='SEC', season=2025)
        row.update(changes)
        return classify(row)

    def test_half_season(self):
        self.assertEqual(self.label(6), 'SEC Starter · 2025')
        self.assertEqual(self.label(5), 'SEC Backup · 2025')
        self.assertEqual(self.label(6,13), 'SEC Backup · 2025')
        self.assertEqual(self.label(7,13), 'SEC Starter · 2025')

    def test_unknown_and_invalid(self):
        self.assertIn('unverified',self.label(6,None))
        self.assertIn('unverified',self.label(6,0))
        self.assertIn('unverified',self.label(13,12))
        self.assertIn('unverified',self.label(6,nfl_snaps=None))

    def test_future_classes_are_high_school(self):
        for year in (2027, 2028, 2030):
            self.assertEqual(classify({'class_field': year, 'draft_round': 1}), 'HS Recruit')
        self.assertEqual(classify({'class_field': 2026}), 'Outcome unverified')

    def test_nfl_priority(self):
        self.assertEqual(self.label(6,draft_round=2),'NFL drafted')
        self.assertEqual(self.label(6,nfl_snaps=10,undrafted=True),'NFL UDFA')

if __name__ == '__main__': unittest.main()
