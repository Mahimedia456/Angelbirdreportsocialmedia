"""Preserve supplied social-story URLs as leads without inventing content or reach.

A public Instagram story URL alone does NOT prove the brand was tagged, that the
story is accessible, or that it was published on the day of observation.
"""
import json
from pathlib import Path
from urllib.parse import urlparse
from .schema import Finding

ROOT=Path(__file__).resolve().parents[1]
WATCHLIST=ROOT/'data'/'social_story_watchlist.json'

def story_handle(url):
    parsed=urlparse(str(url or ''))
    hostname=(parsed.hostname or '').lower()
    if hostname not in ('instagram.com','www.instagram.com'):
        return ''
    pieces=[p for p in parsed.path.split('/') if p]
    if len(pieces) not in (2,3) or pieces[0].lower()!='stories':
        return ''
    handle=pieces[1]
    if not handle or len(handle)>45 or not all(c.isalnum() or c in '._' for c in handle):
        return ''
    if len(pieces)==3 and (not pieces[2].isdigit() or len(pieces[2])>25):
        return ''
    return handle

def watchlist_leads(day,root=None):
    path=Path(root or ROOT)/'data'/'social_story_watchlist.json'
    if not path.exists():return []
    content=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(content,list):return []
    result=[]
    used=set()
    for record in content[:250]:
        if not isinstance(record,dict) or record.get('observed_date')!=day:
            continue
        url=str(record.get('url') or '').strip()
        username=story_handle(url)
        if not username or url in used:continue
        used.add(url)
        result.append(Finding(
            title='Instagram Story research lead: @'+username,
            platform='Instagram',url=url,author='@'+username,
            content_type='story',status='unverified',
            published_date='',date_evidence='',
            reference_date=day,priority='Watch',sentiment='Not applicable',
            source_excerpt='',
            summary=('Original Story URL supplied for investigation. '
                     'Original photo/video, caption, any brand mention or tag, '
                     'and publication date have not been independently verified.'),
            verification_note=(
              'USER-SUPPLIED STORY LINK ONLY. Not counted in verified posts, '
              'stories, reach, engagement, brand mentions or tags. '
              'Story may have expired or require Instagram login.'),
            response_action='Check original Story with authorized access before classifying brand mention.',
        ))
    return result

def include_watchlist(report,root=None):
    already={f.url.rstrip('/').lower() for f in (
      report.today_findings+report.unverified_leads)}
    added=0
    for lead in watchlist_leads(report.report_date,root):
        key=lead.url.rstrip('/').lower()
        if key in already:continue
        report.unverified_leads.append(lead)
        already.add(key)
        added+=1
    if added:
        report.visibility_gaps.append(
          f'{added} supplied Instagram Story links were retained as unverified '
          'leads. No source media/date or brand tag was accessible for confirmation.')
    return report,added
