"""Autonomous daily GPT web-research sweeps, grouped by platform.

Bounded, billable search; each date/topic has independent cache & attempt guard.
GitHub Actions may run the prompts unattended. No Reddit API credentials.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from .schema import ResearchReport
from .paid_gpt import _json, _normalize_response, verify_ai_candidates, merge

ROOT=Path(__file__).resolve().parents[1]

SWEEPS=(
    ('social',(
        'Facebook public posts/groups where indexed, Instagram public posts, '
        'X/Twitter public posts, LinkedIn public pages/creators. Discover original '
        'Angelbird Technologies post or comment PERMALINKS, not homepages or '
        'generic search pages. Include authors, source post dates, views, likes, '
        'reactions, comments, reposts/shares when actually visible, image URLs '
        'owned by the original source, and verbatim-short brand excerpts. '
        'Do not imply private Meta or LinkedIn content was accessed.'
    )),
    ('community',(
        'Reddit public indexed posts and comment PERMALINKS (NO Reddit API), '
        'YouTube reviewers and comments, DPReview/Blackmagic/RED/Sony camera forums, '
        'videography discussions. Target real usage and faults of Angelbird media, '
        'product compatibility, customer feedback and creator demonstrations. '
        'Extract individual author comments with original comment URL and date.'
    )),
    ('editorial',(
        'Google-indexed news and original journalism, Angelbird product announcements '
        'from independent publishers, original journalist/byline, dated camera '
        'review articles, original source thumbnail credits, and retailer price '
        'snapshots with observation timestamp. Price/stock is not social sentiment '
        'and retailer listings do not become new verified social reviews.'
    )),
)

def _paths(day, scope,root):
    prefix=root/'data'/day[:4]/day[5:7]/f'Angelbird-Social-Monitoring-{day}-gpt-{scope}'
    prefix.parent.mkdir(parents=True,exist_ok=True)
    return {suffix:Path(str(prefix)+'-'+suffix+'.'+ext) for suffix,ext in (
        ('attempt','json'),('raw','txt'),('usage','json'),('evidence','json'))}

def _write(path,data):
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')

def _instructions(day, scope, targets):
    return (
        f'You are doing SCHEDULED Angelbird brand monitoring for {day}, in Asia/Karachi. '
        'Do the public web search NOW; never give advice to search later. '
        f'This sweep targets {scope}: {targets} '
        'Explore at least two distinct targeted query themes with the available '
        'search capacity, when supported. Prefer original post/comment URL not '
        'search engine result pages. Search broadly enough to find real posts, '
        'then follow to original public page if possible. Only claim CHECKED when '
        'the original post or a provider API was inspected, not merely a search result. '
        'The newest verified findings MUST be dated precisely '+day+'. '
        'Research ONLY this one calendar date. Do not collect, summarize or report posts '
        'from preceding days. Return older_leads as an empty list. '
        'Undated source leads go in unverified_leads ONLY if directly observed on the target date; '
        'product listings and price snapshots go in retail_observations only with an '
        'explicit observation timestamp for the reporting date. Include reference_date. '
        'Keep original article publication vs a price last-updated field distinct. '
        'A source excerpt must mention Angelbird or AV PRO directly. '
        'Never invent author, quote, original URL, engagement, photo or full traffic. '
        'If publisher original date is not visible, mark the source unverified. '
        'For each item return: url, platform, title, author, publisher, published_date, '
        'date_evidence, source_excerpt, summary, sentiment, priority, status, '
        'image_url, image_credit_url, image_context, product, impact, response_action, '
        'engagement (numeric sourced counts only), engagement_source, comments (list of '
        '{author,text,date,url}), verification_note. '
        'For post replies/comments use individual permalinks wherever possible. '
        'Every platform searched and source inaccessible must appear honestly in coverage. '
        'Do NOT claim coverage for platforms outside this sweep. '
        'Use comments ONLY where the original comment author/url is available. '
        'Do not fill missing platform data with prior-date posts. '
        'No sampling boilerplate, duplicate sources, fake image links or fabricated '
        'metrics. JSON only with exact keys report_date, status, headline, '
        'today_findings, unverified_leads, older_leads, retail_observations, '
        'coverage (list {platform,checked,summary}), visibility_gaps, methodology. '
        f'report_date={day}. Original source date evidence is mandatory for verified.'
    )

def research_sweeps(day,existing,root=None):
    root=Path(root or ROOT)
    key=os.getenv('OPENAI_API_KEY','')
    if not key:return existing,[{'status':'skipped','reason':'OPENAI_API_KEY missing'}]
    model=os.getenv('OPENAI_MODEL','gpt-4.1-mini')
    if model not in ('gpt-4.1-mini','gpt-4o-mini'):
        raise RuntimeError('Cost guard: only GPT-4.1-mini and GPT-4o-mini allowed')
    max_rounds=max(1,min(3,int(os.getenv('GPT_MAX_RESEARCH_ROUNDS','3'))))
    max_web=max(1,min(2,int(os.getenv('GPT_MAX_WEB_CALLS','2'))))
    force=os.getenv('GPT_FORCE_RESEARCH','').lower() in ('1','true')
    logs=[]
    for scope,targets in SWEEPS[:max_rounds]:
        paths=_paths(day,scope,root)
        if paths['evidence'].exists() and not force:
            try:
                saved=json.loads(paths['evidence'].read_text(encoding='utf-8'))
                evidence=ResearchReport.model_validate(saved).enforce_date_guardrails()
                # Existing verified status was source-checked in earlier run; rechecking
                # on later same-day runs remains conservative.
                evidence=verify_ai_candidates(evidence,existing)
                existing,merged=merge(existing,evidence)
                logs.append({'scope':scope,'status':'cached_evidence','api_calls':0,
                             'merged':merged})
                continue
            except (ValueError,OSError) as exc:
                logs.append({'scope':scope,'status':'invalid_cache',
                             'error':str(exc)[:140],'api_calls':0})
        if paths['attempt'].exists() and not force:
            logs.append({'scope':scope,'status':'previous_attempt_protected','api_calls':0})
            continue
        _write(paths['attempt'],{'status':'started','scope':scope,'report_date':day,
                                'start_utc':datetime.now(timezone.utc).isoformat(),
                                'model':model,'web_call_limit':max_web,
                                'note':'One request per platform sweep per report date. No automatic retries.'})
        try:
            from openai import OpenAI
            response=OpenAI(timeout=110,max_retries=0).responses.create(
                model=model,input=_instructions(day,scope,targets),
                tools=[{'type':'web_search','search_context_size':'low'}],
                tool_choice='required',max_tool_calls=max_web,
                max_output_tokens=4200)
            raw=response.output_text or ''
            paths['raw'].write_text(raw,encoding='utf-8')
            observed=sum(1 for e in response.output or []
                         if getattr(e,'type','')=='web_search_call')
            usage=response.usage.model_dump(mode='json') if getattr(response,'usage',None) else {}
            _write(paths['usage'],{'scope':scope,'model':model,'search_events':observed,
                                   'usage':usage,'response_id':getattr(response,'id',''),
                                   'pricing':'OpenAI account usage dashboard; dollar cap not guaranteed'})
            parsed=_normalize_response(_json(raw),day)
            if parsed.get('report_date')!=day:
                raise ValueError('Wrong report date returned')
            evidence=ResearchReport.model_validate(parsed).enforce_date_guardrails()
            evidence=verify_ai_candidates(evidence,existing)
            _write(paths['evidence'],evidence.model_dump(mode='json'))
            existing,merged=merge(existing,evidence)
            _write(paths['attempt'],{'status':'completed','scope':scope,
                                     'api_calls':1,'web_search_events':observed})
            logs.append({'scope':scope,'status':'completed','api_calls':1,
                         'search_events':observed,'merged':merged})
        except Exception as exc:
            # Failure does not block the other independent platform groups or PDF.
            _write(paths['attempt'],{'status':'failed','scope':scope,'error':str(exc)[:300]})
            logs.append({'scope':scope,'status':'failed','api_calls':'attempted',
                         'reason':str(exc)[:170]})
            existing.visibility_gaps.append(
                f'{scope} research unavailable; API attempt guarded against repeat billing.')
    return existing,logs
