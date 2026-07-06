"""Load AllSides CSV, tag short/long, prepare for classification."""

import csv
import json
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))
from config import ALLSIDES_CSV, DATA_DIR, FIVE_TO_THREE

ALLSIDES_DIR = DATA_DIR / "allsides"
ALLSIDES_DIR.mkdir(parents=True, exist_ok=True)

SHORT_THRESHOLD = 200


def main():
    articles = []
    skipped = 0

    with open(ALLSIDES_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            text = (row.get("text") or "").strip()
            title = (row.get("title") or "").strip()
            source = (row.get("source") or "").strip()
            rating = (row.get("bias_rating") or "").strip().lower()

            if not text and not title:
                skipped += 1
                continue
            if rating not in ("left", "center", "right"):
                skipped += 1
                continue

            display_text = text if text else title
            is_short = len(display_text) < SHORT_THRESHOLD
            rating_3 = rating
            rating_5 = rating

            articles.append({
                "article_id": f"allsides_{i}",
                "domain": source,
                "source_name": source,
                "headline": title,
                "text": display_text,
                "ground_truth_3class": rating_3,
                "ground_truth_5class": rating_5,
                "length_tag": "short" if is_short else "long",
                "char_len": len(display_text),
                "condition": "original",
            })

    out_path = ALLSIDES_DIR / "original.jsonl"
    with open(out_path, "w") as f:
        for a in articles:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")

    total = len(articles)
    short_count = sum(1 for a in articles if a["length_tag"] == "short")
    long_count = total - short_count

    print(f"Loaded {total} articles ({skipped} skipped)")
    print(f"  Short (<{SHORT_THRESHOLD} chars): {short_count} ({short_count/total*100:.1f}%)")
    print(f"  Long  (>={SHORT_THRESHOLD} chars): {long_count} ({long_count/total*100:.1f}%)")

    print(f"\n3-class distribution:")
    for cls, count in sorted(Counter(a["ground_truth_3class"] for a in articles).items()):
        print(f"  {cls:<10} {count:>5} ({count/total*100:.1f}%)")

    print(f"\nShort articles by class:")
    short_arts = [a for a in articles if a["length_tag"] == "short"]
    for cls, count in sorted(Counter(a["ground_truth_3class"] for a in short_arts).items()):
        print(f"  {cls:<10} {count:>5} ({count/len(short_arts)*100:.1f}%)")

    print(f"\nTop 15 sources:")
    for src, count in Counter(a["source_name"] for a in articles).most_common(15):
        print(f"  {src:<40} {count:>5}")

    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
