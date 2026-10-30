"""A4 Angelbird report renderer. Reference: user-provided 30 Oct 2026 interim PDF.
Visual constants intentionally isolated; no change to palette/section hierarchy."""
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT,TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.utils import simpleSplit
from xml.sax.saxutils import escape
from pathlib import Path

INK=colors.HexColor('#2e414b')
GREEN=colors.HexColor('#207c4d')
PALE=colors.HexColor('#e5f2e9')
GREY=colors.HexColor('#f0f2f3')
LINE=colors.HexColor('#d7dee0')
WHITE=colors.white
PAGE_W,PAGE_H=A4
MARGIN=44
WIDTH=PAGE_W-2*MARGIN

def font_setup():
    candidates=[('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),('/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf')]
    for a,b in candidates:
        if Path(a).is_file() and Path(b).is_file():
            pdfmetrics.registerFont(TTFont('Angel',a));pdfmetrics.registerFont(TTFont('AngelBold',b))
            return 'Angel','AngelBold'
    return 'Helvetica','Helvetica-Bold'

FONT,BOLD=font_setup()
S={
 'label':ParagraphStyle('label',fontName=BOLD,fontSize=8,leading=11,textColor=INK),
 'body':ParagraphStyle('body',fontName=FONT,fontSize=8.4,leading=12.6,textColor=INK,spaceAfter=7),
 'small':ParagraphStyle('small',fontName=FONT,fontSize=7,leading=10,textColor=INK),
 'micro':ParagraphStyle('micro',fontName=FONT,fontSize=6.8,leading=9,textColor=INK),
 'title':ParagraphStyle('title',fontName=BOLD,fontSize=17,leading=22,textColor=WHITE),
 'white':ParagraphStyle('white',fontName=BOLD,fontSize=9,leading=13,textColor=WHITE),
 'item':ParagraphStyle('item',fontName=BOLD,fontSize=10,leading=14,textColor=INK),
 'green':ParagraphStyle('green',fontName=BOLD,fontSize=7,leading=10,textColor=GREEN),
}

def para(txt,style='body'):
    return Paragraph(escape(str(txt or '')).replace('\n','<br/>'),S[style])

def header(report):
    date=report.report_date
    small=Paragraph('<font color="#dbe7ec">ANGELBIRD | SOCIAL MONITORING</font>',S['label'])
    title=Paragraph('Social Media Monitoring Report',S['title'])
    subtitle=Paragraph(f'<font color="#ffffff">{escape(date)} | {escape(report.status)} | {escape(report.generated_at_pkt)}</font>',S['small'])
    t=Table([[small],[title],[subtitle]],colWidths=[WIDTH],rowHeights=[17,34,20])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),INK),('TOPPADDING',(0,0),(-1,0),12),('LEFTPADDING',(0,0),(-1,-1),17),('BOTTOMPADDING',(0,-1),(-1,-1),12)]))
    return t

def section(label):
    t=Table([[Paragraph(f'<font color="white">{escape(label.upper())}</font>',S['white'])]],colWidths=[WIDTH])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),INK),('LEFTPADDING',(0,0),(-1,-1),15),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
    return t

def metric(n,label,bg,fg):
    big=Paragraph(f'<font size="19" color="{fg.hexval()}"><b>{n}</b></font>',ParagraphStyle('nb',parent=S['label'],alignment=TA_CENTER,leading=24))
    lab=Paragraph(f'<font color="{fg.hexval()}">{escape(label)}</font>',ParagraphStyle('ml',parent=S['label'],alignment=TA_CENTER,fontSize=6.5,leading=9))
    t=Table([[big],[lab]],colWidths=[WIDTH/4-7],rowHeights=[29,29])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),bg),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),3)]))
    return t

def metrics(report):
    items=[(len(report.today_findings),'NEW VERIFIED<br/>MENTIONS',INK,WHITE),
      (sum(f.sentiment=='Negative' for f in report.today_findings),'NEW VERIFIED<br/>COMPLAINTS',PALE,GREEN),
      (0,'CONFIRMED NEW<br/>CARD FAULTS',GREY,INK),
      (len(report.retail_observations),'ACTIVE RETAIL<br/>OFFERS NOTED',PALE,GREEN)]
    inner=[]
    for n,l,bg,fg in items:
        # Preserve intended 0 confirmed faults unless independently adjudicated (system does not auto-adjudicate)
        inner.append(metric(n,l.replace('<br/>','\n'),bg,fg))
    t=Table([inner],colWidths=[WIDTH/4]*4)
    t.setStyle(TableStyle([('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),5),('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    return t

def qr_drawing(url):
    code=qr.QrCodeWidget(url)
    x0,y0,x1,y1=code.getBounds()
    size=59
    drawing=Drawing(size,size,transform=[size/(x1-x0),0,0,size/(y1-y0),0,0])
    drawing.add(code)
    return drawing

def card(f,index,kind):
    is_retail=kind=='retail'; accent=GREEN if is_retail else INK
    label=f'{index} | {f.platform.upper()} | {f.status.upper()} | {f.priority.upper()}'
    title=escape(f.title)
    sub=f'{f.summary}'
    if f.author:sub+=' | By: '+f.author
    if f.published_date:sub+=' | Published: '+f.published_date
    if f.product:sub+=' | Product: '+f.product
    if f.date_evidence and not is_retail:sub+=' | Date proof: '+f.date_evidence
    if f.details:sub+='\n'+f.details
    link=escape(f.url,{'"':'&quot;'})
    content=[para(label,'green' if is_retail else 'label'),Paragraph(title,S['item']),Spacer(1,8),para(sub,'small'),
        Paragraph(f'<link href="{link}" color="#207c4d"><b>OPEN ORIGINAL SOURCE &gt;</b></link>',S['green'])]
    if f.url:
        t=Table([[content,qr_drawing(f.url)]],colWidths=[WIDTH-84,76])
    else:t=Table([[content]],colWidths=[WIDTH])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f7f8f8')),('LINEBEFORE',(0,0),(0,-1),4,accent),('BOX',(0,0),(-1,-1),.5,LINE),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),12),('LEFTPADDING',(0,0),(-1,-1),12)]))
    return KeepTogether([t,Spacer(1,9)])

def greybox(title,lines):
    txt=[Paragraph(escape(title.upper()),S['label'])]+[para(x,'small') for x in lines]
    t=Table([[txt]],colWidths=[WIDTH]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),GREY),('BOX',(0,0),(-1,-1),.5,LINE),('LEFTPADDING',(0,0),(-1,-1),15),('RIGHTPADDING',(0,0),(-1,-1),15),('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    return t

def footer(canvas,doc):
    canvas.saveState();canvas.setStrokeColor(LINE);canvas.line(MARGIN,45,PAGE_W-MARGIN,45)
    canvas.setFont(FONT,6.5);canvas.setFillColor(INK)
    canvas.drawString(MARGIN,31,'Angelbird Insights 2026 | Evidence-first monitoring')
    canvas.drawRightString(PAGE_W-MARGIN,31,'Page '+str(doc.page))
    canvas.restoreState()

def render_pdf(report,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=MARGIN,leftMargin=MARGIN,topMargin=34,bottomMargin=60,
      title=f'Angelbird Social Media Monitoring {report.report_date}',author='Angelbird Monitoring Automation')
    story=[header(report),Spacer(1,12),metrics(report),Spacer(1,17),para('In one line: '+(report.headline or 'Monitoring summary not available.'))]
    story += [Spacer(1,6),section(f'{report.report_date} | New verified findings'),Spacer(1,12)]
    if report.today_findings:
        for i,f in enumerate(report.today_findings,1):story.append(card(f,'N'+str(i),'today'))
    else: story.append(greybox('No exact-date verified new mentions', ['This is a demonstration: no sources were searched.' if 'DEMO' in report.status else 'No exact-date new items were verified from the sources searched. This does not establish universal absence.']))
    story.extend([Spacer(1,14),section(f'{report.report_date} | Active retail observations'),Spacer(1,12)])
    if report.retail_observations:
        for i,f in enumerate(report.retail_observations,1):story.append(card(f,'R'+str(i),'retail'))
    else:story.append(greybox('Retail observations',['No independently evidenced retailer offers captured.']))
    story.extend([Spacer(1,14),greybox('Public source coverage | '+report.report_date,[c.platform+': '+c.summary for c in report.coverage] or ['No platform searches recorded.']),Spacer(1,8)])
    story.append(para('Scope: Publicly retrievable/indexed material only. Private groups, platform login walls and unindexed comments remain visibility gaps. Delivery dates are not publication dates.','micro'))
    story.extend([Spacer(1,15),section('Previous issues & verification'),Spacer(1,10),para('Older leads and unverified results are NOT included in today\'s sentiment or incident totals.','small')])
    if report.older_leads:
        for i,f in enumerate(report.older_leads,1):story.append(card(f,'H'+str(i),'older'))
    else:story.append(greybox('Existing response watchlist',['No historical items were provided to this run.']))
    if report.unverified_leads:
        story.extend([Spacer(1,12),section('Unverified leads | Follow-up needed'),Spacer(1,10)])
        for i,f in enumerate(report.unverified_leads,1):story.append(card(f,'U'+str(i),'unverified'))
    story.extend([Spacer(1,12),section('Reporting rules'),Spacer(1,10),greybox('Evidence criteria',[
      '1. Count only distinct posts/comments/articles with independently verifiable publication date on the exact report day.',
      '2. Retail promotions do not change positive/neutral/negative sentiment counts.',
      '3. Do not classify user allegations as independently confirmed card faults.',
      '4. Older Reddit comments and older leads never enter today\'s counts.',
      '5. Search coverage is not universal platform coverage.'])])
    if report.visibility_gaps:
        story.extend([Spacer(1,10),greybox('Visibility gaps',report.visibility_gaps)])
    story.extend([Spacer(1,14),greybox('Report status',[report.status,'Generated at '+report.generated_at_pkt,'Verified mentions: '+str(len(report.today_findings)),'Retail observations: '+str(len(report.retail_observations)),report.methodology])])
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
