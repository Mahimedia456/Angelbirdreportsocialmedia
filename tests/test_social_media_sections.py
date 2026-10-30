import re
import tempfile
import unittest
from pathlib import Path
from pypdf import PdfReader
from src.schema import Finding, ResearchReport
from src.social_content import content_type, content_counts, source_labels
from src.pdf_report_v2 import render_pdf

class TestSocialPostsStoriesMentions(unittest.TestCase):
    def record(self,url,title,kind='',tags=None):
        return Finding(
            url=url,title=title,platform='Facebook',content_type=kind,
            published_date='2026-10-30',status='verified',
            date_evidence='Original Facebook post date 2026-10-30 10:00 PKT',
            source_excerpt='Angelbird product discussed #Angelbird @creator',
            hashtags=['#Angelbird'],mentioned_accounts=['@creator'],
            tagged_accounts=tags or [],
            comments=[{'author':'Viewer','text':'Great info on Angelbird',
                       'date':'2026-10-30','url':'https://facebook.com/comments/123'}])
    def test_public_source_labels_and_origin(self):
        labels=source_labels('Testing Angelbird #Angelbird @creator #Angelbird')
        self.assertEqual(labels['hashtags'],['#Angelbird'])
        self.assertEqual(labels['mentioned_accounts'],['@creator'])
        self.assertEqual(content_type(self.record(
            'https://www.facebook.com/stories/1000/2000/','Story sample')),'story')
        self.assertEqual(content_type(self.record(
            'https://www.instagram.com/reel/abcdef/','Reel sample')),'reel')
        self.assertEqual(content_type(self.record(
            'https://www.facebook.com/posts/123','Tagged sample','tagged_post',['@partner'])),'tagged_post')
    def test_same_facebook_section_contains_story_tagged_post_comments(self):
        items=[
            self.record('https://www.facebook.com/stories/1000/2000/','Story: Angelbird recording'),
            self.record('https://www.facebook.com/posts/1000','Tagged camera post','tagged_post',['@partner']),
            self.record('https://www.facebook.com/posts/2000','Normal post')
        ]
        counts=content_counts(items)
        self.assertEqual(counts['story'],1)
        self.assertEqual(counts['tagged_post'],1)
        self.assertEqual(counts['post'],1)
        report=ResearchReport(report_date='2026-10-30',today_findings=items,
            report_period_start='2026-10-30',report_period_end='2026-10-30')
        with tempfile.TemporaryDirectory() as tmp:
            pdf=Path(tmp)/'social.pdf'
            render_pdf(report,pdf)
            self.assertEqual(pdf.read_bytes()[:4],b'%PDF')
            extracted=' '.join(page.extract_text() or '' for page in PdfReader(str(pdf)).pages)
            normalized=re.sub(r'\s+',' ',extracted).upper()
            self.assertNotIn('SEARCH AND ACCESS AUDIT',normalized)
            self.assertIn('STORIES: 1',normalized)
            self.assertIn('TAGGED POSTS: 1',normalized)
            self.assertIn('PUBLIC @MENTIONS',normalized)
            self.assertIn('SOURCE HASHTAGS',normalized)
            self.assertIn('TAGGED ACCOUNTS',normalized)

if __name__=='__main__': unittest.main()
