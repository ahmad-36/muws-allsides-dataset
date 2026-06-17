# Multi-Source News Scrape — Corpus Status

**Dataset**: AllSides Featured Coverage, January 2025 – May 2026  
**Source**: `output_2025_2026/allsides_jan2025_may2026_combined.jsonl`  
**Stories**: 1,919 | **Article slots**: 5,756 (3 stances × 1,919, minus 1 missing right slot)  
**Unique domains**: 278  
**Last updated**: 2026-06-17

---

## Overall Progress

| Metric | Count | Percentage |
|--------|------:|----------:|
| Total article slots | 5,756 | — |
| Successfully scraped | 2,859 | 49.7% |
| Failed / not attempted | 2,897 | 50.3% |

---

## Stance Breakdown

| Stance | Total Slots | Scraped | Success Rate |
|--------|------------:|--------:|-------------:|
| Left   | 1,919       | 676     | 35.2%        |
| Center | 1,919       | 1,097   | 57.2%        |
| Right  | 1,918       | 1,086   | 56.6%        |

**Left is underrepresented** — primarily due to the NYT IP ban (259 slots, only 20 recovered via Wayback Machine) and WSJ paywall (75 slots, 0 scraped).

---

## Top 5 Domains per Stance

### Left

| # | Domain | Slots | Scraped | Rate |
|---|--------|------:|--------:|-----:|
| 1 | nytimes.com | 259 | 20 | 7.7% |
| 2 | apnews.com | 194 | 194 | 100% |
| 3 | cnn.com | 163 | 163 | 100% |
| 4 | theguardian.com | 113 | 113 | 100% |
| 5 | nbcnews.com | 113 | 113 | 100% |

### Center

| # | Domain | Slots | Scraped | Rate |
|---|--------|------:|--------:|-----:|
| 1 | thehill.com | 369 | 368 | 99.7% |
| 2 | newsweek.com | 281 | 281 | 100% |
| 3 | reuters.com | 271 | 174 | 64.2% |
| 4 | bbc.com | 266 | 266 | 100% |
| 5 | wsj.com | 157 | 0 | 0% |

### Right

| # | Domain | Slots | Scraped | Rate |
|---|--------|------:|--------:|-----:|
| 1 | foxnews.com | 496 | 484 | 97.6% |
| 2 | nypost.com | 324 | 323 | 99.7% |
| 3 | washingtonexaminer.com | 179 | 179 | 100% |
| 4 | foxbusiness.com | 98 | 98 | 100% |
| 5 | nationalreview.com | 88 | 0 | 0% |

---

## All Scraped Domains — Full Status

| Domain | Pipeline | Slots | Success | Failed | Rate | Notes |
|--------|----------|------:|--------:|-------:|-----:|-------|
| apnews.com | media_pipeline | 194 | 194 | 0 | 100% | |
| bbc.com | media_pipeline | 266 | 266 | 0 | 100% | |
| cnn.com | media_pipeline | 163 | 163 | 0 | 100% | |
| foxbusiness.com | media_pipeline | 98 | 98 | 0 | 100% | |
| foxnews.com | media_pipeline | 496 | 484 | 12 | 97.6% | |
| nbcnews.com | media_pipeline | 113 | 113 | 0 | 100% | |
| newsweek.com | media_pipeline | 281 | 281 | 0 | 100% | |
| nypost.com | media_pipeline | 324 | 323 | 1 | 99.7% | |
| nytimes.com | media_pipeline | 259 | 20 | 239 | 7.7% | IP banned; 20 via Wayback |
| reuters.com | media_pipeline | 271 | 174 | 97 | 64.2% | Partial recovery via patch |
| thehill.com | media_pipeline | 369 | 368 | 1 | 99.7% | |
| washingtonexaminer.com | media_pipeline | 179 | 179 | 0 | 100% | |
| theguardian.com | scrapers/ | 113 | 113 | 0 | 100% | |
| washingtonpost.com | scrapers/ | 104 | 104 | 0 | 100% | Paywalled — avg 365 chars |
| politico.com | scrapers/ | 91 | 85 | 6 | 93.4% | 6 failed from rate limiting |

**Total across scraped domains**: 3,321 slots attempted → 2,965 success

---

## Gaps & Quality Concerns

### IP-Banned / Paywalled Domains (0% or near-0%)

| Domain | Slots | Issue |
|--------|------:|-------|
| nytimes.com | 259 | IP banned — 20 recovered via Wayback Machine |
| wsj.com | 157 | Paywalled, no scraper built |
| nationalreview.com | 88 | No scraper built |

### Quality Warning: washingtonpost.com

All 104 WaPo entries are marked SUCCESS but contain **very short bodies** (average ~365 characters vs. 4,000–6,000 for other domains). The paywall truncates `__NEXT_DATA__` content to 1–2 paragraphs before the `subscribe-cta` block. Trafilatura fallback captures what's available but cannot bypass the paywall. These entries should be flagged as **partial content** in downstream analysis.

### Unscraped Long-Tail

The remaining ~2,435 slots (278 − 15 = 263 domains) are from long-tail sources with fewer than ~75 slots each. The top unscraped long-tail domains include:

- usatoday.com, cbsnews.com, breitbart.com, dailymail.co.uk
- abcnews.go.com, npr.org, axios.com, forbes.com

---

## Extraction Features

All scrapers extract:
- **Markdown headings** (`## `) for `h2`/`h3` within article body
- **Images** with alt text and captions (figure/figcaption, LD+JSON, og:image fallbacks)
- **Videos** (where available — LD+JSON VideoObject, embedded players)
- **Interactive embeds** (iframes within article scope)

Parsers use `get_text(" ", strip=True)` to prevent word-merging across inline elements.

---

## Architecture

```
Scraper/
├── media_pipeline.py          # Unified pipeline for 12 core domains
├── scrapers/
│   ├── base.py                # Shared framework (session rotation, rate limiting, resume)
│   ├── theguardian.py         # Per-domain scraper
│   ├── washingtonpost.py      # Per-domain scraper (paywalled)
│   └── politico.py            # Per-domain scraper
├── per_domain/                # JSON output files (one per domain)
├── output_2025_2026/          # AllSides JSONL dataset
└── multi-news-scrape-status.md  # This file
```
