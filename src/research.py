"""Budget-limited, single-request monitoring. No unbounded multi-sweep agent."""
import json, os, re
from pathlib import Path
from .schema import ResearchReport

ROOT = Path(__file__).resolve().parents[1]
PROMPT = ROOT / 'prompts' / 'research.md'

def parse_json(text):
    value=text.strip()
    if value.startswith('‌'): value=value[1:]
    if value.startswith('```'):
        value=re.sub(r'^```(?:json)?\s*|\s*```$', '', value, flags=re.I)
    return json.loads(value)

def research_day(report_date):
    if not os.getenv('OPENAI_API_KEY'):
        raise RuntimeError('OPENAI_API_KEY missing')
    model=os.getenv('OPENAI_MODEL','gpt-4.1-mini')
    if model not in {'gpt-4.1-mini','gpt-4o-mini'}:
        raise RuntimeError('Cost guard: OPENAI_MODEL must be gpt-4.1-mini or gpt-4o-mini. Set GitHub variable OPENAI_MODEL=gpt-4.1-mini.')
    max_calls=max(1,min(2,int(os.getenv('MAX_WEB_CALLS','2'))))
    cache=ROOT/'data'/report_date[:4]/report_date[5:7]/f'Angelbird-Social-Monitoring-{report_date}.json'
    if cache.exists() and os.getenv('FORCE_RESEARCH','').lower() not in {'true','1'}:
        print('Reusing existing report JSON. No API charges.',flush=True)
        return ResearchReport.model_validate(json.loads(cache.read_text(encoding='utf-8'))).enforce_date_guardrails(),[]
    from openai import OpenAI
    client=OpenAI(timeout=120,max_retries=0)
    print(f'Low-cost research: one request, max {max_calls} web tool calls, model {model}',flush=True)
    shape={'report_date':report_date,'status':'Budget-limited monitoring run','headline':'Evidence-based summary','today_findings':[],
        'retail_observations':[],'unverified_leads':[],'older_leads':[],
        'coverage':[{'platform':'Reddit / YouTube / social / forums / retailers','summary':'Bounded public search','checked':True}],
        'visibility_gaps':['Budget-limited public-index coverage, not exhaustive'],'methodology':'Original URLs and exact dates required'}
    instructions=('Return ONLY a compact JSON object, with keys and arrays exactly as requested. '
        'Each finding must include title, platform, url, author, published_date, date_evidence, summary, sentiment, priority, status, image_url, product, details. '
        'Use sentiment Positive/Negative/Neutral/Question/Not applicable, priority Urgent/High/Medium/Low/Watch, '
        'status verified/unverified/older/retail. Null dates become empty strings. '
        'Verify original URL and publication date before counting a new report-date mention. '
        'Include only up to 7 high-value records total. Never invent URLs/dates, never count undated leads as verified, '
        'and never count retailer offers as sentiment. If evidence is weak, explicitly mark gaps and zero confirmed today.')
    request=(f'Report date {report_date}, timezone Asia/Karachi. Search Angelbird mentions in public indexed Reddit, '
        'YouTube, Facebook, Instagram, LinkedIn, camera forums, press and retailers. '
        'Prioritize dated customer feedback/issues, and avoid broad undated retail catalogs. '
        'Concentrate search budget on high-signal dated results. Output compact JSON, no markdown. '
        f'JSON skeleton: {json.dumps(shape)}')
    response=client.responses.create(model=model,tools=[{'type':'web_search','search_context_size':'low'}],
        tool_choice='required',max_tool_calls=max_calls,max_output_tokens=4500,
        instructions=instructions,input=request)
    raw=response.output_text or ''
    # Preserve raw result so an unexpected format does not force paid research again.
    scratch=ROOT/'data'/report_date[:4]/report_date[5:7]
    scratch.mkdir(parents=True,exist_ok=True)
    (scratch/f'Angelbird-Social-Monitoring-{report_date}-raw-response.txt').write_text(raw,encoding='utf-8')
    report=ResearchReport.model_validate(parse_json(raw)).enforce_date_guardrails()
    if report.report_date!=report_date: raise ValueError('Research date mismatch')
    return report,[{'scope':'single budget-limited public web research','text':raw}]
