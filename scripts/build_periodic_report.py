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
    # Reject synthetic sample-style URLs generated in earlier GPT suggestions.
    # Retain a count in the audit, but never present them as real social sources.
    def is_synthetic_sample(item):
        url=(item.url or '').lower()
        return any(fragment in url for fragment in (
            '/posts/1234567890', '/comments/abc123/', 'watch?v=def456',
            '/status/1234567890'))
    rejected_example_leads=[x.url for x in leads if is_synthetic_sample(x)]
    leads=[x for x in leads if not is_synthetic_sample(x)]
    gathered.sort(key=lambda x:x.published_date or '',reverse=True)
    # Keep a platform-specific count of supplied source media and observations.
    media_with_file=lambda x: any((ROOT/path).is_file() for path in x.image_files)
    media_link=lambda x: bool(x.image_url or x.images or x.image_credit_url)
    source_media={'embedded_verified':sum(media_with_file(x) for x in gathered),
                  'linked_verified':sum(media_link(x) for x in gathered),
                  'embedded_leads':sum(media_with_file(x) for x in leads),
                  'linked_leads':sum(media_link(x) for x in leads),
                  'missing_media_verified':sum(not media_with_file(x) and not media_link(x) for x in gathered)}
    grouped=platform_summary(gathered);unverified=platform_summary(leads)
    output=ROOT/'reports'/str(end.year)/f'{end.month:02d}'/f'{brand}-Social-Monitoring-{args.period.title()}-{start}_to_{end}.pdf'
    output.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(output),pagesize=A4,topMargin=35,bottomMargin=60,leftMargin=pdf.MARGIN,rightMargin=pdf.MARGIN)
    story=[pdf.band(brand.upper()+' | '+args.period.upper()+' SOCIAL MONITORING',f'{start} TO {end}'),
           Spacer(1,9),pdf.P(f'Saved daily research snapshots: {len(saved)} of {(end-start).days+1}. Missing days are incomplete coverage, NOT zero activity.','small'),
           Spacer(1,8)]
    story.extend([pdf.P(f'{len(gathered)-archived} direct source records; {archived} dated archive records. '
                              'Saved references are identified separately from newly checked original sources.','small'),Spacer(1,8)])
    intro_end=len(story)
    # Analytical breakdown only describes collected evidence, not global platform reach.
    sentiments=Counter(x.sentiment for x in gathered)
    products=Counter(str(x.product).strip() for x in gathered if str(x.product or '').strip())
    weekly_buckets=Counter('Week '+str(1+(int(x.published_date[8:10])-1)//7) for x in gathered if x.published_date)
    measured=Counter()
    for item in gathered:
        for key in ('views','likes','comments','shares','reactions','reposts'):
            val=item.engagement.get(key) if item.engagement else None
            if isinstance(val,(int,float)) and val>=0:measured[key]+=val
    # Two-tier KPI: source-discovered records must be visible even when the
    # exact posting date is unavailable. Never mix these with verified dated totals.
    lead_urls_by_platform={}
    for platform in PLATFORMS:
        lead_urls_by_platform[platform]=len({x.url.strip().rstrip('/').lower() for x in unverified.get(platform,[])})
    story.extend([Spacer(1,8),
                  pdf.P('Research status: Dated source records and discovery leads remain separate. '
                        'Original source leads are listed by platform in the KPI table below.','small'),
                  Spacer(1,7)])
    # Platform scorecards count source records. Also show genuine format-level KPIs.
    social_types=Counter(content_type(x) for x in gathered)
    distinct_threads={x.url.split('/comment/')[0].split('&lc=')[0].rstrip('/').lower()
                      for x in gathered if x.url and x.platform not in ('Google / News / Articles','Retailers')}
    replies=sum(len(x.comments or []) for x in gathered)
    # Two separate, auditable tabular dashboards above the complete source cards.
    from reportlab.platypus import LongTable, TableStyle
    from reportlab.lib import colors
    def dashboard(title, headers, rows, widths):
        out=[Spacer(1,10),pdf.band(title),Spacer(1,7)]
        # ReportLab does not auto-fit column widths; clamp to the printable page.
        if sum(widths)>pdf.W:
            ratio=pdf.W/sum(widths)
            widths=[w*ratio for w in widths]
        grid=LongTable([[pdf.P(str(v),'caption') for v in headers]]+
                       [[pdf.P(str(v),'small') for v in row] for row in rows],
                       colWidths=widths,repeatRows=1,hAlign='LEFT')
        grid.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E9EDF0')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F6F8F9')]),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
            ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5)]))
        if 'SENTIMENT' in title.upper():
            grid.setStyle(TableStyle([
                ('BACKGROUND',(1,1),(1,-1),colors.HexColor('#E7F5EB')),
                ('TEXTCOLOR',(1,1),(1,-1),colors.HexColor('#187448')),
                ('BACKGROUND',(2,1),(2,-1),colors.HexColor('#FBE9E8')),
                ('TEXTCOLOR',(2,1),(2,-1),colors.HexColor('#AA302C')),
                ('BACKGROUND',(3,1),(3,-1),colors.HexColor('#FFF1CA')),
                ('TEXTCOLOR',(3,1),(3,-1),colors.HexColor('#906600')),
                ('BACKGROUND',(4,1),(4,-1),colors.HexColor('#FFF6E6')),
            ]))
        out.extend([grid,Spacer(1,7)])
        return out
    post_rows=[]
    kpi_rows=[]
    for platform in PLATFORMS:
        items=grouped[platform]
        types=Counter(content_type(x) for x in items)
        metrics={}
        for field in ('views','likes','comments','shares'):
            values=[x.engagement.get(field) for x in items
                    if isinstance(x.engagement,dict) and
                    isinstance(x.engagement.get(field),(int,float))]
            metrics[field]=str(int(sum(values))) if values else 'N/A'
        post_rows.append([platform,types.get('post',0),types.get('video',0),
                          types.get('reel',0),types.get('story',0),
                          types.get('comment',0),sum(len(x.comments or []) for x in items),
                          metrics['views'],metrics['likes'],metrics['comments']])
        leads_in_platform=unverified.get(platform,[])
        known_media=sum(media_with_file(x) for x in items)
        linked_media=sum(media_link(x) for x in items)
        kpi_rows.append([platform,len(items),lead_urls_by_platform[platform],
                         len({x.url.rstrip('/').lower() for x in items}|{
                             x.url.rstrip('/').lower() for x in leads_in_platform}),
                         known_media,linked_media,
                         sum(len(x.comments or []) for x in leads_in_platform)])
    # Overall KPI is based on observed source data, never a platform-wide estimate.
    total_metrics={}
    measured_sources={}
    for metric in ('views','likes','comments','shares','reactions','reposts'):
        values=[x.engagement.get(metric) for x in gathered if isinstance(x.engagement,dict)
                and isinstance(x.engagement.get(metric),(int,float))]
        total_metrics[metric]=int(sum(values)) if values else None
        measured_sources[metric]=len(values)
    positive=sum(x.sentiment=='Positive' for x in gathered)
    negative=sum(x.sentiment=='Negative' for x in gathered)
    neutral=sum(x.sentiment=='Neutral' for x in gathered)
    question=sum(x.sentiment=='Question' for x in gathered)
    unknown_sentiment=sum(x.sentiment=='Not applicable' for x in gathered)
    def observed(metric):
        return f"{total_metrics[metric]:,}" if total_metrics[metric] is not None else 'N/A'
    # ONE consolidated executive KPI card area; detailed tables remain below.
    from src.kpi_cards import kpi_dashboard
    source_urls=len({x.url.rstrip('/').lower() for x in gathered+leads if x.url})
    card_groups=[
        ('SOURCE COVERAGE',[
            ('Dated sources',len(gathered)),('Pending leads',len(leads)),
            ('Unique source URLs',source_urls),('Days captured',f'{len(saved)}/{(end-start).days+1}')]),
        ('OBSERVED ENGAGEMENT',[
            ('Views',total_metrics['views']),('Likes',total_metrics['likes']),
            ('Comments',total_metrics['comments']),('Shares',total_metrics['shares'])]),
        ('OVERALL SENTIMENT',[
            ('Positive',positive),('Negative',negative),
            ('Neutral',neutral),('Questions',question)]),
        ('POST FORMATS',[
            ('Posts',social_types.get('post',0)),('Videos',social_types.get('video',0)),
            ('Reels',social_types.get('reel',0)),('Stories',social_types.get('story',0))]),
        ('ADDITIONAL ENGAGEMENT AND EVIDENCE',[
            ('Reactions',total_metrics['reactions']),('Reposts',total_metrics['reposts']),
            ('Linked replies',replies),('Cached images',source_media['embedded_verified'])]),
        ('SUPPORTING RECORDS',[
            ('Retail entries',len(offers)),('Articles',social_types.get('article',0)),
            ('Comment findings',social_types.get('comment',0)),('Not classified',unknown_sentiment)]),
    ]
    story[intro_end:intro_end]=kpi_dashboard(pdf,card_groups)
    dashboard_card_groups=card_groups
    sentiment_rows=[]
    for platform in PLATFORMS:
        items=grouped[platform]
        sentiment_rows.append([platform,sum(x.sentiment=='Positive' for x in items),
                               sum(x.sentiment=='Negative' for x in items),
                               sum(x.sentiment=='Neutral' for x in items),
                               sum(x.sentiment=='Question' for x in items),
                               sum(x.sentiment=='Not applicable' for x in items)])
    story.extend(dashboard('SOCIAL MEDIA SENTIMENT | BY PLATFORM',
        ['Platform','Positive','Negative','Neutral','Questions','N/A'],
        sentiment_rows,[137,79,79,79,79,75]))
    story.extend(dashboard('POST ANALYTICS | FORMAT AND ENGAGEMENT',
        ['Platform','Posts','Videos','Reels','Stories','Comments','Replies','Views','Likes','Comments metric'],
        post_rows,[87,42,42,41,42,53,44,51,44,55]))
    story.extend([pdf.P('Comment records and quoted replies are separate. Engagement shows numeric observations only; N/A is not zero.','small'),Spacer(1,6)])
    story.extend(dashboard('PLATFORM KPI | VERIFIED, DISCOVERED AND MEDIA',
        ['Platform','Dated','Leads','Source URLs','Images','Media links','Lead replies'],
        kpi_rows,[110,55,55,72,58,75,65]))
    story.extend([pdf.P('Retail observations (separate from social posts): '+str(len(offers))
                       +' | Unique retailer URLs: '+str(len({x.url.rstrip('/').lower() for x in offers}))
                       +'. Dated and discovered source counts must not be added as verified post totals.','small'),Spacer(1,8)])
    empty_platforms=[]
    for platform in PLATFORMS:
        items=grouped.get(platform,[])
        pending=unverified.get(platform,[])
        if not items and not pending and platform not in ('Facebook',):
            empty_platforms.append(platform)
            continue
        story.extend([Spacer(1,14),
                      pdf.band(platform+' | SOURCE EVIDENCE',
                               f'{len(items)} dated | {len(pending)} pending'),
                      Spacer(1,8)])
        for index,item in enumerate(items,1):
            story.extend([Spacer(1,8),pdf.P(f'{platform.upper()} | {content_type(item).upper()} | {item.published_date}','caption'),
                          pdf.P(item.title,'item'),Spacer(1,4),pdf.P('Author: '+(item.author or 'Not available'),'meta'),
                          pdf.P('SENTIMENT: '+item.sentiment,
                                'positive' if item.sentiment=='Positive' else
                                'negative' if item.sentiment=='Negative' else
                                'neutral' if item.sentiment in ('Neutral','Not applicable') else 'question'),
                          pdf.link(item.url,'OPEN ORIGINAL SOURCE'),pdf.source_url_line(item.url),Spacer(1,5)])
            for label,value in [('Source excerpt',item.source_excerpt),('Analysis',item.summary),('Impact',item.impact),('Response',item.response_action),('Date evidence',item.date_evidence)]:
                if value:story.extend([pdf.P(label+': '+str(value),'small'),Spacer(1,5)])
            for label,values in [('Hashtags',item.hashtags),('Mentions',item.mentioned_accounts),('Tagged accounts',item.tagged_accounts)]:
                if values:story.extend([pdf.P(label+': '+', '.join(values),'small'),Spacer(1,4)])
            if item.engagement:story.extend([pdf.P('Observed metrics: '+', '.join(str(k)+': '+str(v) for k,v in item.engagement.items()),'small'),Spacer(1,4)])
            for media_url in dict.fromkeys(([item.image_url] if item.image_url else [])+list(item.images or [])+([item.image_credit_url] if item.image_credit_url else [])):
                if media_url.startswith(('https://','http://')):
                    story.extend([pdf.link(media_url,'OPEN SOURCE IMAGE / MEDIA'),pdf.source_url_line(media_url),Spacer(1,4)])
            story.extend(pdf.evidence_thumbnail(item,max_width=pdf.W-48))
            for n,c in enumerate(item.comments or [],1):
                story.extend([pdf.P('COMMENT '+str(n)+' | '+str(c.get('author','')),'caption'),pdf.P(str(c.get('text','')),'small'),Spacer(1,4)])
                if c.get('url'):story.append(pdf.link(c['url'],'OPEN COMMENT'))
            story.append(Spacer(1,9))
        if not items:story.extend([pdf.P('No dated source record available in saved research for this period. Not evidence of zero real-world activity.','small'),Spacer(1,5)])
        if platform=='Facebook' and brand=='Atomos':
            story.extend([pdf.P('FACEBOOK DATA QUALITY NOTE','caption'),
                          pdf.P('An older Facebook finding was withdrawn because its purported post URL contained a placeholder ID. '
                                'It is not original-source evidence. Any real Facebook mention will appear here once its actual '
                                'permalink, author and publication context are established.','small'),
                          Spacer(1,8)])
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
                for media_url in dict.fromkeys(([x.image_url] if x.image_url else [])+list(x.images or [])+([x.image_credit_url] if x.image_credit_url else [])):
                    if media_url.startswith(('https://','http://')):
                        story.extend([pdf.link(media_url,'OPEN SOURCE IMAGE / MEDIA'),pdf.source_url_line(media_url),Spacer(1,4)])
                story.extend(pdf.evidence_thumbnail(x,max_width=pdf.W-48))
                if x.engagement:
                    story.extend([pdf.P('Public metrics as cited in source archive (not verified this run): '+', '.join(str(k)+': '+str(v) for k,v in x.engagement.items()),'small'),Spacer(1,4)])
                for i,comment in enumerate(x.comments or [],1):
                    story.extend([pdf.P('RELATED COMMENT '+str(i)+' | '+str(comment.get('author','')),'caption'),
                                  pdf.P(str(comment.get('text','')),'small'),Spacer(1,4)])
                story.append(Spacer(1,12))
    if empty_platforms:
        story.extend([Spacer(1,9),pdf.P('No original dated or pending source records found in saved research for: '
                                      +', '.join(empty_platforms)+'. This does not establish zero real-world activity.',
                                      'small'),Spacer(1,9)])
    story.extend([Spacer(1,9),pdf.band('RETAIL SOURCE OBSERVATIONS'),Spacer(1,6)])
    retail_counts=Counter(x.platform for x in offers)
    story.extend([pdf.P('Retail evidence KPI: '+str(len(offers))+' dated observations | '
                       +str(len({x.url.rstrip('/').lower() for x in offers}))+' unique original URLs. '
                       'Retail metrics are not social engagement.','small'),Spacer(1,8)])
    for item in offers:
        story.extend([pdf.P(item.title,'item'),Spacer(1,5),
                      pdf.P('Observation date: '+(item.reference_date or item.published_date or 'Unknown'),'small'),
                      pdf.link(item.url,'RETAIL ORIGINAL SOURCE'),pdf.source_url_line(item.url),Spacer(1,5)])
        for label,value in [('Description',item.summary),('Product',item.product),
                            ('Source excerpt',item.source_excerpt),('Verification',item.verification_note)]:
            if value:story.extend([pdf.P(label+': '+str(value),'small'),Spacer(1,4)])
        if item.engagement:
            story.extend([pdf.P('Price / product data (as recorded): '+', '.join(str(k)+': '+str(v) for k,v in item.engagement.items()),'small'),Spacer(1,4)])
        for media_url in dict.fromkeys(([item.image_url] if item.image_url else [])+list(item.images or [])):
            if media_url.startswith(('https://','http://')):
                story.extend([pdf.link(media_url,'OPEN SOURCE IMAGE / MEDIA'),pdf.source_url_line(media_url),Spacer(1,4)])
        story.extend(pdf.evidence_thumbnail(item,max_width=pdf.W-48))
        story.append(Spacer(1,12))
    doc.build(story,onFirstPage=pdf.footer,onLaterPages=pdf.footer)
    result={'period':args.period,'start':str(start),'end':str(end),'path':output.relative_to(ROOT).as_posix(),
            'snapshots':len(saved),'archived_findings':archived,'dated_findings':len(gathered),'unverified_leads':len(leads),
            'platform_counts':{p:len(grouped[p]) for p in PLATFORMS},'sentiment_counts':dict(sentiments),'observed_product_labels':dict(products.most_common(10)),'record_type_counts':dict(Counter(content_type(x) for x in gathered)),'platform_discovery_leads':lead_urls_by_platform,'unique_social_url_groups':len(distinct_threads),'linked_reply_excerpts':replies,'daily_coverage_percent':round(100*len(saved)/((end-start).days+1),1),'source_media':source_media,'retail_observations_count':len(offers),'retail_unique_urls':len({x.url.rstrip('/').lower() for x in offers}),'post_analytics_rows':post_rows,'platform_kpi_rows':kpi_rows,'kpi_card_groups':dashboard_card_groups,'rejected_synthetic_example_urls':rejected_example_leads,'overall_kpi':{'dated_records':len(gathered),'pending_leads':len(leads),'metrics':total_metrics,'metric_source_counts':measured_sources,'sentiment':{'positive':positive,'negative':negative,'neutral':neutral,'question':question,'not_applicable':unknown_sentiment}},'platform_sentiment_rows':sentiment_rows}
    (ROOT/'reports'/f'{args.period}-latest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
if __name__=='__main__':main()
