import json, os, re, time
from pathlib import Path
from .schema import ResearchReport

PROMPT = Path(__file__).resolve().parents[1] / 'prompts' / 'research.md'
SEARCHES = [
    'Reddit and camera discussion forums: Angelbird dated posts AND comments',
    'YouTube creator videos and indexed comments mentioning Angelbird',
    'Facebook public pages/groups Angelbird feedback posts, Instagram and LinkedIn',
    'Photography/videography news, Newsshooter, CineD, PetaPixel, reviewer articles',
    'Angelbird retailers/resellers listings and current dated promotions worldwide',
]

def parse_json(text):
    text=text.strip()
    if text.startswith('```'):
        text=re.sub(r'^```(?:json)?\s*|\s*```$', '', text, flags=re.I)
    return json.loads(text)

def research_day(report_date):
    if not os.getenv('OPENAI_API_KEY'):
        raise RuntimeError('OPENAI_API_KEY missing. Configure GitHub Actions repository secret.')
    from openai import OpenAI
    client=OpenAI(timeout=180)
    model=os.getenv('OPENAI_MODEL','gpt-5.5')
    chunks=[]
    for i,scope in enumerate(SEARCHES,1):
        print(f'[{i}/{len(SEARCHES)}] Researching {scope}', flush=True)
        r=client.responses.create(
            model=model,
            tools=[{'type':'web_search','search_context_size':'high'}],
            tool_choice='required',
            instructions=PROMPT.read_text(encoding='utf-8'),
            input=(f'Actual target date is {report_date} (Pakistan time). Research ONLY scope: {scope}. '
                   'Do multiple targeted source/date searches. Respond with concise evidence-led findings '
                   'including original URLs and independently verified publication dates. '
                   'Separate verified today, older leads, retailer offers, and unverified leads. '
                   'Report source coverage and visibility limitations. Use factual concise prose.'),
        )
        chunks.append({'scope':scope,'text':r.output_text})
        time.sleep(1)
    print('Synthesizing structured report', flush=True)
    schema_example={
      'report_date':report_date,'status':'Evening monitoring run','headline':'One-line sourced summary',
      'today_findings':[],'retail_observations':[],'unverified_leads':[],'older_leads':[],
      'coverage':[{'platform':'Reddit / forums','summary':'Searched public indexed results; outcome','checked':True}],
      'visibility_gaps':['Private groups and login-only comments'],
      'methodology':'Exact-date independently verified evidence only'
    }
    r=client.responses.create(model=model,instructions=PROMPT.read_text(encoding='utf-8'),
        input=('Merge the following 5 research sweep results. Deduplicate by actual source URL. '
               'Emit a SINGLE valid JSON object matching this shape (finding objects have keys '
               'title, platform, url, author, published_date, date_evidence, summary, sentiment, '
               'priority, status, image_url, product, details). No guessed verification. '
               'For a verified item, published_date MUST be exactly report_date and date_evidence nonempty. '
               'If uncertain mark unverified. Find only evidence present in sweep data. '
               f'JSON shape: {json.dumps(schema_example)}\n'
               f'SWEEP DATA:\n{json.dumps(chunks,ensure_ascii=False)}'))
    report=ResearchReport.model_validate(parse_json(r.output_text)).enforce_date_guardrails()
    if report.report_date != report_date: raise ValueError('Research date mismatch')
    return report,chunks
