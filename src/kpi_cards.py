"""Compact evidence-based KPI cards for unlimited-length monthly/weekly PDF reports."""
from reportlab.platypus import Table, TableStyle, Spacer
from reportlab.lib import colors

def kpi_dashboard(pdf, groups):
    """One executive section, groups rendered as 4-column cards with measured values only.

    groups: [(heading, [(label, value), ...]), ...]
    """
    result=[Spacer(1,9),pdf.band("OVERALL KPI DASHBOARD"),Spacer(1,8)]
    for group_name,cards in groups:
        result.append(pdf.P(group_name.upper(),'caption'))
        result.append(Spacer(1,4))
        for start in range(0,len(cards),4):
            chunk=cards[start:start+4]
            cells=[]
            for label,value in chunk:
                display="N/A" if value is None else f"{value:,}" if isinstance(value,(int,float)) else str(value)
                cells.append([pdf.P(display,'kpi'),Spacer(1,2),pdf.P(label,'kpilabel')])
            while len(cells)<4:cells.append([])
            panel=Table([cells],colWidths=[pdf.W/4]*4,hAlign='LEFT')
            panel.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#F1F5F7')),
                ('GRID',(0,0),(-1,-1),0.6,colors.HexColor('#DBE3E8')),
                ('TOPPADDING',(0,0),(-1,-1),9),
                ('BOTTOMPADDING',(0,0),(-1,-1),9),
                ('LEFTPADDING',(0,0),(-1,-1),4),
                ('RIGHTPADDING',(0,0),(-1,-1),4),
                ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ]))
            result.extend([panel,Spacer(1,7)])
        result.append(Spacer(1,2))
    result.append(pdf.P(
        'Observed source records only. Discovery leads have unconfirmed original dates; '
        'engagement totals cover only sources with measured numeric values. '
        'N/A is not zero. Historical references and repeated crossposts are not a census of all social activity.',
        'small'))
    result.append(Spacer(1,10))
    return result
