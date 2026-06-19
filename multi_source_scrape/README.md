# Project 2: Multi-Source News Article Scraper

Scrapes the full article text behind the featured left/center/right links from the AllSides dataset (Project 1). Each news domain has a dedicated scraper with custom HTML parsing.

## Usage

Each domain has its own script in `scrapers/`. Run individually:

```bash
# Scrape new articles
python scrapers/foxnews.py --mode scrape

# Retry failed entries
python scrapers/foxnews.py --mode patch

# Re-scrape SUCCESS entries to update images/captions
python scrapers/foxnews.py --mode refresh

# Print coverage report
python scrapers/foxnews.py --mode audit

# Common flags
python scrapers/bbc.py --mode scrape --limit 10 --debug --stance left
```

## Scrapers

All scrapers use `scrapers/base.py` for shared infrastructure (session management, rate limiting, resume logic, output persistence).

### Core 9 (top 3 per stance)

| Stance | Domain | File |
|--------|--------|------|
| Left | nytimes.com | `scrapers/nytimes.py` |
| Left | apnews.com | `scrapers/apnews.py` |
| Left | cnn.com | `scrapers/cnn.py` |
| Center | thehill.com | `scrapers/thehill.py` |
| Center | newsweek.com | `scrapers/newsweek.py` |
| Center | reuters.com | `scrapers/reuters.py` |
| Right | foxnews.com | `scrapers/foxnews.py` |
| Right | nypost.com | `scrapers/nypost.py` |
| Right | washingtonexaminer.com | `scrapers/washingtonexaminer.py` |

### Extended Coverage

bbc, theguardian, washingtonpost, politico, foxbusiness, nbcnews, and 20+ more domains.

## Output

- `output/per_domain/<domain>.json` — per-domain scraped articles
- `output/crawled_articles_corpus.json` — legacy combined output (from media_pipeline)

## Docs

- `docs/PIPELINE_SPEC.md` — original build spec
- `docs/multi-news-scrape-status.md` — scrape coverage status
