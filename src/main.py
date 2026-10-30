"""Daily monitoring entry point. JSON research and PDF rendering are separately executable."""
import json,os
from datetime import datetime,date
from pathlib import Path
from zoneinfo import ZoneInfo
from .schema import ResearchReport,Coverage
from .public_research import collect_day,cache_historical_images
from .history import compile_history
from .chatgpt_import import import_chatgpt_evidence
from .paid_gpt import supplement as paid_supplement, merge as merge_paid
from .pdf_report_v2 import render_pdf

ROOT=Path(__file__).resolve().parents[1]

def main():
    now=datetime.now(ZoneInfo('Asia/Karachi'))
    target=(os.getenv('REPORT_DATE') or '').strip() or now.date().isoformat()
    date.fromisoformat(target)
    dry=os.getenv('DRY_RUN','').lower() in ('true','1','yes')
    render_only=os.getenv('REPORT_ONLY','').lower() in ('true','1','yes')
    data=ROOT/'data'/target[:4]/target[5:7]
    data.mkdir(parents=True,exist_ok=True)
    base=f'Angelbird-Social-Monitoring-{target}'+('-DEMO' if dry else '')
    json_path=data/(base+'.json')
    sweeps=[]
    engine=os.getenv('RESEARCH_ENGINE','python').strip().lower()
    if engine!='python' and not render_only and not dry:
        raise RuntimeError('Only free Python collection is enabled. ChatGPT web evidence is imported from JSON, not a paid API.')
    if render_only:
        if not json_path.exists():
            raise FileNotFoundError('No saved research JSON for '+target+'. Render-only does not call the API.')
        print('REPORT_ONLY enabled: building PDF from saved research + historical archive, no API charges.')
        report=ResearchReport.model_validate(json.loads(json_path.read_text(encoding='utf-8'))).enforce_date_guardrails()
    elif dry:
        report=ResearchReport(report_date=target,status='DEMO ONLY - no live research',
             headline='Demonstration layout: no new daily research performed.',
             coverage=[Coverage(platform=p,summary='Not checked (demo only)',checked=False)
                for p in ('Reddit / forums','YouTube','Facebook / Instagram / LinkedIn','News / resellers')],
             visibility_gaps=['No live research performed in demo mode.'])
    else:
        print('Collecting public sources with Python and connected YouTube API (no OpenAI API calls).',flush=True)
        report,sweeps=collect_day(target)
    report,import_audit=import_chatgpt_evidence(report,ROOT)
    if import_audit['found']:
        sweeps.append({'scope':'ChatGPT web research JSON import','data':import_audit})
    if not render_only and not dry and os.getenv('GPT_RESEARCH_ENABLED','false').lower() in ('1','true','yes'):
        print('Optional paid GPT research: one request, maximum two web searches per date.',flush=True)
        paid_report, paid_audit=paid_supplement(target, report)
        report, paid_added=merge_paid(report,paid_report)
        sweeps.append({'scope':'Paid GPT bounded supplement','data':dict(paid_audit,merged=paid_added)})
        if paid_report is None:
            report.visibility_gaps.append('Optional paid GPT supplement unavailable: see GPT attempt diagnostics; free findings preserved.')
    report=compile_history(report,ROOT)
    fetch_images=os.getenv('FETCH_EVIDENCE_IMAGES','').lower() in ('1','true','yes')
    if not dry and engine=='python' and (not render_only or fetch_images):
        image_audit=cache_historical_images(report)
        sweeps.append({'scope':'Historical source image cache','data':image_audit})
    # A previously saved model run counted unrelated Reddit platform news as an
    # Angelbird mention. When relevance guardrails exclude all such candidates,
    # replace the stale source-summary language with an accurate limited-coverage note.
    if not report.today_findings and report.status!='Python public-source monitoring' and any('candidate items excluded' in gap for gap in report.visibility_gaps):
        report.headline=(f'No directly evidenced new Angelbird brand mentions were retained for {target} '
                         f'from this bounded research run. Previous dated findings are preserved below.')
        report.status='Limited source coverage - relevance corrected'
    report.headline=(f'{len(report.today_findings)} dated new Angelbird source finding(s), '
                     f'{len(report.retail_observations)} current-day price/retail observations, '
                     f'{len(report.historical_findings)} previous-five-day references. '
                     'Coverage limited to source-accessible results; retail snapshots are not social posts.')
    report.generated_at_pkt=now.strftime('%Y-%m-%d %H:%M PKT')
    dest=ROOT/'reports'/target[:4]/target[5:7]
    dest.mkdir(parents=True,exist_ok=True)
    # Retain machine-readable daily evidence and cumulative historical sections.
    json_path.write_text(report.model_dump_json(indent=2),encoding='utf-8')
    if sweeps:
        (data/(base+'-research-evidence.json')).write_text(
            json.dumps(sweeps,ensure_ascii=False,indent=2),encoding='utf-8')
    pdf=dest/(base+'.pdf')
    render_pdf(report,pdf)
    print(f'PDF generated: {pdf} | Today={len(report.today_findings)} | Prior={len(report.historical_findings)}')
    return pdf

if __name__=='__main__':
    main()
