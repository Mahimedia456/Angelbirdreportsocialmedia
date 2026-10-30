import json
import tempfile
import unittest
from pathlib import Path
from src.schema import Finding,ResearchReport
from src.history import compile_history
from src.pdf_report_v2 import render_pdf

def finding(title,day,excerpt,author='u/test'):
    return {'title':title,'platform':'Reddit','url':'https://www.reddit.com/r/test/comments/old/',
        'published_date':day,'date_evidence':'Original source page displayed this date',
        'source_excerpt':excerpt,'author':author,'sentiment':'Positive',
        'priority':'Low','status':'older','summary':'A previously referenced brand comment.'}

class TestCumulativePDF(unittest.TestCase):
    def test_latest_first_and_reused_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            folder=root/'data'
            folder.mkdir()
            entries=[finding('Angelbird old 1','2026-10-22','Angelbird was good','u/a'),
                finding('Angelbird old 2','2026-10-28','Angelbird used on set','u/b')]
            seed={'findings':entries+[finding('Angelbird future','2026-10-31','Angelbird','u/c')],
                  'retail_observations':[]}
            (folder/'reference_history_2026_10_29.json').write_text(json.dumps(seed))
            day=root/'data'/'2026'/'10'
            day.mkdir(parents=True)
            older={'report_date':'2026-10-29','today_findings':[
                finding('Angelbird review 29','2026-10-29','Angelbird AV PRO works','u/d'),
                finding('Generic Reddit feature launch','2026-10-29','Reddit launched features','u/other')]}
            (day/'Angelbird-Social-Monitoring-2026-10-29.json').write_text(json.dumps(older))
            report=ResearchReport(report_date='2026-10-30',headline='Monitoring brief')
            compile_history(report,root)
            self.assertEqual([x.published_date for x in report.historical_findings],
                ['2026-10-29','2026-10-28'])
            self.assertEqual(len(report.today_findings),0)
            self.assertTrue(all(x.published_date >= '2026-10-25' for x in report.historical_findings))
            self.assertEqual(report.report_period_start,'2026-10-25')
            self.assertEqual(report.report_period_end,'2026-10-30')
            pdf=root/'report.pdf'
            render_pdf(report,pdf)
            self.assertTrue(pdf.exists())
            self.assertGreater(pdf.stat().st_size,1000)
            self.assertEqual(pdf.read_bytes()[:4],b'%PDF')

    def test_unrelated_reddit_article_dropped(self):
        item=Finding(title='Reddit launches new feeds',platform='Reddit',
            url='https://example.com/reddit-news',
            summary='Could influence Angelbird users indirectly',
            published_date='2026-10-30',date_evidence='Source page dated 30 October 2026',
            source_excerpt='New Following feeds launched on Reddit',
            status='verified')
        report=ResearchReport(report_date='2026-10-30',today_findings=[item]).enforce_date_guardrails()
        self.assertEqual(len(report.today_findings),0)
        self.assertEqual(len(report.unverified_leads),0)
        self.assertTrue(any('excluded' in x for x in report.visibility_gaps))

if __name__=='__main__':
    unittest.main()
