# Project 1: AllSides Headline Roundup Crawl (Jan 2025 – May 2026)

Crawls the [AllSides Balanced News Headline Roundups](https://www.allsides.com/headline-roundups) to produce a structured JSONL dataset of stories with left/center/right featured article links and metadata.

## Output

`output/allsides_jan2025_may2026_combined.jsonl` — 1,919 stories, each with:
- Headline, date, topic tags
- Featured left/center/right article links with source, headline, bias rating
- Additional `more_left`/`more_center`/`more_right` arrays

## Analysis

`analysis/allsides_analysis.md` — corpus statistics including domain frequencies, stance distributions, co-occurrence pairs, and cross-stance mobility.
