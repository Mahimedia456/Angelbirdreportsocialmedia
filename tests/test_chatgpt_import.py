import json
import tempfile
import unittest
from pathlib import Path
from src.schema import ResearchReport
from src.chatgpt_import import import_chatgpt_evidence
from src.public_research import youtube_date_pkt

class TestChatGPTImport(unittest.TestCase):
    def test_merges_only_real_url_source_excerpts_and_date_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            folder=root/'data'/'2026'/'10';folder.mkdir(parents=True)
            finding={'title':'Angelbird card observed in original dated review',
                     'url':'https://example.com/angelbird-30','platform':'Industry articles',
                     'author':'Original editor',
                     'source_excerpt':'Angelbird AV PRO CFexpress was used for this production.',
                     'published_date':'2026-10-30',
                     'date_evidence':'Original page first-party timestamp 2026-10-30',
                     'status':'verified','sentiment':'Positive','priority':'Low'}
            invalid={**finding,'url':'https://example.com/angelbird-undated',
                     'date_evidence':'','published_date':'','status':'verified'}
            data={'report_date':'2026-10-30','today_findings':[finding,invalid],
                  'coverage':[{'platform':'ChatGPT review','checked':True,
                               'summary':'Original source links manually inspected'}]}
            (folder/'Angelbird-Social-Monitoring-2026-10-30-chatgpt.json').write_text(json.dumps(data))
            report=ResearchReport(report_date='2026-10-30')
            report, audit=import_chatgpt_evidence(report,root)
            self.assertEqual(len(report.today_findings),1)
            self.assertEqual(len(report.unverified_leads),1)
            self.assertTrue(audit['found'])
            report, again=import_chatgpt_evidence(report,root)
            self.assertEqual(again['inserted'],0)
            self.assertEqual(len(report.today_findings),1)
    def test_wrong_day_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            folder=root/'data'/'2026'/'10';folder.mkdir(parents=True)
            (folder/'Angelbird-Social-Monitoring-2026-10-30-chatgpt.json').write_text(
                '{"report_date":"2026-10-29"}')
            with self.assertRaises(ValueError):
                import_chatgpt_evidence(ResearchReport(report_date='2026-10-30'),root)
    def test_youtube_timestamp_uses_pakistan_date(self):
        self.assertEqual(youtube_date_pkt('2026-10-29T21:30:00Z'),'2026-10-30')
        self.assertEqual(youtube_date_pkt('2026-10-30T20:30:00Z'),'2026-10-31')

if __name__=='__main__':
    unittest.main()
