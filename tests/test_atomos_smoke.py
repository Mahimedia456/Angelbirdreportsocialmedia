import tempfile
import unittest
from pathlib import Path
from src.schema import Finding,ResearchReport
from src.report_scope import scope_to_day
from src.public_research import BRAND
from src.pdf_report_v2 import render_pdf
from src.platform_analytics import platform_summary

class TestAtomosDaily(unittest.TestCase):
    def test_brand_scope(self):
        self.assertTrue(BRAND.search('Atomos Ninja TX field monitor'))
        self.assertTrue(BRAND.search('AtomOS firmware update'))
        self.assertTrue(BRAND.search('ATOMOSphere cloud workflow'))
        self.assertFalse(BRAND.search('Angelbird memory card'))
        self.assertFalse(BRAND.search('Ninja blender unrelated'))
    def test_single_day_and_pdf(self):
        item=Finding(title='Atomos Ninja TX creator post',platform='YouTube',
             url='https://www.youtube.com/watch?v=qAl9K4dgiTc',published_date='2026-10-30',
             date_evidence='Original source published 2026-10-30 13:25 PKT',
             source_excerpt='Atomos Ninja TX on-camera monitoring',status='verified',
             sentiment='Positive',priority='Low')
        report=scope_to_day(ResearchReport(report_date='2026-10-30',
               today_findings=[item],headline='Original day source summary'))
        self.assertEqual(len(report.today_findings),1)
        self.assertEqual(len(platform_summary(report.today_findings)['YouTube']),1)
        with tempfile.TemporaryDirectory() as folder:
            dest=Path(folder)/'test.pdf'
            render_pdf(report,dest)
            self.assertTrue(dest.exists())
            self.assertEqual(dest.read_bytes()[:4],b'%PDF')
    def test_unrelated_angelbird_not_counted(self):
        item=Finding(title='Different media brand',platform='Reddit',
             url='https://www.reddit.com/r/cameras/comments/abc',
             published_date='2026-10-30',date_evidence='Original published 2026-10-30',
             source_excerpt='Angelbird AV PRO field review',status='verified')
        report=scope_to_day(ResearchReport(report_date='2026-10-30',today_findings=[item]))
        self.assertEqual(len(report.today_findings),0)

if __name__=='__main__':
    unittest.main()
