"""Best-effort public image cache for monthly archived evidence.

Only URLs explicitly supplied as source media evidence are considered.
No HTML page scraping, private accounts, login workarounds, or stock substitutions.
"""
import argparse, hashlib, json, io
from pathlib import Path
from urllib.parse import urlsplit
import requests
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
def eligible(url):
    try:
        u=urlsplit(url)
        if u.scheme!='https' or not u.hostname:return False
        host=u.hostname.lower()
        if host in ('localhost',) or host.endswith(('.local','.internal')):return False
        if host.startswith(('127.','10.','192.168.','169.254.')):return False
        # Only direct image resources, never social HTML/login/auth endpoints.
        return u.path.lower().endswith(('.jpg','.jpeg','.png','.webp'))
    except Exception:return False

def main():
    p=argparse.ArgumentParser();p.add_argument('--period',default='2026-10')
    a=p.parse_args();count=0;failed=0;skipped=0;updated=[]
    base=ROOT/'assets'/'periodic-source-images'/a.period
    for file in sorted((ROOT/'data').glob('reference_*.json')):
        try:doc=json.loads(file.read_text(encoding='utf-8'))
        except (OSError,ValueError):continue
        changed=False
        for item in doc.get('findings',[]):
            if not isinstance(item,dict):continue
            urls=([item.get('image_url')] if item.get('image_url') else [])+list(item.get('images') or [])
            current=list(item.get('image_files') or [])
            for url in urls[:5]:
                if not isinstance(url,str) or not eligible(url):skipped+=1;continue
                hashval=hashlib.sha256(url.encode()).hexdigest()[:22]
                rel=Path('assets')/'periodic-source-images'/a.period/(hashval+'.jpg')
                dest=ROOT/rel
                if dest.is_file():
                    if rel.as_posix() not in current:current.append(rel.as_posix());changed=True
                    continue
                try:
                    res=requests.get(url,timeout=12,headers={'User-Agent':'Mozilla/5.0 AttributedPublicImageArchive/1.0'},allow_redirects=False,stream=True)
                    res.raise_for_status()
                    if 'image/' not in res.headers.get('Content-Type','').lower():failed+=1;continue
                    data=b''
                    for chunk in res.iter_content(65536):
                        data+=chunk
                        if len(data)>5_000_000:break
                    if len(data)>5_000_000:failed+=1;continue
                    with Image.open(io.BytesIO(data)) as im:
                        im.verify()
                    with Image.open(io.BytesIO(data)) as im:
                        if im.width<96 or im.height<96:skipped+=1;continue
                        im.thumbnail((1100,1100))
                        if im.mode not in ('RGB','L'):im=im.convert('RGB')
                        dest.parent.mkdir(parents=True,exist_ok=True)
                        im.save(dest,'JPEG',quality=81,optimize=True)
                    current.append(rel.as_posix());changed=True;count+=1
                except Exception:failed+=1
            if changed:item['image_files']=current
        if changed:
            file.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
            updated.append(str(file.relative_to(ROOT)))
    audit={'images_cached':count,'source_fetch_failures':failed,'ineligible_media_urls':skipped,'archives_updated':updated}
    (ROOT/'reports'/'image-cache-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(audit))
if __name__=='__main__':main()
