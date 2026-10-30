"""Executive KPI cards: source-safe values with semantic status colors.

Positive = green, Neutral / questions = amber, Negative = red.
No metric is inferred from missing values. Works with unlimited page count.
"""
from reportlab.platypus import Table, TableStyle, Spacer
from reportlab.lib import colors

GREEN=colors.HexColor('#168253')
GREEN_BG=colors.HexColor('#E9F6EF')
YELLOW=colors.HexColor('#9B6B00')
YELLOW_BG=colors.HexColor('#FFF5D7')
RED=colors.HexColor('#B83F3B')
RED_BG=colors.HexColor('#FFF0EE')
BLUE=colors.HexColor('#345D77')
BLUE_BG=colors.HexColor('#ECF3F7')
BORDER=colors.HexColor('#DDE4E8')

def _theme(label):
    name=str(label).lower().strip()
    if name in ('positive','likes','reactions'):
        return GREEN,GREEN_BG
    if name in ('negative','complaints'):
        return RED,RED_BG
    if name in ('neutral','questions','not classified','pending leads','leads','days captured'):
        return YELLOW,YELLOW_BG
    return BLUE,BLUE_BG

def kpi_dashboard(pdf, groups):
    content=[Spacer(1,8),pdf.band('EXECUTIVE KPI DASHBOARD'),Spacer(1,9)]
    for name,entries in groups:
        content.extend([pdf.P(name.title(),'caption'),Spacer(1,5)])
        for start in range(0,len(entries),4):
            batch=list(entries[start:start+4])
            cards=[]
            commands=[]
            for i,(label,value) in enumerate(batch):
                color,bg=_theme(label)
                value='N/A' if value is None else f'{value:,}' if isinstance(value,(int,float)) else str(value)
                # Avoid fitting narrow-card text into two lines unexpectedly.
                if len(value)>14:value=value[:13]+'...'
                cards.append([pdf.P(f'<font color="{'#%02X%02X%02X' % (int(color.red*255),int(color.green*255),int(color.blue*255))}">{value}</font>','kpi',raw=True),
                              Spacer(1,3),pdf.P(str(label),'kpilabel')])
                commands += [('BACKGROUND',(i,0),(i,0),bg),
                             ('LINEBEFORE',(i,0),(i,0),2,color)]
            while len(cards)<4:cards.append([])
            panel=Table([cards],colWidths=[pdf.W/4]*4,hAlign='LEFT')
            panel.setStyle(TableStyle(commands+[
                ('GRID',(0,0),(-1,-1),0.6,BORDER),
                ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                ('LEFTPADDING',(0,0),(-1,-1),8),
                ('RIGHTPADDING',(0,0),(-1,-1),7),
                ('TOPPADDING',(0,0),(-1,-1),11),
                ('BOTTOMPADDING',(0,0),(-1,-1),11),
            ]))
            content.extend([panel,Spacer(1,8)])
    content.extend([pdf.P('Observed sources only. Pending records and incomplete metrics are separate; N/A does not mean zero.','micro'),Spacer(1,12)])
    return content
