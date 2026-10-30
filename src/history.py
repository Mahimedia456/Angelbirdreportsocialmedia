"""Merge earlier dated reports into the latest daily PDF without further OpenAI calls."""
from __future__ import annotations
import json
import re
from datetime import date
from pathlib import Path
from .schema import Finding, ResearchReport

def _key(f: Finding):
    # A Reddit thread can contain several separate comments, so author + excerpt matter.
    return (f.url.rstrip('/').lower(), f.author.casefold().strip(), f.source_excerpt.casefold().strip()[:90])

def _older(f: Finding, target: str):
    return bool(f.published_date and f.published_date < target)

def _relevant(f: Finding):
    # Reject unrelated news articles inherited from faulty earlier runs.
    return bool(re.search(r'\\bangelbird\\b|\\bav[ -]?pro\\b',f.title+' '+f.source_excerpt+' '+f.product,re.I))

def _load_finding(raw):
    try: return Finding.model_validate(raw)
    except Exception: return None

def compile_history(report: ResearchReport, root: Path):
    target=report.report_date
    historic=list(report.historical_findings)
    retail=list(report.historical_retail)
    watch=list(report.older_leads)
    seed=root/'data'/'reference_history_2026_10_29.json'
    if seed.is_file():
        raw=json.loads(seed.read_text(encoding='utf-8'))
        for entry in raw.get('findings',[]):
            f=_load_finding(entry)
            if f is not None and _older(f,target) and _relevant(f):
                f.status='older'
                historic.append(f)
        for entry in raw.get('retail_observations',[]):
            f=_load_finding(entry)
            if f is not None and _older(f,target):
                f.status='retail';f.sentiment='Not applicable'
                retail.append(f)
    # Every previously generated real-day JSON is a potential historical source.
    # Exclude demo files and the current date; never count older results as current.
    for path in sorted((root/'data').glob('????/??/Angelbird-Social-Monitoring-????-??-??.json')):
        if path.name.endswith('-DEMO.json'):continue
        try: raw=json.loads(path.read_text(encoding='utf-8'))
        except (ValueError,OSError):continue
        day=str(raw.get('report_date') or '')
        if not day or day>=target:continue
        for entry in raw.get('today_findings',[]):
            f=_load_finding(entry)
            # Earlier model outputs without a direct excerpt are not verified archive evidence.
            if f is not None and _older(f,target) and _relevant(f) and re.search(r'\\bangelbird\\b|\\bav[ -]?pro\\b', f.source_excerpt,re.I):
                f.status='older';historic.append(f)
        for entry in raw.get('retail_observations',[]):
            f=_load_finding(entry)
            if f is not None and _older(f,target) and _relevant(f):
                f.status='retail';f.sentiment='Not applicable';retail.append(f)
        for entry in raw.get('older_leads',[]):
            f=_load_finding(entry)
            if f is not None and _older(f,target) and _relevant(f):
                f.status='older';watch.append(f)
    watch_path=root/'data'/'watchlist.json'
    if watch_path.is_file():
        for entry in json.loads(watch_path.read_text(encoding='utf-8')):
            f=_load_finding(entry)
            if f is not None and _older(f,target) and _relevant(f):
                f.status='older';watch.append(f)
    def unique(items):
        seen=set(); out=[]
        for f in sorted(items,key=lambda x:x.published_date or '',reverse=True):
            if not _older(f,target):continue
            key=_key(f)
            if key in seen:continue
            seen.add(key);out.append(f)
        return out
    report.historical_findings=unique(historic)
    report.historical_retail=unique(retail)
    hist_keys={_key(f) for f in report.historical_findings}
    report.older_leads=[f for f in unique(watch) if _key(f) not in hist_keys]
    dates=[f.published_date for f in report.historical_findings+report.today_findings if f.published_date]
    report.report_period_start=min(dates) if dates else target
    report.report_period_end=target
    return report
