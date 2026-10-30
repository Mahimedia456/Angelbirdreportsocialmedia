"""Create a static GitHub Pages website without changing any report PDF."""
from __future__ import annotations
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "_site"
SOURCE = ROOT / "website"
PDF_PATTERN = re.compile(r"Angelbird-Social-Monitoring-(\d{4}-\d{2}-\d{2})(-DEMO)?\.pdf$", re.I)

PERIOD_NAME=re.compile(r'Angelbird-Social-Monitoring-(Weekly|Monthly)-(\\d{4}-\\d{2}-\\d{2})_to_(\\d{4}-\\d{2}-\\d{2})\\.pdf -> list[dict]:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)
    for filename in ("index.html", "styles.css", "app.js"):
        shutil.copy2(SOURCE / filename, OUTPUT / filename)
    (OUTPUT / ".nojekyll").write_text("", encoding="utf-8")
    reports = []
    for source in sorted((ROOT / "reports").glob("*/*/*.pdf")):
        match = PDF_PATTERN.fullmatch(source.name)
        if not match:
            period=PERIOD_NAME.fullmatch(source.name)
            if not period:continue
            kind,start,end=period.groups()
            year,month,_=end.split('-')
            if source.parent.name!=month or source.parent.parent.name!=year:continue
            rel=source.relative_to(ROOT)
            destination=OUTPUT/rel
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,destination)
            reports.append({'id':kind.lower()+'-'+start+'-'+end,'date':end,'month':year+'-'+month,
                            'type':kind.lower(),'start':start,'end':end,'name':source.name,
                            'demo':False,'path':rel.as_posix()})
            continue
        day, demo = match.groups()
        year, month, _ = day.split("-")
        if source.parent.name != month or source.parent.parent.name != year:
            continue
        rel = source.relative_to(ROOT)
        destination = OUTPUT / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        reports.append({"id": day + ("-DEMO" if demo else ""), "date": day,
                        "month": year + "-" + month, "name": source.name,
                        "type": "daily", "demo": bool(demo), "path": rel.as_posix()})
    reports.sort(key=lambda r: (r["date"], not r["demo"]), reverse=True)
    (OUTPUT / "reports-index.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
    print(f"Website built: {len(reports)} PDF reports; output={OUTPUT}")
    return reports

if __name__ == "__main__":
    build()
,re.I)

def build() -> list[dict]:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)
    for filename in ("index.html", "styles.css", "app.js"):
        shutil.copy2(SOURCE / filename, OUTPUT / filename)
    (OUTPUT / ".nojekyll").write_text("", encoding="utf-8")
    reports = []
    for source in sorted((ROOT / "reports").glob("*/*/*.pdf")):
        match = PDF_PATTERN.fullmatch(source.name)
        if not match:
            continue
        day, demo = match.groups()
        year, month, _ = day.split("-")
        if source.parent.name != month or source.parent.parent.name != year:
            continue
        rel = source.relative_to(ROOT)
        destination = OUTPUT / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        reports.append({"id": day + ("-DEMO" if demo else ""), "date": day,
                        "month": year + "-" + month, "name": source.name,
                        "demo": bool(demo), "path": rel.as_posix()})
    reports.sort(key=lambda r: (r["date"], not r["demo"]), reverse=True)
    (OUTPUT / "reports-index.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
    print(f"Website built: {len(reports)} PDF reports; output={OUTPUT}")
    return reports

if __name__ == "__main__":
    build()
