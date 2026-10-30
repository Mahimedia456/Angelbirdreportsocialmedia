"""Public-source Angelbird monitoring. Python does collection; no OpenAI calls.

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
from pathlib import Path
from urllib.parse import quote_plus, urlparse, urljoin, parse_qs
from xml.etree import ElementTree
import requests
from bs4 import BeautifulSoup
from .schema import Finding, Coverage, ResearchReport

ROOT=Path(__file__).resolve().parents[1]
BRAND=re.compile(r'\bangelbird\b|\bav[\s-]?pro\b',re.I)
NEG=re.compile(r'overheat|hotter|failure|failed|corrupt|crash|broken|problem|error|not working|complain|recording stop',re.I)
POS=re.compile(r'recommend|excellent|best|great|reliable|fast|impressive|love|superb|works well',re.I)
PRODUCT=re.compile(r'(Angelbird\s+.{0,45}?(?:CFexpress|microSD|SD\s*card|card reader|SSD|AV\s*PRO)|AV\s*PRO[^.,;\n]{0,60})',re.I)
DOMAINS={'reddit.com':'Reddit','youtube.com':'YouTube','youtu.be':'YouTube',
 'facebook.com':'Facebook','instagram.com':'Instagram','linkedin.com':'LinkedIn',
 'dpreview.com':'Camera forums','eoshd.com':'Camera forums','newsshooter.com':'Industry articles',
 'cined.com':'Industry articles','petapixel.com':'Industry articles',
 'bhphotovideo.com':'Retailers','adorama.com':'Retailers','cvp.com':'Retailers'}
GROUPS={
 'Reddit':['site:reddit.com "Angelbird" {date}','site:reddit.com "Angelbird" "card" {month} {year}'],
 'YouTube':['site:youtube.com/watch "Angelbird" {date}','site:youtube.com "Angelbird" {month} {year}'],
 'Facebook':['site:facebook.com "Angelbird" {date}'],
 'Instagram':['site:instagram.com "Angelbird" {date}'],
 'LinkedIn':['site:linkedin.com/posts "Angelbird" {date}'],
 'Camera forums':['site:dpreview.com/forums "Angelbird" {month} {year}',
                  '"Angelbird" "CFexpress" camera forum {date}'],
 'Industry articles':['site:newsshooter.com "Angelbird" {month} {year}',
                      'site:cined.com "Angelbird" {month} {year}',
                      '"Angelbird" camera review {date}'],
 'Retailers':['site:bhphotovideo.com "Angelbird" AV PRO {month} {year}',
              'site:cvp.com "Angelbird" CFexpress {month} {year}'],
}

def iso(value):
    v=str(value or '').strip()
    m=re.search(r'\b(20\d\d-\d\d-\d\d)\b',v)
    if m:
        try:return date.fromisoformat(m.group(1)).isoformat()
        except ValueError:pass
    for fmt in ('%a, %d %b %Y %H:%M:%S %z','%d %b %Y','%b %d, %Y','%B %d, %Y','%d %B %Y'):
        try:return datetime.strptime(v[:35],fmt).date().isoformat()
        except ValueError:pass
    return ''

def valid_url(url):
    u=urlparse(str(url or ''))
    return u.scheme in ('http','https') and bool(u.hostname)

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
        self.s.headers.update({'User-Agent':'AngelbirdSocialMonitoring/2.1 (public research and attribution)'})
        self.audit=[]
        self.candidates={}
        self.findings=[]
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
        self.candidates[url]={**item,'url':url,'group':group,'discovery':discovery,'search_date':search_date}
        self.counts[group+'.candidates']+=1

    def index_query(self,group,query):
        self.queries+=1
        found=0
        # Bing public RSS plus optional commercial Brave Search key. Neither is claimed as direct source proof.
        key=os.getenv('BRAVE_SEARCH_API_KEY','')
        if key:
            response,state=self.get('https://api.search.brave.com/res/v1/web/search',
                params={'q':query,'count':12},headers={'X-Subscription-Token':key})
            if response:
                try:
                    for item in response.json().get('web',{}).get('results',[]):
                        self.add({'url':item.get('url',''),'title':item.get('title',''),
                                  'snippet':BeautifulSoup(item.get('description',''),'html.parser').get_text(' ',strip=True)},
                                 group,'Brave index')
                        found+=1
                except ValueError:state='Invalid search API response'
            else:self.gaps.append(f'{group}: Brave search {state}')
        else:
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
                                 group,'Bing RSS',item.findtext('pubDate') or '')
                        found+=1
                except ElementTree.ParseError:state='Unparseable index feed'
            if not response or state!='OK':self.gaps.append(f'{group}: Bing index {state}')
        self.audit.append({'group':group,'stage':'search','query':query,'results':found,
                           'index':'Brave' if key else 'Bing RSS'})
        self.counts[group+'.queries']+=1

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
                params={'q':f'Angelbird when:1d after:{self.date} before:{self.end}','hl':'en'})
            if response:
                try:
                    rss=ElementTree.fromstring(response.text)
                    for item in rss.findall('.//item'):
                        self.add({'url':item.findtext('link'),'title':item.findtext('title'),
                                  'snippet':item.findtext('description')},'Industry articles','Google News RSS')
                except ElementTree.ParseError:self.gaps.append('Google News feed parsing failed')
            else:self.gaps.append('Google News index: '+state)
        return len(self.candidates)

    def youtube(self):
        key=os.getenv('YOUTUBE_API_KEY','').strip()
        if not key:
            self.gaps.append('YouTube: Data API key not configured; direct comments unavailable')
            return
        r,state=self.get('https://www.googleapis.com/youtube/v3/search',
            params={'part':'snippet','q':'Angelbird','type':'video','order':'date',
                    'publishedAfter':self.date+'T00:00:00Z','publishedBefore':self.end+'T00:00:00Z',
                    'maxResults':25,'key':key})
        if not r:
            self.gaps.append('YouTube API search '+state);return
        try:videos=r.json().get('items',[])
        except ValueError:return
        self.counts['YouTube.api_searches']+=1
        for obj in videos[:12]:
            vid=(obj.get('id') or {}).get('videoId')
            sn=obj.get('snippet') or {}
            if not vid:continue
            url=f'https://www.youtube.com/watch?v={vid}'
            content=sn.get('title','')+' '+sn.get('description','')
            thumb=(sn.get('thumbnails',{}).get('medium') or {}).get('url','')
            parent=None
            if BRAND.search(content):
                f=classify(url,content,'YouTube',iso(sn.get('publishedAt')),
                           'YouTube Data API video publishedAt',sn.get('title',''),
                           sn.get('channelTitle',''),thumb)
                if f:
                    self.accept(f,'YouTube API video')
                    parent=f if f.published_date==self.date else None
            cr,cs=self.get('https://www.googleapis.com/youtube/v3/commentThreads',
                params={'part':'snippet','videoId':vid,'maxResults':100,'order':'time',
                        'textFormat':'plainText','key':key})
            if not cr:
                self.audit.append({'group':'YouTube','url':url,'stage':'comments','result':cs})
                continue
            self.counts['YouTube.comments_calls']+=1
            try:comments=cr.json().get('items',[])
            except ValueError:continue
            for item in comments:
                outer=(item.get('snippet') or {}).get('topLevelComment') or {}
                cs=(outer.get('snippet') or {})
                txt=cs.get('textOriginal') or cs.get('textDisplay') or ''
                published=iso(cs.get('publishedAt'))
                if parent is not None and len(parent.comments)<6:
                    parent.comments.append({'author':cs.get('authorDisplayName',''),
                                            'text':txt[:400], 'date':published,
                                            'likes':cs.get('likeCount',0)})
                if not BRAND.search(txt):continue
                comment_url=url+'&lc='+quote_plus(outer.get('id',''))
                f=classify(comment_url,txt,'YouTube',published,'YouTube Data API comment publishedAt',
                           'YouTube video comment: '+sn.get('title','')[:95],
                           cs.get('authorDisplayName',''),thumb,
                           {'likes':cs.get('likeCount',0),'replies':(item.get('snippet') or {}).get('totalReplyCount',0)})
                if f:self.accept(f,'YouTube API original comment')

    def reddit(self):
        cid=os.getenv('REDDIT_CLIENT_ID','')
        secret=os.getenv('REDDIT_CLIENT_SECRET','')
        if not(cid and secret):
            self.gaps.append('Reddit OAuth not configured; direct comment thread access not guaranteed')
            return
        try:
            r=self.s.post('https://www.reddit.com/api/v1/access_token',
                auth=(cid,secret),data={'grant_type':'client_credentials'},
                timeout=12,headers={'User-Agent':os.getenv('REDDIT_USER_AGENT',
                   'script:angelbird.monitoring:v2.1 (public-source research)')})
            r.raise_for_status()
            token=r.json().get('access_token')
            if not token:raise ValueError('No Reddit access token')
        except (requests.RequestException,ValueError) as exc:
            self.gaps.append('Reddit OAuth failed: '+str(exc)[:100]);return
        h={'Authorization':'bearer '+token,
           'User-Agent':os.getenv('REDDIT_USER_AGENT',
                    'script:angelbird.monitoring:v2.1 (public-source research)')}
        r,state=self.get('https://oauth.reddit.com/search',
            params={'q':'Angelbird','sort':'new','t':'week','limit':'60','type':'link'},
            headers=h)
        if not r:
            self.gaps.append('Reddit official search '+state);return
        posts=(r.json().get('data') or {}).get('children') or []
        self.counts['Reddit.api_posts']+=len(posts)
        for e in posts[:18]:
            p=e.get('data') or {}
            post_date=datetime.fromtimestamp(p.get('created_utc',0),tz=timezone.utc).date().isoformat()
            url='https://www.reddit.com'+p.get('permalink','')
            body=p.get('title','')+' '+p.get('selftext','')
            parent=None
            if BRAND.search(body):
                f=classify(url,body,'Reddit',post_date,'Reddit OAuth created_utc',
                    p.get('title',''),p.get('author',''),'',{'score':p.get('score',0),
                    'comments':p.get('num_comments',0)})
                if f:
                    self.accept(f,'Reddit OAuth post')
                    parent=f if f.published_date==self.date else None
            if int(p.get('num_comments',0))<=0:continue
            thread,ts=self.get('https://oauth.reddit.com'+p.get('permalink',''),
                params={'limit':'70','depth':'2'},headers=h)
            if not thread:
                self.audit.append({'group':'Reddit','url':url,'stage':'comments','result':ts});continue
            try:tree=thread.json()
            except ValueError:continue
            if not isinstance(tree,list) or len(tree)<2:continue
            for e in (tree[1].get('data') or {}).get('children') or []:
                c=e.get('data') or {}
                if not isinstance(c,dict):continue
                if parent is not None and len(parent.comments)<6:
                    parent.comments.append({'author':c.get('author',''),
                                            'text':str(c.get('body',''))[:400],
                                            'date':datetime.fromtimestamp(c.get('created_utc',0),tz=timezone.utc).date().isoformat(),
                                            'score':c.get('score',0)})
                if not BRAND.search(c.get('body','')):continue
                cdate=datetime.fromtimestamp(c.get('created_utc',0),tz=timezone.utc).date().isoformat()
                cid=c.get('id','')
                curl=url.rstrip('/')+'/'+cid+'/'
                f=classify(curl,c.get('body',''),'Reddit',cdate,'Reddit OAuth comment created_utc',
                    'Reddit comment in '+p.get('title','')[:100],c.get('author',''),'',{'score':c.get('score',0)})
                if f:self.accept(f,'Reddit OAuth original comment')

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
        img=''
        m=soup.find('meta',attrs={'property':'og:image'})
        if m:img=urljoin(r.url,m.get('content',''))
        for t in soup(['script','style','noscript','svg','nav','footer','header']):t.decompose()
        area=soup.find('article') or soup.find('main') or soup.body or soup
        content=area.get_text(' ',strip=True)[:50000]
        # Read original-source body, never treat a search snippet or a crawl date as source proof.
        result=classify(r.url,content,group,when,evidence,title,author,img)
        if not result:
            self.counts[group+'.no_brand_original']+=1;return
        if when==self.date:
            self.accept(result,'Original public page')
        else:
            self.counts[group+'.not_dated_today']+=1
            self.audit.append({'stage':'unverified-date','group':group,'url':r.url,'source_date':when,
                               'title':title[:140]})

    def download_images(self):
        from PIL import Image as PILImage, ImageOps
        from io import BytesIO
        for f in self.findings:
            if self.images>=self.image_limit:break
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
                dest=self.root/('source_'+str(self.images+1).zfill(3)+'.jpg')
                im.save(dest,format='JPEG',quality=80,optimize=True)
                f.image_files=[dest.relative_to(ROOT).as_posix()]
                self.images+=1
                self.audit.append({'stage':'image','url':u,'result':'cached attributed thumbnail',
                                   'asset':str(dest.relative_to(ROOT))})
            except Exception as exc:
                self.audit.append({'stage':'image','url':u,'result':str(exc)[:100]})

    def run(self):
        self.youtube()
        self.reddit()
        self.search()
        for e in list(self.candidates.values())[:self.page_limit]:
            if e['url'] in self.seen:continue
            self.fetched+=1
            self.page(e)
        self.download_images()
        verified=[f for f in self.findings if f.published_date==self.date and f.status=='verified']
        coverage=[]
        for group in GROUPS:
            q=self.counts[group+'.queries']
            api=self.counts[group+'.api_searches']+self.counts[group+'.api_posts']
            attempted=self.counts[group+'.source_attempts']
            verified_count=self.counts[group+'.verified']
            failed=self.counts[group+'.fetch_failed']
            coverage.append(Coverage(platform=group,
                checked=bool(q or api),
                summary=(f'{q} indexed query(s); {attempted} original source fetch(es), '
                         f'{failed} inaccessible, {verified_count} exact-day source-verified mention(s). '
                         'Indexed search is not proof of exhaustive platform coverage.')))
        headline=(f'{len(verified)} direct Angelbird mention(s) independently dated {self.date} '
                 f'from accessible public sources. Source coverage and access limitations follow.')
        report=ResearchReport(report_date=self.date,status='Python public-source monitoring',
            headline=headline,today_findings=verified,coverage=coverage,
            visibility_gaps=self.gaps+[
              'Public indexes do not expose all posts and comments; private/login-only content is not collected.',
              'No result does not establish no brand activity on a platform.'],
            methodology=(f'Python collector: {self.queries} public search query attempts, '
                         f'{self.fetched} original-page attempts, '
                         f'{self.images} attributable image thumbnails; optional Reddit/YouTube APIs. '
                         'New verified posts require original source dates and direct Angelbird text.'))
        return report,[{'scope':'Python public source audit','data':self.audit,
                        'counts':dict(self.counts),'search_queries':self.queries,
                        'original_pages_attempted':self.fetched,'cached_images':self.images}]
def collect_day(day):
    return PublicResearch(day).run()
