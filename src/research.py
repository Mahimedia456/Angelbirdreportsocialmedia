"""Budget-limited, single-request monitoring. No unbounded multi-sweep agent."""
import json, os, re
from pathlib import Path
from .schema import ResearchReport

ROOT = Path(__file__).resolve().parents[1]
PROMPT = ROOT / 'prompts' / 'research.md'

def parse_json(text):
    value=text.strip()
    value=value.lstrip('\ufeff\u200c\u200b')
    if value.startswith('```'):
        value=re.sub(r'^```(?:json)?\s*|\s*```$', '', value, flags=re.I)
    return json.loads(value)

def substantive_report(payload):
    if not isinstance(payload,dict):
        return False
    headline=str(payload.get('headline') or '').strip()
    if not headline or headline in ('Evidence-based summary','One-line sourced summary'):
        return False
    if any(payload.get(k) for k in ('today_findings','retail_observations','unverified_leads','older_leads')):
        return True
    # An empty day can still be a valid report if its coverage is source-specific,
    # explicitly describes actual searches and gaps, and is not a default template.
    coverage=payload.get('coverage') or []
    return bool(coverage and any(
        isinstance(x,dict) and len(str(x.get('summary') or '').strip())>=45
        and str(x.get('summary')).strip()!='Bounded public search'
        for x in coverage))

def research_day(report_date):
    if not os.getenv('OPENAI_API_KEY'):
        raise RuntimeError('OPENAI_API_KEY missing')
    model=os.getenv('OPENAI_MODEL','gpt-4.1-mini')
    if model not in {'gpt-4.1-mini','gpt-4o-mini'}:
        raise RuntimeError('Cost guard: OPENAI_MODEL must be gpt-4.1-mini or gpt-4o-mini. Set GitHub variable OPENAI_MODEL=gpt-4.1-mini.')
    max_calls=max(1,min(2,int(os.getenv('MAX_WEB_CALLS','2'))))
    cache=ROOT/'data'/report_date[:4]/report_date[5:7]/f'Angelbird-Social-Monitoring-{report_date}.json'
    if cache.exists() and os.getenv('FORCE_RESEARCH','').lower() not in {'true','1'}:
        saved=json.loads(cache.read_text(encoding='utf-8'))
        if substantive_report(saved):
            print('Reusing previous substantive report JSON, no API charges.',flush=True)
            return ResearchReport.model_validate(saved).enforce_date_guardrails(),[]
        print('Prior report is a placeholder. Not using it as research evidence.',flush=True)
    from openai import OpenAI
    client=OpenAI(timeout=120,max_retries=0)
    print(f'Low-cost research: one request, max {max_calls} web tool calls, model {model}',flush=True)
    instructions = PROMPT.read_text(encoding='utf-8') + """
Conduct targeted research in priority order: 1 Reddit user posts/comments, 2 YouTube creator posts/comments, 3 camera forums, 4 public social/press, 5 retailers only if budget remains.\nStay within the small search budget. Actually use web search, report original source URLs,
and detail sources checked. Never reuse example JSON, or generic placeholders such as
'Evidence-based summary' or 'Bounded public search'. No claims of full platform coverage.
Return ONE JSON object with keys: report_date, status, headline, today_findings,
retail_observations, unverified_leads, older_leads, coverage, visibility_gaps, methodology.
Each finding has keys title, platform, url, author, published_date, date_evidence, summary,
sentiment, priority, status, image_url, product, details, source_excerpt, response_action,
impact, verification_note, engagement (object), images (list of image URLs).
source_excerpt must quote or faithfully transcribe actual original post text explicitly naming Angelbird or AV PRO.
Do not mark a same-day mention verified unless source_excerpt demonstrates DIRECT brand mention.
Generic Reddit/platform news or speculative implications for Angelbird are irrelevant and excluded.
For comments, include the original comment permalink and author where available.
Record response priority, sentiment, creator/reviewer context and metrics only when visible.
If no same-day verified mentions are found, explain actual platform coverage and evidence gaps.
Keep independently verified 30 Oct mentions separate from older and undated sources.
All findings must have original clickable URLs. Do not invent sources.
"""
    request = (f'Angelbird monitoring for {report_date} Asia/Karachi. Prioritize distinct queries: Angelbird Reddit {report_date}; Angelbird YouTube {report_date}; Angelbird camera forum {report_date}. Search public posts/comments '
               'on Reddit, YouTube, camera forums, indexed social accounts, news and retailers. '
               'Prioritize customer feedback and source dates. Show genuine found leads including '
               'undated leads marked unverified. Provide a specific evidence-driven headline '
               'and coverage per searched platform. Return complete JSON, not a template.')
    response=client.responses.create(model=model,tools=[{'type':'web_search','search_context_size':'low'}],
        tool_choice='required',max_tool_calls=max_calls,max_output_tokens=4500,
        instructions=instructions,input=request)
    raw=response.output_text or ''
    # Preserve raw result so an unexpected format does not force paid research again.
    scratch=ROOT/'data'/report_date[:4]/report_date[5:7]
    scratch.mkdir(parents=True,exist_ok=True)
    (scratch/f'Angelbird-Social-Monitoring-{report_date}-raw-response.txt').write_text(raw,encoding='utf-8')
    usage=getattr(response,'usage',None)
    usage_info=usage.model_dump(mode='json') if usage is not None else {}
    tool_calls=[x for x in response.output if getattr(x,'type','') in ('web_search_call','web_search_preview')]
    diagnostics={'model':model,'max_web_calls':max_calls,'observed_web_call_events':len(tool_calls),
                 'usage':usage_info,'response_id':getattr(response,'id',''),
                 'note':'Token counts are API-reported. Dollar cost requires the account usage dashboard; no hard per-run dollar cap.'}
    (scratch/f'Angelbird-Social-Monitoring-{report_date}-usage.json').write_text(json.dumps(diagnostics,indent=2),encoding='utf-8')
    print('API usage:',json.dumps(diagnostics,ensure_ascii=False),flush=True)
    parsed=parse_json(raw)
    if not substantive_report(parsed):
        raise RuntimeError('Placeholder-only AI result. Raw output saved. No finished report generated; inspect source evidence before paid rerun.')
    report=ResearchReport.model_validate(parsed).enforce_date_guardrails()
    if report.report_date!=report_date: raise ValueError('Research date mismatch')
    return report,[{'scope':'bounded targeted research','text':raw}]
