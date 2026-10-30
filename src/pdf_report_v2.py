"""Angelbird Report V2: latest dated evidence first, chronological historical dossier.
Layout derives from the user-provided eight-page Angelbird 29 Oct reference report.
Rendering uses saved JSON only, no API request or network image fetching.
"""
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse, unquote
from PIL import Image as PILImage
from .platform_analytics import PLATFORMS, platform_summary, analytics_rows, traffic_disclaimer
from .social_content import content_type, content_counts, LABELS, SOCIAL
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

def source_url_line(url, label='ORIGINAL URL'):
    # Visible and clickable URL rather than a generic action label.
    if not str(url).startswith(('http://','https://')):
        return P(label+': not available','micro')
    uri=escape(str(url),{'"':'&quot;'})
    parsed=urlparse(url)
    display=parsed.netloc+unquote(parsed.path)
    if parsed.query:display+='?'+parsed.query
    if len(display)>105:display=display[:99]+'...'
    return P('<b>'+escape(label)+':</b> <link href="'+uri+'" color="#24835c">'+escape(display)+'</link>','micro',raw=True)

def image_provenance(item):
    if item.image_url:return item.image_url
    if item.images:return item.images[0]
    return ''

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
    """Only same-day post metrics. Historical numbers never appear in this PDF."""
    top=Table([[P('ANGELBIRD | DAILY SOCIAL MONITORING','subtitle')],
               [P(f'Angelbird Social & Web Report | {report.report_date}','title')],
               [P(f'Coverage: {report.report_date} ONLY | Research: {report.research_as_of_pkt or "cutoff not recorded"} | Rendered: {report.generated_at_pkt}','subtitle')]],colWidths=[W])
    top.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),DARK),
         ('LEFTPADDING',(0,0),(-1,-1),18),
         ('TOPPADDING',(0,0),(-1,0),13),
         ('BOTTOMPADDING',(0,-1),(-1,-1),13)]))
    todays=list(report.today_findings)
    sentiments=Counter(i.sentiment for i in todays)
    items=[(len(todays),'Dated sources',DARK,WHITE),
           (sentiments['Positive'],'Positive',GREEN_PALE,GREEN),
           (sentiments['Neutral'],'Neutral',GREY,DARK),
           (sentiments['Negative'],'Negative',RED_PALE,RED),
           (sentiments['Question'],'Questions',GREY,DARK)]
    grid=Table([[metric(*x) for x in items]],colWidths=[W/5]*5)
    grid.setStyle(TableStyle([('LEFTPADDING',(0,0),(-1,-1),0),
         ('RIGHTPADDING',(0,0),(-1,-1),2),
         ('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    return [top,Spacer(1,11),P('VERIFIED NEW MENTIONS | ORIGINAL DATE '+report.report_date,'caption'),
            Spacer(1,7),grid,Spacer(1,10),
            P(f'{len(report.retail_observations)} separate dated retailer price/offer observation(s). '
              'Catalog listings and old posts do not count as newly published social mentions.','small'),
            Spacer(1,6),P('Summary: '+(report.headline or 'Limited search coverage'),'small'),
            Spacer(1,4),P('Report is a dated public-source monitoring snapshot, not a complete '
                        'inventory of inaccessible/private social activity.','micro')]

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
             Spacer(1,5),P('CONTENT TYPE: '+LABELS[content_type(item)].upper(),'caption'),
             Spacer(1,6),P('Source: '+item.platform+(' | '+item.author if item.author else '')+
                          (' | '+item.published_date if item.published_date else ' | Date not verified'),'meta'),
             link(item.url),Spacer(1,3),source_url_line(item.url,'POST / ARTICLE LINK')]
    if getattr(item,'publisher',''):content.extend([Spacer(1,3),P('Publisher: '+item.publisher,'micro')])
    if getattr(item,'hashtags',None):
        content.extend([Spacer(1,4),P('Source hashtags: '+', '.join(item.hashtags[:12]),'small')])
    if getattr(item,'mentioned_accounts',None):
        content.extend([Spacer(1,4),P('Public @mentions: '+', '.join(item.mentioned_accounts[:12]),'small')])
    if getattr(item,'tagged_accounts',None):
        content.extend([Spacer(1,4),P('Tagged accounts (source-confirmed): '+', '.join(item.tagged_accounts[:12]),'small')])
    if item.product:content.extend([Spacer(1,5),P('Product: '+item.product,'small')])
    image_src=image_provenance(item)
    if image_src:
        content.extend([Spacer(1,5),link(image_src,'OPEN SOURCE PHOTO'),
                        Spacer(1,3),source_url_line(image_src,'PHOTO URL')])
        if getattr(item,'image_context',''):
            content.append(P('Image provenance: '+item.image_context,'micro'))
        if getattr(item,'image_credit_url',''):
            content.append(source_url_line(item.image_credit_url,'PHOTO OWNER / CREDIT'))
    embedded_photo=evidence_thumbnail(item,max_width=W-105)
    if embedded_photo:content.extend(embedded_photo)
    elif image_src:
        content.extend([Spacer(1,5),P('Preview unavailable. Original image link is provided; access may require login.','micro')])
    else:
        content.extend([Spacer(1,5),P('Original post image not accessible; use the direct post link above.','micro')])
    excerpt=excerpt_text(item)
    if excerpt:
        content.extend([Spacer(1,9),panel([P('ORIGINAL SOURCE EXCERPT','caption'),Spacer(1,3),P(excerpt[:450],'small')],bg=GREY,accent=accent,width=W-96)])
    if item.summary:content.extend([Spacer(1,8),P('<b>What happened:</b> '+escape(item.summary[:900]),'small',raw=True)])
    if item.impact:content.extend([Spacer(1,7),panel(P('<b>Angelbird impact:</b> '+escape(item.impact[:500]),'small',raw=True),bg=GREEN_PALE,width=W-96)])
    if item.response_action:content.extend([Spacer(1,6),P('<b>Angelbird response:</b> '+escape(item.response_action[:350]),'small',raw=True)])
    if item.engagement:
        stats='    |    '.join(f'{k.replace("_"," ").title()}: {v}' for k,v in list(item.engagement.items())[:7])
        content.extend([Spacer(1,6),P('Public engagement (where observed): '+stats,'micro')])
        if getattr(item,'engagement_source',''):content.append(P('Metrics source: '+item.engagement_source,'micro'))
    if getattr(item,'comments',None):
        content.extend([Spacer(1,9),P('PUBLIC COMMENTS | ORIGINAL CONTEXT','caption'),Spacer(1,4)])
        for c in item.comments[:5]:
            author=str(c.get('author') or 'Public commenter')[:60]
            message=str(c.get('text') or '')[:320]
            stamp=str(c.get('date') or '')
            content.extend([P(author+(' | '+stamp if stamp else ''),'green'),P(message,'small')])
            if c.get('url'):content.append(link(c['url'],'OPEN ORIGINAL COMMENT'))
            content.append(Spacer(1,4))
    if item.date_evidence:content.extend([Spacer(1,5),P('Date source: '+item.date_evidence,'micro')])
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
             Spacer(1,5),link(item.url),Spacer(1,3),source_url_line(item.url,'RETAIL POST LINK')]
    image_src=image_provenance(item)
    if image_src:
        content.extend([Spacer(1,4),source_url_line(image_src,'SOURCE IMAGE URL')])
        if getattr(item,'image_context',''):content.append(P('Image provenance: '+item.image_context,'micro'))
        if getattr(item,'image_credit_url',''):
            content.append(source_url_line(item.image_credit_url,'PHOTO OWNER / CREDIT'))
    embedded=evidence_thumbnail(item,max_width=W-40)
    if embedded:content.extend(embedded)
    elif image_src:content.append(P('Image preview unavailable; original image URL above.','micro'))
    else:content.append(P('Original product photo could not be retrieved.','micro'))
    if item.details:content.extend([Spacer(1,5),P('Snapshot details: '+item.details,'small')])
    if item.date_evidence:content.extend([Spacer(1,5),P('Date / price evidence: '+item.date_evidence,'micro')])
    if getattr(item,'publisher',''):content.extend([Spacer(1,3),P('Publisher / price index: '+item.publisher,'micro')])
    if item.verification_note:content.extend([Spacer(1,4),P(item.verification_note,'micro')])
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

def _fmt_count(metrics, field):
    if field not in metrics['available']:return 'N/A'
    return format(metrics['totals'].get(field,0),',')

def instagram_story_lead_card(item):
    """Compact explicit unverified Story link; not a verified Atomos/Angelbird mention."""
    parts=[
        P('INSTAGRAM STORY LINK | UNVERIFIED','caption'),
        Spacer(1,4),
        P('Source account: '+(item.author or 'Not known'),'small'),
        Spacer(1,4),
        source_url_line(item.url,('OPEN INSTAGRAM STORY LINK' if len([p for p in urlparse(item.url).path.split('/') if p])==3 else 'OPEN INSTAGRAM STORIES ACCOUNT PAGE')),
        Spacer(1,5),
        P('Original Story media, tag/mention, brand association, reach and '
          'publication date NOT independently accessible. This is a supplied '
          'research lead, NOT a confirmed brand mention.','micro')
    ]
    return [panel(parts,accent=AMBER),Spacer(1,7)]

def platform_scorecard(platform,items,day_label):
    from .platform_analytics import metric_summary
    m=metric_summary(items)
    rows=[
        [P('SOURCE','caption'),P('POSTS','caption'),P('VIEWS','caption'),P('LIKES','caption'),
         P('COMMENTS','caption'),P('SHARES','caption')],
        [P(platform,'small'),P(str(len(items)),'small'),P(_fmt_count(m,'views'),'small'),
         P(_fmt_count(m,'likes'),'small'),P(_fmt_count(m,'comments'),'small'),
         P(_fmt_count(m,'shares'),'small')]
    ]
    tab=Table(rows,colWidths=[128,45,80,80,84,W-417])
    tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),GREY),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[WHITE]),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
        ('VALIGN',(0,0),(-1,-1),'TOP')]))
    note=P('Metrics reflect only accessible original-source/API observations as of the report run. N/A = not available.','micro')
    result=[band(platform+' | source details',day_label+' | '+str(len(items))+' source(s)'),Spacer(1,7),tab,Spacer(1,5),note,Spacer(1,7)]
    if platform in SOCIAL:
        totals=content_counts(items)
        parts=[f'{label}: {totals.get(kind,0)}' for kind,label in (
            ('post','Posts'),('story','Stories'),('reel','Reels'),
            ('mention','Mentions'),('tagged_post','Tagged posts'),
            ('comment','Comment findings'),('video','Videos'))]
        linked=sum(len(x.comments) for x in items)
        parts.append(f'Linked public replies: {linked}')
        result.extend([P(' | '.join(parts),'micro'),Spacer(1,7)])
    return result

def source_sections(items,tag,day_label,include_empty=False):
    # The source cards go DIRECTLY below that platform's analytics scorecard.
    groups=platform_summary(items)
    out=[]
    for platform in PLATFORMS:
        records=groups[platform]
        if not records and not include_empty:continue
        out.extend([Spacer(1,9)]+platform_scorecard(platform,records,day_label))
        if not records:
            out.extend([P('No source-verified dated post in accessible results; source visibility may be restricted.','small'),Spacer(1,8)])
        else:
            for index,item in enumerate(records,1):
                out.extend(finding_card(item,tag+'-'+str(index)))
    return out
def footer(canvas,doc):
    canvas.saveState()
    canvas.setStrokeColor(BORDER)
    canvas.line(MARGIN,45,PAGE_W-MARGIN,45)
    canvas.setFont(FONT,6.7)
    canvas.setFillColor(DARK)
    canvas.drawString(MARGIN,32,'Angelbird Insights 2026 | Social Monitoring')
    canvas.drawRightString(PAGE_W-MARGIN,32,f'Page {doc.page}')
    canvas.restoreState()

def platform_dossier(report):
    # Every top-level platform KPI has its matching posts and source links below.
    dated=list(report.today_findings)+list(report.historical_findings)
    date_today=report.report_date
    latest=platform_summary(report.today_findings)
    previous=platform_summary(report.historical_findings)
    undated=platform_summary(report.unverified_leads)
    section=[]
    for platform in PLATFORMS:
        current=latest[platform]
        old=previous[platform]
        leads=undated[platform]
        all_posts=current+old
        if platform=='Retailers':
            listings=list(report.retail_observations)+list(report.historical_retail)
            section.extend([Spacer(1,13),band('Retailers | observed product and offer listings',
                                              str(len(listings))+' offers / price records'),Spacer(1,8),
                            P('Retailer figures are price snapshots, not social posts or engagement metrics.','small')])
            for i,item in enumerate(report.retail_observations,1):
                section.extend([Spacer(1,6),P('LATEST PRICE CHECK | '+date_today,'caption')])
                section.extend(simple_card(item,i))
            for i,item in enumerate(report.historical_retail,1):
                section.extend([Spacer(1,6),P('HISTORICAL PRICE SNAPSHOT | '+str(item.published_date or 'date uncertain'),'caption')])
                section.extend(simple_card(item,i))
            for i,item in enumerate(leads,1):
                section.extend([Spacer(1,6),P('RETAIL SOURCE LEAD | unverified date','caption')])
                section.extend(finding_card(item,'R-U'+str(i)))
            if not listings and not leads:
                section.extend([P('No accessible dated product listing was retained for this reporting window.','small'),Spacer(1,10)])
            continue
        section.extend([Spacer(1,15)]+platform_scorecard(platform,all_posts,
                        'LATEST '+date_today+' + previous five days'))
        section.extend([P('Verified source links shown below: '+str(len(all_posts))+'; '
                          'new today: '+str(len(current))+'; previous five days: '+str(len(old))+'; '
                          'undated leads: '+str(len(leads))+'.','small'),Spacer(1,8)])
        if current:
            section.extend([P('NEW POSTS | '+date_today,'caption'),Spacer(1,7)])
            for i,item in enumerate(current,1):section.extend(finding_card(item,'N'+str(i)))
        else:
            section.extend([P('No independently date-verified new post for '+date_today+' in accessible sources.','micro'),Spacer(1,8)])
        if old:
            for i,item in enumerate(sorted(old,key=lambda x:x.published_date or '',reverse=True),1):
                section.extend([P('PREVIOUS POST | '+(item.published_date or 'date not verified'),'caption'),Spacer(1,5)])
                section.extend(finding_card(item,'H'+str(i)))
        if leads:
            section.extend([P('UNVERIFIED LEADS | Not included in observed post KPIs','caption'),Spacer(1,7)])
            for i,item in enumerate(leads,1):section.extend(finding_card(item,'U'+str(i)))
    return section

def render_pdf(report,path):
    """Professional single-day social report; each platform KPI immediately precedes its sources."""
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(path),pagesize=A4,topMargin=34,bottomMargin=60,
        leftMargin=MARGIN,rightMargin=MARGIN,
        title=f'Angelbird Social Monitoring {report.report_date} (only)',
        author='Angelbird Social Monitoring')
    day=report.report_date
    todays=[f for f in report.today_findings if f.published_date==day]
    retail=[f for f in report.retail_observations if f.reference_date==day]
    undated=[f for f in report.unverified_leads if f.reference_date==day]
    groups=platform_summary(todays)
    uncertain=platform_summary(undated)
    story=summary_header(report)
    story.extend([Spacer(1,12)])
    story.extend(engagement_overview(todays))
    story.extend([P('Analytics above covers ONLY original posts/articles dated '+day+
                     '. Metrics appear only when original sources or authorized APIs supplied '
                     'numeric observations, not as cross-platform traffic estimates.','small'),
                  Spacer(1,9),band(day+' | Platform findings and evidence'),
                  Spacer(1,7)])
    for platform in PLATFORMS:
        records=groups[platform]
        candidates=uncertain[platform]
        if platform=='Retailers':
            story.extend([Spacer(1,10),band('RETAIL / PRICE OBSERVATIONS | '+day,
                                          str(len(retail))+' dated price snapshots'),
                          Spacer(1,7),P('Retail observations are neither customer reviews nor '
                                         'newly published social posts.','small'),Spacer(1,8)])
            if retail:
                for n,item in enumerate(retail,1):story.extend(simple_card(item,n))
            else:
                story.extend([P('No retailer price or product snapshot with a '
                                'verified '+day+' observation timestamp was retained.','small'),
                              Spacer(1,9)])
            continue
        story.extend([Spacer(1,10)])
        story.extend(platform_scorecard(platform,records,day+' ONLY'))
        if records:
            for n,item in enumerate(records,1):
                story.extend(finding_card(item,'D'+str(n)))
        else:
            story.extend([P('No independently dated '+day+' Angelbird post/article was '
                            'confirmed in the accessible material for this platform. '
                            'This does not prove no posts exist.','small'),Spacer(1,8)])
        if candidates:
            stories=[x for x in candidates if platform=='Instagram' and content_type(x)=='story']
            other=[x for x in candidates if x not in stories]
            if stories:
                story.extend([P(f'INSTAGRAM STORIES TO VERIFY | {len(stories)} original links, 0 verified by URL alone','caption'),
                              Spacer(1,6),
                              P('Original links have been preserved below. No Story image, '
                                'the monitored brand tag, publication time or views have '
                                'been inferred from the URLs.','micro'),Spacer(1,7)])
                for item in stories:story.extend(instagram_story_lead_card(item))
            if other:
                story.extend([P('PUBLIC SOURCE LEADS | original date or brand not verified','caption'),
                              Spacer(1,6)])
                for n,item in enumerate(other,1):story.extend(finding_card(item,'U'+str(n)))
    # Access coverage and search methodology remain in saved JSON, not PDF pages.
    counts=Counter(x.sentiment for x in todays)
    actions=[x for x in todays if x.priority in ('Urgent','High','Medium')
             and 'required' in (x.response_action or '').lower()]
    story.extend([Spacer(1,13),band('30 October | Summary and response actions'),
                  Spacer(1,9),
                  panel([P(f'{len(todays)} original-date verified new source(s) on {day}; '
                           f'{len(retail)} same-day retail price observations.','small'),
                         Spacer(1,6),
                         P(f'{counts["Positive"]} positive, {counts["Neutral"]} neutral, '
                           f'{counts["Negative"]} negative, {counts["Question"]} questions. '
                           'Unavailable social metrics are not zero.','small'),
                         Spacer(1,6),
                         P(f'{len(actions)} posts have an evidence-backed response action. '
                           'No previous-date findings have been counted or displayed.','small')],bg=GREY),
                  Spacer(1,8),P(traffic_disclaimer(),'micro')])
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
