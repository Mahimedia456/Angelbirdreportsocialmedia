import json,os
from datetime import datetime,date
from pathlib import Path
from zoneinfo import ZoneInfo
from .schema import ResearchReport, Finding, Coverage
from .research import research_day
from .pdf_report import render_pdf

ROOT=Path(__file__).resolve().parents[1]

def main():
    now=datetime.now(ZoneInfo('Asia/Karachi'))
    target=(os.getenv('REPORT_DATE') or '').strip() or now.date().isoformat()
    date.fromisoformat(target)
    dry=os.getenv('DRY_RUN','').lower() in ('true','1','yes')
    if dry:
        report=ResearchReport(report_date=target,status='DEMO ONLY - no live research',
            headline='Demonstration report only. No live source verification was performed.',
            coverage=[Coverage(platform=s,summary='Not checked: demonstration mode',checked=False)
                      for s in ('Reddit / forums','YouTube','Facebook / Instagram / LinkedIn','News / resellers')],
            visibility_gaps=['No live web search performed in demonstration mode.'])
        sweeps=[]
    else:
        report,sweeps=research_day(target)
    # Preserve explicit dated historical leads from the supplied reference without
    # counting them as today's mentions or overwriting anything newer.
    watch_path=ROOT/'data'/'watchlist.json'
    if watch_path.exists():
        for raw in json.loads(watch_path.read_text(encoding='utf-8')):
            old=Finding.model_validate(raw)
            if old.published_date != target and all(old.url != x.url for x in report.older_leads):
                report.older_leads.append(old)
    report.generated_at_pkt=now.strftime('%Y-%m-%d %H:%M PKT')
    dest=ROOT/'reports'/target[:4]/target[5:7]
    dest.mkdir(parents=True,exist_ok=True)
    data=ROOT/'data'/target[:4]/target[5:7]
    data.mkdir(parents=True,exist_ok=True)
    base=f'Angelbird-Social-Monitoring-{target}' + ('-DEMO' if dry else '')
    (data/(base+'.json')).write_text(report.model_dump_json(indent=2),encoding='utf-8')
    if sweeps:
        (data/(base+'-research-evidence.json')).write_text(json.dumps(sweeps,ensure_ascii=False,indent=2),encoding='utf-8')
    pdf=dest/(base+'.pdf')
    render_pdf(report,pdf)
    print('PDF generated:',pdf)
    return pdf

if __name__=='__main__':main()
