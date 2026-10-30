# Angelbird Source-Based Research V3

## Goal
Daily *actual* Angelbird post and media monitoring, not AI-invented findings. The production workflow defaults to Python. It searches across Reddit, YouTube, public Facebook/Instagram/LinkedIn indexes, camera forums, editorial sites and retailers, fetches available first-party pages, verifies original publication dates, and caches source thumbnails. The cumulative PDF shows the latest day followed by the preceding five calendar dates.

## Research modes
- `RESEARCH_ENGINE=python` (default): no OpenAI API calls. Python requests, BeautifulSoup, public search indexes, and configured official platform APIs.
- `RESEARCH_ENGINE=openai` (explicit opt-in only): paid OpenAI model/search workflow; not used in the default GitHub cron.
- `DRY_RUN=true`: demonstration without live source collection.
- `REPORT_ONLY=true`: regenerate saved JSON/PDF without research calls or fetching images.

## Recommended GitHub Actions secrets
| Secret | Use |
|---|---|
| `BRAVE_SEARCH_API_KEY` | Reliable public search index for platforms, groups, articles and retailers. Without it, Bing RSS best-effort fallback may block or miss results. Check the provider's own pricing and quotas. |
| `YOUTUBE_API_KEY` | Official YouTube Data API: videos and public top-level comments. Access/quota subject to Google policy. |
| `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` | Reddit authenticated Data API, only for apps granted the necessary access. |
| `REDDIT_USER_AGENT` (repository variable) | Descriptive Reddit app identifier and contact/user, as required by Reddit's policy. |

Do not paste API keys into source code. The Python run still works *best-effort* without these credentials, but cannot promise broad social coverage or direct comment access.

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
