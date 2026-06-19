# Qbias

A dataset and toolkit for studying media bias in news coverage through the AllSides Balanced News platform.

## Projects

### [allsides_crawl/](allsides_crawl/) — AllSides Dataset (Jan 2025 – May 2026)

Crawls AllSides headline roundups to produce a structured dataset of 1,919 stories with left/center/right featured articles, bias ratings, and metadata.

### [multi_source_scrape/](multi_source_scrape/) — Full-Text Article Scraper

Custom per-domain scrapers that fetch the full article body text from the top news outlets in the AllSides dataset. Currently covers 30+ domains with ~2,900 articles successfully scraped.

## Setup

```bash
pip install -r requirements.txt
```

## Original Dataset

The original Qbias dataset (2022) containing 21,747 articles and 671,669 search query suggestions is documented below for reference. See the [MUWS workshop paper](https://github.com/muws-workshop/Qbias) for details.
