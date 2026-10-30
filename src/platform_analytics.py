"""Platform-specific evidence grouping and *observed* social engagement analytics.

Counts only sourced public post metrics. Never presents estimated website visitors
or private impressions as measured audience traffic.
"""
from collections import Counter
from urllib.parse import urlparse

PLATFORMS=(
    'Facebook','Instagram','X / Twitter','LinkedIn','Reddit','YouTube',
    'Camera Forums','Google / News / Articles','Retailers'
)
METRIC_ALIASES={'views':('views','post_views','video_views'),
                'likes':('likes','post_likes','reactions'),
                'comments':('comments','post_comments'),
                'shares':('shares','post_shares','reposts')}
HOSTS={
 'facebook.com':'Facebook','fb.watch':'Facebook',
 'instagram.com':'Instagram',
 'x.com':'X / Twitter','twitter.com':'X / Twitter',
 'linkedin.com':'LinkedIn',
 'reddit.com':'Reddit','redd.it':'Reddit',
 'youtube.com':'YouTube','youtu.be':'YouTube',
 'dpreview.com':'Camera Forums','eoshd.com':'Camera Forums',
 'reduser.net':'Camera Forums','bmcuser.com':'Camera Forums',
 'forum.blackmagicdesign.com':'Camera Forums',
 'bhphotovideo.com':'Retailers','adorama.com':'Retailers',
 'cvp.com':'Retailers','proav.co.uk':'Retailers',
 'galaxus.de':'Retailers','x-kom.pl':'Retailers',
}
def category(item):
    text=str(getattr(item,'platform','') or '').lower()
    host=(urlparse(str(getattr(item,'url','') or '')).hostname or '').lower()
    for domain,result in HOSTS.items():
        if host==domain or host.endswith('.'+domain):
            return result
    if 'facebook' in text or 'meta page' in text:return 'Facebook'
    if 'instagram' in text:return 'Instagram'
    if 'twitter' in text or text in ('x','x.com'):return 'X / Twitter'
    if 'linkedin' in text:return 'LinkedIn'
    if 'reddit' in text:return 'Reddit'
    if 'youtube' in text:return 'YouTube'
    if 'forum' in text:return 'Camera Forums'
    if any(term in text for term in ('retail','shop','store','reseller','marketplace')):
        return 'Retailers'
    return 'Google / News / Articles'

def _number(raw):
    """Numeric metrics only. Never parse phrases like 'about 10K' into exact counts."""
    if isinstance(raw,bool):return None
    if isinstance(raw,(int,float)) and raw>=0:return int(raw)
    if isinstance(raw,str):
        text=raw.strip().replace(',','')
        if text.isdigit():return int(text)
    return None

def metric_summary(items):
    totals=Counter()
    available=set()
    observed_posts=0
    for item in items:
        engagement=getattr(item,'engagement',None) or {}
        if not isinstance(engagement,dict):continue
        seen_metric=False
        for field,aliases in METRIC_ALIASES.items():
            # Use only the first grounded value per measurement family;
            # reactions and likes may refer to the same event.
            n=next((_number(engagement.get(alias)) for alias in aliases
                    if _number(engagement.get(alias)) is not None),None)
            if n is None:continue
            available.add(field)
            totals[field]+=n
            seen_metric=True
        if seen_metric:observed_posts+=1
    return {'totals':dict(totals),'available':sorted(available),
            'posts_with_public_metrics':observed_posts,'posts_total':len(items)}

def platform_summary(items):
    grouped={k:[] for k in PLATFORMS}
    for item in items:grouped[category(item)].append(item)
    return grouped

def analytics_rows(items):
    grouped=platform_summary(items)
    return [{'platform':name,'count':len(records),**metric_summary(records)}
            for name,records in grouped.items()]

def traffic_disclaimer():
    return ('Views, likes, comments, reactions, reposts and shares are public post-level '
            'observations ONLY where original sources or approved APIs supplied numeric '
            'values. Missing means not available, never zero. Post views are not unique '
            'website visitors or conversion traffic. Third-party website sessions, '
            'referral visits, impressions and campaign conversions require the '
            'owner\'s authorized analytics property or verified data export.')
