import unittest
from src.schema import Finding, ResearchReport

class TestAIResponseCompatibility(unittest.TestCase):
    def test_nullable_fields_and_complex_details(self):
        data={"report_date":"2026-10-30","retail_observations":[{
            "title":"Retail offer","platform":"Retail","url":"https://example.com/offer",
            "published_date":None,"image_url":None,"details":{"region":"Poland","note":"Availability is not a published review"},
            "sentiment":"retail_observation","priority":"high","status":"verified_retail_offer_date_not_publication_date"}]}
        report=ResearchReport.model_validate(data).enforce_date_guardrails()
        self.assertEqual(len(report.retail_observations),1)
        item=report.retail_observations[0]
        self.assertEqual(item.status,"retail")
        self.assertEqual(item.sentiment,"Not applicable")
        self.assertEqual(item.priority,"High")
        self.assertEqual(item.published_date,"")
        self.assertIn("Poland",item.details)

    def test_unverified_today_does_not_enter_verified_totals(self):
        payload={"report_date":"2026-10-30","today_findings":[{
            "title":"Uncertain claim","platform":"Reddit","url":"https://reddit.com/r/example/comments/test",
            "published_date":"2026-10-30","date_evidence":"","source_excerpt":"Angelbird card mentioned in user comment","status":"verified", "sentiment":"negative/mixed"}]}
        report=ResearchReport.model_validate(payload).enforce_date_guardrails()
        self.assertEqual(len(report.today_findings),0)
        self.assertEqual(len(report.unverified_leads),1)
        self.assertEqual(report.unverified_leads[0].sentiment,"Not applicable")

    def test_valid_same_date_stays_and_duplicates_removed(self):
        item={"title":"Comment","platform":"Forum","url":"https://example.com/x","published_date":"2026-10-30",
            "date_evidence":"Original page visibly says 30 Oct 2026","source_excerpt":"Angelbird memory card mentioned in original comment","status":"verified","sentiment":"Negative"}
        report=ResearchReport.model_validate({"report_date":"2026-10-30","today_findings":[item,item]}).enforce_date_guardrails()
        self.assertEqual(len(report.today_findings),1)

    def test_invalid_link_excluded_not_fabricated(self):
        report=ResearchReport.model_validate({"report_date":"2026-10-30","unverified_leads":[{"title":"No original URL","url":None}]})
        self.assertEqual(len(report.unverified_leads),0)
        self.assertIn("excluded",report.visibility_gaps[0])

if __name__ == "__main__":
    unittest.main()
