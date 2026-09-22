import unittest
from datetime import date
from update_profile import parse_calendar, streaks

class CalendarTests(unittest.TestCase):
    def test_tooltips_join_by_id_not_dom_order(self):
        source = '''<td data-date="2026-09-20" id="a" data-level="2"></td>
        <td data-date="2026-09-21" id="b" data-level="0"></td>
        <tool-tip for="b">No contributions on September 21st.</tool-tip>
        <tool-tip for="a">12 contributions on September 20th.</tool-tip>'''
        self.assertEqual(parse_calendar(source), [('2026-09-20',12,2),('2026-09-21',0,0)])
    def test_missing_tooltip_fails_instead_of_faking_zero(self):
        with self.assertRaises(ValueError):
            parse_calendar('<td data-date="2026-09-21" id="a" data-level="2"></td>')
    def test_today_can_be_unfinished(self):
        days=[('2026-09-18',1,1),('2026-09-19',2,1),('2026-09-20',1,1),('2026-09-21',0,0)]
        self.assertEqual(streaks(days,date(2026,9,21)),(3,3))
    def test_gap_and_zero_history(self):
        days=[('2026-09-18',4,1),('2026-09-19',0,0),('2026-09-20',0,0),('2026-09-21',0,0)]
        self.assertEqual(streaks(days,date(2026,9,21)),(0,1))
        self.assertEqual(streaks([('2026-09-21',0,0)],date(2026,9,21)),(0,0))

if __name__=='__main__':unittest.main()
