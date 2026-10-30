# Atomos Social & Web Monitoring

An independent Atomos daily media monitoring app, based on the proven Angelbird reporting engine, with no Angelbird data or PDFs.

- Website: Atomos-inspired dark broadcast-production design; year/month/day calendar, latest report, embedded PDF viewer.
- Daily schedule: 19:00 Pakistan time (14:00 UTC), covering that same calendar day.
- Research: free public source indexes, optional YouTube Data API, bounded GPT-4.1-mini web research via GitHub Actions. Same-day verified original URLs only.
- Sections: Facebook, Instagram, X, LinkedIn, Reddit public index, YouTube, camera forums, articles/Google News, retailers.
- Evidence: published date, author, source excerpt, public metrics, original photos and comments where available. No invented traffic.
- Strict brand scope: Atomos, AtomOS, ATOMOSphere and directly attributed Atomos products.
- Outputs: data/YYYY/MM/Atomos-Social-Monitoring-YYYY-MM-DD.json and matching PDF in reports/YYYY/MM/.

## Configure after publishing this clone in its own repository

1. Create empty repository `Mahimedia456/Atomosreportsocialmedia` and push the orphan working tree from branch `atomos-report-clone-ready` as main.
2. Add `OPENAI_API_KEY` and optional `YOUTUBE_API_KEY` in the NEW repository's GitHub Actions Secrets (secrets cannot be copied from another repo).
3. Use Vercel to import the NEW repository, project build command `node scripts/build_website.mjs`, output `_site`, independent from Angelbird.
4. Verify GitHub Actions workflow and live site; no automatic run is guaranteed before the new repository is created and configured.

Reference for product/category scope: https://www.atomos.com/ and https://www.atomos.com/news-feed/.
