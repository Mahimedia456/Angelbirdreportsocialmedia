"""Daily monitoring entry point. JSON research and PDF rendering are separately executable."""
import json,os
from datetime import datetime,date
from pathlib import Path
from zoneinfo import ZoneInfo
from .schema import ResearchReport,Coverage
from .research import research_day
from .history import compile_history
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
        report,sweeps=research_day(target)
    report=compile_history(report,ROOT)
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
