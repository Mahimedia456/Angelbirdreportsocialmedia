"""Merge manually researched ChatGPT web findings with free Python/YT evidence.

This module does not call OpenAI. The findings JSON is added to GitHub after
research in a ChatGPT conversation and is independently date-guarded on import.
"""
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from .schema import ResearchReport

FIELDS=('today_findings','unverified_leads','older_leads','retail_observations')

def _key(item):
    u=urlsplit(item.url.strip())
    canonical=urlunsplit((u.scheme.lower(),u.netloc.lower(),u.path.rstrip('/'),u.query,''))
    return canonical, item.author.lower().strip()

def import_chatgpt_evidence(report: ResearchReport, root: Path):
    path=(root/'data'/report.report_date[:4]/report.report_date[5:7]/
          f'Atomos-Social-Monitoring-{report.report_date}-chatgpt.json')
    if not path.is_file():
        return report,{'found':False,'inserted':0,'source':'No ChatGPT evidence file'}
    raw=json.loads(path.read_text(encoding='utf-8'))
    if str(raw.get('report_date','')) != report.report_date:
        raise ValueError('ChatGPT evidence report_date does not match current report; refusing import.')
    imported=ResearchReport.model_validate(raw).enforce_date_guardrails()
    added={}
    for field in FIELDS:
        existing=getattr(report,field)
        prior={_key(x) for x in existing}
        count=0
        for item in getattr(imported,field):
            if field=='older_leads' and item.published_date >= report.report_date:continue
            if field=='today_findings' and item.published_date != report.report_date:continue
            if _key(item) in prior:continue
            existing.append(item);prior.add(_key(item));count+=1
        added[field]=count
    covered={x.platform.lower() for x in report.coverage}
    for c in imported.coverage:
        if c.platform.lower() not in covered:
            report.coverage.append(c);covered.add(c.platform.lower())
    if sum(added.values()):
        report.methodology=(report.methodology+' | ChatGPT interactive web-research findings imported '
            'from reviewed source-linked JSON; no OpenAI API request performed by GitHub Actions.')
    report.visibility_gaps.extend(x for x in imported.visibility_gaps
                                  if x not in report.visibility_gaps)
    return report,{'found':True,'inserted':sum(added.values()),'by_bucket':added,
                   'source':path.relative_to(root).as_posix()}
