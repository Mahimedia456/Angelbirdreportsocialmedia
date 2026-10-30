import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from src.schema import ResearchReport
from src.scheduled_research import research_sweeps, SWEEPS

class TestScheduledGPT(unittest.TestCase):
    def test_scheduled_sweeps_are_grouped_capped_and_cached(self):
        calls=[]
        output=json.dumps({'report_date':'2026-10-30',
            'status':'Limited public-source checks',
            'headline':'No independently dated social posts confirmed by these source checks',
            'today_findings':[],'older_leads':[],'unverified_leads':[],
            'retail_observations':[],'coverage':[],
            'visibility_gaps':['Some sources blocked']})
        class FakeClient:
            def create(self,**kwargs):
                calls.append(kwargs)
                return SimpleNamespace(output_text=output,output=[SimpleNamespace(type='web_search_call')],
                    usage=SimpleNamespace(model_dump=lambda **k:{'input_tokens':150,'output_tokens':200}),
                    id='unit-test')
        module=SimpleNamespace(OpenAI=lambda **kwargs:SimpleNamespace(responses=FakeClient()))
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(sys.modules,{'openai':module}),patch.dict(os.environ,{
                'OPENAI_API_KEY':'fake-never-used',
                'OPENAI_MODEL':'gpt-4.1-mini',
                'GPT_MAX_RESEARCH_ROUNDS':'3',
                'GPT_MAX_WEB_CALLS':'2',
                'GPT_FORCE_RESEARCH':'false'
            }):
                initial=ResearchReport(report_date='2026-10-30')
                result,log=research_sweeps('2026-10-30',initial,Path(directory))
                self.assertEqual(len(calls),3)
                self.assertTrue(all(call['max_tool_calls']==2 for call in calls))
                self.assertTrue(any('Facebook' in call['input'] and 'LinkedIn' in call['input'] for call in calls))
                self.assertTrue(any('Reddit' in call['input'] and 'YouTube' in call['input'] for call in calls))
                self.assertTrue(any('original journalism' in call['input'] for call in calls))
                self.assertEqual([item['scope'] for item in log],[x[0] for x in SWEEPS])
                _result,rerun=research_sweeps('2026-10-30',result,Path(directory))
                self.assertEqual(len(calls),3)
                self.assertEqual(sum(x['api_calls'] for x in rerun),0)
    def test_without_paid_key_does_not_call_api(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'OPENAI_API_KEY':''}):
            result,log=research_sweeps('2026-10-30',ResearchReport(report_date='2026-10-30'),Path(directory))
            self.assertEqual(log[0]['status'],'skipped')

if __name__=='__main__':
    unittest.main()
