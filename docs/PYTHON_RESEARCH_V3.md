# Angelbird Source-Based Research V3

## Goal
Daily *actual* Angelbird post and media monitoring, not AI-invented findings. The production workflow defaults to Python. It searches across Reddit, YouTube, public Facebook/Instagram/LinkedIn indexes, camera forums, editorial sites and retailers, fetches available first-party pages, verifies original publication dates, and caches source thumbnails. The cumulative PDF shows the latest day followed by the preceding five calendar dates.

## Research modes
- `RESEARCH_ENGINE=python` (default): no OpenAI API calls. Python requests, BeautifulSoup, public search indexes, and configured official platform APIs.
- `RESEARCH_ENGINE=openai` (legacy explicit opt-in): this uses **paid** OpenAI API calls and is NOT a free alternative. Do not select it when avoiding paid credits.
- `DRY_RUN=true`: demonstration without live source collection.
- `REPORT_ONLY=true`: regenerate saved JSON/PDF without research calls or fetching images.

## Recommended GitHub Actions secrets
| Secret | Use |
|---|---|
| No search key needed | Public Bing RSS, Google News RSS and GDELT open news-index discovery (no paid search service). Pages are independently checked for Angelbird text and publication dates. |
| `YOUTUBE_API_KEY` | Official YouTube Data API: videos and public top-level comments. Access/quota subject to Google policy. |
| `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` | Reddit authenticated Data API, only for apps granted the necessary access. |
| `REDDIT_USER_AGENT` (repository variable) | Descriptive Reddit app identifier and contact/user, as required by Reddit's policy. |

Do not paste API keys into source code. The Python run works *best-effort* without these optional platform credentials, but cannot promise broad social coverage or direct comment access.

## Evidence acceptance rules
1. Discovery snippets are candidate leads only, not confirmed posts.
2. A new verified finding requires a directly relevant Angelbird/AV PRO mention in first-party source text, a real permalink, and a publication timestamp from the original page or authorized API matching `REPORT_DATE`.
3. Posts/comments from the previous five dates remain in the historical section; no double-counting in today's KPIs.
4. Login-only, private and blocked content remains a clearly marked visibility gap.
5. The PDF may embed resized original-page/official-thumbnail images when successfully retrieved, with original-source attribution and links. It does not fabricate screenshots or republish complete copyrighted photo sets.
6. Reddit or YouTube API comments are separately attributed to their creators. Only comments directly mentioning the brand qualify as Angelbird findings; off-topic comments may be shown strictly as context.

## Archive
- `data/YYYY/MM/Angelbird-Social-Monitoring-YYYY-MM-DD.json`: structured report
- `data/YYYY/MM/*-research-evidence.json`: source search/fetch audit (queries, URLs, errors)
- `assets/YYYY/MM/YYYY-MM-DD/*.jpg`: downloaded original-source thumbnails when accessible
- `reports/YYYY/MM/Angelbird-Social-Monitoring-YYYY-MM-DD.pdf`: original dated report

## Source/coverage caveat
Public search engines and platform APIs impose availability, authentication, and rate limits. They are not full social-listening APIs. A zero-result day means only that **no direct exact-day mention was verified in accessible searched material**. It does not mean zero worldwide posts. Facebook groups and Instagram posts are often inaccessible without authorized API permissions. Native webpage images cannot be embedded when the source blocks requests or permits linking only.

## Testing locally
```powershell
cd E:\Angelbirdreportsocialmedia
py -m pip install -r requirements.txt
py -m unittest discover -s tests -v
$env:RESEARCH_ENGINE = 'python'
$env:REPORT_DATE = '2026-10-30'
$env:DRY_RUN = 'false'
py -m src.main
```

Production cron is 19:00 Asia/Karachi and the PDF filename follows the selected reporting date. Search/query caps can be set through `MAX_SEARCH_QUERIES`, `MAX_SOURCE_PAGES`, `MAX_SOURCE_IMAGES`, and `MAX_HISTORICAL_IMAGES`.

## Quality and visual template
29 October 2026 eight-page reference PDF determines the visual system. Five sentiment metrics, direct evidence cards, source photos where available, author/date, comment rows, product details, engagement, Angelbird impact, response recommendation, QR/linked originals, and cumulative feedback are rendered. Page length increases with actual findings.

## Strict zero-cost search policy
- Scheduled GitHub workflow: `RESEARCH_ENGINE=python`, `FREE_SOURCES_ONLY=true`, no Brave secret and no OpenAI API usage.
- Discovery uses public RSS/search-index pages and free GDELT DOC results (original publisher URLs). GDELT is news/editorial coverage, not an exhaustive Reddit/Facebook/Instagram post index.
- Official YouTube Data API provides a quota allocation when enabled, but access and eligibility depend on Google. Only use within free quota; keep billing disabled if necessary.
- ChatGPT web search inside the ChatGPT app cannot be directly reused as a free GitHub Actions API. OpenAI API web searches are metered; avoid them to meet the no-paid requirement.
- A successful RSS response does not mean the original source was checked. Each report retains query audit and coverage limitations. Unavailable platforms remain explicitly unverified.
