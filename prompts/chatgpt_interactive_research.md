# Atomos interactive ChatGPT research (NO OpenAI API billing)

Run this prompt **inside this ChatGPT conversation with web search**, not in GitHub Actions and not with an OpenAI API key.

Research Atomos Technologies for **{{REPORT_DATE}}**, and preserve the five earlier calendar days **{{PREVIOUS_FIVE_DATES}}**.

Find original dated public posts, video reviews, individual comments, creator demonstrations, camera forum discussions, industry coverage, product compatibility and genuine retail promotions across YouTube, publicly indexed Reddit posts (no Reddit OAuth), Facebook/Instagram/LinkedIn public posts, camera forums, editorial and regional reseller websites. Prefer substantive user feedback over generic brand/product catalog entries. Use targeted independent queries and inspect original URLs; do not claim unindexed or private groups were inspected.

For **each find** extract original permalink, actual author, original post timestamp with timezone (NOT crawl/update date), direct Atomos source excerpt, product, concise context, sentiment (Positive/Negative/Neutral/Question/Not applicable), urgency (Urgent/High/Medium/Low/Watch), engagement if visible, source image/thumbnail URL, individual attributable comments if visible, and actionable response advice. Do not fabricate image URLs or counts.

Strict evidence rules:
- Only exact-day directly dated posts/comments can be `today_findings`, with `status: verified`, original URL, direct source excerpt explicitly mentioning Atomos/AV PRO, `published_date: {{REPORT_DATE}}` and a specific `date_evidence` describing original timestamp verification.
- If source date is uncertain, only put it in `unverified_leads` (`status: unverified`). An older article updated today is NOT a new post. Current prices are observations, not new social sentiment.
- Older dated finds in the preceding five days belong in `older_leads` and will appear chronologically below today's section.
- An article about Reddit/YouTube platform features without Atomos mention is not a brand mention.
- Cite source links, and report which platforms were actually checked vs inaccessible. If no exact-day source was verified, be explicit about limited evidence; do not claim global zero mentions.
- Don't repeat already saved URLs unnecessarily; prefer new evidence.

**Output:** Give a readable review, then a complete machine-readable JSON object intended for:
`data/YYYY/MM/Atomos-Social-Monitoring-YYYY-MM-DD-chatgpt.json`.

JSON shape:
```json
{
  "report_date": "{{REPORT_DATE}}",
  "status": "Interactive web evidence",
  "headline": "Source-based daily summary",
  "today_findings": [],
  "unverified_leads": [],
  "older_leads": [],
  "retail_observations": [],
  "coverage": [
    {"platform": "YouTube", "checked": false, "summary": "Actual searches and access limits"}
  ],
  "visibility_gaps": [],
  "methodology": "ChatGPT public web research, original URLs manually checked"
}
```
Each finding can include `title`, `platform`, `url`, `author`, `published_date`, `date_evidence`, `source_excerpt`, `summary`, `sentiment`, `priority`, `status`, `image_url`, `product`, `details`, `impact`, `response_action`, `engagement`, and `comments` (array with `author`, `text`, `date`). No placeholders presented as actual evidence.

After user or assistant saves this JSON through GitHub to the named location, the Python reporting program automatically merges it with YouTube Data API and free public RSS sources, deduplicates, preserves previous five days, caches accessible source images, and renders the PDF **without calling the paid OpenAI API**.

**IMPORTANT:** No automatic GitHub job has access to ChatGPT's browser or this chat. A human-initiated ChatGPT research turn and commit is needed to refresh this file.
