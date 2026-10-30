"""Deterministic final October archive render: existing validated source JSON only.

No web/API calls, no mutation of source JSON or original cached media.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from pypdf import PdfReader
from src.schema import ResearchReport
from src.pdf_report_v2 import render_pdf

ROOT=Path(__file__).resolve().parents[1]
BRAND="Atomos" if ROOT.name.lower()=="smratomos" else "Angelbird"
BASE="2026-10"
OUT=ROOT/"reports"/"2026"/"10"

def json_file(day):
    return ROOT/"data"/"2026"/"10"/f"{BRAND}-Social-Monitoring-{day}.json"

def pdf_file(day):
    return OUT/f"{BRAND}-Social-Monitoring-{day}.pdf"

def verify_pdf(path):
    pdf=PdfReader(str(path), strict=True)
    if not pdf.pages:
        raise AssertionError(f"Empty PDF: {path}")
    return len(pdf.pages)

def daily():
    OUT.mkdir(parents=True,exist_ok=True)
    records=[]
    for n in range(31):
        day=(date(2026,10,1)+timedelta(days=n)).isoformat()
        source=json_file(day)
        if not source.is_file():
            raise FileNotFoundError(f"Missing original daily JSON {day}")
        original=source.read_bytes()
        item=ResearchReport.model_validate(json.loads(original.decode("utf-8"))).enforce_date_guardrails()
        if str(item.report_date)!=day:
            raise AssertionError(f"Wrong original report date {source}: {item.report_date}")
        dest=pdf_file(day)
        render_pdf(item,dest)
        pages=verify_pdf(dest)
        if source.read_bytes()!=original:
            raise AssertionError(f"Original source changed while rendering: {source}")
        records.append(dict(day=day,pages=pages,bytes=dest.stat().st_size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
        print("FINAL_DAILY_PDF",day,pages,flush=True)
    (ROOT/"reports"/"final-daily-render-audit.json").write_text(
       json.dumps({"brand":BRAND,"month":BASE,"daily_count":len(records),
                   "origin":"existing original daily JSON; no network/API used",
                   "records":records},indent=2)+"\n",encoding="utf-8")
    print("FINAL_DAILY_RENDER_PASS",BRAND,len(records))

def check():
    expected=[pdf_file((date(2026,10,1)+timedelta(days=n)).isoformat()) for n in range(31)]
    expected+=[OUT/f"{BRAND}-Social-Monitoring-Weekly-2026-10-24_to_2026-10-30.pdf",
               OUT/f"{BRAND}-Social-Monitoring-Monthly-2026-10-01_to_2026-10-31.pdf"]
    for p in expected:
        if not p.is_file():
            raise AssertionError(f"Missing final output: {p}")
        verify_pdf(p)
    manifest=json.loads((ROOT/"reports-index.json").read_text(encoding="utf-8"))
    if len(manifest)!=33:
        raise AssertionError(f"Expected 33 non-demo reports, received {len(manifest)}")
    names={r.get("path") for r in manifest}
    if any(p.relative_to(ROOT).as_posix() not in names for p in expected):
        raise AssertionError("Final archive has broken report-index references")
    month=json.loads((ROOT/"reports"/"monthly-latest.json").read_text(encoding="utf-8"))
    if month.get("snapshots")!=31 or month.get("end")!="2026-10-31":
        raise AssertionError("Month-end coverage isn't 31 saved source snapshots")
    fb=ROOT/"data"/"facebook"/f"{BRAND.lower()}-facebook-audit-2026-10.json"
    if not fb.is_file():
        raise FileNotFoundError("Source-access limitations audit missing: "+str(fb))
    fba=json.loads(fb.read_text(encoding="utf-8"))
    print("FINAL_ARCHIVE_PASS",json.dumps(dict(brand=BRAND,files=len(expected),
      monthly_findings=month.get("dated_findings"),
      unverified_leads=month.get("unverified_leads"),
      retail_observations=month.get("retail_observations_count"),
      fb_verified_evidence_audit=fba.get("verified_record_count",fba.get("verified_facebook_count")),
      facebook_access_incomplete=True)))

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--check",action="store_true")
    args=ap.parse_args()
    check() if args.check else daily()
