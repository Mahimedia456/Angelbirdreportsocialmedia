import json
import tempfile
import unittest
from pathlib import Path
from pypdf import PdfReader
from src.schema import ResearchReport
from src.story_watchlist import story_handle,watchlist_leads,include_watchlist
from src.pdf_report_v2 import render_pdf
from src.platform_analytics import analytics_rows

class InstagramStoryLeadsTest(unittest.TestCase):
    def test_safe_story_url_and_no_brand_assumptions(self):
        self.assertEqual(story_handle('https://www.instagram.com/stories/kevinweddings/4018804834358765706/'),'kevinweddings')
        self.assertEqual(story_handle('instagram.com/stories/kevinweddings/'),'')
        self.assertEqual(story_handle('https://www.instagram.com/stories/mvmediahouse_/'),'mvmediahouse_')
        self.assertEqual(story_handle('https://evil.com/stories/test/'),'')

    def test_date_scoped_unverified_links_in_platform_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            (base/'data').mkdir()
            input_urls=[
                'https://www.instagram.com/stories/kevinweddings/4018804834358765706/',
                'https://www.instagram.com/stories/mvmediahouse_/',
            ]
            (base/'data'/'social_story_watchlist.json').write_text(json.dumps(
                [{'url':url,'observed_date':'2026-10-30'} for url in input_urls]+[
                 {'url':'https://www.instagram.com/stories/yesterday/','observed_date':'2026-10-29'}]))
            report=ResearchReport(report_date='2026-10-30')
            report,n=include_watchlist(report,base)
            self.assertEqual(n,2)
            self.assertEqual(len(report.today_findings),0)
            self.assertEqual(len(report.unverified_leads),2)
            self.assertTrue(all(not x.published_date and x.status=='unverified' for x in report.unverified_leads))
            self.assertTrue(all(not x.engagement and not x.image_url for x in report.unverified_leads))
            self.assertEqual(len(watchlist_leads('2026-10-29',base)),1)
            with tempfile.TemporaryDirectory() as dest:
                pdf=Path(dest)/'report.pdf'
                render_pdf(report,pdf)
                pages=PdfReader(str(pdf)).pages
                text=' '.join(x.extract_text() or '' for x in pages)
                self.assertIn('INSTAGRAM STORIES TO VERIFY',text.upper())
                self.assertIn('0 verified',text)
                self.assertNotIn('SEARCH AND ACCESS AUDIT',text.upper())
                links=set()
                for p in pages:
                    for annot in p.annotations or []:
                        a=annot.get_object().get('/A')
                        if a and a.get('/URI'):links.add(str(a.get('/URI')))
                self.assertTrue(set(input_urls)<=links)

if __name__=='__main__':
    unittest.main()
