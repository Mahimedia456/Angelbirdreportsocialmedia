"""Optional one-request paid GPT research supplement for public Angelbird findings.

Zero repeat billing for the same report day unless explicitly forced. One Responses
request with max 2 web calls; fail-open to YouTube/free results on API errors.
"""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from .schema import ResearchReport
from .public_research import PublicResearch, BRAND

ROOT=Path(__file__).resolve().parents[1]

def _json(text):
    s=(text or '').strip().lstrip('\ufeff\u200c\u200b')
    if s.startswith('```'):
        s=re.sub(r'^\x60{3}(?:json)?\s*|\s*\x60{3}$','',s,flags=re.I)
    try:return json.loads(s)
    except ValueError:
        first=s.find('{');last=s.rfind('}')
        if first>=0 and last>first:return json.loads(s[first:last+1])
        raise

def _cache_paths(day):
    prefix=ROOT/'data'/day[:4]/day[5:7]/f'Angelbird-Social-Monitoring-{day}-gpt'
    prefix.parent.mkdir(parents=True,exist_ok=True)
    return {name:Path(str(prefix)+extension) for name,extension in
           [('evidence','-evidence.json'),('attempt','-attempt.json'),
            ('usage','-usage.json'),('raw','-raw.txt')]}

def _save(path, data):
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')

def verify_ai_candidates(report, already_verified):
    """Never count a GPT claim as a new verified mention without original-page proof."""
    checker=PublicResearch(report.report_date)
    checked=0; keep=[]
    original={x.url.rstrip('/').lower() for x in already_verified.today_findings}
    for item in report.today_findings:
        if item.url.rstrip('/').lower() in original:
            keep.append(item)
            continue
        if checked<7 and BRAND.search(item.source_excerpt):
            checked+=1
            checker.page({'url':item.url,'group':item.platform or 'Industry articles',
                          'title':item.title,'snippet':item.source_excerpt})
            verified_urls={x.url.rstrip('/').lower() for x in checker.findings}
            if item.url.rstrip('/').lower() in verified_urls:
                keep.append(item)
                continue
        item.status='unverified'
        item.verification_note=(item.verification_note+' | ' if item.verification_note else '')+(
            'GPT search candidate: original post publication date could not be independently verified by the collector.')
        report.unverified_leads.append(item)
    report.today_findings=keep
    if checked:
        report.visibility_gaps.append(
            f'{checked} GPT candidate URL(s) checked against original sources; uncorroborated posts are unverified, not new KPIs.')
    return report

def supplement(day, existing):
    p=_cache_paths(day)
    if p['evidence'].exists() and os.getenv('GPT_FORCE_RESEARCH','').lower() not in ('1','true'):
        data=json.loads(p['evidence'].read_text(encoding='utf-8'))
        report=ResearchReport.model_validate(data).enforce_date_guardrails()
        return verify_ai_candidates(report,existing),{'cache':'reused', 'api_calls':0}
    if p['attempt'].exists() and os.getenv('GPT_FORCE_RESEARCH','').lower() not in ('1','true'):
        return None,{'cache':'prior_attempt_guard','api_calls':0}
    model=os.getenv('OPENAI_MODEL','gpt-4.1-mini')
    if model not in ('gpt-4.1-mini','gpt-4o-mini'):
        raise ValueError('GPT cost guard supports only mini models.')
    max_web=max(1,min(2,int(os.getenv('GPT_MAX_WEB_CALLS','2'))))
    if not os.getenv('OPENAI_API_KEY'):
        return None,{'status':'skipped','reason':'OPENAI_API_KEY missing'}
    _save(p['attempt'],{'status':'started','report_date':day,'model':model,
                       'max_web_calls':max_web,'time_utc':datetime.now(timezone.utc).isoformat(),
                       'note':'One paid request max per date unless manually forced'})
    try:
        from openai import OpenAI
        client=OpenAI(timeout=110,max_retries=0)
        prompt=(
            f'Research Angelbird Technologies and AV PRO memory cards on {day} (Asia/Karachi). '
            'Use the available web search tool to locate actual original posts, individual public comments, '
            'camera reviews, indexed social posts, and product-related customer complaints. '
            'Start with 2 tightly targeted Angelbird search queries on the exact date; consider public Reddit '
            'posts through search index only (no Reddit API), YouTube creators/comments, public Facebook/Instagram/'
            'LinkedIn, technical forums, editorial reviews and retailers. '
            'Also include worthwhile evidence dated in the previous 5 calendar days as older_leads. '
            'Exclude generic platform news, Angelbird corporate homepage and undated catalog/search pages. '
            'Do not invent findings, authors, quotes, source images or engagement numbers. '
            'Differentiate exact-day sources from older, undated and current retail listings. '
            'For every finding give the exact original post permalink, original post date/date_evidence, '
            'source_excerpt showing Angelbird/AV PRO, title, platform, author, sentiment, priority, '
            'summary, impact, response_action, optional image_url, engagement and relevant comments. '
            'If a timestamp cannot be independently established, label the item unverified. '
            'Never claim all networks were checked on a 2-search budget. '
            'Return only a JSON object matching keys: report_date, status, headline, today_findings, '
            'unverified_leads, older_leads, retail_observations, coverage (array of '
            '{platform,checked,summary}), visibility_gaps (array), methodology. '
            f'report_date must be {day}. No boilerplate or sample placeholders.'
        )
        response=client.responses.create(model=model, input=prompt,
            tools=[{'type':'web_search','search_context_size':'low'}],
            tool_choice='required',max_tool_calls=max_web,max_output_tokens=4400)
        raw=response.output_text or ''
        p['raw'].write_text(raw,encoding='utf-8')
        usage=getattr(response,'usage',None)
        events=sum(1 for item in (getattr(response,'output',None) or [])
                   if getattr(item,'type','')=='web_search_call')
        _save(p['usage'],{'model':model,'observed_search_events':events,
                          'max_web_calls':max_web,
                          'usage':usage.model_dump(mode='json') if usage else {},
                          'response_id':getattr(response,'id',''),
                          'cost_note':'Actual charges only in OpenAI API Usage; no fixed dollar cap.'})
        try:
            parsed=_json(raw)
            if not isinstance(parsed,dict) or parsed.get('report_date')!=day:
                raise ValueError('AI returned invalid or wrong-date JSON')
            if str(parsed.get('headline','')).strip() in ('Evidence-based summary','One-line sourced summary'):
                raise ValueError('AI returned boilerplate')
            report=ResearchReport.model_validate(parsed).enforce_date_guardrails()
            report=verify_ai_candidates(report,existing)
            _save(p['evidence'],report.model_dump(mode='json'))
            _save(p['attempt'],{'status':'finished','report_date':day,'model':model,
                                'observed_search_events':events})
            return report,{'status':'finished','observed_search_events':events,'api_calls':1}
        except (ValueError,TypeError) as exc:
            _save(p['attempt'],{'status':'invalid_output','message':str(exc)[:250],
                                'report_date':day,'api_calls':1})
            return None,{'status':'invalid_output','detail':str(exc)[:200],'api_calls':1}
    except Exception as exc:
        # Do not retry automatically. The free report can still be completed.
        detail=str(exc)[:280]
        _save(p['attempt'],{'status':'error','detail':detail,'report_date':day})
        return None,{'status':'error','detail':detail,'api_calls':1}

def merge(report, supplement_report):
    if supplement_report is None:return report,{}
    from .chatgpt_import import _key
    added={}
    for bucket in ('today_findings','unverified_leads','older_leads','retail_observations'):
        existing=getattr(report,bucket)
        seen={_key(x) for x in existing}
        count=0
        for item in getattr(supplement_report,bucket):
            key=_key(item)
            if key in seen:continue
            existing.append(item);seen.add(key);count+=1
        added[bucket]=count
    report.visibility_gaps.extend(x for x in supplement_report.visibility_gaps
                                  if x not in report.visibility_gaps)
    for c in supplement_report.coverage:
        if c.checked or 'GPT' in c.platform:
            report.coverage.append(c)
    report.methodology=(report.methodology+
                        ' | Optional one-request GPT web-search supplement, original-URL checks and cached evidence.')
    return report,added
