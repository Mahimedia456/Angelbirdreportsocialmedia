"""One-time weekly PDF from existing dated, saved evidence only. No research/API/cron."""
import json
from pathlib import Path
from datetime import date, timedelta
from collections import Counter
from reportlab.platypus import SimpleDocTemplate, Spacer
from reportlab.lib.pagesizes import A4
from src.schema import ResearchReport
from src import pdf_report_v2 as pdf
from src.platform_analytics import PLATFORMS, platform_summary
from src.social_content import content_type

ROOT=Path(__file__).resolve().parents[1]
END=date(2026,10,30)
START=END-timedelta(days=6)
BRAND='Atomos' if 'atomos' in str(ROOT).lower() else 'Angelbird'
# Repo-name independent: schema and source header agree on the brand.
if (ROOT/'src'/'brand_scope.py').exists():
    import inspect
    source=(ROOT/'src'/'pdf_report_v2.py').read_text(encoding='utf-8')
    BRAND='ATOMOS' if 'ATOMOS | DAILY' in source else 'ANGELBIRD'

def inside(d):
    try:return START<=date.fromisoformat(d)<=END
    except (ValueError,TypeError):return False

def main():
    findings,offers,leads=[],[],[]
    reference_findings,reference_offers=[],[]
    seen=set()
    saved_dates=[]
    for day_offset in range(7):
        d=START+timedelta(days=day_offset)
        p=ROOT/'data'/d.strftime('%Y')/d.strftime('%m')/(f'{BRAND.title()}-Social-Monitoring-{d.isoformat()}.json')
        if not p.exists():continue
        saved_dates.append(d.isoformat())
        report=ResearchReport.model_validate(json.loads(p.read_text(encoding='utf-8')))
        for field,target in [('today_findings',findings),('historical_findings',findings),
                             ('retail_observations',offers),('historical_retail',offers),
                             ('unverified_leads',leads)]:
            for item in getattr(report,field):
                period_date=(item.reference_date or item.published_date) if field in ('retail_observations','historical_retail') else item.published_date
                if field=='unverified_leads':
                    if not inside(period_date):continue
                elif not inside(period_date):continue
                if field in ('today_findings','historical_findings') and (item.status!='verified' or not item.date_evidence):continue
                key=(('retail' if target is offers else 'lead' if target is leads else 'finding'),item.url.rstrip('/').lower())
                if key in seen:continue
                seen.add(key);target.append(item)
    # The user's 29-Oct reference report is saved separately, not in daily JSON files.
    # Preserve its original provenance rather than claiming independently verified.
    archive=ROOT/'data'/'reference_history_2026_10_29.json'
    if archive.exists():
        from src.schema import Finding
        archived=json.loads(archive.read_text(encoding='utf-8'))
        for obj in archived.get('findings',[]):
            if not inside(obj.get('published_date')):continue
            try:item=Finding.model_validate(dict(obj,status='older'))
            except Exception:continue
            key=('finding',item.url.rstrip('/').lower())
            if key not in seen:
                seen.add(key);reference_findings.append(item)
        for obj in archived.get('retail_observations',[]):
            date_value=obj.get('reference_date') or obj.get('published_date')
            if not inside(date_value):continue
            try:item=Finding.model_validate(dict(obj,status='retail'))
            except Exception:continue
            key=('retail',item.url.rstrip('/').lower())
            if key not in seen:
                seen.add(key);reference_offers.append(item)
    findings.sort(key=lambda x:(x.published_date,x.platform,x.url),reverse=True)
    all_findings=findings+reference_findings
    all_offers=offers+reference_offers
    dest=ROOT/'reports'/'2026'/'10'/f'{BRAND.title()}-Social-Monitoring-Weekly-2026-10-24_to_2026-10-30.pdf'
    dest.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(dest),pagesize=A4,topMargin=34,bottomMargin=60,leftMargin=pdf.MARGIN,rightMargin=pdf.MARGIN,
        title=f'{BRAND.title()} Weekly Social Monitoring | 24-30 October 2026')
    story=[pdf.band(f'{BRAND.upper()} | WEEKLY SOCIAL MONITORING','24 - 30 OCTOBER 2026'),
           Spacer(1,12),pdf.P('7-DAY OBSERVED ENGAGEMENT & SOURCE EVIDENCE','item'),Spacer(1,7),
           pdf.P('Weekly preview: 24-30 October 2026 (Pakistan time). Evidence compiled from saved repository records only; no new research performed.','small'),
           Spacer(1,8),pdf.P(f'Daily source files available: {len(saved_dates)} of 7 ({", ".join(saved_dates) or "none"}). Missing days are incomplete coverage, NOT zero brand mentions.','small'),Spacer(1,12)]
    story.extend(pdf.engagement_overview(all_findings))
    counts=Counter(x.sentiment for x in all_findings)
    story.extend([pdf.P(f'Direct verified: {len(findings)}  |  Archived references: {len(reference_findings)}  |  Retail: {len(all_offers)}  |  Positive: {counts["Positive"]}  |  Neutral: {counts["Neutral"]}  |  Negative: {counts["Negative"]}  |  Questions: {counts["Question"]}','small'),Spacer(1,10),
                  pdf.band('WEEKLY PLATFORM KPIS AND INDIVIDUAL EVIDENCE','POST / COMMENT / STORY / VIDEO / ARTICLE')])
    grouped=platform_summary(all_findings)
    uncertain=platform_summary(leads)
    for platform in PLATFORMS:
        records=grouped[platform]
        story.append(Spacer(1,13))
        story.extend(pdf.platform_scorecard(platform,records,'24-30 OCTOBER 2026'))
        if records:
            for i,item in enumerate(records,1):
                story.extend([pdf.P('PUBLISHED '+str(item.published_date)+'  |  '+('ARCHIVED REFERENCE | ' if item in reference_findings else 'SOURCE VERIFIED | ')+content_type(item).upper(),'caption'),Spacer(1,5)])
                story.extend(pdf.finding_card(item,'W'+str(i)))
        else:
            story.extend([pdf.P('No date-verified item available in the saved weekly dataset. This does not establish that no posts existed.','small'),Spacer(1,7)])
        if uncertain.get(platform):
            story.append(pdf.P('UNVERIFIED LEADS (EXCLUDED FROM KPI COUNTS)','caption'))
            for i,item in enumerate(uncertain[platform],1):story.extend(pdf.finding_card(item,'U'+str(i)))
        if platform=='Retailers':
            story.extend([pdf.P(f'{len(all_offers)} dated retailer snapshots; {len(reference_offers)} archive-sourced, excluded from post KPIs.','small'),Spacer(1,7)])
            for i,item in enumerate(all_offers,1):story.extend(pdf.simple_card(item,i))
    story.extend([Spacer(1,10),pdf.P(f'Archived references: {len(reference_findings)} items sourced from the user-provided 29 October reference report; not independently reverified.','small'),Spacer(1,8),pdf.band('WEEKLY COVERAGE AND VERIFICATION NOTES'),Spacer(1,9),
                  pdf.P('This is a one-time manual weekly compilation. The 7-day window is not a claim that seven daily scans were completed. Missing metrics are unavailable, not zero. The saved evidence may contain inaccessible Instagram Stories or other platforms; URLs alone are never proof of content, media or publication date.','small'),
                  Spacer(1,8),pdf.P('No weekly schedule, cron trigger, research API call or modifications to daily reports are introduced.','small')])
    doc.build(story,onFirstPage=pdf.footer,onLaterPages=pdf.footer)
    manifest=ROOT/'weekly-reports-index.json'
    manifest.write_text(json.dumps([{'brand':BRAND,'start':START.isoformat(),'end':END.isoformat(),'path':dest.relative_to(ROOT).as_posix(),
                                   'saved_source_dates':saved_dates,'verified_items':len(findings),'archived_reference_items':len(reference_findings),'retail_snapshots':len(all_offers)}],indent=2)+'\n')
    print(f'CREATED {dest} | verified={len(findings)} | source_days={len(saved_dates)} | retail={len(offers)}')

if __name__=='__main__':main()
