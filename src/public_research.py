"""Public-source Atomos monitoring. Python does collection; no OpenAI calls.

Search discovers candidates; only first-party pages or authorized provider APIs can
verify publication dates. Public images are cached as attributed, low-res thumbnails.
A source blocked by login/robots is reported as unavailable, never invented.
"""
import html
import json
import os
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import quote_plus, urlparse, urljoin, parse_qs
from xml.etree import ElementTree
import requests
from bs4 import BeautifulSoup
from .schema import Finding, Coverage, ResearchReport

ROOT=Path(__file__).resolve().parents[1]
BRAND=re.compile(r'\batomos\b|\batomosphere\b|\batom[- ]?os\b',re.I)
NEG=re.compile(r'overheat|hotter|failure|failed|corrupt|crash|broken|problem|error|not working|complain|recording stop',re.I)
POS=re.compile(r'recommend|excellent|best|great|reliable|fast|impressive|love|superb|works well',re.I)
PRICE=re.compile(r'(?:USD|EUR|GBP|CAD|PKR|INR|[$€£₹])\s?\d[\d,.]*',re.I)
PRODUCT=re.compile(r'(?:Atomos\\s+)?(?:Ninja(?:\\s+(?:TX\\s*GO|TX|RAW|Ultra|V\\+))?|Shogun(?:\\s+(?:Ultra|AV-19M?|Classic))?|Shinobi(?:\\s+(?:7\\s*(?:II|RX)|II|GO))?|Sumo(?:\\s+PRO-19)?|AtomOS(?:phere)?|StudioSonic|TX-RX|UltraSync|A-Eye)[^,.;\\n]{0,65}',re.I)
DOMAINS={'reddit.com':'Reddit','youtube.com':'YouTube','youtu.be':'YouTube',
 'facebook.com':'Facebook','instagram.com':'Instagram','linkedin.com':'LinkedIn',
 'x.com':'X / Twitter','twitter.com':'X / Twitter',
 'dpreview.com':'Camera forums','eoshd.com':'Camera forums','newsshooter.com':'Industry articles',
 'cined.com':'Industry articles','petapixel.com':'Industry articles',
 'bhphotovideo.com':'Retailers','adorama.com':'Retailers','cvp.com':'Retailers'}
GROUPS={
 'Reddit':['site:reddit.com "Atomos" {date}','site:reddit.com "Atomos" "card" {month} {year}'],
 'YouTube':['site:youtube.com/watch "Atomos" {date}','site:youtube.com "Atomos" {month} {year}'],
 'Facebook':['site:facebook.com "Atomos" {date}'],
 'Instagram':['site:instagram.com "Atomos" {date}'],
 'LinkedIn':['site:linkedin.com/posts "Atomos" {date}'],
 'X / Twitter':['site:x.com "Atomos" {date}'],
 'Camera forums':['site:dpreview.com/forums "Atomos" {month} {year}',
                  '"Atomos" "CFexpress" camera forum {date}'],
 'Industry articles':['site:newsshooter.com "Atomos" {month} {year}',
                      'site:cined.com "Atomos" {month} {year}',
                      '"Atomos" camera review {date}'],
 'Retailers':['site:bhphotovideo.com "Atomos" Ninja Shogun {month} {year}',
              'site:cvp.com "Atomos" monitor recorder {month} {year}'],
}

def iso(value):
    v=str(value or '').strip()
    m=re.search(r'(?<!\d)(20\d\d-\d\d-\d\d)(?!\d)',v)
    if m:
        try:return date.fromisoformat(m.group(1)).isoformat()
        except ValueError:pass
    for fmt in ('%a, %d %b %Y %H:%M:%S %z','%d %b %Y','%b %d, %Y','%B %d, %Y','%d %B %Y'):
        try:return datetime.strptime(v[:35],fmt).date().isoformat()
        except ValueError:pass
    return ''

def youtube_date_pkt(value):
    """Convert an API timestamp into the report timezone, not UTC calendar date."""
    try:
        stamp=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        if stamp.tzinfo is None:stamp=stamp.replace(tzinfo=timezone.utc)
        return stamp.astimezone(ZoneInfo('Asia/Karachi')).date().isoformat()
    except (ValueError,TypeError):
        return iso(value)

def valid_url(url):
    u=urlparse(str(url or ''))
    return u.scheme in ('http','https') and bool(u.hostname)

def matches_source_domain(group,url):
    host=(urlparse(url).hostname or '').lower()
    if not host:return False
    allowed={
        'Reddit':('reddit.com','redd.it'),
        'YouTube':('youtube.com','youtu.be'),
        'Facebook':('facebook.com','fb.watch'),
        'Instagram':('instagram.com'),
        'LinkedIn':('linkedin.com'),
        'X / Twitter':('x.com','twitter.com'),
        'Camera forums':('dpreview.com','eoshd.com','reduser.net','bmcuser.com',
                         'forum.blackmagicdesign.com','nikonites.com','sonyalpha.blog'),
        'Retailers':('bhphotovideo.com','adorama.com','cvp.com','proav.co.uk',
                     'downtowncamera.com','ofertasgaming.com','atomos.com')
    }
    if group=='Industry articles':
        other=tuple(v for k,values in allowed.items() for v in values if k!='Retailers')
        return not any(host==d or host.endswith('.'+d) for d in other) and not host.endswith('amazon.com')
    domains=allowed.get(group,())
    return any(host==d or host.endswith('.'+d) for d in domains)

def source_group(url, default):
    host=(urlparse(url).hostname or '').lower()
    for domain, group in DOMAINS.items():
        if host==domain or host.endswith('.'+domain):return group
    return default

def excerpt(text):
    words=re.sub(r'\s+',' ',html.unescape(str(text or ''))).strip()
    m=BRAND.search(words)
    if not m:return ''
    return words[max(0,m.start()-170):min(len(words),m.end()+360)].strip()

def sentiment(text):
    t=text or ''
    if '?' in t and not NEG.search(t):return 'Question'
    if NEG.search(t):return 'Negative'
    if POS.search(t):return 'Positive'
    return 'Neutral'

def classify(url, content, group, when, evidence, title='',author='',image='',stats=None):
    content=html.unescape(content or '')
    snippet=excerpt(content)
    if not snippet:return None
    if not valid_url(url):return None
    product=PRODUCT.search(content)
    status='verified' if when and evidence else 'unverified'
    return Finding(
        title=(title or snippet[:90])[:180], platform=source_group(url,group),
        url=url, published_date=when, date_evidence=evidence or '',
        source_excerpt=snippet,summary=snippet[:500],author=(author or '')[:110],
        sentiment=sentiment(snippet),priority=('High' if NEG.search(snippet) else
                'Medium' if '?' in snippet else 'Low'),status=status,
        product=product.group(0)[:80] if product else '',
        image_url=image if valid_url(image) else '',
        engagement=stats or {},
        impact=('Customer feedback requires technical review.' if NEG.search(snippet) else
                'Public brand or product mention; contextual relevance only.'),
        response_action=('Review source and consider technical response.' if NEG.search(snippet) else
                         'Optional review.' if '?' in snippet else 'Not required.'))

class PublicResearch:
    def __init__(self, day):
        self.day=date.fromisoformat(day)
        self.date=day
        self.end=(self.day+timedelta(days=1)).isoformat()
        self.limit=int(os.getenv('MAX_SEARCH_QUERIES','18'))
        self.page_limit=int(os.getenv('MAX_SOURCE_PAGES','35'))
        self.image_limit=int(os.getenv('MAX_SOURCE_IMAGES','12'))
        self.s=requests.Session()
        self.s.headers.update({'User-Agent':'AtomosSocialMonitoring/2.1 (public research and attribution)'})
        self.audit=[]
        self.candidates={}
        self.findings=[]
        self.unverified=[]
        self.older=[]
        self.retail=[]
        self.gaps=[]
        self.counts=Counter()
        self.seen=set()
        self.queries=0
        self.fetched=0
        self.images=0
        self.root=ROOT/'assets'/day[:4]/day[5:7]/day
        self.root.mkdir(parents=True,exist_ok=True)

    def get(self, url, params=None, headers=None, timeout=13):
        try:
            r=self.s.get(url,params=params,headers=headers,timeout=timeout,allow_redirects=True)
            if r.status_code!=200:return None,f'HTTP {r.status_code}'
            if len(r.content)>3_000_000:return None,'Content larger than 3MB'
            return r,'OK'
        except requests.RequestException as exc:
            return None,str(exc)[:100]

    def add(self, item,group,discovery,search_date=''):
        url=str(item.get('url') or '').split('#')[0]
        if not valid_url(url):return
        if 'news.google.com/rss/articles/' in url:
            # Google's opaque redirects are not original evidence, but are kept in the audit.
            self.audit.append({'group':group,'stage':'candidate','url':url,'outcome':'unresolved Google News redirect'})
            return
        if url in self.candidates:return
        if not matches_source_domain(group,url):
            self.counts[group+'.wrong_source_domain']+=1
            return
        # Do not use source-fetch budget on unrelated indexed search results.
        indexed_text=str(item.get('title') or '')+' '+str(item.get('snippet') or '')
        if not BRAND.search(indexed_text):
            self.counts[group+'.irrelevant_index_hits']+=1
            return
        self.candidates[url]={**item,'url':url,'group':group,'discovery':discovery,'search_date':search_date}
        self.counts[group+'.candidates']+=1

    def ddg_fallback(self,group,query):
        """Best-effort second public index. Respect blocks/rate limits; no bypasses."""
        if getattr(self,'ddg_blocked',False):return
        response,state=self.get('https://html.duckduckgo.com/html/',params={'q':query},timeout=12)
        if not response:
            self.gaps.append(f'{group}: alternate public index {state}')
            if '429' in state or '403' in state:self.ddg_blocked=True
            return
        soup=BeautifulSoup(response.text,'html.parser')
        count=0
        for block in soup.select('.result')[:12]:
            a=block.select_one('a.result__a')
            if not a:continue
            href=a.get('href','')
            parsed=urlparse(urljoin('https://duckduckgo.com',href))
            redirect=parse_qs(parsed.query).get('uddg',[])
            original=redirect[0] if redirect else (urljoin('https://duckduckgo.com',href))
            text=(block.select_one('.result__snippet') or block)
            snippet=text.get_text(' ',strip=True)
            if BRAND.search(a.get_text(' ',strip=True)+' '+snippet):
                self.add({'url':original,'title':a.get_text(' ',strip=True),'snippet':snippet},
                         group,'DuckDuckGo HTML')
                count+=1
        self.audit.append({'group':group,'stage':'search-fallback','query':query,
                           'relevant_index_candidates':count,'index':'DuckDuckGo HTML'})
        if count:self.counts[group+'.fallback_candidates']+=count

    def index_query(self,group,query):
        self.queries+=1
        found=0
        initial=self.counts[group+'.candidates']
        # Public search discovery only: no paid search API, no GPT/API billing.
        response,state=self.get('https://www.bing.com/search',
                                params={'q':query,'format':'rss','count':'20'})
        if response:
            try:
                root=ElementTree.fromstring(response.text)
                for item in root.findall('.//item'):
                    url=item.findtext('link') or ''
                    title=item.findtext('title') or ''
                    desc=item.findtext('description') or ''
                    self.add({'url':url,'title':html.unescape(title),
                              'snippet':BeautifulSoup(desc,'html.parser').get_text(' ',strip=True)},
                             group,'Bing public RSS',item.findtext('pubDate') or '')
                    found+=1
                self.counts[group+'.successful_queries']+=1
            except ElementTree.ParseError:state='Unparseable public RSS feed'
        if not response or state!='OK':
            self.gaps.append(f'{group}: public search index {state}')
        if self.counts[group+'.candidates']==initial:
            if self.counts[group+'.fallback_attempts']<1:
                self.counts[group+'.fallback_attempts']+=1
                self.ddg_fallback(group,query)
        self.audit.append({'group':group,'stage':'search','query':query,'results':found,
                           'index':'Bing public RSS, optional DDG fallback'})
        self.counts[group+'.queries']+=1

    def free_gdelt_news(self):
        """GDELT public DOC feed: discovered articles still require original-page proof."""
        start=self.day.strftime('%Y%m%d')+'000000'
        finish=(self.day+timedelta(days=1)).strftime('%Y%m%d')+'000000'
        response,state=self.get('https://api.gdeltproject.org/api/v2/doc/doc',
            params={'query':'"Atomos"','mode':'artlist','format':'json',
                    'startdatetime':start,'enddatetime':finish,
                    'maxrecords':'50','sort':'datedesc'},timeout=16)
        if not response:
            self.audit.append({'stage':'free-news-search','provider':'GDELT',
                               'state':state,'source_verified':False})
            self.gaps.append('GDELT free news index: '+state)
            return
        try:
            payload=response.json()
            articles=payload.get('articles',[]) if isinstance(payload,dict) else []
            accepted=0
            for obj in articles[:50]:
                url=str(obj.get('url') or '')
                title=str(obj.get('title') or '')
                if not valid_url(url) or not BRAND.search(title):continue
                if not matches_source_domain('Industry articles',url):continue
                previous=self.counts['Industry articles.candidates']
                self.add({'url':url,'title':title,'snippet':title},
                         'Industry articles','GDELT open news index',
                         obj.get('seendate',''))
                if self.counts['Industry articles.candidates']>previous:accepted+=1
            self.counts['Industry articles.gdelt_queries']+=1
            self.audit.append({'stage':'free-news-search','provider':'GDELT',
                               'returned':len(articles),'candidates':accepted,
                               'source_verified':False})
        except (ValueError,TypeError,AttributeError):
            self.gaps.append('GDELT free news response could not be parsed')

    def known_sources(self):
        """Revisit supplied original post URLs even if public search indexes miss them."""
        path=ROOT/'data'/'reference_history_2026_10_29.json'
        if path.is_file():
            try:
                entries=json.loads(path.read_text(encoding='utf-8')).get('findings',[])
                for item in entries:
                    url=item.get('url','')
                    group=source_group(url,'Industry articles')
                    if group in GROUPS and matches_source_domain(group,url):
                        self.add({'url':url,'title':item.get('title',''),
                                  'snippet':item.get('source_excerpt') or item.get('summary','')},
                                  group,'User-provided original reference URL')
            except (OSError,ValueError):pass
        extra=ROOT/'data'/'monitored_urls.json'
        if extra.is_file():
            try:
                for item in json.loads(extra.read_text(encoding='utf-8')):
                    if not isinstance(item,dict):continue
                    url=item.get('url','')
                    group=item.get('platform') or source_group(url,'Industry articles')
                    if group in GROUPS and matches_source_domain(group,url):
                        self.add({'url':url,'title':item.get('title','Atomos source'),
                                  'snippet':item.get('description','Atomos post')},
                                 group,'Curated original URL')
            except (OSError,ValueError):pass

    def search(self):
        for group,queries in GROUPS.items():
            for template in queries:
                if self.queries>=self.limit:break
                self.index_query(group,template.format(date=self.date,year=self.day.year,
                                 month=self.day.strftime('%B')))
        # Google News RSS is a secondary public feed for editorial discovery only.
        if self.queries<self.limit:
            self.queries+=1
            response,state=self.get('https://news.google.com/rss/search',
                params={'q':f'Atomos when:1d after:{self.date} before:{self.end}','hl':'en'})
            if response:
                try:
                    rss=ElementTree.fromstring(response.text)
                    for item in rss.findall('.//item'):
                        self.add({'url':item.findtext('link'),'title':item.findtext('title'),
                                  'snippet':item.findtext('description')},'Industry articles','Google News RSS')
                except ElementTree.ParseError:self.gaps.append('Google News feed parsing failed')
            else:self.gaps.append('Google News index: '+state)
        self.free_gdelt_news()
        self.known_sources()
        return len(self.candidates)

    def youtube(self):
        """One low-quota official video search, bounded public comment calls."""
        key=os.getenv('YOUTUBE_API_KEY','').strip()
        if not key:
            self.gaps.append('YouTube Data API key unavailable to workflow; videos/comments not checked directly')
            return
        max_videos=max(0,min(12,int(os.getenv('YT_MAX_COMMENT_VIDEOS','6'))))
        start=datetime(self.day.year,self.day.month,self.day.day,
                       tzinfo=ZoneInfo('Asia/Karachi')).astimezone(timezone.utc)
        finish=(start+timedelta(days=1))
        fmt=lambda t:t.strftime('%Y-%m-%dT%H:%M:%SZ')
        r,state=self.get('https://www.googleapis.com/youtube/v3/search',
            params={'part':'snippet','q':'Atomos','type':'video','order':'date',
                    'publishedAfter':fmt(start),'publishedBefore':fmt(finish),
                    'maxResults':20,'key':key})
        if not r:
            self.gaps.append('YouTube official API search '+state)
            return
        try: videos=r.json().get('items',[])
        except (ValueError,AttributeError):
            self.gaps.append('YouTube API response parsing failed')
            return
        self.counts['YouTube.api_searches']+=1
        selected=[]
        for obj in videos:
            vid=(obj.get('id') or {}).get('videoId','')
            sn=obj.get('snippet') or {}
            if not re.fullmatch('[a-zA-Z0-9_-]{11}',str(vid or '')):continue
            content=sn.get('title','')+' '+sn.get('description','')
            if not BRAND.search(content):continue
            url=f'https://www.youtube.com/watch?v={vid}'
            thumb=(sn.get('thumbnails',{}).get('medium') or {}).get('url','')
            day=youtube_date_pkt(sn.get('publishedAt'))
            if day==self.date:
                video=classify(url,content,'YouTube',day,'YouTube Data API publishedAt converted to PKT',
                    sn.get('title',''),sn.get('channelTitle',''),thumb)
                if video:self.accept(video,'YouTube official API original video metadata')
            selected.append((vid,sn,thumb))
        # Watch older relevant video threads for NEW daily comments without repeating search calls.
        watch=ROOT/'data'/'youtube_watchlist.json'
        if watch.is_file():
            try:
                vids=json.loads(watch.read_text(encoding='utf-8'))
                for obj in vids[:20] if isinstance(vids,list) else []:
                    vid=obj if isinstance(obj,str) else obj.get('video_id','') if isinstance(obj,dict) else ''
                    if re.fullmatch('[a-zA-Z0-9_-]{11}',str(vid or '')) and vid not in [x[0] for x in selected]:
                        selected.append((vid,{'title':'Monitored Atomos video','channelTitle':''},''))
            except (OSError,ValueError):
                self.gaps.append('YouTube watchlist parsing failed')
        # One batch videos.list request gives source-traceable public view/like/comment
        # counts for all newly published video findings. No analytics permissions needed.
        discovered=[x[0] for x in selected if x[0]]
        if discovered:
            stats_response,stats_status=self.get('https://www.googleapis.com/youtube/v3/videos',
                params={'part':'statistics','id':','.join(dict.fromkeys(discovered[:25])),
                        'key':key})
            if stats_response:
                self.counts['YouTube.statistics_calls']+=1
                try:
                    for obj in stats_response.json().get('items',[]):
                        video_url='https://www.youtube.com/watch?v='+str(obj.get('id',''))
                        record=next((f for f in self.findings if f.url==video_url),None)
                        if record is None:continue
                        stats=obj.get('statistics') or {}
                        for response_key,metric_name in (('viewCount','views'),
                                                         ('likeCount','likes'),
                                                         ('commentCount','comments')):
                            value=stats.get(response_key)
                            if str(value or '').isdigit():
                                record.engagement[metric_name]=int(value)
                        record.engagement_source='YouTube Data API videos.list statistics'
                except (ValueError,TypeError,AttributeError):
                    self.gaps.append('YouTube public video statistics could not be parsed')
            else:self.gaps.append('YouTube statistics endpoint: '+stats_status)
        for vid,sn,thumb in selected[:max_videos]:
            url=f'https://www.youtube.com/watch?v={vid}'
            parent=next((x for x in self.findings if x.url==url),None)
            cr,cs=self.get('https://www.googleapis.com/youtube/v3/commentThreads',
                params={'part':'snippet','videoId':vid,'maxResults':100,'order':'time',
                        'textFormat':'plainText','key':key})
            if not cr:
                self.audit.append({'group':'YouTube','url':url,'stage':'comments','result':cs})
                continue
            self.counts['YouTube.comments_calls']+=1
            try:comments=cr.json().get('items',[])
            except (ValueError,AttributeError):continue
            for item in comments:
                outer=(item.get('snippet') or {}).get('topLevelComment') or {}
                cs=(outer.get('snippet') or {})
                txt=cs.get('textOriginal') or cs.get('textDisplay') or ''
                published=youtube_date_pkt(cs.get('publishedAt'))
                if parent is not None and len(parent.comments)<5:
                    parent.comments.append({'author':cs.get('authorDisplayName',''),
                                            'text':txt[:360],'date':published,
                                            'likes':cs.get('likeCount',0)})
                if published!=self.date or not BRAND.search(txt):continue
                cid=outer.get('id','')
                comment_url=url+('&lc='+quote_plus(cid) if cid else '')
                f=classify(comment_url,txt,'YouTube',published,
                           'YouTube Data API original comment publishedAt converted to PKT',
                           'Comment on: '+sn.get('title','')[:100],
                           cs.get('authorDisplayName',''),thumb,
                           {'likes':cs.get('likeCount',0),
                            'replies':(item.get('snippet') or {}).get('totalReplyCount',0)})
                if f:self.accept(f,'YouTube API original public comment')

    def accept(self, item, origin):
        if not item or not BRAND.search(item.source_excerpt):return
        if item.published_date!=self.date:
            self.counts[item.platform+'.other_dates']+=1
            return
        key=item.url.split('#')[0].lower()
        if key in self.seen:return
        self.seen.add(key)
        item.verification_note=origin
        self.findings.append(item)
        self.counts[item.platform+'.verified']+=1

    def page(self,entry):
        url=entry['url']
        r,state=self.get(url)
        group=entry['group']
        self.audit.append({'stage':'source-fetch','group':group,'url':url,'result':state,
                           'final_url':r.url if r else None})
        self.counts[group+'.source_attempts']+=1
        if not r:
            self.counts[group+'.fetch_failed']+=1
            return
        if 'html' not in (r.headers.get('content-type') or '').lower():return
        host=urlparse(r.url).hostname or ''
        if 'google.com' in host or 'bing.com' in host or 'login.' in host:
            self.counts[group+'.inaccessible']+=1;return
        soup=BeautifulSoup(r.text,'html.parser')
        if soup.find('meta',attrs={'name':'robots','content':re.compile('noindex',re.I)}):
            self.counts[group+'.noindex']+=1
            return
        title_tag=soup.find('h1') or soup.title
        title=title_tag.get_text(' ',strip=True) if title_tag else entry.get('title','')
        when=''
        evidence=''
        for field,key in [('property','article:published_time'),('itemprop','datePublished'),
                          ('name','datePublished'),('name','pubdate'),('name','citation_publication_date')]:
            m=soup.find('meta',attrs={field:key})
            if m:
                when=iso(m.get('content',''))
                if when:
                    evidence=f'Original first-party page {key}'
                    break
        for tag in soup.select('script[type="application/ld+json"]')[:8]:
            if when:break
            try:
                ld=json.loads(tag.get_text())
                objs=ld if isinstance(ld,list) else [ld]
                for obj in objs:
                    if not isinstance(obj,dict):continue
                    when=iso(obj.get('datePublished') or obj.get('uploadDate'))
                    if when:
                        evidence='Original first-party JSON-LD datePublished'
                        break
            except (ValueError,TypeError):continue
        author=''
        by=soup.find('meta',attrs={'name':'author'})
        if by:author=by.get('content','')
        if not author:
            for node in soup.select('script[type="application/ld+json"]')[:8]:
                try:
                    doc=json.loads(node.get_text())
                    for record in doc if isinstance(doc,list) else [doc]:
                        if not isinstance(record,dict):continue
                        person=record.get('author',{})
                        if isinstance(person,list):person=person[0] if person else {}
                        if isinstance(person,dict) and person.get('name'):
                            author=str(person['name'])[:100]
                            break
                        if isinstance(person,str):author=person[:100];break
                except (ValueError,TypeError):pass
                if author:break
        publisher=''
        name_tag=soup.find('meta',attrs={'property':'og:site_name'})
        if name_tag:publisher=str(name_tag.get('content') or '')[:100]
        img=''
        m=soup.find('meta',attrs={'property':'og:image'})
        if not m:m=soup.find('meta',attrs={'name':'twitter:image'})
        if m:img=urljoin(r.url,m.get('content',''))
        for t in soup(['script','style','noscript','svg','nav','footer','header']):t.decompose()
        area=soup.find('article') or soup.find('main') or soup.body or soup
        content=area.get_text(' ',strip=True)[:50000]
        # Read original-source body, never treat a search snippet or a crawl date as source proof.
        result=classify(r.url,content,group,when,evidence,title,author,img)
        if result: result.publisher=publisher or (urlparse(r.url).hostname or '')
        if group=='Retailers' and result:
            # A checked product/offer is market data, never a newly published social post.
            path=urlparse(r.url).path.lower().rstrip('/')
            if path in ('','/','/shop','/category/memory-cards-29') or '/search' in path:
                self.audit.append({'group':group,'stage':'retail-skip','url':r.url,
                                   'reason':'Brand/category homepage, not an individual offer'})
                return
            price=PRICE.search(result.source_excerpt)
            result.status='retail'
            result.sentiment='Not applicable'
            result.published_date=''
            result.reference_date=self.date
            result.date_evidence='Listing observed '+self.date+'; this is NOT a publishing date'
            result.verification_note='Product/retail source observed on report date; prices and availability may change.'
            result.details='Visible price near brand entry: '+price.group(0) if price else 'No reliable individual listing price established'
            if not any(x.url==result.url for x in self.retail):
                self.retail.append(result)
                self.counts['Retailers.observations']+=1
            return
        if not result:
            self.counts[group+'.no_brand_original']+=1;return
        if when==self.date:
            self.accept(result,'Original public page')
        else:
            self.counts[group+'.not_dated_today']+=1
            self.audit.append({'stage':'unverified-date','group':group,'url':r.url,'source_date':when,
                               'title':title[:140]})
            if not when:
                result.status='unverified'
                result.verification_note='Original page mentions Atomos but no original publish date was proven.'
                if not any(x.url==result.url for x in self.unverified):
                    self.unverified.append(result)
            elif (self.day-timedelta(days=5)).isoformat()<=when<self.date:
                result.status='older'
                result.verification_note="Original page has a previous-five-day publication date, not today's."
                if not any(x.url==result.url for x in self.older):
                    self.older.append(result)

    def download_images(self,prefix='source'):
        from PIL import Image as PILImage, ImageOps
        from io import BytesIO
        for f in self.findings+self.unverified[:6]+self.older[:6]+self.retail[:5]:
            if self.images>=self.image_limit:break
            if f.image_files:continue
            u=f.image_url
            if not valid_url(u):continue
            r,status=self.get(u)
            if not r or not (r.headers.get('Content-Type') or '').lower().startswith('image/'):
                self.audit.append({'stage':'image','url':u,'result':status if not r else 'not image'})
                continue
            try:
                im=PILImage.open(BytesIO(r.content))
                im=ImageOps.exif_transpose(im)
                im.thumbnail((850,600))
                if im.width<80 or im.height<60:continue
                if im.mode not in ('RGB','L'):im=im.convert('RGB')
                dest=self.root/(prefix+'_'+str(self.images+1).zfill(3)+'.jpg')
                im.save(dest,format='JPEG',quality=80,optimize=True)
                f.image_files=[dest.relative_to(ROOT).as_posix()]
                self.images+=1
                self.audit.append({'stage':'image','url':u,'result':'cached attributed thumbnail',
                                   'asset':str(dest.relative_to(ROOT))})
            except Exception as exc:
                self.audit.append({'stage':'image','url':u,'result':str(exc)[:100]})

    def run(self):
        self.youtube()
        self.search()
        # Round-robin source fetching: no single platform may consume the budget.
        queues={group:[] for group in GROUPS}
        for e in self.candidates.values():
            queues.setdefault(e['group'],[]).append(e)
        per_group=max(1,int(os.getenv('MAX_SOURCE_PAGES_PER_GROUP','6')))
        for round_index in range(per_group):
            for group in GROUPS:
                if self.fetched>=self.page_limit:break
                entries=queues.get(group,[])
                if round_index>=len(entries):continue
                e=entries[round_index]
                if e['url'] in self.seen:continue
                self.fetched+=1
                self.page(e)
            if self.fetched>=self.page_limit:break
        self.download_images()
        verified=[f for f in self.findings if f.published_date==self.date and f.status=='verified']
        coverage=[]
        for group in GROUPS:
            q=self.counts[group+'.queries']
            api=self.counts[group+'.api_searches']
            attempted=self.counts[group+'.source_attempts']
            verified_count=self.counts[group+'.verified']
            failed=self.counts[group+'.fetch_failed']
            success=self.counts[group+'.successful_queries']
            coverage.append(Coverage(platform=group,
                checked=bool(attempted or api),
                summary=(f'{q} indexed query attempt(s), {success} index response(s), '
                         f'{attempted} original source fetch(es), {failed} inaccessible; '
                         f'{verified_count} exact-day source-verified mention(s). '
                         'A blocked index or missing official API is not a negative search result.')))
        headline=(f'{len(verified)} directly dated Atomos mention(s) established for {self.date} '
                 f'from {self.fetched} first-party page attempts; previous five days are listed separately.')
        status='Python public-source monitoring'
        if not self.fetched and not self.counts['YouTube.api_searches']:
            status='INCOMPLETE - No original source pages checked'
            headline='Search indexes returned no usable original sources. The 30 October activity level is unknown, not confirmed zero.'
            self.gaps.append('No source-page evidence could be checked with current index/API access. Configure provider credentials.')
        report=ResearchReport(report_date=self.date,status=status,
            headline=headline,today_findings=verified,unverified_leads=self.unverified[:15],
            older_leads=self.older[:20],retail_observations=self.retail[:15],coverage=coverage,
            visibility_gaps=self.gaps+[
              'Public indexes do not expose all posts and comments; private/login-only content is not collected.',
              'No result does not establish no brand activity on a platform.'],
            methodology=(f'Python collector: {self.queries} public search query attempts, '
                         f'{self.fetched} original-page attempts, '
                         f'{self.images} attributable image thumbnails; YouTube Data API when connected, no Reddit OAuth. '
                         'New verified posts require original source dates and direct Atomos text.'))
        return report,[{'scope':'Python public source audit','data':self.audit,
                        'counts':dict(self.counts),'search_queries':self.queries,
                        'original_pages_attempted':self.fetched,'cached_images':self.images,
                        'undated_brand_sources':len(self.unverified),
                        'previous_five_day_brand_sources':len(self.older)}]
def collect_day(day):
    return PublicResearch(day).run()


def _discover_original_preview(engine, item):
    """Best-effort public OG post-image preview; never borrow unrelated Google images."""
    if not valid_url(item.url):return ''
    from urllib.parse import urljoin, urlparse
    r,state=engine.get(item.url,timeout=10)
    if not r or 'html' not in (r.headers.get('content-type') or '').lower():
        engine.audit.append({'stage':'post-image-discovery','url':item.url,'status':state})
        return ''
    soup=BeautifulSoup(r.text,'html.parser')
    title=soup.title.get_text(' ',strip=True) if soup.title else ''
    # Generic login, Facebook wall, or sign-in HTML is not evidence of a post photo.
    if any(phrase in title.lower() for phrase in ('log in', 'sign in', 'login required')):
        engine.audit.append({'stage':'post-image-discovery','url':item.url,
                             'status':'login page; no image attributed'})
        return ''
    image=''
    for tag_type,name in (('property','og:image'),('name','twitter:image')):
        tag=soup.find('meta',attrs={tag_type:name})
        if tag and valid_url(urljoin(r.url,tag.get('content',''))):
            image=urljoin(r.url,tag.get('content',''))
            break
    if not image:return ''
    # Reject site logo/avatar images likely unrelated to specific source material.
    if any(word in image.lower() for word in ('logo','avatar','placeholder','icon-default')):
        return ''
    engine.audit.append({'stage':'post-image-discovery','url':item.url,
                         'status':'original page advertised source preview',
                         'image_url':image})
    item.image_context='Public original-post preview from source og:image / twitter:image metadata.'
    item.image_credit_url=item.url
    return image

def cache_historical_images(report):
    """Bounded official/public post thumbnails for every platform's source card."""
    engine=PublicResearch(report.report_date)
    items=(report.today_findings+report.historical_findings+
           report.retail_observations+report.historical_retail+
           report.unverified_leads)
    max_images=min(14,int(os.getenv('MAX_REPORT_IMAGES','10')))
    max_preview_checks=min(18,int(os.getenv('MAX_POST_PREVIEW_CHECKS','10')))
    engine.image_limit=max_images
    preview_checks=0
    candidates=[]
    for item in items:
        if item.image_files:continue
        if not item.image_url and item.images:
            candidate=item.images[0]
            if valid_url(candidate) and not candidate.lower().endswith(('.html','.htm')):
                item.image_url=candidate
        if not item.image_url and preview_checks<max_preview_checks:
            preview_checks+=1
            item.image_url=_discover_original_preview(engine,item)
        if item.image_url:candidates.append(item)
    engine.findings=candidates
    engine.download_images(prefix='original')
    return {'cached_report_images':engine.images,'original_post_preview_checks':preview_checks,
            'image_audit':engine.audit}
