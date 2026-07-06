"""Tier 1: premsa/political-bias-prediction-allsides-DeBERTa — 3-class encoder."""

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from config import MODEL_ENCODER, CONDITIONED_DIR, RESULTS_DIR, LABEL_3CLASS
from chunking import semantic_chunk, aggregate_logits

CONDITIONS = ["original", "stripped", "swapped_cross", "swapped_same"]
OUTPUT_FILE = RESULTS_DIR / "encoder_3class.jsonl"


def load_completed(output_file):
    done = set()
    if output_file.exists():
        with open(output_file) as f:
            for line in f:
                r = json.loads(line)
                done.add((r["article_id"], r["condition"]))
    return done


def classify_article(text, model, tokenizer, device):
    chunks = semantic_chunk(text, tokenizer, max_chunk_tokens=510)
    all_logits = []

    for chunk in chunks:
        inputs = tokenizer(
            chunk, return_tensors="pt", truncation=True, max_length=512, padding=False,
        ).to(device)
        with torch.no_grad():
            logits = model(**inputs).logits.cpu().numpy()[0]
        all_logits.append(logits)

    pred_idx, mean_logits = aggregate_logits(all_logits)
    return pred_idx, mean_logits, len(chunks)


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    print(f"Loading {MODEL_ENCODER}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ENCODER)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_ENCODER).to(device)
    model.eval()

    # premsa model uses LABEL_0/1/2 → map to left/center/right (alphabetical, per training data)
    label_map = {0: "left", 1: "center", 2: "right"}
    print(f"  Label map: {label_map}")

    completed = load_completed(OUTPUT_FILE)
    print(f"  Already completed: {len(completed)} predictions")

    total_articles = 0
    total_chunks = 0
    start_time = time.time()

    with open(OUTPUT_FILE, "a") as out_f:
        for cond_name in CONDITIONS:
            cond_file = CONDITIONED_DIR / f"{cond_name}.jsonl"
            articles = []
            with open(cond_file) as f:
                for line in f:
                    articles.append(json.loads(line))

            pending = [a for a in articles if (a["article_id"], cond_name) not in completed]
            if not pending:
                print(f"  {cond_name}: all {len(articles)} done, skipping")
                continue

            print(f"  {cond_name}: {len(pending)} to process ({len(articles) - len(pending)} cached)")

            for art in tqdm(pending, desc=f"encoder/{cond_name}"):
                pred_idx, mean_logits, n_chunks = classify_article(
                    art["text"], model, tokenizer, device,
                )
                pred_label = label_map[pred_idx]
                total_articles += 1
                total_chunks += n_chunks

                result = {
                    "article_id": art["article_id"],
                    "condition": cond_name,
                    "model": "encoder",
                    "n_classes": 3,
                    "predicted_label": pred_label,
                    "ground_truth": art["ground_truth_3class"],
                    "correct": pred_label == art["ground_truth_3class"],
                    "mean_logits": mean_logits,
                    "n_chunks": n_chunks,
                    "domain": art["domain"],
                }
                out_f.write(json.dumps(result, ensure_ascii=False) + "\n")
                out_f.flush()

    elapsed = time.time() - start_time
    print(f"\nDone. {total_articles} articles ({total_chunks} chunks) in {elapsed:.0f}s")
    if total_articles > 0:
        print(f"  Avg chunks/article: {total_chunks / total_articles:.1f}")


if __name__ == "__main__":
    main()
