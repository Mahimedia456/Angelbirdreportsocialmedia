"""Enrich retailer evidence from original public product pages.

Original-page photographs are explicitly identified as product photos, never user posts.
Do not rewrite or assert historical indexed reference prices as current verified prices.
"""
import json
from pathlib import Path
from urllib.parse import urlsplit, urljoin
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
ALLOWED=('cvp.com','bhphotovideo.com')
def permitted(url):
    try:
        u=urlsplit(url)
        return u.scheme=='https' and bool(u.hostname) and any(
            u.hostname==host or u.hostname.endswith('.'+host) for host in ALLOWED)
    except Exception:return False

def main():
    updated=0;accessible=0;photos=0;errors=[]
    for path in sorted((ROOT/'data').glob('reference_retail_*.json')):
        record=json.loads(path.read_text(encoding='utf-8'))
        changed=False
        for item in record.get('retail_observations',[]):
            url=item.get('url','')
            if not permitted(url):continue
            try:
                response=requests.get(url,timeout=12,allow_redirects=False,
                                      headers={'User-Agent':'Mozilla/5.0 PublicEvidenceReporter/1.0'})
                if response.status_code!=200 or not response.text:
                    errors.append({'source':url,'http':response.status_code});continue
                soup=BeautifulSoup(response.text[:1500000],'html.parser')
                title=soup.title.get_text(' ',strip=True) if soup.title else ''
                brand='Atomos' if 'atomos' in str(ROOT).lower() else 'Angelbird'
                if brand.lower() not in title.lower() and brand.lower() not in soup.get_text(' ',strip=True)[:5000].lower():
                    errors.append({'source':url,'error':'brand not found'});continue
                accessible+=1
                item['source_accessed_at_pkt']=datetime.now(ZoneInfo('Asia/Karachi')).isoformat(timespec='seconds')
                item['original_page_access']='Original product HTML accessible; brand matched'
                changed=True
                if not item.get('image_url'):
                    tag=soup.find('meta',attrs={'property':'og:image'}) or soup.find('meta',attrs={'name':'twitter:image'})
                    src=urljoin(url,tag.get('content','')) if tag else ''
                    if src.startswith('https://') and urlsplit(src).hostname:
                        item['image_url']=src
                        item['image_context']='Retail product photo, not original social post image'
                        photos+=1
            except requests.RequestException as e:
                errors.append({'source':url,'error':str(e)[:100]})
        if changed:
            path.write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
            updated+=1
    audit={'reference_files_updated':updated,'original_product_pages_checked':accessible,
           'retailer_product_photos_linked':photos,'errors':errors}
    (ROOT/'reports').mkdir(exist_ok=True)
    (ROOT/'reports'/'retail-source-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(audit))
if __name__=='__main__':main()
