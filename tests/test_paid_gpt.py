import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import sys

from src import paid_gpt
from src.schema import ResearchReport

class TestBoundedPaidGPT(unittest.TestCase):
    def test_json_fenced_parse(self):
        self.assertEqual(paid_gpt._json('```json\n{"report_date":"2026-10-30"}\n```')['report_date'],
                         '2026-10-30')

    def test_only_one_paid_request_per_date_and_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls=[]
            raw=json.dumps({
                'report_date':'2026-10-30',
                'status':'Limited GPT public-source research',
                'headline':'No exact-date source could be validated on this limited run',
                'today_findings':[],
                'unverified_leads':[{'title':'Angelbird field use (date not confirmed)',
                    'url':'https://example.com/angelbird','source_excerpt':'Angelbird media used in the field',
                    'status':'unverified','platform':'Industry articles','published_date':''}],
                'coverage':[{'platform':'GPT public web index','checked':True,
                             'summary':'One targeted search made, original dates remain uncertain.'}]
            })
            class FakeResponses:
                def create(self,**kw):
                    calls.append(kw)
                    return SimpleNamespace(output_text=raw,output=[SimpleNamespace(type='web_search_call')],
                        usage=SimpleNamespace(model_dump=lambda **_:{'input_tokens':120,'output_tokens':240}),
                        id='fake-response')
            fake_openai=SimpleNamespace(OpenAI=lambda **_:SimpleNamespace(responses=FakeResponses()))
            with patch.object(paid_gpt,'ROOT',Path(tmp)),patch.dict(sys.modules,{'openai':fake_openai}),patch.dict(
                'os.environ',{'OPENAI_API_KEY':'fake-test-key','OPENAI_MODEL':'gpt-4.1-mini',
                              'GPT_MAX_WEB_CALLS':'2'},clear=False):
                prior=ResearchReport(report_date='2026-10-30')
                got,one=paid_gpt.supplement('2026-10-30',prior)
                self.assertEqual(one['api_calls'],1)
                self.assertEqual(len(calls),1)
                self.assertEqual(calls[0]['max_tool_calls'],2)
                self.assertEqual(len(got.unverified_leads),1)
                again,two=paid_gpt.supplement('2026-10-30',prior)
                self.assertEqual(two['api_calls'],0)
                self.assertEqual(len(calls),1)
                self.assertEqual(len(again.unverified_leads),1)
                self.assertTrue((Path(tmp)/'data'/'2026'/'10'/
                    'Angelbird-Social-Monitoring-2026-10-30-gpt-usage.json').is_file())

    def test_model_permalinks_recovered_as_unverified_retail_candidates(self):
        raw={'report_date':'2026-10-30','headline':'Source-dependent findings',
             'today_findings':[{'permalink':'https://www.bhphotovideo.com/c/product/example',
                 'source_excerpt':'Angelbird AV PRO UHS-II card listing',
                 'date_evidence':'2026-10-28','engagement':'26 reviews'}],
             'older_leads':[{'permalink':'https://www.digitalcameraworld.com/post',
                 'source_excerpt':'Angelbird launch announced',
                 'date_evidence':'2026-09-19'}]}
        out=paid_gpt._normalize_response(raw,'2026-10-30')
        self.assertEqual(len(out['today_findings']),0)
        self.assertEqual(len(out['unverified_leads']),1)
        self.assertTrue(out['unverified_leads'][0]['url'].startswith('https://www.bhphotovideo.com'))
        self.assertEqual(out['unverified_leads'][0]['engagement']['source_note'],'26 reviews')
        self.assertEqual(len(out['older_leads']),0)

    def test_missing_key_does_not_call_api(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(paid_gpt,'ROOT',Path(tmp)),patch.dict(
            'os.environ',{'OPENAI_API_KEY':''},clear=False):
            result,meta=paid_gpt.supplement('2026-10-30',ResearchReport(report_date='2026-10-30'))
            self.assertIsNone(result)
            self.assertEqual(meta['status'],'skipped')

if __name__=='__main__':
    unittest.main()
