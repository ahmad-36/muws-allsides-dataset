# Pipeline Spec — Unpatched Domain Files

**Date:** 2026-06-20

## Issue

The following 6 domain files in `output/per_domain/` were **never patched** and still
contain the old scraper output (no `extracted_images`, `extracted_videos`, or
`extracted_interactives` fields). They need to be re-scraped or patched to match the
format of the other 9 domains.

## Affected Files

| # | Domain             | File                        |
|---|--------------------|-----------------------------|
| 1 | bbc.com            | `bbc.com.json`              |
| 2 | foxbusiness.com    | `foxbusiness.com.json`      |
| 3 | nbcnews.com        | `nbcnews.com.json`          |
| 4 | politico.com       | `politico.com.json`         |
| 5 | theguardian.com    | `theguardian.com.json`      |
| 6 | washingtonpost.com | `washingtonpost.com.json`   |

## Verified Domains (UI-inspected)

| # | Domain          | File                      | images | videos | interactives | Status |
|---|-----------------|---------------------------|--------|--------|--------------|--------|
| 1 | apnews.com      | `apnews.com.json`         | ✅     | ✅     | ✅           | ✅ Verified 2026-06-21 |

## What to Check

- Verify whether image/media extraction works for each domain's scraper.
- Re-run the scraper in `refresh` or `patch` mode to populate media fields.
- Confirm output schema matches the patched domains (`extracted_images`, `extracted_videos`, `extracted_interactives`).

## Context

The other 9 domains were patched and their updated files are now in `output/per_domain/`.
The pre-patch originals have been archived to `archive/scraper_archive/old_json/` with
an `.old.json` suffix.
