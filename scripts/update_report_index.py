"""Generate a public daily-report manifest whenever the scheduled bot saves a PDF.

The manifest is committed to main, so Vercel clients can refresh latest reports from
GitHub even if the static deployment has not rebuilt yet.
"""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NAME=re.compile(r'Angelbird-Social-Monitoring-(\d{4}-\d{2}-\d{2})(-DEMO)?\.pdf$',re.I)

PERIOD_NAME=re.compile(r'Angelbird-Social-Monitoring-(Weekly|Monthly)-(\d{4}-\d{2}-\d{2})_to_(\d{4}-\d{2}-\d{2})\.pdf$',re.I)

def build():
    out=[]
    for pdf in sorted((ROOT/'reports').glob('*/*/*.pdf')):
        m=NAME.fullmatch(pdf.name)
        if not m:
            period=PERIOD_NAME.fullmatch(pdf.name)
            if not period:continue
            kind,start,end=period.groups()
            year,month,_=end.split('-')
            if pdf.parent.name!=month or pdf.parent.parent.name!=year:continue
            rel=pdf.relative_to(ROOT).as_posix()
            out.append({'id':kind.lower()+'-'+start+'-'+end,'date':end,'month':year+'-'+month,
                        'type':kind.lower(),'start':start,'end':end,'name':pdf.name,
                        'demo':False,'path':rel,
                        'source_url':'https://raw.githubusercontent.com/Mahimedia456/Angelbirdreportsocialmedia/main/'+rel})
            continue
        day, demo=m.groups()
        year,month,_=day.split('-')
        if pdf.parent.name!=month or pdf.parent.parent.name!=year:continue
        rel=pdf.relative_to(ROOT).as_posix()
        out.append({'id':day+('-DEMO' if demo else ''),'date':day,
                    'month':f'{year}-{month}','name':pdf.name,
                    'type':'daily','demo':bool(demo),'path':rel,
                    'source_url':'https://raw.githubusercontent.com/Mahimedia456/Angelbirdreportsocialmedia/main/'+rel})
    real_dates={x['date'] for x in out if not x['demo']}
    out=[x for x in out if not x['demo'] or x['date'] not in real_dates]
    out.sort(key=lambda x:(x['date'],not x['demo']),reverse=True)
    (ROOT/'reports-index.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(f'Root reports manifest refreshed: {len(out)} PDF(s); latest={out[0]["date"] if out else "none"}')
    return out

if __name__=='__main__':build()
