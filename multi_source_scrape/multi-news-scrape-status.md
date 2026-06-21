# Multi-Source News Scrape — Corpus Analysis

**Dataset**: AllSides Featured Coverage, January 2025 – May 2026  
**Source**: `allsides_crawl/output/allsides_jan2025_may2026_combined.jsonl`  
**Stories**: 1,919 | **Article slots**: 5,757 (3 stances × 1,919)  
**Unique domains in dataset**: 279  
**Domains scraped**: 15  
**Last updated**: 2026-06-21

---

## 1. Overall Progress

| Metric | Count | % of Total |
|--------|------:|-----------:|
| Total article slots in dataset | 5,757 | — |
| Slots attempted (15 domains) | 3,334 | 57.9% |
| Successfully scraped | 2,978 | 51.7% |
| Failed (attempted but not recovered) | 356 | 6.2% |
| Not attempted (264 domains) | 2,423 | 42.1% |

---

## 2. Stance Breakdown

### Of the full dataset (1,919 stories per stance)

| Stance | Total Slots | Successfully Scraped | Success Rate |
|--------|------------:|---------------------:|-------------:|
| Left   | 1,919       | 784                  | 40.9%        |
| Center | 1,919       | 1,104                | 57.5%        |
| Right  | 1,919       | 1,090                | 56.8%        |

### Of attempted slots only

| Stance | Attempted | Scraped | Success Rate |
|--------|----------:|--------:|-------------:|
| Left   | 1,034     | 784     | 75.8%        |
| Center | 1,193     | 1,104   | 92.5%        |
| Right  | 1,107     | 1,090   | 98.5%        |

**Left is underrepresented** — the NYT IP ban (259 slots, only 20 recovered) is the single largest gap. An additional 814 left-stance slots are spread across 50 unscraped domains.

---

## 3. What's Included — All 15 Scraped Domains

| Domain | Entries | Success | Failed | Rate | Avg Body (chars) | Images | Videos | Interactives | Primary Stance |
|--------|--------:|--------:|-------:|-----:|------------------:|-------:|-------:|-------------:|----------------|
| foxnews.com | 498 | 486 | 12 | 97.6% | 4,399 | 473 | 0 | 469 | Right |
| thehill.com | 373 | 372 | 1 | 99.7% | 3,581 | 370 | 0 | 341 | Center |
| nypost.com | 325 | 324 | 1 | 99.7% | 3,743 | 324 | 0 | 305 | Right |
| newsweek.com | 281 | 281 | 0 | 100% | 5,773 | 281 | 0 | 0 | Center |
| reuters.com | 271 | 185 | 86 | 68.3% | 3,799 | 104 | 0 | 54 | Center |
| bbc.com | 266 | 266 | 0 | 100% | 5,375 | 222 | 0 | 0 | Center |
| nytimes.com | 265 | 20 | 245 | 7.5% | 10,558 | 7 | 0 | 0 | Left |
| apnews.com | 194 | 194 | 0 | 100% | 6,043 | 191 | 103 | 26 | Left |
| washingtonexaminer.com | 179 | 179 | 0 | 100% | 3,712 | 179 | 171 | 2 | Right |
| cnn.com | 163 | 163 | 0 | 100% | 6,204 | 162 | 52 | 0 | Left |
| nbcnews.com | 113 | 113 | 0 | 100% | 5,702 | 113 | 0 | 0 | Left |
| theguardian.com | 113 | 113 | 0 | 100% | 4,836 | 113 | 0 | 0 | Left |
| washingtonpost.com | 104 | 99 | 5 | 95.2% | 327 | 99 | 0 | 0 | Left |
| foxbusiness.com | 98 | 98 | 0 | 100% | 3,416 | 98 | 0 | 0 | Right |
| politico.com | 91 | 85 | 6 | 93.4% | 5,333 | 83 | 0 | 2 | Left |

---

## 4. What Failed — and Why

### 4.1 nytimes.com — IP Banned (245 failures)

NYT returned HTTP 403 for all requests. 20 articles were recovered via the Wayback Machine using date-hinted timestamps extracted from URLs. The remaining 239 slots are unrecoverable without a residential proxy or NYT subscription. This is the single biggest gap in the corpus — 259 left-stance slots, only 20 recovered.

### 4.2 reuters.com — Partial IP Ban (86 failures)

Reuters blocked the scraper IP early in the process. After the ban lifted, a patch run recovered 81 additional articles (from the corpus file). 86 entries remain failed — likely articles removed from Reuters or still returning errors. Total: 185/271 success (68.3%).

### 4.3 foxnews.com — Parse Failures (12 failures)

11 articles returned HTTP 200 but the parser extracted an empty body (non-standard page layouts like video-only pages or live blogs). 1 article returned HTTP 404 (deleted).

### 4.4 politico.com — Rate Limiting (6 failures)

6 articles hit HTTP 403 from Politico's rate limiter. The scraper's built-in backoff (60s pause after 3 consecutive fails) recovered most, but 6 remained blocked.

### 4.5 washingtonpost.com — Parse Failures (5 failures)

5 articles returned HTTP 200 but the extracted content was navigation/sidebar text, not article content. These non-standard page types couldn't be parsed.

### 4.6 thehill.com, nypost.com — Isolated Failures (1 each)

thehill.com: 1 article with empty body from a non-standard page layout. nypost.com: 1 article returned HTTP 404 (deleted).

---

## 5. Quality Warnings

### washingtonpost.com — Paywalled Content

All 99 successful WaPo entries have **very short bodies** averaging only ~327 characters (vs. 4,000–6,000 for other domains). The `__NEXT_DATA__` JSON truncates content to 1–2 paragraphs before a `subscribe-cta` block. Trafilatura fallback captures what's available but cannot bypass the paywall. **These entries should be treated as partial content** in downstream analysis.

### nytimes.com — Very Small Sample

Only 20 of 259 NYT articles were recovered (via Wayback Machine). This sample is too small to be representative of NYT's coverage and introduces selection bias — only articles archived by the Wayback Machine at the right timestamp are included.

---

## 6. What's Not Included — Top Unscraped Domains

264 domains in the AllSides dataset have no scraper. The largest ones:

### Left-Stance Gaps (814 unscraped slots across 50 domains)

| Domain | Left Slots | Total Slots | Why Not Scraped |
|--------|----------:|------------:|-----------------|
| cbsnews.com | 81 | 81 | No scraper built |
| axios.com | 75 | 75 | No scraper built |
| edition.cnn.com | 66 | 66 | Separate subdomain from cnn.com; not merged |
| npr.org | 59 | 59 | No scraper built |
| usatoday.com | 55 | 56 | No scraper built |
| abcnews.go.com | 47 | 47 | No scraper built |
| thedailybeast.com | 36 | 36 | No scraper built |
| cnbc.com | 33 | 33 | No scraper built |
| aljazeera.com | 31 | 31 | No scraper built |
| bloomberg.com | 30 | 30 | Paywalled |
| independent.co.uk | 30 | 30 | No scraper built |

### Center-Stance Gaps (644 unscraped slots across 37 domains)

| Domain | Center Slots | Total Slots | Why Not Scraped |
|--------|-------------:|------------:|-----------------|
| wsj.com | 157 | 184 | Paywalled |
| newsnationnow.com | 66 | 66 | No scraper built |
| san.com | 65 | 65 | No scraper built |
| forbes.com | 57 | 57 | No scraper built |
| unherd.com | 46 | 48 | No scraper built |
| fortune.com | 44 | 44 | No scraper built |

### Right-Stance Gaps (775 unscraped slots across 36 domains)

| Domain | Right Slots | Total Slots | Why Not Scraped |
|--------|------------:|------------:|-----------------|
| nationalreview.com | 88 | 88 | No scraper built |
| washingtontimes.com | 86 | 86 | No scraper built |
| dailymail.co.uk | 57 | 57 | No scraper built |
| breitbart.com | 56 | 56 | No scraper built |
| theepochtimes.com | 56 | 56 | No scraper built |
| newsmax.com | 54 | 54 | No scraper built |
| justthenews.com | 47 | 47 | No scraper built |
| dailycaller.com | 42 | 42 | No scraper built |
| dailywire.com | 37 | 38 | No scraper built |
| zerohedge.com | 34 | 34 | No scraper built |

---

## 7. Left-Stance Recovery Effort

To address left-stance underrepresentation, three dedicated scrapers were built:

| Domain | Slots | Scraped | Rate | Notes |
|--------|------:|--------:|-----:|-------|
| theguardian.com | 113 | 113 | 100% | Full article body, images with captions |
| washingtonpost.com | 104 | 99 | 95.2% | Paywalled — avg ~327 chars per body |
| politico.com | 91 | 85 | 93.4% | 6 failed from rate limiting |

These three domains added ~297 left-stance articles. Reuters was also patched after its IP ban lifted, recovering 81 additional center-stance articles.

---

## 8. Extraction Features

All scrapers extract:
- **Markdown headings** (`## `) for `h2`/`h3` within article body
- **Images** with alt text and captions (figure/figcaption, LD+JSON, og:image fallbacks)
- **Videos** (where available — LD+JSON VideoObject, embedded players)
- **Interactive embeds** (iframes within article scope)

Parsers use `get_text(" ", strip=True)` to prevent word-merging across inline elements.

---

## 9. Data Sources

| Source | Location | Description |
|--------|----------|-------------|
| Per-domain JSON | `multi_source_scrape/output/per_domain/` | 15 domain files — primary output for newer scrapers |
| Corpus JSON | `multi_source_scrape/output/crawled_articles_corpus.json` | 9 domains from initial media_pipeline runs; contains reuters entries not in per_domain |
| AllSides JSONL | `allsides_crawl/output/allsides_jan2025_may2026_combined.jsonl` | Source dataset — all 1,919 stories with left/center/right article links |

**Note**: Reuters data is split across two files. `per_domain/reuters.com.json` has 104 entries (all success) from the dedicated scraper. `crawled_articles_corpus.json` has the full 271 reuters entries (185 success) from the earlier pipeline run. The corpus file is the authoritative source for reuters totals.

---

## 10. Architecture

```
Qbias/
├── allsides_crawl/
│   ├── crawler/full_scrape.py           # AllSides Featured Coverage crawler
│   ├── output/                          # JSONL dataset
│   └── analysis/                        # AllSides-level analysis
├── multi_source_scrape/
│   ├── scrapers/
│   │   ├── base.py                      # Shared framework (session rotation, rate limiting, resume)
│   │   ├── foxnews.py                   # Per-domain scrapers (one file per domain)
│   │   ├── cnn.py
│   │   └── ...                          # 40+ scraper files
│   ├── output/
│   │   ├── per_domain/                  # 15 active domain JSON files
│   │   └── crawled_articles_corpus.json # 9-domain corpus from initial pipeline
│   ├── docs/
│   │   ├── PIPELINE_SPEC.md
│   │   └── multi-news-scrape-status.md  # This file
│   └── ui_analysis/
│       └── dataset_explorer.py
├── data/                                # Original dataset files
└── archive/                             # Old scripts, test entries, patched files
```
