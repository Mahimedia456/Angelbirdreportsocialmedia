"""Original-source-backed social formats; stories, tags and mentions stay within their platform."""
import re
from collections import Counter
from urllib.parse import urlparse,parse_qs
from .platform_analytics import category

SOCIAL=('Facebook','Instagram','X / Twitter','LinkedIn','Reddit','YouTube')
TYPES=('post','story','reel','mention','tagged_post','comment','video','article','retailer')
LABELS={'post':'Post','story':'Story','reel':'Reel','mention':'Mention',
        'tagged_post':'Tagged post','comment':'Comment','video':'Video',
        'article':'Article','retailer':'Retail listing'}
HASHTAG=re.compile(r'(?<!\w)#[A-Za-z][A-Za-z0-9_]{1,60}')
HANDLE=re.compile(r'(?<![\w@])@[A-Za-z][A-Za-z0-9_.]{1,40}')

def content_type(item):
    url=str(getattr(item,'url','') or '')
    parsed=urlparse(url)
    path=parsed.path.lower()
    platform=category(item)
    if platform=='YouTube' and ('lc' in parse_qs(parsed.query) or '&lc=' in url):return 'comment'
    if platform in ('Facebook','Instagram'):
        if '/stories/' in path or '/story.php' in path or '/story/' in path:return 'story'
        if '/reel/' in path or '/reels/' in path:return 'reel'
        if '/comments/' in path or '/comment/' in path:return 'comment'
    raw=str(getattr(item,'content_type','') or '').strip().lower().replace(' ','_')
    if raw in TYPES:
        if platform in SOCIAL and raw in ('post','story','reel','mention','tagged_post','comment','video'):
            return raw
        if platform not in SOCIAL and raw in ('article','retailer'):return raw
    if platform=='YouTube':return 'video'
    if platform=='Retailers':return 'retailer'
    if platform not in SOCIAL:return 'article'
    return 'post'

def source_labels(value):
    text=str(value or '')[:1500]
    return {'hashtags':list(dict.fromkeys(HASHTAG.findall(text)))[:12],
            'mentioned_accounts':list(dict.fromkeys(HANDLE.findall(text)))[:12]}

def content_counts(items):
    return dict(Counter(content_type(x) for x in items))
