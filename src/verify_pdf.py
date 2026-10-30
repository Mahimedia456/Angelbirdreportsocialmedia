"""Production PDF evidence audit: platform metrics must lead to corresponding source cards.

Checks source links as actual PDF hyperlinks and original post titles in the
right platform section. It does NOT claim original-platform API completeness.
"""
import json
import re
import sys
from pathlib import Path
from pypdf import PdfReader
from .platform_analytics import PLATFORMS,platform_summary
from .schema import ResearchReport

ROOT=Path(__file__).resolve().parents[1]

def clean(s):
    return re.sub(r'\s+','',str(s)).casefold()

def verify(day):
    report_file=ROOT/'data'/day[:4]/day[5:7]/f'Angelbird-Social-Monitoring-{day}.json'
    pdf=ROOT/'reports'/day[:4]/day[5:7]/f'Angelbird-Social-Monitoring-{day}.pdf'
    data=ResearchReport.model_validate_json(report_file.read_text(encoding='utf-8'))
    reader=PdfReader(str(pdf))
    texts=[p.extract_text() or '' for p in reader.pages]
    full_text=clean(' '.join(texts))
    urls=set()
    for page in reader.pages:
        for ann in page.annotations or []:
            entry=ann.get_object()
            action=entry.get('/A')
            if action and action.get('/URI'):
                urls.add(str(action['/URI']))
    checked=0
    for source in data.today_findings+data.historical_findings:
        if clean(source.title) not in full_text:
            raise RuntimeError(f'Original source title absent from generated PDF: {source.title}')
        if source.url not in urls:
            raise RuntimeError(f'Original source hyperlink absent from generated PDF: {source.url}')
        checked+=1
    all_sources=data.today_findings+data.historical_findings
    groups=platform_summary(all_sources)
    # Source cards must live between their own platform section heading and the
    # next platform section heading; this is what maps KPI rows to actual evidence.
    pdf_text=' '.join(texts)
    low=pdf_text.casefold()
    all_positions=[]
    for platform in PLATFORMS:
        heading=platform.casefold()
        match=re.search(r'(?<!\w)'+re.escape(heading)+r'\s*\|',low)
        if match:all_positions.append((platform,match.start()))
    if len(all_positions)<7:
        raise RuntimeError('Platform-specific scorecard headings missing.')
    for index,(platform,start) in enumerate(all_positions):
        finish=all_positions[index+1][1] if index+1<len(all_positions) else len(pdf_text)
        section=clean(pdf_text[start:finish])
        for source in groups[platform]:
            if clean(source.title) not in section:
                raise RuntimeError(f'{platform} source not shown under that platform analytics: {source.title}')
    audit={'date':day,'pages':len(reader.pages),
           'dated_posts_checked':checked,
           'source_hyperlinks':len(urls),'platform_sections':len(all_positions),
           'result':'passed'}
    out=pdf.with_name(pdf.stem+'-quality.json')
    out.write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print('PDF evidence audit:',json.dumps(audit))
    return audit

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: python -m src.verify_pdf YYYY-MM-DD')
    verify(sys.argv[1])
