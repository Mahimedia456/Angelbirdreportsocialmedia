"""Discover the publicly listed brand catalog without hardcoded model lists.

Source is the manufacturer's current public shop/categories; NOT historical
October stock, independent social sentiment, or proof of exhaustive private SKUs.
All reachable product URLs/variants are retained, with a transparent crawl audit.
"""
import json, re
from collections import deque
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin,urlsplit,urlunsplit
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
ATOMOS='smratomos' in str(ROOT).lower()
BRAND='Atomos' if ATOMOS else 'Angelbird'
DOMAIN='www.atomos.com' if ATOMOS else 'www.angelbird.com'
BASE='https://'+DOMAIN
SEEDS=[BASE+'/shop/'] if ATOMOS else [BASE+'/',BASE+'/category/memory-cards-29/']
MAX_LIST_PAGES=100

def absolute(href,current):
    url=urljoin(current,href or '')
    sp=urlsplit(url)
    if sp.scheme!='https' or sp.hostname not in (DOMAIN,DOMAIN.removeprefix('www.')):return ''
    return urlunsplit((sp.scheme,sp.netloc,sp.path,sp.query,''))

def list_page(url):
    path=urlsplit(url).path.lower()
    if ATOMOS:
        return path.startswith(('/shop/','/product-category/')) or path=='/shop'
    return path=='/' or path.startswith(('/category/','/categories/'))

def product_page(url):
    path=urlsplit(url).path.lower()
    return path.startswith('/product/') if ATOMOS else path.startswith('/prod/')

def fallback_name(url):
    text=urlsplit(url).path.rstrip('/').split('/')[-1]
    return re.sub(r'[-_]+',' ',text).strip().title()

def main():
    pending=deque(SEEDS);seen=set();products={};errors=[];pages=[]
    session=requests.Session()
    session.headers.update({'User-Agent':'Mozilla/5.0 (compatible; SourceProvenanceCatalog/1.0)'})
    while pending and len(seen)<MAX_LIST_PAGES:
        url=pending.popleft()
        if url in seen or not list_page(url):continue
        seen.add(url)
        try:
            r=session.get(url,timeout=15,allow_redirects=False)
            if r.status_code!=200 or 'html' not in r.headers.get('content-type','').lower():
                errors.append({'url':url,'status':r.status_code});continue
            soup=BeautifulSoup(r.text[:3000000],'html.parser')
            pages.append(url)
            for a in soup.select('a[href]'):
                dest=absolute(a.get('href'),url)
                if not dest:continue
                if product_page(dest):
                    label=(a.get('title') or a.get('aria-label') or a.get_text(' ',strip=True)).strip()
                    if len(label)<6 or label.lower().startswith(('add to','out of stock','buy now','select options','view product')):
                        parent=a.find_parent(['li','article','section','div'])
                        if parent:
                            heading=parent.find(['h2','h3','h4'])
                            label=heading.get_text(' ',strip=True) if heading else ''
                    if not label or len(label)<6:label=fallback_name(dest)
                    name=re.sub(r'\s+',' ',label)[:190]
                    if dest not in products:
                        products[dest]={'title':name,'url':dest,'discovered_from':url,
                                        'catalog_status':'public manufacturer listing - current snapshot'}
                    elif len(name)>len(products[dest]['title']) and len(name)<180:
                        products[dest]['title']=name
                elif list_page(dest) and dest not in seen and dest not in pending:
                    # Pagination and category links are surfaced by the official shop.
                    pending.append(dest)
        except requests.RequestException as e:
            errors.append({'url':url,'error':str(e)[:130]})
    now=datetime.now(ZoneInfo('Asia/Karachi')).isoformat(timespec='seconds')
    payload={'brand':BRAND,'source':'Official manufacturer public category/shop pages',
             'observed_at_pkt':now,'historical_price_assertion':False,
             'official_catalog_items':len(products),'list_pages_checked':len(pages),
             'truncated_page_budget':bool(pending),'pages':pages,'errors':errors,
             'products':sorted(products.values(),key=lambda x:(x['title'].lower(),x['url']))}
    dest=ROOT/'data'/'official_catalog_latest.json'
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'brand':BRAND,'products':len(products),'pages':len(pages),
                      'errors':len(errors),'truncated':bool(pending)}))
if __name__=='__main__':main()
