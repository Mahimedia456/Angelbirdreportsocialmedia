"""Build unlimited-length weekly/monthly evidence report from dated saved research."""
import argparse,json,re
from pathlib import Path
from datetime import date,timedelta
from collections import Counter
from calendar import monthrange
from reportlab.platypus import SimpleDocTemplate,Spacer
from reportlab.lib.pagesizes import A4
from src.schema import ResearchReport
from src.platform_analytics import PLATFORMS,platform_summary
from src.social_content import content_type
from src import pdf_report_v2 as pdf

ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--period',choices=['weekly','monthly'],required=True)
    ap.add_argument('--end',default='')
    args=ap.parse_args()
    end=date.fromisoformat(args.end) if args.end else date.today()
    start=end-timedelta(days=6) if args.period=='weekly' else end.replace(day=1)
    brand='Atomos' if 'smratomos' in str(ROOT).lower() else 'Angelbird'
    gathered=[];leads=[];offers=[];saved=[];seen=set()
    for n in range((end-start).days+1):
        d=start+timedelta(days=n)
        p=ROOT/'data'/d.strftime('%Y')/d.strftime('%m')/(f'{brand}-Social-Monitoring-{d}.json')
        if not p.exists():continue
        try:report=ResearchReport.model_validate(json.loads(p.read_text(encoding='utf-8')))
        except Exception as e:
            print('INVALID DAILY EVIDENCE',p,str(e));continue
        saved.append(str(d))
        for field,target in [('today_findings',gathered),('historical_findings',gathered),
                             ('unverified_leads',leads),('retail_observations',offers),('historical_retail',offers)]:
            for item in getattr(report,field):
                stamp=item.reference_date or item.published_date if target is offers else item.published_date
                try:valid=start<=date.fromisoformat(str(stamp))<=end
                except (ValueError,TypeError):valid=False
                if not valid:continue
                if target is gathered and (item.status!='verified' or not item.date_evidence):continue
                key=(item.url.strip().lower().rstrip('/'), 'offer' if target is offers else 'lead' if target is leads else 'finding')
                if key in seen:continue
                seen.add(key);target.append(item)
    gathered.sort(key=lambda x:x.published_date or '',reverse=True)
    grouped=platform_summary(gathered);unverified=platform_summary(leads)
    output=ROOT/'reports'/str(end.year)/f'{end.month:02d}'/f'{brand}-Social-Monitoring-{args.period.title()}-{start}_to_{end}.pdf'
    output.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(output),pagesize=A4,topMargin=35,bottomMargin=60,leftMargin=pdf.MARGIN,rightMargin=pdf.MARGIN)
    story=[pdf.band(brand.upper()+' | '+args.period.upper()+' SOCIAL MONITORING',f'{start} TO {end}'),
           Spacer(1,9),pdf.P(f'Saved daily research snapshots: {len(saved)} of {(end-start).days+1}. Missing days are incomplete coverage, NOT zero activity.','small'),
           Spacer(1,8)]
    story.extend(pdf.engagement_overview(gathered))
    types=Counter(content_type(x) for x in gathered)
    story.extend([Spacer(1,8),pdf.P('CONTENT TYPES | '+', '.join(f'{k}: {types.get(k,0)}' for k in ('post','story','reel','tagged_post','mention','comment','video','article')),'small'),
                  Spacer(1,5),pdf.P(f'Linked comment excerpts: {sum(len(x.comments or []) for x in gathered)} | Engagement unavailable means N/A, not zero.','small')])
    for platform in PLATFORMS:
        items=grouped.get(platform,[])
        story.extend([Spacer(1,13)]+pdf.platform_scorecard(platform,items,f'{start} TO {end}'))
        for index,item in enumerate(items,1):
            story.extend([Spacer(1,8),pdf.P(f'{platform.upper()} | {content_type(item).upper()} | {item.published_date}','caption'),
                          pdf.P(item.title,'item'),Spacer(1,4),pdf.P('Author: '+(item.author or 'Not available')+' | Sentiment: '+item.sentiment,'meta'),
                          pdf.link(item.url,'OPEN ORIGINAL SOURCE'),pdf.source_url_line(item.url),Spacer(1,5)])
            for label,value in [('Source excerpt',item.source_excerpt),('Analysis',item.summary),('Impact',item.impact),('Response',item.response_action),('Date evidence',item.date_evidence)]:
                if value:story.extend([pdf.P(label+': '+str(value),'small'),Spacer(1,5)])
            for label,values in [('Hashtags',item.hashtags),('Mentions',item.mentioned_accounts),('Tagged accounts',item.tagged_accounts)]:
                if values:story.extend([pdf.P(label+': '+', '.join(values),'small'),Spacer(1,4)])
            if item.engagement:story.extend([pdf.P('Observed metrics: '+', '.join(str(k)+': '+str(v) for k,v in item.engagement.items()),'small'),Spacer(1,4)])
            story.extend(pdf.evidence_thumbnail(item,max_width=pdf.W-48))
            for n,c in enumerate(item.comments or [],1):
                story.extend([pdf.P('COMMENT '+str(n)+' | '+str(c.get('author','')),'caption'),pdf.P(str(c.get('text','')),'small'),Spacer(1,4)])
                if c.get('url'):story.append(pdf.link(c['url'],'OPEN COMMENT'))
            story.append(Spacer(1,9))
        if not items:story.extend([pdf.P('No dated source record available in saved research for this period. Not evidence of zero real-world activity.','small'),Spacer(1,5)])
        if unverified.get(platform):
            story.append(pdf.P('UNVERIFIED LEADS | EXCLUDED FROM KPIs','caption'))
            for x in unverified[platform]:
                story.extend([pdf.P(x.title,'small'),pdf.link(x.url,'OPEN SOURCE LEAD'),Spacer(1,5)])
    story.extend([Spacer(1,9),pdf.P('Retail price observations: '+str(len(offers))+' (not social posts)','small')])
    for item in offers:
        story.extend([pdf.P(item.title,'small'),pdf.link(item.url,'RETAIL SOURCE'),Spacer(1,5)])
    doc.build(story,onFirstPage=pdf.footer,onLaterPages=pdf.footer)
    result={'period':args.period,'start':str(start),'end':str(end),'path':output.relative_to(ROOT).as_posix(),
            'snapshots':len(saved),'dated_findings':len(gathered),'unverified_leads':len(leads),
            'platform_counts':{p:len(grouped[p]) for p in PLATFORMS}}
    (ROOT/'reports'/f'{args.period}-latest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
if __name__=='__main__':main()
