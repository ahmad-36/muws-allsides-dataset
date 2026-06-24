# Qbias

A dataset and toolkit for studying media bias in news coverage through the AllSides Balanced News platform. Covers 1,919 stories (Jan 2025 – May 2026) with left/center/right featured articles, full-text scraping across 15 domains, and a Streamlit explorer UI.

## Setup

```bash
# Clone and install (uv recommended)
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt

# Or with pip
pip install -r requirements.txt
```

## Dataset Explorer UI

Browse articles, view locally downloaded images, and inspect extracted content.

```bash
streamlit run multi_source_scrape/ui_analysis/dataset_explorer.py
```

The UI defaults to loading from `multi_source_scrape/output/per_domain_clean/` (cleaned JSON with local image paths). You can also point it at any directory containing per-domain JSON files, or upload JSON files directly.

## Project Structure

### 1. AllSides Crawl (`allsides_crawl/`)

Crawls AllSides headline roundups to produce a structured JSONL dataset of stories with left/center/right featured article links, bias ratings, and metadata.

- **Output**: `allsides_crawl/output/allsides_jan2025_may2026_combined.jsonl` — 1,919 stories
- **Analysis**: `allsides_crawl/analysis/allsides_analysis.md`

### 2. Multi-Source Scraper (`multi_source_scrape/`)

Per-domain scrapers that fetch full article text and images from the top news outlets in the AllSides dataset. 15 domains, ~2,900 articles scraped.

#### Running Scrapers

```bash
cd multi_source_scrape/scrapers

# Scrape new articles (downloads images automatically)
python foxnews.py --mode scrape

# Retry failed entries
python foxnews.py --mode patch

# Re-scrape to update images/captions
python foxnews.py --mode refresh

# Print coverage report
python foxnews.py --mode audit

# Common flags
python bbc.py --mode scrape --limit 10 --debug --stance left

# Write output to a custom directory
python bbc.py --mode scrape --output-dir /path/to/output
```

Scrapers automatically download article images to `output/images/{domain}/{story_id}/{stance}/` and add a `local_path` field to each image entry in the JSON.

#### Scraped Domains

| Stance | Domains |
|--------|---------|
| Left | nytimes.com, apnews.com, cnn.com, nbcnews.com, theguardian.com, washingtonpost.com, politico.com |
| Center | thehill.com, newsweek.com, reuters.com, bbc.com |
| Right | foxnews.com, nypost.com, washingtonexaminer.com, foxbusiness.com |

All scrapers use `scrapers/base.py` for shared infrastructure (session rotation, rate limiting, resume logic, atomic output).

#### Output

```
multi_source_scrape/output/
├── per_domain/              # Scraped JSON (one file per domain, with local_path for images)
├── images/                  # Downloaded article images
│   └── {domain}/{story_id}/{stance}/{index}_{filename}
```

## Corpus Status

See `multi_source_scrape/multi-news-scrape-status.md` for detailed coverage statistics, failure analysis, and quality warnings.

## Original Dataset

The original Qbias dataset (2022) containing 21,747 articles and 671,669 search query suggestions is documented in the [MUWS workshop paper](https://github.com/muws-workshop/Qbias).
