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

def _normalize_response(raw, day):
    """Repair alternate model field names; separate retail from genuine social evidence."""
    from datetime import date, timedelta
    from urllib.parse import urlparse
    import re
    out=dict(raw)
    buckets={k:[] for k in ('today_findings','unverified_leads','older_leads','retail_observations')}
    today=date.fromisoformat(day)
    retail_domains=('bhphotovideo.com','galaxus.de','galaxus.ch','x-kom.pl','adorama.com','cvp.com','proav.co.uk')
    for bucket in buckets:
        for original in out.get(bucket,[]) if isinstance(out.get(bucket),list) else []:
            if not isinstance(original,dict):continue
            item=dict(original)
            item['url']=str(item.get('url') or item.get('permalink') or '').strip()
            if not item['url'].startswith(('http://','https://')):continue
            host=(urlparse(item['url']).hostname or '').lower()
            if not re.search(r'\bangelbird\b|\bav[ -]?pro\b',str(item.get('source_excerpt') or ''),re.I):
                continue
            if not isinstance(item.get('engagement'),dict):
                stats=item.get('engagement')
                item['engagement']={'source_note':str(stats)[:180]} if stats else {}
            if not isinstance(item.get('comments'),list):
                item['comments']=[c for c in item.get('relevant_comments',[])
                                  if isinstance(c,dict)] if isinstance(item.get('relevant_comments'),list) else []
            raw_date=str(item.get('published_date') or '')
            if not raw_date:
                match=re.search(r'20\d\d-\d\d-\d\d',str(item.get('date_evidence') or ''))
                raw_date=match.group(0) if match else ''
            try: candidate_day=date.fromisoformat(raw_date)
            except ValueError:candidate_day=None
            retail=any(host==d or host.endswith('.'+d) for d in retail_domains)
            if retail:
                # A currently indexed product page is not a newly published review.
                item['published_date']=''
                item['status']='unverified'
                item['verification_note']='GPT discovered an Angelbird retailer listing; current listing date/review date not independently verified.'
                buckets['unverified_leads'].append(item)
            elif candidate_day and candidate_day<today-timedelta(days=5):
                # Outside requested current + 5 previous-day window.
                continue
            elif bucket=='today_findings' and candidate_day==today and len(str(item.get('date_evidence') or ''))>=12:
                item['published_date']=day
                item['status']='verified'
                buckets['today_findings'].append(item)
            elif candidate_day and today-timedelta(days=5)<=candidate_day<today and len(str(item.get('date_evidence') or ''))>=12:
                item['published_date']=candidate_day.isoformat()
                item['status']='older'
                buckets['older_leads'].append(item)
            else:
                item['published_date']=''
                item['status']='unverified'
                item['verification_note']='GPT search lead with original publication date not independently proven.'
                buckets['unverified_leads'].append(item)
    out.update(buckets)
    out['visibility_gaps']=list(out.get('visibility_gaps',[])) if isinstance(out.get('visibility_gaps'),list) else []
    out['visibility_gaps'].append('GPT retail/product sources are treated as unverified leads, not new verified social mentions.')
    return out

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
        # Reparse saved original AI response to recover permalink/engagement field variants,
        # without making a second paid request.
        if p['raw'].exists():
            try: data=_normalize_response(_json(p['raw'].read_text(encoding='utf-8')),day)
            except (ValueError,TypeError):data=json.loads(p['evidence'].read_text(encoding='utf-8'))
        else:data=json.loads(p['evidence'].read_text(encoding='utf-8'))
        report=ResearchReport.model_validate(data).enforce_date_guardrails()
        report=verify_ai_candidates(report,existing)
        _save(p['evidence'],report.model_dump(mode='json'))
        return report,{'cache':'reparsed_original_response', 'api_calls':0}
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
            parsed=_normalize_response(_json(raw),day)
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
