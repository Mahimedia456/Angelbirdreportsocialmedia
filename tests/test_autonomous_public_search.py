"""Regression: source discovery is autonomous; examples are not evidence."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from src.social_search_queries import GROUPS
from src.public_research import PublicResearch
from src.schema import ResearchReport
from src.report_scope import scope_to_day
from src.main import ROOT

class TestRealSourceSearch(unittest.TestCase):
    def test_each_social_platform_has_index_queries(self):
        for platform in ('Facebook','Instagram','LinkedIn','X / Twitter','Reddit'):
            self.assertGreaterEqual(len(GROUPS[platform]),2)
            self.assertTrue(any('site:' in x for x in GROUPS[platform]))
        self.assertTrue(any('/reel/' in x for x in GROUPS['Instagram']))
        self.assertTrue(any('/stories/' in x for x in GROUPS['Instagram']))
        self.assertEqual(len(GROUPS['Industry articles']),3)
    def test_search_index_only_is_not_verified(self):
        engine=PublicResearch('2026-10-30')
        entry=dict(url='https://www.instagram.com/reel/ABC1234/',
                   group='Instagram',
                   title='Angelbird creator reel monitor review',
                   snippet='Angelbird camera product testing')
        engine.retain_index_only(entry,'HTTP 403')
        self.assertEqual(len(engine.unverified),1)
        lead=engine.unverified[0]
        self.assertEqual(lead.status,'unverified')
        self.assertEqual(lead.reference_date,'2026-10-30')
        self.assertEqual(lead.published_date,'')
        self.assertEqual(lead.engagement,{})
        self.assertEqual(len(engine.findings),0)
    def test_real_original_page_date_not_search_crawl_date(self):
        engine=PublicResearch('2026-10-30')
        html='''<html><head><title>Angelbird camera recorder review</title>
            <meta property="article:published_time" content="2026-10-30"/></head>
            <body><article><h1>Angelbird product test</h1>
            <p>Field testing the Angelbird video camera monitor and recorder.</p></article></body></html>'''
        response=SimpleNamespace(url='https://example.org/review/angelbird-video-monitor',
                                 headers={'content-type':'text/html'},text=html)
        entry=dict(url=response.url,group='Industry articles',
                   title='Angelbird video monitor review',
                   snippet='Angelbird camera monitor recorder review')
        with patch.object(engine,'get',return_value=(response,'OK')):
            engine.page(entry)
        self.assertEqual(len(engine.findings),1)
        item=engine.findings[0]
        self.assertEqual(item.published_date,'2026-10-30')
        self.assertEqual(item.status,'verified')
        self.assertTrue(item.source_excerpt)
        self.assertTrue(item.date_evidence.startswith('Original first-party'))
    def test_prior_user_examples_do_not_appear_in_generated_day(self):
        # The old, user-provided example Story URLs were NOT independently sourced.
        report=ResearchReport(report_date='2026-10-30',unverified_leads=[{
          'url':'https://www.instagram.com/stories/unoadventuresph/4019174313416392791/',
          'platform':'Instagram','status':'unverified','reference_date':'2026-10-30',
          'verification_note':'USER-SUPPLIED STORY LINK ONLY. Not verified.'}])
        scoped=scope_to_day(report)
        self.assertFalse(scoped.unverified_leads)
        self.assertFalse([x for x in scoped.today_findings if x.platform=='Instagram'])

if __name__=='__main__':unittest.main()
