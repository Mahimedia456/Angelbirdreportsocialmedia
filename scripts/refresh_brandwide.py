"""Revisit one daily report using brand-wide queries WITHOUT replacing saved evidence.

Previously captured originals are immutable; new original-source findings and
source-only leads are merged by canonical source URL and kept separate.
"""
import argparse,json
from pathlib import Path
from src.public_research import collect_day
from src.schema import ResearchReport
from src.platform_analytics import category

ROOT=Path(__file__).resolve().parents[1]
BRAND='Atomos' if 'smratomos' in str(ROOT).lower() else 'Angelbird'
FIELDS=('today_findings','historical_findings','retail_observations','historical_retail',
        'unverified_leads','older_leads')

def source_key(item):
    return str(item.url or '').split('#')[0].strip().rstrip('/').lower()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--date',required=True)
    args=ap.parse_args()
    day=args.date
    path=ROOT/'data'/day[:4]/day[5:7]/f'{BRAND}-Social-Monitoring-{day}.json'
    if not path.is_file():raise FileNotFoundError(f'Original saved source report missing: {path}')
    previous=ResearchReport.model_validate(json.loads(path.read_text(encoding='utf-8')))
    new_report,sweeps=collect_day(day)
    new_report=ResearchReport.model_validate(new_report.model_dump(mode='json'))
    additions={}
    dated_urls={source_key(x) for field in ('today_findings','historical_findings') for x in getattr(previous,field)}
    for field in FIELDS:
        old_items=list(getattr(previous,field))
        seen={source_key(x) for x in old_items}
        added=0
        for item in getattr(new_report,field):
            key=source_key(item)
            if key in seen or (field in ('unverified_leads','older_leads') and key in dated_urls):
                continue
            old_items.append(item);seen.add(key);added+=1
            if field in ('today_findings','historical_findings'):dated_urls.add(key)
        setattr(previous,field,old_items)
        additions[field]=added
    # Avoid a misleading verified dated count when the same URL appears in an
    # indexed lead and a source-verified record.
    for field in ('unverified_leads','older_leads'):
        setattr(previous,field,[x for x in getattr(previous,field)
                                   if source_key(x) not in dated_urls])
    # Existing status and source provenance are retained; include new coverage.
    coverage_seen={(x.platform,x.summary) for x in previous.coverage}
    for entry in new_report.coverage:
        key=(entry.platform,entry.summary)
        if key not in coverage_seen:
            previous.coverage.append(entry);coverage_seen.add(key)
    gaps=set(previous.visibility_gaps)
    previous.visibility_gaps.extend(x for x in new_report.visibility_gaps if x not in gaps)
    previous.methodology+=' | Brand-wide original-source refresh: all available products and general brand topics'
    path.write_text(json.dumps(previous.model_dump(mode='json'),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    log={'day':day,'brand':BRAND,'additions':additions,
         'dated_total':len(previous.today_findings)+len(previous.historical_findings),
         'leads_total':len(previous.unverified_leads)}
    audit_path=path.with_name(path.stem+'-brandwide-audit.json')
    audit_path.write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(log))
if __name__=='__main__':main()
