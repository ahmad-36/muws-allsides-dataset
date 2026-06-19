# Multi-Source News Scrape — Corpus Status

**Dataset**: AllSides Featured Coverage, January 2025 – May 2026  
**Source**: `allsides_crawl/output/allsides_jan2025_may2026_combined.jsonl`  
**Stories**: 1,919 | **Article slots**: 5,756 (3 stances x 1,919, minus 1 missing right slot)  
**Unique domains**: 278  
**Last updated**: 2026-06-17

---

## Overall Progress

| Metric | Count | Percentage |
|--------|------:|----------:|
| Total article slots | 5,756 | -- |
| Successfully scraped | 2,859 | 49.7% |

---

## Stance Breakdown

| Stance | Total Slots | Scraped | Success Rate |
|--------|------------:|--------:|-------------:|
| Left   | 1,919       | 676     | 35.2%        |
| Center | 1,919       | 1,097   | 57.2%        |
| Right  | 1,918       | 1,086   | 56.6%        |

**Left is underrepresented** -- primarily due to the NYT IP ban (259 slots, only 20 recovered via Wayback Machine) and WSJ paywall (75 slots, 0 scraped).

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

## Gaps & Quality Concerns

### IP-Banned / Paywalled Domains

| Domain | Slots | Issue |
|--------|------:|-------|
| nytimes.com | 259 | IP banned -- 20 recovered via Wayback Machine |
| wsj.com | 157 | Paywalled, no scraper built |
| nationalreview.com | 88 | No scraper built |

### Quality Warning: washingtonpost.com

All 104 WaPo entries are marked SUCCESS but contain very short bodies (average ~365 characters). The paywall truncates content. These entries should be flagged as partial content in downstream analysis.

---

## Architecture

```
multi_source_scrape/
├── scrapers/
│   ├── base.py                # Shared framework (session rotation, rate limiting, resume)
│   ├── foxnews.py             # Per-domain scraper (one file per domain)
│   ├── thehill.py
│   ├── bbc.py
│   └── ...                    # 30+ domain scrapers
├── output/
│   ├── per_domain/            # JSON output files (one per domain)
│   └── crawled_articles_corpus.json
└── docs/
    ├── PIPELINE_SPEC.md
    └── multi-news-scrape-status.md  (this file)
```
