"""Stage 1+2: Load articles, normalize, generate all text conditions, save to disk."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    MULTI_SOURCE_DIR, DATA_DIR, CONDITIONED_DIR, PUBLISHER_REGISTRY,
    FIVE_TO_THREE, strip_publisher, swap_publisher,
)


def load_multi_source():
    articles = []
    for fpath in sorted(MULTI_SOURCE_DIR.glob("*.json")):
        domain = fpath.stem
        if domain not in PUBLISHER_REGISTRY:
            print(f"WARNING: skipping unknown domain {domain}")
            continue

        with open(fpath) as f:
            data = json.load(f)

        info = PUBLISHER_REGISTRY[domain]
        for slug, article in data.items():
            for side_key, side_data in article.items():
                if not isinstance(side_data, dict):
                    continue
                body = side_data.get("extracted_body_text", "")
                if not body or len(body) < 50:
                    continue

                rating_raw = side_data.get("rating", info["rating_5class"])
                rating_5 = rating_raw.replace("-", " ").lower().strip()
                rating_3 = FIVE_TO_THREE.get(rating_5, "center")

                articles.append({
                    "article_id": f"{domain}__{slug}__{side_key}",
                    "domain": domain,
                    "source_name": info["display_name"],
                    "headline": side_data.get("extracted_headline", ""),
                    "body_text": body,
                    "ground_truth_5class": rating_5,
                    "ground_truth_3class": rating_3,
                    "contributors": side_data.get("contributors", ""),
                })

    return articles


def generate_conditions(articles):
    conditions = {
        "original": [],
        "stripped": [],
        "swapped_cross": [],
        "swapped_same": [],
    }

    for art in articles:
        domain = art["domain"]
        text = art["body_text"]
        base = {
            "article_id": art["article_id"],
            "domain": domain,
            "source_name": art["source_name"],
            "headline": art["headline"],
            "ground_truth_5class": art["ground_truth_5class"],
            "ground_truth_3class": art["ground_truth_3class"],
        }

        conditions["original"].append({**base, "text": text, "condition": "original"})

        stripped_text = strip_publisher(text, domain)
        stripped_headline = strip_publisher(art["headline"], domain)
        conditions["stripped"].append({
            **base,
            "text": stripped_text,
            "headline": stripped_headline,
            "condition": "stripped",
        })

        cross_target = PUBLISHER_REGISTRY[domain]["cross_swap"]
        cross_text = swap_publisher(text, domain, cross_target)
        cross_headline = swap_publisher(art["headline"], domain, cross_target)
        conditions["swapped_cross"].append({
            **base,
            "text": cross_text,
            "headline": cross_headline,
            "condition": "swapped_cross",
            "swapped_to": cross_target,
            "swapped_to_name": PUBLISHER_REGISTRY[cross_target]["display_name"],
        })

        same_target = PUBLISHER_REGISTRY[domain]["same_swap"]
        same_text = swap_publisher(text, domain, same_target)
        same_headline = swap_publisher(art["headline"], domain, same_target)
        conditions["swapped_same"].append({
            **base,
            "text": same_text,
            "headline": same_headline,
            "condition": "swapped_same",
            "swapped_to": same_target,
            "swapped_to_name": PUBLISHER_REGISTRY[same_target]["display_name"],
        })

    return conditions


def save_jsonl(records, path):
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main():
    print("Loading multi_source_scrape articles...")
    articles = load_multi_source()
    print(f"  Loaded {len(articles)} articles from {len(set(a['domain'] for a in articles))} domains")

    save_jsonl(articles, DATA_DIR / "articles.jsonl")
    print(f"  Saved articles.jsonl")

    print("Generating text conditions...")
    conditions = generate_conditions(articles)
    for name, records in conditions.items():
        path = CONDITIONED_DIR / f"{name}.jsonl"
        save_jsonl(records, path)
        print(f"  Saved {name}.jsonl ({len(records)} articles)")

    print("\nDomain breakdown:")
    from collections import Counter
    domain_counts = Counter(a["domain"] for a in articles)
    for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
        rating = PUBLISHER_REGISTRY[domain]["rating_5class"]
        print(f"  {domain:<30} {count:>4} articles  ({rating})")

    print("\n3-class distribution:")
    class_counts = Counter(a["ground_truth_3class"] for a in articles)
    for cls, count in sorted(class_counts.items()):
        print(f"  {cls:<10} {count:>4} ({count/len(articles)*100:.1f}%)")

    print("\nDone.")


if __name__ == "__main__":
    main()
