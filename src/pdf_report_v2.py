"""Angelbird Report V2: latest dated evidence first, chronological historical dossier.
Layout derives from the user-provided eight-page Angelbird 29 Oct reference report.
Rendering uses saved JSON only, no API request or network image fetching.
"""
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from PIL import Image as PILImage
from .platform_analytics import PLATFORMS, platform_summary, analytics_rows, traffic_disclaimer
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing

DARK=colors.HexColor('#30424c')
GREEN=colors.HexColor('#24835c')
GREEN_PALE=colors.HexColor('#e5f3ea')
GREY=colors.HexColor('#f0f2f4')
RED=colors.HexColor('#b53f3c')
RED_PALE=colors.HexColor('#f9eae9')
AMBER=colors.HexColor('#b88330')
AMBER_PALE=colors.HexColor('#fcf2e1')
BORDER=colors.HexColor('#dce3e5')
WHITE=colors.white
PAGE_W,PAGE_H=A4
MARGIN=42
W=PAGE_W-MARGIN*2

def fonts():
    options=[
       ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
       ('/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf')]
    for regular,bold in options:
        if Path(regular).exists() and Path(bold).exists():
            try:
                pdfmetrics.registerFont(TTFont('AngelV2',regular))
                pdfmetrics.registerFont(TTFont('AngelV2Bold',bold))
                return 'AngelV2','AngelV2Bold'
            except Exception: pass
    return 'Helvetica','Helvetica-Bold'
FONT,BOLD=fonts()
styles={
 'title':ParagraphStyle('v2-title',fontName=BOLD,fontSize=17,leading=23,textColor=WHITE),
 'subtitle':ParagraphStyle('v2-subtitle',fontName=FONT,fontSize=8,leading=12,textColor=colors.HexColor('#e3edf0')),
 'white':ParagraphStyle('v2-white',fontName=BOLD,fontSize=10,leading=14,textColor=WHITE),
 'item':ParagraphStyle('v2-item',fontName=BOLD,fontSize=10.3,leading=14.5,textColor=DARK),
 'body':ParagraphStyle('v2-body',fontName=FONT,fontSize=8.1,leading=12.5,textColor=DARK),
 'small':ParagraphStyle('v2-small',fontName=FONT,fontSize=7.3,leading=11,textColor=DARK),
 'micro':ParagraphStyle('v2-micro',fontName=FONT,fontSize=6.4,leading=9,textColor=DARK),
 'meta':ParagraphStyle('v2-meta',fontName=FONT,fontSize=7.0,leading=10,textColor=colors.HexColor('#586e76')),
 'kpi':ParagraphStyle('v2-kpi',fontName=BOLD,fontSize=20,leading=26,textColor=DARK,alignment=TA_CENTER),
 'kpilabel':ParagraphStyle('v2-kpilabel',fontName=BOLD,fontSize=6,leading=9,textColor=DARK,alignment=TA_CENTER),
 'green':ParagraphStyle('v2-green',fontName=BOLD,fontSize=7.1,leading=11,textColor=GREEN),
 'caption':ParagraphStyle('v2-caption',fontName=BOLD,fontSize=7,leading=11,textColor=DARK),
}

def P(value,kind='body',raw=False):
    s=str(value or '')
    if not raw:s=escape(s).replace('\n','<br/>')
    return Paragraph(s,styles[kind])

def link(url,label='OPEN ORIGINAL SOURCE'):
    if not str(url).startswith(('https://','http://')):return P('Original source URL not available','micro')
    u=escape(url,{'"':'&quot;'})
    return P(f'<link href="{u}" color="#24835c"><b>{escape(label)} &gt;</b></link>','green',raw=True)

def qr_image(url,size=48):
    q=qr.QrCodeWidget(url)
    a,b,c,d=q.getBounds()
    scale=size/(c-a)
    out=Drawing(size,size,transform=[scale,0,0,scale,0,0])
    out.add(q)
    return out

def band(title,small=''):
    content=P(escape(title.upper())+(f' <font color="#bad2cd" size="7">  {escape(small)}</font>' if small else ''),'white',raw=True)
    tab=Table([[content]],colWidths=[W],hAlign='LEFT')
    tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),DARK),('LEFTPADDING',(0,0),(-1,-1),13),
       ('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
    return tab

def panel(contents,bg=GREY,accent=None,width=W):
    if not isinstance(contents,list):contents=[contents]
    tab=Table([[contents]],colWidths=[width])
    commands=[('BACKGROUND',(0,0),(-1,-1),bg),('BOX',(0,0),(-1,-1),.5,BORDER),
              ('LEFTPADDING',(0,0),(-1,-1),13),('RIGHTPADDING',(0,0),(-1,-1),13),
              ('TOPPADDING',(0,0),(-1,-1),11),('BOTTOMPADDING',(0,0),(-1,-1),9)]
    if accent is not None:commands.append(('LINEBEFORE',(0,0),(0,-1),4,accent))
    tab.setStyle(TableStyle(commands))
    return tab

def metric(value,name,bg,fg):
    num=P(f'<font color="{fg.hexval()}">{int(value)}</font>','kpi',raw=True)
    label=P(f'<font color="{fg.hexval()}">{escape(name.upper())}</font>','kpilabel',raw=True)
    tab=Table([[num],[label]],colWidths=[(W/5)-4.6],rowHeights=[33,28])
    tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),bg),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
       ('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3)]))
    return tab

def summary_header(report):
    start=report.report_period_start or report.report_date
    top=Table([[P('ANGELBIRD | SOCIAL MONITORING','subtitle')],
               [P('Social Media Monitoring Report','title')],
               [P(f'Report date: {report.report_date}  |  Cumulative period: {start} to {report.report_date}  |  {report.generated_at_pkt}','subtitle')]],colWidths=[W])
    top.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),DARK),('LEFTPADDING',(0,0),(-1,-1),18),
       ('TOPPADDING',(0,0),(-1,0),13),('BOTTOMPADDING',(0,-1),(-1,-1),13)]))
    # The 29 October reference uses five sentiment KPI cards.
    listed=list(report.today_findings)+list(report.historical_findings)
    totals=Counter(i.sentiment for i in listed)
    vals=[(len(listed),'Mentions found',DARK,WHITE),
         (totals['Positive'],'Positive',GREEN_PALE,GREEN),
         (totals['Neutral'],'Neutral',GREY,DARK),
         (totals['Negative'],'Negative',RED_PALE,RED),
         (totals['Question'],'Question',GREY,DARK)]
    metrics=Table([[metric(*x) for x in vals]],colWidths=[W/5]*5)
    metrics.setStyle(TableStyle([('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),2),
       ('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    return [top,Spacer(1,12),metrics,Spacer(1,13),
            P(f'Latest day: {len(report.today_findings)} verified mention(s) on {report.report_date}. '
              f'{len(report.historical_findings)} earlier historical mention(s) are shown below and NOT counted as new today.'),
            P('In one line: '+(report.headline or 'No source-specific daily summary available.'),'small')]

def accent_for(item):
    return {'Positive':GREEN,'Negative':RED,'Question':AMBER,'Neutral':colors.HexColor('#798892')}.get(item.sentiment,DARK)

def excerpt_text(item):
    return (getattr(item,'source_excerpt','') or '').strip()

def evidence_thumbnail(item,max_width=None):
    """Embed a safely located cached original-source preview, never remote URL fetch."""
    max_width=max_width or (W-103)
    from pathlib import Path
    base=Path(__file__).resolve().parents[1]
    assets=(base/'assets').resolve()
    for name in getattr(item,'image_files',[])[:2]:
        try:
            path=(base/name).resolve()
            if not path.is_relative_to(assets) or not path.is_file():continue
            with PILImage.open(path) as im:
                iw,ih=im.size
            if iw<40 or ih<40:continue
            scale=min(max_width/iw,142/ih,1.0)
            visual=Image(str(path),width=iw*scale,height=ih*scale)
            visual.hAlign='LEFT'
            return [Spacer(1,8),P('SOURCE VISUAL | THUMBNAIL','caption'),
                    Spacer(1,4),visual,Spacer(1,3),
                    P('Thumbnail from linked public source. Refer to original post for context and rights.','micro')]
        except (OSError,ValueError):continue
    return []

def finding_card(item,number,historical=False):
    accent=accent_for(item)
    content=[P(f'{escape(number)}   |   {escape(item.platform.upper())}   |   {escape(item.sentiment.upper())}   |   {escape(item.priority.upper())}','green',raw=True),
             Spacer(1,4),P(item.title,'item'),
             Spacer(1,6),P('Source: '+item.platform+(' | '+item.author if item.author else '')+
                          (' | '+item.published_date if item.published_date else ' | Date not verified'),'meta'),
             link(item.url)]
    if item.product:content.extend([Spacer(1,5),P('Product: '+item.product,'small')])
    if item.image_url:
        content.extend([Spacer(1,4),link(item.image_url,'VIEW SOURCE IMAGE')])
    elif item.images:
        content.extend([Spacer(1,4),link(item.images[0],'VIEW SOURCE PHOTO')])
    content.extend(evidence_thumbnail(item,max_width=W-105))
    excerpt=excerpt_text(item)
    if excerpt:
        content.extend([Spacer(1,9),panel([P('ORIGINAL SOURCE EXCERPT','caption'),Spacer(1,3),P(excerpt[:450],'small')],bg=GREY,accent=accent,width=W-96)])
    if item.summary:content.extend([Spacer(1,8),P('<b>What happened:</b> '+escape(item.summary[:900]),'small',raw=True)])
    if item.impact:content.extend([Spacer(1,7),panel(P('<b>Angelbird impact:</b> '+escape(item.impact[:500]),'small',raw=True),bg=GREEN_PALE,width=W-96)])
    if item.response_action:content.extend([Spacer(1,6),P('<b>Angelbird response:</b> '+escape(item.response_action[:350]),'small',raw=True)])
    if item.engagement:
        stats='    |    '.join(f'{k.replace("_"," ").title()}: {v}' for k,v in list(item.engagement.items())[:7])
        content.extend([Spacer(1,6),P('Stats: '+stats,'micro')])
    if getattr(item,'comments',None):
        content.extend([Spacer(1,9),P('PUBLIC COMMENTS | ORIGINAL CONTEXT','caption'),Spacer(1,4)])
        for c in item.comments[:5]:
            author=str(c.get('author') or 'Public commenter')[:60]
            message=str(c.get('text') or '')[:320]
            stamp=str(c.get('date') or '')
            content.extend([P(author+(' | '+stamp if stamp else ''),'green'),P(message,'small'),Spacer(1,4)])
    if item.verification_note:content.extend([Spacer(1,5),P('Reference note: '+item.verification_note,'micro')])
    left=W-70
    t=Table([[content,qr_image(item.url,45)]],colWidths=[left,70])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),WHITE),('BOX',(0,0),(-1,-1),.6,BORDER),
         ('LINEBEFORE',(0,0),(0,-1),4,accent),('VALIGN',(0,0),(-1,-1),'TOP'),
         ('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),8),
         ('TOPPADDING',(0,0),(-1,-1),11),('BOTTOMPADDING',(0,0),(-1,-1),11)]))
    return [t,Spacer(1,10)]

def simple_card(item,index,kind='retail'):
    content=[P(f'{kind.upper()} {index}  |  {item.platform}','green'),Spacer(1,4),
             P(item.title,'item'),Spacer(1,5),P(item.summary or 'No detail recorded.','small'),
             Spacer(1,5),link(item.url)]
    if item.verification_note: content.extend([Spacer(1,4),P(item.verification_note,'micro')])
    return [panel(content,accent=AMBER if kind=='retail' else GREEN),Spacer(1,9)]


def engagement_overview(items):
    rows=[[P('PLATFORM','caption'),P('POSTS','caption'),P('VIEWS','caption'),
           P('LIKES','caption'),P('COMMENTS','caption'),P('SHARES','caption')]]
    for row in analytics_rows(items):
        totals=row['totals']
        def cell(key,alts=()):
            names=(key,)+tuple(alts)
            present=any(x in row['available'] for x in names)
            value=sum(totals.get(x,0) for x in names)
            return f'{value:,}' if present else 'N/A'
        rows.append([P(row['platform'],'small'),P(str(row['count']),'small'),
                     P(cell('views'),'small'),P(cell('likes',('reactions',)),'small'),
                     P(cell('comments'),'small'),P(cell('shares',('reposts',)),'small')])
    table=Table(rows,colWidths=[128,45,80,80,84,W-417],repeatRows=1)
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),GREY),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[WHITE,colors.HexColor('#f9fafb')]),
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
        ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
        ('VALIGN',(0,0),(-1,-1),'TOP')]))
    return [band('Platform Analytics | observed public engagement'),Spacer(1,8),
            table,Spacer(1,8),P(traffic_disclaimer(),'micro'),Spacer(1,12)]

def grouped_platform_cards(items,prefix,empty=False):
    output=[]
    groups=platform_summary(items)
    for platform in PLATFORMS:
        records=groups[platform]
        if not records and not empty:continue
        output.extend([Spacer(1,8),band(platform,f'{len(records)} verified item(s)'),Spacer(1,8)])
        if not records:
            output.extend([P('No original dated post verified in accessible sources. '
                             'This is not proof of no activity.','small'),Spacer(1,6)])
            continue
        for n,item in enumerate(records,1):
            output.extend(finding_card(item,f'{prefix}-{n}'))
    return output

def footer(canvas,doc):
    canvas.saveState()
    canvas.setStrokeColor(BORDER)
    canvas.line(MARGIN,45,PAGE_W-MARGIN,45)
    canvas.setFont(FONT,6.7)
    canvas.setFillColor(DARK)
    canvas.drawString(MARGIN,32,'Angelbird Insights 2026 | Social Monitoring')
    canvas.drawRightString(PAGE_W-MARGIN,32,f'Page {doc.page}')
    canvas.restoreState()

def render_pdf(report,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(path),pagesize=A4,topMargin=34,bottomMargin=60,leftMargin=MARGIN,rightMargin=MARGIN,
        title=f'Angelbird Social Monitoring {report.report_date}',author='Angelbird Social Monitoring')
    story=summary_header(report)
    story.extend([Spacer(1,12)])
    story.extend(engagement_overview(report.today_findings+report.historical_findings))
    story.extend([band(f'{report.report_date} | Latest verified posts',
                       f'{len(report.today_findings)} new dated source(s)'),Spacer(1,8)])
    story.extend(grouped_platform_cards(report.today_findings,'N',empty=True))
    if report.unverified_leads:
        story.extend([band('New / unverified leads','Not counted as verified today'),Spacer(1,10)])
        for n,item in enumerate(report.unverified_leads,1):
            if item.published_date and item.published_date < report.report_date:continue
            story.extend(finding_card(item,f'U{n}'))
    story.extend([Spacer(1,8),band(f'{report.report_date} | Retail observations'),Spacer(1,10)])
    if report.retail_observations:
        for n,item in enumerate(report.retail_observations,1):story.extend(simple_card(item,n))
    else:story.extend([panel(P('No dated retailer promotion independently established in this daily run.','small')),Spacer(1,12)])
    story.extend([Spacer(1,7),band(f'{report.report_date} | Source coverage'),Spacer(1,9)])
    if report.coverage:
        for c in report.coverage:
            story.append(P(('CHECKED: ' if c.checked else 'NOT CHECKED: ')+c.platform+' - '+c.summary,'small'))
    else:story.append(P('No source-specific search coverage logged; treat this daily report as incomplete.','small'))
    if report.visibility_gaps:
        story.extend([Spacer(1,6),P('Access limitations: '+'; '.join(report.visibility_gaps[:10]),'micro')])
    story.extend([Spacer(1,18),band('Earlier social highlights',
                  f'{report.report_period_start or report.report_date} through previous day | five-day history'),Spacer(1,11),
                  P('Historical items below are sourced from the previous reference report and earlier saved daily JSON. '
                    'They remain separate from the newest-day findings and must not be counted again as new.','small')])
    groups=defaultdict(list)
    for item in report.historical_findings:
        groups[item.published_date].append(item)
    # Always display exactly five preceding dates, whether or not records exist.
    for offset in range(1,6):
        day=(date.fromisoformat(report.report_date)-timedelta(days=offset)).isoformat()
        items=groups.get(day,[])
        story.extend([Spacer(1,9),band(day,f'{len(items)} saved historical mention(s)'),Spacer(1,10)])
        if items:
            story.extend(grouped_platform_cards(items,f'H{day[-2:]}',empty=False))
        else:
            story.extend([panel(P('No source-linked dated entry saved for this day. '
                                  'This does not establish that no Angelbird activity occurred.','small')),
                          Spacer(1,8)])
    if report.historical_retail:
        story.extend([Spacer(1,10),band('Earlier retailer observations','Historical prices are not current quotes'),Spacer(1,9)])
        for n,item in enumerate(report.historical_retail,1):story.extend(simple_card(item,n))
    if report.older_leads:
        story.extend([Spacer(1,9),band('Existing response watchlist','Older leads / no new-day KPI effect'),Spacer(1,9)])
        for n,item in enumerate(report.older_leads,1):story.extend(finding_card(item,f'W{n}',historical=True))
    counts=Counter(x.sentiment for x in list(report.historical_findings)+list(report.today_findings))
    watch=[x for x in report.older_leads+report.historical_findings if x.priority in ('High','Urgent','Medium')
           and 'Required' in (x.response_action or '')]
    story.extend([Spacer(1,14),band('Overall feedback'),Spacer(1,10),
       panel([P(f'<b>{len(report.historical_findings)+len(report.today_findings)} total archival-and-current mentions</b> '
                 f'| {counts["Positive"]} positive | {counts["Neutral"]} neutral '
                 f'| {counts["Negative"]} negative | {counts["Question"]} question','small',raw=True),
             Spacer(1,6),P(f'{len(watch)} historical response-action item(s) identified from the available evidence. '
                           'No card faults are automatically adjudicated as confirmed.','small'),
             Spacer(1,6),P(f'Newest report day: {report.report_date}. '
                           f'Only {len(report.today_findings)} new verified mention(s) are attributed to this day.','small')],bg=GREY),
       Spacer(1,10),P('Source policy: exact original URLs and date evidence required for newly verified mentions. '
                      'Public/indexed scope only; private groups and unindexed comments may be missing. '
                      'Historical source details were imported from a supplied previous report and require '
                      'periodic revalidation.','micro')])
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
