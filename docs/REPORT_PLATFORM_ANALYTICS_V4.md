# Angelbird platform-wise reporting and public analytics (V4)

## Daily report layout

The report has a single reporting date with newest verified posts first, followed by the previous five calendar days, each divided into active platforms. Nine explicit categories: Facebook, Instagram, X / Twitter, LinkedIn, Reddit, YouTube, Camera Forums, Google / News / Articles, Retailers.

Each accessible source record may include:
- Direct original post or article permalink, original author and publisher, publication date evidence
- Direct Angelbird/AV PRO source excerpt, sentiment, response priority, product and impact
- Source-hosted `og:image` / `twitter:image` (small cached and attributed thumbnail if retrieval permits)
- Visible public comments, individual comment URLs and author attribution when accessible
- Source-observed public engagement stats, with a distinct `engagement_source`.

Google Search/Google News are **discovery**, not the original publisher. The linked news organization's own site supplies the author, date and illustration. The collector does **not** scrape Google Images indiscriminately or assume a picture is licensed for reuse.

## Analytics definitions and access

| Category | Allowed output | What cannot be inferred |
| --- | --- | --- |
| YouTube (connected Data API key) | Public video views, likes and comment counts from `videos.list(part=statistics)`; public top-level comments via `commentThreads.list` | Unique website visitors, audience demographics and channel-owner-only analytics |
| Facebook / Instagram | Authenticated / publicly accessible post content and visible public reactions/comments, when permitted; other results may only be indexed source leads | Page/post insights for third-party accounts without Meta's authorized permissions |
| X / Twitter | Verified publicly accessible post and posted public metrics when supplied by a legitimate source | Protected posts, private impression demographics, full keyword coverage without authorized API |
| LinkedIn | Indexed post links and accessible public metrics | Organization analytics or members' private insights without approved permissions |
| Reddit | Original public/indexed post and comment references; NO Reddit OAuth | Full private/unindexed discussions or an authenticated subreddit-wide search |
| Camera forums | Accessible public posts, thread authors and visible replies | Traffic to forums not under user ownership |
| Google / News / Articles | Article original URL, journalist byline, publisher, verified date, credited source image | Google ranking/clicks for other sites or their GA4 sessions |
| Retailers | Accessible dated offers and current listing observations separated from sentiment | Store orders, sales or referral conversions |

Public metrics are captured only if numeric values are actually exposed by original sources or an approved API. A missing value prints `N/A`, **never 0**. Known field aliases like `post_views` and `post_likes` are normalized without double-counting. `page_followers` are NOT treated as views of the mentioned post.

**Actual website traffic** (users, sessions, referral visits, conversions) requires access to the website owner's GA4 property or a verified analytics export. Google Search impressions/clicks require that site's Search Console access. No such owner access is currently integrated into this repository.

## YouTube efficiency

Daily monitoring calls a single `search.list` (generally 100 units), one batched `videos.list(part=statistics)` for the publicly returned video IDs (generally 1 unit), and at most 6 `commentThreads.list` calls (typically 1 unit each); actual quota costs and availability are controlled by YouTube. Search and comment times are converted to Pakistan local date. Existing videos can be added to `data/youtube_watchlist.json` to look for NEW daily comments.

## Scope and accuracy

- Daily paid GPT research is separately bounded to one mini-model Responses request with up to two web-search calls, cached by report date. It cannot exhaustively discover posts on every platform.
- The free Python collector searches public RSS/indexed results and accessible original pages. Search-index presence alone never proves an original publication date.
- Facebook/Instagram private groups, restricted LinkedIn members and protected X posts cannot be scraped or silently marked searched.
- The PDF includes platform sections even when no source-verified new record exists, with explicit access uncertainty.
- Existing 29 October reference findings remain historical evidence and do not inflate the newest day's KPIs.

For reliable full social listening and **traffic from every website**, you would need additional authorized connectors or service accounts plus website-owner analytics grants; it is not equivalent to generic Google or GPT search.
