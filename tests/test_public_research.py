import unittest
from unittest.mock import Mock
from src.public_research import iso, excerpt, classify, PublicResearch

class TestOriginalSourceExtraction(unittest.TestCase):
    def test_exact_date_and_brand_mention(self):
        f=classify("https://www.example.com/a","Reporter tested an Angelbird AV PRO CFexpress card, and it works well.",
           "Industry articles","2026-10-30","Original article:published_time",
           "Field-test: Angelbird media","Editor")
        self.assertEqual(f.status,"verified")
        self.assertEqual(f.sentiment,"Positive")
        self.assertIn("Angelbird",f.source_excerpt)

    def test_generic_reddit_platform_news_not_angelbird(self):
        self.assertIsNone(classify("https://example.com/reddit-feeds","Reddit launched feeds for everyone.",
            "Reddit","2026-10-30","Article publishedAt"))

    def test_date_parse(self):
        self.assertEqual(iso("2026-10-30T12:15:00Z"),"2026-10-30")
        self.assertEqual(iso("Fri, 30 Oct 2026 10:00:00 +0000"),"2026-10-30")
        self.assertEqual(iso("no original date"),"")

    def test_original_page_with_brand_no_day_does_not_verify(self):
        c=PublicResearch("2026-10-30")
        doc='<html><head><title>Angelbird field recording</title></head><body><article>Angelbird AV PRO works great on camera.</article></body></html>'
        fake=Mock()
        fake.status_code=200
        fake.url="https://camera.example.com/post"
        fake.text=doc
        fake.headers={"content-type":"text/html"}
        c.get=Mock(return_value=(fake,"OK"))
        c.page({"url":fake.url,"group":"Industry articles","title":"","snippet":""})
        self.assertEqual(len(c.findings),0)
        self.assertEqual(c.counts["Industry articles.not_dated_today"],1)

    def test_original_page_date_in_first_party_metadata(self):
        c=PublicResearch("2026-10-30")
        doc='<html><head><meta property="article:published_time" content="2026-10-30T12:15:00Z"/></head><body><article>Angelbird AV PRO SE used on Sony cameras. Works well.</article></body></html>'
        fake=Mock()
        fake.status_code=200
        fake.url="https://camera.example.com/post"
        fake.text=doc
        fake.headers={"content-type":"text/html"}
        c.get=Mock(return_value=(fake,"OK"))
        c.page({"url":fake.url,"group":"Industry articles","title":"","snippet":""})
        self.assertEqual(len(c.findings),1)
        self.assertEqual(c.findings[0].published_date,"2026-10-30")

if __name__=="__main__":
    unittest.main()
