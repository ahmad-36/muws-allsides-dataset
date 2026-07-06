"""Tier 2: NLI zero-shot — 3-class and 5-class via entailment scoring."""

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    MODEL_NLI, CONDITIONED_DIR, RESULTS_DIR,
    NLI_HYPOTHESES_3CLASS, NLI_HYPOTHESES_5CLASS,
)
from chunking import semantic_chunk, aggregate_logits

CONDITIONS = ["original", "stripped", "swapped_cross", "swapped_same"]


def load_completed(output_file):
    done = set()
    if output_file.exists():
        with open(output_file) as f:
            for line in f:
                r = json.loads(line)
                done.add((r["article_id"], r["condition"]))
    return done


def nli_classify_chunk(premise, hypotheses, model, tokenizer, device):
    """Score entailment for each hypothesis against the premise. Returns logits per label."""
    scores = []
    for label_name, hypothesis in hypotheses.items():
        inputs = tokenizer(
            premise, hypothesis,
            return_tensors="pt", truncation="only_first", max_length=512, padding=False,
        ).to(device)
        with torch.no_grad():
            logits = model(**inputs).logits.cpu().numpy()[0]
        entailment_score = logits[model.config.label2id.get("entailment", 2)]
        scores.append(entailment_score)
    return np.array(scores)


def classify_article_nli(text, hypotheses, model, tokenizer, device):
    chunks = semantic_chunk(text, tokenizer, max_chunk_tokens=400)
    all_logits = []

    for chunk in chunks:
        scores = nli_classify_chunk(chunk, hypotheses, model, tokenizer, device)
        all_logits.append(scores)

    pred_idx, mean_logits = aggregate_logits(all_logits)
    label_names = list(hypotheses.keys())
    return label_names[pred_idx], mean_logits, len(chunks)


def run_nli(n_classes, hypotheses, gt_key, output_file, model, tokenizer, device):
    completed = load_completed(output_file)
    print(f"\n  [{n_classes}-class] Already completed: {len(completed)} predictions")

    total = 0
    start = time.time()

    with open(output_file, "a") as out_f:
        for cond_name in CONDITIONS:
            cond_file = CONDITIONED_DIR / f"{cond_name}.jsonl"
            articles = []
            with open(cond_file) as f:
                for line in f:
                    articles.append(json.loads(line))

            pending = [a for a in articles if (a["article_id"], cond_name) not in completed]
            if not pending:
                print(f"    {cond_name}: all done, skipping")
                continue

            print(f"    {cond_name}: {len(pending)} to process")

            for art in tqdm(pending, desc=f"nli-{n_classes}/{cond_name}"):
                pred_label, mean_logits, n_chunks = classify_article_nli(
                    art["text"], hypotheses, model, tokenizer, device,
                )

                gt = art[gt_key].replace(" ", "_")
                result = {
                    "article_id": art["article_id"],
                    "condition": cond_name,
                    "model": "nli",
                    "n_classes": n_classes,
                    "predicted_label": pred_label,
                    "ground_truth": gt,
                    "correct": pred_label == gt,
                    "mean_logits": mean_logits,
                    "n_chunks": n_chunks,
                    "domain": art["domain"],
                }
                out_f.write(json.dumps(result, ensure_ascii=False) + "\n")
                out_f.flush()
                total += 1

    elapsed = time.time() - start
    print(f"    Done {n_classes}-class: {total} predictions in {elapsed:.0f}s")


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    print(f"Loading {MODEL_NLI}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NLI)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NLI).to(device)
    model.eval()
    print(f"  Labels: {model.config.id2label}")

    print("\nRunning 3-class NLI...")
    run_nli(
        n_classes=3,
        hypotheses=NLI_HYPOTHESES_3CLASS,
        gt_key="ground_truth_3class",
        output_file=RESULTS_DIR / "nli_3class.jsonl",
        model=model, tokenizer=tokenizer, device=device,
    )

    print("\nRunning 5-class NLI...")
    run_nli(
        n_classes=5,
        hypotheses=NLI_HYPOTHESES_5CLASS,
        gt_key="ground_truth_5class",
        output_file=RESULTS_DIR / "nli_5class.jsonl",
        model=model, tokenizer=tokenizer, device=device,
    )

    print("\nAll NLI runs complete.")


if __name__ == "__main__":
    main()
