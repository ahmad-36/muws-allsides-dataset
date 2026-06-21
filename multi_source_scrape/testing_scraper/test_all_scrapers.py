"""
Test each scraper with one real article to verify parsing works.
Saves results to testing_scraper/results/<domain>.json
"""

import sys
import os
import json
import random
import time
from datetime import datetime, timezone

SCRAPERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scrapers")
sys.path.insert(0, SCRAPERS_DIR)

from curl_cffi import requests as cffi_requests

CHROME_PROFILES = ["chrome", "chrome110", "chrome120"]
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

TEST_URLS = {
    "apnews.com": "https://apnews.com/article/trump-tax-cuts-bill-medicaid-work-requirements-17cbde167f3b434e925a199c3253b8e1",
    "bbc.com": "https://www.bbc.com/news/articles/cx2jwk6gjp1o",
    "cnn.com": "https://www.cnn.com/2025/05/08/china/xi-jinping-putin-china-russia-talks-moscow-intl-hnk",
    "foxbusiness.com": "https://www.foxbusiness.com/economy/cpi-inflation-april-2025",
    "foxnews.com": "https://www.foxnews.com/politics/house-republicans-unveil-new-food-stamp-work-requirements-trumps-big-beautiful-bill",
    "nbcnews.com": "https://www.nbcnews.com/news/us-news/fox-news-analyst-faints-falls-chair-air-host-tries-carry-show-rcna205873",
    "newsweek.com": "https://www.newsweek.com/newsom-california-homeless-encampments-clear-band-2070956",
    "nypost.com": "https://nypost.com/2025/05/12/us-news/liberal-loudmouth-streamer-hasan-piker-claims-he-was-detained-by-us-immigration-officials/",
    "nytimes.com": "https://www.nytimes.com/2025/05/11/business/us-china-trade-stock-market.html",
    "politico.com": "https://www.politico.com/news/2025/05/02/marco-rubio-germany-afd-00324283",
    "reuters.com": "https://www.reuters.com/legal/us-judge-says-trump-can-use-alien-enemies-act-deportations-2025-05-13/",
    "theguardian.com": "https://www.theguardian.com/us-news/2025/may/12/hasan-piker-border-trump-gaza",
    "thehill.com": "https://thehill.com/homenews/house/5288995-trump-trump-medicare-medicaid-cuts/",
    "washingtonexaminer.com": "https://www.washingtonexaminer.com/news/white-house/3407944/trump-dismisses-concerns-qatari-jet-could-be-new-air-force-one/",
    "washingtonpost.com": "https://www.washingtonpost.com/immigration/2025/05/13/deportations-alien-enemies-pennsylvania-trump-judge/",
}

SCRAPER_MODULES = {
    "apnews.com": "apnews",
    "bbc.com": "bbc",
    "cnn.com": "cnn",
    "foxbusiness.com": "foxbusiness",
    "foxnews.com": "foxnews",
    "nbcnews.com": "nbcnews",
    "newsweek.com": "newsweek",
    "nypost.com": "nypost",
    "nytimes.com": "nytimes",
    "politico.com": "politico",
    "reuters.com": "reuters",
    "theguardian.com": "theguardian",
    "thehill.com": "thehill",
    "washingtonexaminer.com": "washingtonexaminer",
    "washingtonpost.com": "washingtonpost",
}

EXTRA_HEADERS = {
    "nytimes.com": {"Referer": "https://www.google.com/"},
    "washingtonpost.com": {"Referer": "https://www.google.com/"},
}


def fetch(url, domain):
    session = cffi_requests.Session(impersonate=random.choice(CHROME_PROFILES))
    headers = EXTRA_HEADERS.get(domain, {})
    try:
        resp = session.get(url, timeout=20, headers=headers)
        return resp.status_code, resp.text
    except Exception as e:
        return 0, f"NETWORK_ERROR: {e}"


def run_test(domain, url, parse_fn):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"\n{'='*60}")
    print(f"  {domain}")
    print(f"  {url[:80]}")
    print(f"{'='*60}")

    status_code, html = fetch(url, domain)
    if status_code == 0:
        print(f"  FETCH FAILED: {html[:200]}")
        return {"domain": domain, "url": url, "status": "FETCH_FAILED", "error": html[:500]}

    print(f"  HTTP {status_code} — {len(html)} bytes")

    try:
        result_tuple = parse_fn(html, url)
        if len(result_tuple) == 5:
            headline, body, images, videos, interactives = result_tuple
        elif len(result_tuple) == 4:
            headline, body, images, interactives = result_tuple
            videos = []
        elif len(result_tuple) == 3:
            headline, body, images = result_tuple
            videos = []
            interactives = []
        else:
            headline, body = result_tuple
            images = []
            videos = []
            interactives = []
    except Exception as e:
        print(f"  PARSE ERROR: {e}")
        return {"domain": domain, "url": url, "status": "PARSE_ERROR", "error": str(e)}

    body_len = len(body) if body else 0
    status = "SUCCESS" if body and body_len >= 50 else "WEAK_PARSE"

    print(f"  Headline: {(headline or '(none)')[:80]}")
    print(f"  Body: {body_len} chars")
    print(f"  Images: {len(images)}, Videos: {len(videos)}, Interactives: {len(interactives)}")
    print(f"  Status: {status}")

    if body:
        preview = body[:300].replace("\n", " ")
        print(f"  Preview: {preview}...")

    result = {
        "domain": domain,
        "url": url,
        "scrape_timestamp": ts,
        "http_status_code": status_code,
        "execution_status": status,
        "extracted_headline": headline or "",
        "extracted_body_text": body or "",
        "extracted_images": images,
        "extracted_videos": videos,
        "extracted_interactives": interactives,
    }
    return result


def main():
    import importlib

    os.makedirs(RESULTS_DIR, exist_ok=True)

    summary = []
    all_results = {}

    for domain, module_name in SCRAPER_MODULES.items():
        url = TEST_URLS[domain]
        try:
            mod = importlib.import_module(module_name)
            parse_fn = mod.parse
        except Exception as e:
            print(f"\n  IMPORT ERROR for {domain}: {e}")
            summary.append({"domain": domain, "status": "IMPORT_ERROR", "error": str(e)})
            continue

        result = run_test(domain, url, parse_fn)
        all_results[domain] = result
        summary.append({
            "domain": domain,
            "status": result.get("execution_status", result.get("status")),
            "headline_len": len(result.get("extracted_headline", "")),
            "body_len": len(result.get("extracted_body_text", "")),
            "images": len(result.get("extracted_images", [])),
        })

        # Save in the format the explorer expects: {story_id: {slot: article}}
        story_id = f"test_{domain.replace('.', '_')}"
        wrapped = {story_id: {"center": result}}
        out_path = os.path.join(RESULTS_DIR, f"{domain}.json")
        with open(out_path, "w") as f:
            json.dump(wrapped, f, indent=2, ensure_ascii=False)

        # Be polite between requests
        time.sleep(random.uniform(2.0, 4.0))

    # Print summary table
    print(f"\n\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    print(f"  {'Domain':<25} {'Status':<15} {'Headline':<10} {'Body':<10} {'Images':<6}")
    print(f"  {'-'*25} {'-'*15} {'-'*10} {'-'*10} {'-'*6}")
    for s in summary:
        print(f"  {s['domain']:<25} {s['status']:<15} {s.get('headline_len','?'):<10} {s.get('body_len','?'):<10} {s.get('images','?'):<6}")

    success_count = sum(1 for s in summary if s["status"] == "SUCCESS")
    print(f"\n  {success_count}/{len(summary)} scrapers returned SUCCESS")

    # Save summary
    summary_path = os.path.join(RESULTS_DIR, "_summary.jsonl")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Results saved to: {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
