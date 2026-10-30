"""Strict content QA for an unlimited-page periodic social report.

This checks the actual PDF bytes, not merely whether the ReportLab process exited 0.
"""
import argparse, json, re
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
REQUIRED=[
    "EXECUTIVE KPI DASHBOARD", "OVERALL SENTIMENT", "SOCIAL MEDIA SENTIMENT",
    "POST ANALYTICS", "PLATFORM KPI", "ADDITIONAL ENGAGEMENT",
    "FACEBOOK", "INSTAGRAM", "X / TWITTER", "LINKEDIN",
    "REDDIT", "YOUTUBE", "CAMERA FORUMS", "RETAILERS",
]

def normalized(s):
    return re.sub(r"[^a-z0-9]+"," ",str(s).lower()).strip()

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--period",choices=("weekly","monthly"),default="monthly")
    args=a.parse_args()
    meta=json.loads((ROOT/"reports"/f"{args.period}-latest.json").read_text(encoding="utf-8"))
    target=ROOT/meta["path"]
    reader=PdfReader(str(target),strict=True)
    if not reader.pages:
        raise RuntimeError("PDF contains no pages")
    page_text=[p.extract_text() or "" for p in reader.pages]
    text=" ".join(page_text)
    normalized_text=normalized(text)
    missing=[k for k in REQUIRED if normalized(k) not in normalized_text]
    if missing:
        raise RuntimeError("Required source/KPI sections missing: "+str(missing))
    if "1234567890" in text or "def456" in text or "abc123" in text:
        raise RuntimeError("Synthetic placeholder social URLs leaked into published PDF")
    annotations=0
    images=0
    for page in reader.pages:
        annotations+=len(page.get("/Annots",[]))
        try:images+=len(page.images)
        except Exception:pass
    expected=meta.get("source_media",{}).get("embedded_verified",0)
    if expected and images==0:
        raise RuntimeError("Source images expected in PDF, but none were embedded")
    if meta.get("dated_findings",0) and annotations==0:
        raise RuntimeError("Source detail links absent from PDF annotations")
    overview_index=normalized_text.find(normalized("EXECUTIVE KPI DASHBOARD"))
    source_detail_index=normalized_text.find(normalized("FACEBOOK | SOURCE EVIDENCE"))
    if source_detail_index<0:
        source_detail_index=normalized_text.find(normalized("FACEBOOK | SOURCE DETAILS"))
    if source_detail_index<0 or overview_index>source_detail_index:
        raise RuntimeError("Executive KPI not before per-source detail sections")
    audit={
        "period":args.period,"report":meta["path"],"pages":len(reader.pages),
        "pdf_bytes":target.stat().st_size,"expected_dated_records":meta.get("dated_findings",0),
        "expected_leads":meta.get("unverified_leads",0),
        "original_source_links_in_pdf":annotations,
        "embedded_pdf_image_xobjects":images,
        "images_reported_in_manifest":expected,
        "required_sections_checked":REQUIRED,
        "missing_sections":missing,"synthetic_placeholder_urls_found":False,
        "no_page_cap":True,
        "source_dated_coverage_percent":meta.get("daily_coverage_percent",0),
    }
    path=ROOT/"reports"/f"{args.period}-quality-audit.json"
    path.write_text(json.dumps(audit,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(audit))
if __name__=="__main__":
    main()
