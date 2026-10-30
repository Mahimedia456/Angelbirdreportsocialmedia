# Angelbird Social Media Monitoring Automation

Daily 19:00 Pakistan time GitHub Actions + OpenAI web research + A4 evidence-first PDF. Recreates the **dark slate header, four KPI tiles, green-accent cards, original URL/QR links, source coverage and older-leads section** of the supplied 30 October 2026 interim reference PDF. The PDF layout is code-locked in `src/pdf_report.py`.

## Quick setup (4 steps)

1. GitHub repository: `Mahimedia456/Angelbirdreportsocialmedia`. Upload/commit all ZIP contents to `main` while preserving `.github/workflows/daily-report.yml`.
2. Go to **Settings → Secrets and variables → Actions → New repository secret**, create `OPENAI_API_KEY`. Never put the key in the repo or chat. An OpenAI API account with billing and web-search access is required separately from ChatGPT Plus.
3. Optional: **Settings → Secrets and variables → Actions → Variables**, `OPENAI_MODEL` (default `gpt-5.5`).
4. **Actions → Angelbird Daily Social Monitoring → Run workflow**: select `dry_run=true` for a no-cost local/demo test, or `dry_run=false` for actual research. Supply optional `report_date` in `YYYY-MM-DD` format.

Scheduled run: every day at **19:00 Asia/Karachi** (schedules may be delayed by GitHub). Requires GitHub Actions enabled and default branch `main`. The workflow needs repository content write permission; confirm repository settings allow workflows to write. The scheduled run and manual workflow are independent from a ChatGPT scheduled task.

## Outputs

- `reports/YYYY/MM/Angelbird-Social-Monitoring-YYYY-MM-DD.pdf`
- `data/YYYY/MM/Angelbird-Social-Monitoring-YYYY-MM-DD.json`
- `data/YYYY/MM/Angelbird-Social-Monitoring-YYYY-MM-DD-research-evidence.json`

Dry run filenames append `-DEMO` to avoid overwriting real reports. JSON includes status/verification metadata and platform coverage. Re-running the same date updates that date's files.

## Local development

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
# Create a DEMO PDF without an API key:
DRY_RUN=true REPORT_DATE=2026-10-30 python -m src.main
# Real research:
OPENAI_API_KEY=YOUR_SECRET REPORT_DATE=2026-10-30 python -m src.main
```

On PowerShell: `$env:DRY_RUN='true'; $env:REPORT_DATE='2026-10-30'; python -m src.main`.

## Investigation method

`prompts/research.md` lists exact verification rules and source categories. Separate web research sweeps cover Reddit/forums, YouTube, public Facebook/Instagram/LinkedIn, press/reviews and retailers; synthesis deduplicates by URL. The data model mechanically rejects items counted as new if publication date or date proof is missing/mismatched. Actual source access/date assessment remains AI-dependent: **review important findings manually**. Public/indexed research is not full access to restricted platform comments, private groups or social APIs. A finding must not be described as verified without its original dated evidence. Retail offers do not count as sentiment. Card fault confirmation cannot be inferred from allegations.

## Deployment phases

1. Reference-template analysis and source inventory (included).
2. Research prompts, dated extraction, source evidence schema (included).
3. Multi-sweep agent, deduplication and validation (included).
4. Reference-style PDF generator and demo/test suite (included).
5. GitHub cron and artifact commit workflow (included; needs repo deployment + secret).
6. First live run, source-link QA, PDF visual comparison and monitoring (requires API credentials and real execution).

## Constraints

**Do not copy this repository's original ChatGPT conversation URL into an API call:** a private ChatGPT chat is not a callable prompt endpoint. The prompt text is managed explicitly in `prompts/research.md`. Existing ChatGPT scheduled tasks are not modified. The supplied interim reference was 2 pages; the user's earlier 5-page standard was noted but not directly available as a source file in this package. Visual reproduction is therefore based on the provided 2-page interim PDF, and findings can flow to additional pages rather than a rigid page count.
