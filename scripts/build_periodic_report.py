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
    gathered=[];leads=[];offers=[];saved=[];seen=set();coverage_checks=[]
    for n in range((end-start).days+1):
        d=start+timedelta(days=n)
        p=ROOT/'data'/d.strftime('%Y')/d.strftime('%m')/(f'{brand}-Social-Monitoring-{d}.json')
        if not p.exists():continue
        try:report=ResearchReport.model_validate(json.loads(p.read_text(encoding='utf-8')))
        except Exception as e:
            print('INVALID DAILY EVIDENCE',p,str(e));continue
        saved.append(str(d))
        for status in report.coverage:
            coverage_checks.append((str(d),status.platform,bool(status.checked),str(status.summary or '')))
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
    # Recover original dated historical evidence that is not in the daily collector archive.
    # Keep reference-sourced records identifiable and do not promote them to API-verified.
    from src.schema import Finding
    archived=0
    for archive_path in sorted((ROOT/'data').glob('reference_*.json')):
        try:archive=json.loads(archive_path.read_text(encoding='utf-8'))
        except (OSError,ValueError):continue
        for raw in archive.get('findings',[]):
            if not isinstance(raw,dict):continue
            stamp=raw.get('published_date')
            try:valid=start<=date.fromisoformat(str(stamp))<=end
            except (ValueError,TypeError):valid=False
            if not valid or not raw.get('date_evidence'):continue
            evidence=str(raw.get('date_evidence','')).lower()
            if any(marker in evidence for marker in ('date uncertain','original posting date not established','original post date uncertain','found 28 october','discovery to 28 october')):
                try:lead=Finding.model_validate(dict(raw,status='unverified',published_date=''))
                except Exception:continue
                key=(lead.url.strip().lower().rstrip('/'),'lead')
                if key not in seen:seen.add(key);leads.append(lead)
                continue
            try:item=Finding.model_validate(dict(raw,status='older'))
            except Exception:continue
            key=(item.url.strip().lower().rstrip('/'),'finding')
            if key in seen:continue
            seen.add(key);gathered.append(item);archived+=1
        for raw in archive.get('retail_observations',[]):
            if not isinstance(raw,dict):continue
            stamp=raw.get('reference_date') or raw.get('published_date')
            try:valid=start<=date.fromisoformat(str(stamp))<=end
            except (ValueError,TypeError):valid=False
            if not valid:continue
            try:item=Finding.model_validate(dict(raw,status='retail'))
            except Exception:continue
            key=(item.url.strip().lower().rstrip('/'),'offer')
            if key not in seen:seen.add(key);offers.append(item)
    # Display publicly indexed but unverified social leads in a separate evidence section.
    # They are NOT part of verified monthly platform counts or engagement.
    social_audit=ROOT/'data'/'cross_platform_oct_2026_audit.json'
    if social_audit.exists():
        try:lead_archive=json.loads(social_audit.read_text(encoding='utf-8'))
        except (OSError,ValueError):lead_archive={}
        for raw in lead_archive.get('leads',[]):
            if not isinstance(raw,dict):continue
            try:item=Finding.model_validate(dict(raw,status='unverified'))
            except Exception:continue
            key=(item.url.strip().lower().rstrip('/')+'#'+item.title.lower(),'lead')
            if key not in seen:seen.add(key);leads.append(item)
    for aux_path in sorted((ROOT/'data'/str(end.year)/f'{end.month:02d}').glob('*-gpt-*-evidence.json')):
        try:aux=json.loads(aux_path.read_text(encoding='utf-8'))
        except (OSError,ValueError):continue
        if not isinstance(aux,dict):continue
        for field in ('unverified_leads','older_leads'):
            for raw in aux.get(field,[]):
                if not isinstance(raw,dict) or not raw.get('url'):continue
                try:item=Finding.model_validate(dict(raw,status='unverified'))
                except Exception:continue
                key=(item.url.strip().lower().rstrip('/')+'#'+item.title.lower(),'lead')
                if key not in seen:seen.add(key);leads.append(item)
    gathered.sort(key=lambda x:x.published_date or '',reverse=True)
    grouped=platform_summary(gathered);unverified=platform_summary(leads)
    output=ROOT/'reports'/str(end.year)/f'{end.month:02d}'/f'{brand}-Social-Monitoring-{args.period.title()}-{start}_to_{end}.pdf'
    output.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(output),pagesize=A4,topMargin=35,bottomMargin=60,leftMargin=pdf.MARGIN,rightMargin=pdf.MARGIN)
    story=[pdf.band(brand.upper()+' | '+args.period.upper()+' SOCIAL MONITORING',f'{start} TO {end}'),
           Spacer(1,9),pdf.P(f'Saved daily research snapshots: {len(saved)} of {(end-start).days+1}. Missing days are incomplete coverage, NOT zero activity.','small'),
           Spacer(1,8)]
    story.extend([pdf.P(f'Direct collector records: {len(gathered)-archived}; archived dated records: {archived}. Archive provenance is separately labeled, and older linked sources are not newly verified by this run.','small'),Spacer(1,8)])
    # Analytical breakdown only describes collected evidence, not global platform reach.
    sentiments=Counter(x.sentiment for x in gathered)
    products=Counter(str(x.product).strip() for x in gathered if str(x.product or '').strip())
    weekly_buckets=Counter('Week '+str(1+(int(x.published_date[8:10])-1)//7) for x in gathered if x.published_date)
    measured=Counter()
    for item in gathered:
        for key in ('views','likes','comments','shares','reactions','reposts'):
            val=item.engagement.get(key) if item.engagement else None
            if isinstance(val,(int,float)) and val>=0:measured[key]+=val
    story.extend([Spacer(1,8),pdf.band('EVIDENCE QUALITY AND DEEP ANALYTICS'),Spacer(1,8),
                  pdf.P('These KPIs describe captured original-source records only. Posts column in platform scorecards includes comments and articles and must NOT be interpreted as unique social posts.','small'),
                  Spacer(1,6),pdf.P('Sentiment of observed records: '+', '.join(str(k)+': '+str(v) for k,v in sorted(sentiments.items())),'small'),
                  Spacer(1,5),pdf.P('Source date distribution: '+', '.join(str(k)+': '+str(v) for k,v in sorted(weekly_buckets.items())),'small'),
                  Spacer(1,5),pdf.P('Most frequently mentioned product labels: '+(', '.join(k[:55]+' ('+str(v)+')' for k,v in products.most_common(8)) or 'Not supplied'),'small'),
                  Spacer(1,5),pdf.P('Observed numeric engagement (partial coverage): '+(', '.join(k+': '+str(v) for k,v in sorted(measured.items())) or 'No comparable cross-platform metrics'),'small'),
                  Spacer(1,5),pdf.P('Duplicate threads or repeated complaint crossposts can inflate record counts; do not infer unique incidents or unique reach.','small'),Spacer(1,10)])
    if coverage_checks:
        counts=Counter((platform,checked) for _,platform,checked,_ in coverage_checks)
        story.extend([pdf.band('PLATFORM SEARCH COVERAGE AUDIT'),Spacer(1,8),
                      pdf.P('Public-source checks per saved research day (not proof of exhaustive coverage):','small')])
        for platform in PLATFORMS:
            ntrue=counts[(platform,True)]
            nfalse=counts[(platform,False)]
            if ntrue+nfalse:
                story.extend([pdf.P(f'{platform}: {ntrue} checked / {nfalse} incomplete snapshots','small'),Spacer(1,3)])
        story.append(Spacer(1,7))
    story.extend(pdf.engagement_overview(gathered))
    story.extend([Spacer(1,6),pdf.P(f'Additional original-link leads awaiting date/source confirmation: {len(leads)}. Leads excluded from the verified source KPI above.','small'),Spacer(1,7)])
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
                story.extend([pdf.P(x.title,'item'),Spacer(1,4),
                              pdf.P('Evidence status: UNVERIFIED / original publication date not established','small'),
                              pdf.P('Author: '+(x.author or 'Not recorded')+' | Discovery or reference date: '+(x.reference_date or x.published_date or 'Unknown'),'small'),
                              pdf.link(x.url,'OPEN SOURCE LEAD'),pdf.source_url_line(x.url),Spacer(1,5)])
                for label,value in [('Source excerpt',x.source_excerpt),('Research notes',x.summary),
                                    ('Date limitation',x.date_evidence),('Verification',x.verification_note)]:
                    if value:story.extend([pdf.P(label+': '+str(value),'small'),Spacer(1,4)])
                if x.engagement:
                    story.extend([pdf.P('Public metrics as cited in source archive (not verified this run): '+', '.join(str(k)+': '+str(v) for k,v in x.engagement.items()),'small'),Spacer(1,4)])
                for i,comment in enumerate(x.comments or [],1):
                    story.extend([pdf.P('RELATED COMMENT '+str(i)+' | '+str(comment.get('author','')),'caption'),
                                  pdf.P(str(comment.get('text','')),'small'),Spacer(1,4)])
                story.append(Spacer(1,12))
    story.extend([Spacer(1,9),pdf.P('Retail price observations: '+str(len(offers))+' (not social posts)','small')])
    for item in offers:
        story.extend([pdf.P(item.title,'small'),pdf.link(item.url,'RETAIL SOURCE'),Spacer(1,5)])
    doc.build(story,onFirstPage=pdf.footer,onLaterPages=pdf.footer)
    result={'period':args.period,'start':str(start),'end':str(end),'path':output.relative_to(ROOT).as_posix(),
            'snapshots':len(saved),'archived_findings':archived,'dated_findings':len(gathered),'unverified_leads':len(leads),
            'platform_counts':{p:len(grouped[p]) for p in PLATFORMS},'sentiment_counts':dict(sentiments),'observed_product_labels':dict(products.most_common(10)),'record_type_counts':dict(Counter(content_type(x) for x in gathered))}
    (ROOT/'reports'/f'{args.period}-latest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
if __name__=='__main__':main()
