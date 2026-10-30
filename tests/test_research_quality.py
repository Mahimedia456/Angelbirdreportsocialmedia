import unittest
from src.research import substantive_report

class TestResearchQuality(unittest.TestCase):
    def test_generic_template_rejected(self):
        self.assertFalse(substantive_report({"headline":"Evidence-based summary",
            "coverage":[{"summary":"Bounded public search"}],
            "today_findings":[]}))
    def test_unverified_evidence_is_substantive(self):
        self.assertTrue(substantive_report({"headline":"One undated Reddit discussion requires follow-up",
            "unverified_leads":[{"url":"https://example.com/thread"}]}))
    def test_detailed_zero_results_are_not_automatically_invalid(self):
        self.assertTrue(substantive_report({"headline":"No new dated posts confirmed in searched sources",
            "coverage":[{"platform":"Reddit","summary":"Searched original posts dated 30 October; no posts met source-date evidence criteria."}]}))
    def test_empty_generic_coverage_rejected(self):
        self.assertFalse(substantive_report({"headline":"Nothing found",
            "coverage":[{"platform":"all","summary":"Bounded public search"}]}))

if __name__ == '__main__':
    unittest.main()
