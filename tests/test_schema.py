import unittest
from src.schema import Finding,ResearchReport

class TestEvidence(unittest.TestCase):
    def test_date_guardrail(self):
        a=Finding(title='Old',platform='Reddit',url='https://reddit.com/x',published_date='2026-10-29',date_evidence='Published Oct 29')
        b=Finding(title='New',platform='YouTube',url='https://youtube.com/x',published_date='2026-10-30',date_evidence='Original page shows Oct 30',source_excerpt='Angelbird card mentioned in the original post',status='verified')
        r=ResearchReport(report_date='2026-10-30',today_findings=[a,b]).enforce_date_guardrails()
        self.assertEqual(len(r.today_findings),1)
        self.assertEqual(len(r.unverified_leads),1)
    def test_invalid_url(self):
        with self.assertRaises(Exception):
            Finding(title='x',platform='x',url='not a URL')

if __name__=='__main__':
    unittest.main()
