import tempfile
import unittest
from pathlib import Path
from reportlab.platypus import Table, Paragraph
from src.schema import Finding, ResearchReport
from src.pdf_report_v2 import platform_dossier, render_pdf, source_url_line

def make_item(title,url,day,platform,counts=None):
    return Finding(title=title,url=url,published_date=day,platform=platform,
                   source_excerpt='Angelbird AV PRO memory card used on set.',
                   date_evidence='Original public page date 2026-10-30',
                   status='verified',summary='Original relevant public mention.',
                   engagement=counts or {})

def collect_text(elements):
    out=[]
    def walk(obj):
        if isinstance(obj,Paragraph):
            out.append(obj.text)
        elif isinstance(obj,Table):
            for row in obj._cellvalues:
                for cell in row: walk(cell)
        elif isinstance(obj,(tuple,list)):
            for element in obj:walk(element)
    for e in elements:walk(e)
    return '\n'.join(out)

class TestPlatformDeepDive(unittest.TestCase):
    def test_facebook_and_linkedin_links_follow_their_analytics_section(self):
        facebook=[
            make_item('Creator A Angelbird cards','https://facebook.com/a/posts/111','2026-10-28','Facebook',
                      {'post_views':575,'post_likes':127}),
            make_item('Camera kit bundle Angelbird','https://facebook.com/groups/123/permalink/222','2026-10-28','Facebook'),
            make_item('CFexpress seller Angelbird','https://facebook.com/groups/123/permalink/333','2026-10-28','Facebook'),
        ]
        linkedin=make_item('ComLine and Angelbird','https://www.linkedin.com/posts/comline_ugc','2026-10-27','LinkedIn',
                           {'reactions':32})
        yt=make_item('Angelbird Raven recording','https://youtube.com/watch?v=qAl9K4dgiTc','2026-10-30','YouTube',
                     {'views':200})
        report=ResearchReport(report_date='2026-10-30',today_findings=[yt],
                              historical_findings=facebook+[linkedin])
        text=collect_text(platform_dossier(report))
        self.assertIn('Creator A Angelbird cards',text)
        self.assertIn('Camera kit bundle Angelbird',text)
        self.assertIn('CFexpress seller Angelbird',text)
        self.assertIn('ComLine and Angelbird',text)
        self.assertIn('www.linkedin.com/posts/comline_ugc',text)
        self.assertIn('facebook.com/a/posts/111',text)
        self.assertLess(text.index('FACEBOOK'),text.index('Creator A Angelbird cards'))
        self.assertLess(text.index('Creator A Angelbird cards'),text.index('INSTAGRAM'))
        self.assertLess(text.index('LINKEDIN'),text.index('ComLine and Angelbird'))
        self.assertLess(text.index('YOUTUBE'),text.index('Angelbird Raven recording'))
    def test_new_post_shown_above_older_one_within_same_platform(self):
        old=make_item('Earlier Angelbird review','https://reddit.com/r/cameras/comments/abc','2026-10-29','Reddit')
        new=make_item('Latest Angelbird review','https://reddit.com/r/cameras/comments/xyz','2026-10-30','Reddit')
        report=ResearchReport(report_date='2026-10-30',today_findings=[new],
                              historical_findings=[old])
        text=collect_text(platform_dossier(report))
        self.assertLess(text.index('Latest Angelbird review'),
                        text.index('Earlier Angelbird review'))
        self.assertIn('2026-10-30',text)
        self.assertIn('2026-10-29',text)
    def test_pdf_renders_with_all_platform_sections_without_external_network(self):
        item=make_item('Facebook Angelbird post','https://www.facebook.com/posts/source','2026-10-30','Facebook',
                       {'views':12,'comments':2})
        item.comments=[{'author':'Jane','text':'Angelbird cards worked great',
                        'url':'https://www.facebook.com/comments/123'}]
        report=ResearchReport(report_date='2026-10-30',today_findings=[item])
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report.pdf'
            render_pdf(report,p)
            self.assertTrue(p.is_file())
            self.assertEqual(p.read_bytes()[:4],b'%PDF')
            self.assertGreater(p.stat().st_size,6000)

if __name__=='__main__':
    unittest.main()
