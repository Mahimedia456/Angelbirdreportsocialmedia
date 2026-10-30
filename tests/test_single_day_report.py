import tempfile
import unittest
from pathlib import Path
from pypdf import PdfReader
from src.schema import ResearchReport,Finding
from src.report_scope import scope_to_day
from src.pdf_report_v2 import render_pdf

def source(day,url,group='Facebook'):
    return Finding(title='Angelbird mention '+day,platform=group,url=url,
        published_date=day,status='verified',
        date_evidence='Original posted at '+day+' 14:30 PKT',
        source_excerpt='Angelbird AV PRO CFexpress cards field use')

class TestOnlySelectedDate(unittest.TestCase):
    def test_old_social_and_retail_never_enter_report(self):
        report=ResearchReport(report_date='2026-10-30',
            today_findings=[source('2026-10-30','https://facebook.com/post/today'),
                            source('2026-10-28','https://facebook.com/post/older')],
            historical_findings=[source('2026-10-29','https://reddit.com/r/cameras/old')],
            older_leads=[source('2026-10-27','https://x.com/example/status/1')],
            retail_observations=[
                Finding(url='https://retailer.example/today',platform='Retailers',
                        title='Angelbird price 30',reference_date='2026-10-30',status='retail'),
                Finding(url='https://retailer.example/old',platform='Retailers',
                        title='Angelbird price 29',reference_date='2026-10-29',status='retail')],
            historical_retail=[
                Finding(url='https://retailer.example/historical',title='Angelbird yesterday',
                        reference_date='2026-10-29')],
            unverified_leads=[
                Finding(url='https://fb.example/undated-30',title='Angelbird candidate today',
                        reference_date='2026-10-30'),
                Finding(url='https://fb.example/undated-29',title='Angelbird candidate yesterday',
                        reference_date='2026-10-29')],
            research_as_of_pkt='2026-10-30 18:20 PKT')
        scoped=scope_to_day(report)
        self.assertEqual(len(scoped.today_findings),1)
        self.assertEqual(len(scoped.historical_findings),0)
        self.assertEqual(len(scoped.historical_retail),0)
        self.assertEqual(len(scoped.older_leads),0)
        self.assertEqual(len(scoped.retail_observations),1)
        self.assertEqual(len(scoped.unverified_leads),1)
        self.assertEqual(scoped.report_period_start,'2026-10-30')
        self.assertEqual(scoped.report_period_end,'2026-10-30')
        with tempfile.TemporaryDirectory() as tmp:
            pdf=Path(tmp)/'single-day.pdf'
            render_pdf(scoped,pdf)
            reader=PdfReader(str(pdf))
            text=' '.join(page.extract_text() or '' for page in reader.pages)
            self.assertIn('Angelbird mention 2026-10-30',text)
            self.assertNotIn('Angelbird mention 2026-10-29',text)
            self.assertNotIn('Angelbird mention 2026-10-28',text)
            self.assertNotIn('Angelbird price 29',text)
            self.assertNotIn('PREVIOUS FIVE',text.upper())
            self.assertIn('Angelbird price 30',text)

    def test_no_prior_date_metrics_in_new_day_kpi(self):
        report=ResearchReport(report_date='2026-10-30',
            historical_findings=[source('2026-10-28','https://facebook.com/post/famous')])
        scoped=scope_to_day(report)
        self.assertEqual(len(scoped.today_findings),0)
        self.assertEqual(len(scoped.historical_findings),0)

if __name__=='__main__':
    unittest.main()
