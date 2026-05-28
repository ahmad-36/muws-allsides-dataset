"""
Inspect the in-progress or completed scraper output.
Shows stats, quality checks, and random samples.

Usage:
    python inspect_run.py              # stats + 3 random samples
    python inspect_run.py 5            # stats + 5 random samples
    python inspect_run.py 0            # stats only, no samples
"""
import json
import sys
import random
from collections import Counter

OUTPUT_FILE = "output_2025_2026/allsides_jun2025_may2026.jsonl"


def load_records():
    records = []
    with open(OUTPUT_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def main():
    n_samples = int(sys.argv[1]) if len(sys.argv) > 1 else 3

    records = load_records()
    if not records:
        print("No records found yet.")
        return

    # --- Basic stats ---
    print(f"\n{'='*60}")
    print(f"  SCRAPER OUTPUT: {len(records)} records")
    print(f"{'='*60}")

    dates = sorted(r["date"] for r in records if r.get("date"))
    if dates:
        print(f"  Date range: {dates[0]} to {dates[-1]}")

    # --- Featured article quality ---
    left_headlines = Counter()
    has_featured = 0
    no_featured = 0
    for rec in records:
        left = rec.get("left", {})
        if left and isinstance(left, dict) and left.get("headline"):
            left_headlines[left["headline"]] += 1
            has_featured += 1
        else:
            no_featured += 1

    unique_left = len(left_headlines)
    print(f"\n  Featured articles:")
    print(f"    Has featured left:  {has_featured}/{len(records)}")
    print(f"    Missing featured:   {no_featured}/{len(records)}")
    print(f"    Unique left headlines: {unique_left}")

    if unique_left < len(records) * 0.5 and len(records) > 10:
        print(f"    *** WARNING: Only {unique_left} unique left headlines across {len(records)} records.")
        print(f"    *** This suggests featured articles are being reused (scraper bug).")
    elif unique_left > 0:
        print(f"    OK: {unique_left} unique out of {has_featured} — looks good.")

    # Most repeated left headlines
    if left_headlines:
        top = left_headlines.most_common(3)
        if top[0][1] > 1:
            print(f"\n    Most repeated left headlines:")
            for h, count in top:
                print(f"      {count}x: {h[:70]}")

    # --- Topic distribution ---
    topics = Counter(r.get("topic", "(none)") for r in records)
    print(f"\n  Topics ({len(topics)} unique):")
    for topic, count in topics.most_common(10):
        print(f"    {count:4d} {topic}")
    if len(topics) > 10:
        print(f"    ... and {len(topics) - 10} more")

    # --- Samples ---
    if n_samples > 0:
        sample_indices = random.sample(range(len(records)), min(n_samples, len(records)))
        print(f"\n{'='*60}")
        print(f"  RANDOM SAMPLES ({n_samples})")
        print(f"{'='*60}")

        for idx in sample_indices:
            rec = records[idx]
            print(f"\n  ── Story {idx+1}/{len(records)} ──")
            print(f"  URL:      {rec.get('headline_link', '')}")
            print(f"  Headline: {rec.get('headline', '')}")
            print(f"  Date:     {rec.get('date', '')}")
            print(f"  Topic:    {rec.get('topic', '')}")
            print(f"  Tags:     {rec.get('tags', [])}")
            print(f"  Summary:  {rec.get('summary', '')[:200]}...")

            for stance in ["left", "right", "center"]:
                art = rec.get(stance, {})
                if art and isinstance(art, dict):
                    print(f"  Featured {stance.upper()}:")
                    print(f"    Source:   {art.get('source', '')}")
                    print(f"    Headline: {art.get('headline', '')}")
                    print(f"    Link:     {art.get('link', '')}")
                    print(f"    Rating:   {art.get('rating', '')}")
                else:
                    print(f"  Featured {stance.upper()}: (empty)")

            for side in ["more_left", "more_right", "more_center"]:
                items = rec.get(side, [])
                print(f"  {side} ({len(items)}):")
                for a in items[:2]:
                    print(f"    - [{a.get('rating','')}] {a.get('source','')}: {a.get('headline','')[:65]}")
                if len(items) > 2:
                    print(f"    ... and {len(items)-2} more")

    print(f"\n{'='*60}")
    print("DONE")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
