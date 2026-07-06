"""Stage 5: Evaluation — metrics, comparisons, statistical tests."""

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats
from sklearn.metrics import (
    accuracy_score, f1_score, confusion_matrix, classification_report,
)

sys.path.insert(0, str(Path(__file__).parent))
from config import RESULTS_DIR, ANALYSIS_DIR, LABEL_3CLASS, LABEL_5CLASS

RESULT_FILES = {
    ("encoder", 3): RESULTS_DIR / "encoder_3class.jsonl",
    ("nli", 3): RESULTS_DIR / "nli_3class.jsonl",
    ("nli", 5): RESULTS_DIR / "nli_5class.jsonl",
    ("llm", 3): RESULTS_DIR / "llm_3class.jsonl",
    ("llm", 5): RESULTS_DIR / "llm_5class.jsonl",
}

CONDITIONS = ["original", "stripped", "swapped_cross", "swapped_same"]


def load_results(fpath):
    records = []
    if not fpath.exists():
        return records
    with open(fpath) as f:
        for line in f:
            records.append(json.loads(line))
    return records


def group_by_condition(records):
    grouped = defaultdict(list)
    for r in records:
        grouped[r["condition"]].append(r)
    return grouped


def compute_metrics(records, labels):
    y_true = [r["ground_truth"] for r in records]
    y_pred = [r["predicted_label"] for r in records]

    valid_mask = [(yt in labels and yp in labels) for yt, yp in zip(y_true, y_pred)]
    y_true_f = [yt for yt, v in zip(y_true, valid_mask) if v]
    y_pred_f = [yp for yp, v in zip(y_pred, valid_mask) if v]
    n_invalid = sum(1 for v in valid_mask if not v)

    if not y_true_f:
        return {"accuracy": 0, "macro_f1": 0, "n": 0, "n_invalid": n_invalid}

    acc = accuracy_score(y_true_f, y_pred_f)
    f1 = f1_score(y_true_f, y_pred_f, labels=labels, average="macro", zero_division=0)
    cm = confusion_matrix(y_true_f, y_pred_f, labels=labels)

    return {
        "accuracy": round(acc, 4),
        "macro_f1": round(f1, 4),
        "n": len(y_true_f),
        "n_invalid": n_invalid,
        "confusion_matrix": cm.tolist(),
        "labels": labels,
    }


def compute_per_domain(records, labels):
    by_domain = defaultdict(list)
    for r in records:
        by_domain[r["domain"]].append(r)

    domain_metrics = {}
    for domain, recs in sorted(by_domain.items()):
        m = compute_metrics(recs, labels)
        domain_metrics[domain] = {
            "accuracy": m["accuracy"],
            "macro_f1": m["macro_f1"],
            "n": m["n"],
        }
    return domain_metrics


def compute_flip_rate(original_records, swapped_records):
    orig_by_id = {r["article_id"]: r["predicted_label"] for r in original_records}
    flips = 0
    total = 0
    for r in swapped_records:
        aid = r["article_id"]
        if aid in orig_by_id:
            total += 1
            if r["predicted_label"] != orig_by_id[aid]:
                flips += 1
    return {"flip_rate": round(flips / total, 4) if total > 0 else 0, "flips": flips, "total": total}


def mcnemar_test(original_records, other_records):
    orig_by_id = {r["article_id"]: r["correct"] for r in original_records}
    other_by_id = {r["article_id"]: r["correct"] for r in other_records}

    common = set(orig_by_id.keys()) & set(other_by_id.keys())
    b = sum(1 for aid in common if orig_by_id[aid] and not other_by_id[aid])
    c = sum(1 for aid in common if not orig_by_id[aid] and other_by_id[aid])

    if b + c == 0:
        return {"statistic": 0, "p_value": 1.0, "b": b, "c": c}

    statistic = (abs(b - c) - 1) ** 2 / (b + c) if (b + c) > 0 else 0
    p_value = 1 - stats.chi2.cdf(statistic, df=1)
    return {"statistic": round(statistic, 4), "p_value": round(p_value, 6), "b": b, "c": c}


def flip_rate_binomial_test(flip_rate_info, n_classes):
    chance = 1 - 1 / n_classes
    result = stats.binomtest(
        flip_rate_info["flips"], flip_rate_info["total"], p=chance, alternative="greater",
    )
    return {"p_value": round(result.pvalue, 6), "chance_rate": round(chance, 4)}


def main():
    summary = {}

    for (model_name, n_classes), fpath in RESULT_FILES.items():
        key = f"{model_name}_{n_classes}class"
        labels = LABEL_3CLASS if n_classes == 3 else LABEL_5CLASS
        records = load_results(fpath)

        if not records:
            print(f"  {key}: no results found, skipping")
            continue

        print(f"\n{'='*60}")
        print(f"  {key}: {len(records)} predictions")
        print(f"{'='*60}")

        grouped = group_by_condition(records)
        model_summary = {"conditions": {}, "comparisons": {}}

        for cond in CONDITIONS:
            cond_records = grouped.get(cond, [])
            if not cond_records:
                continue
            metrics = compute_metrics(cond_records, labels)
            domain_metrics = compute_per_domain(cond_records, labels)
            model_summary["conditions"][cond] = {**metrics, "per_domain": domain_metrics}

            print(f"\n  [{cond}] Accuracy: {metrics['accuracy']:.4f} | Macro F1: {metrics['macro_f1']:.4f} | N: {metrics['n']}")
            if metrics.get("n_invalid", 0) > 0:
                print(f"    WARNING: {metrics['n_invalid']} invalid predictions")

        orig = grouped.get("original", [])
        if orig:
            for other_cond in ["stripped", "swapped_cross", "swapped_same"]:
                other = grouped.get(other_cond, [])
                if not other:
                    continue

                flip = compute_flip_rate(orig, other)
                mcn = mcnemar_test(orig, other)

                comp = {
                    "flip_rate": flip,
                    "mcnemar": mcn,
                }

                if other_cond == "swapped_cross":
                    binom = flip_rate_binomial_test(flip, n_classes)
                    comp["binomial_test"] = binom

                model_summary["comparisons"][f"original_vs_{other_cond}"] = comp

                print(f"\n  Original → {other_cond}:")
                print(f"    Flip rate: {flip['flip_rate']:.4f} ({flip['flips']}/{flip['total']})")
                print(f"    McNemar: χ²={mcn['statistic']:.2f}, p={mcn['p_value']:.6f}")
                if "binomial_test" in comp:
                    print(f"    Binomial test (flip > chance): p={binom['p_value']:.6f}")

        cm_dir = ANALYSIS_DIR / "confusion_matrices"
        for cond, info in model_summary["conditions"].items():
            if "confusion_matrix" in info:
                cm_path = cm_dir / f"{key}_{cond}.json"
                with open(cm_path, "w") as f:
                    json.dump({"labels": info["labels"], "matrix": info["confusion_matrix"]}, f, indent=2)

        summary[key] = model_summary

    summary_path = ANALYSIS_DIR / "metrics_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n\nSaved summary to {summary_path}")

    print_comparison_table(summary)


def print_comparison_table(summary):
    print(f"\n\n{'='*80}")
    print("COMPARISON TABLE")
    print(f"{'='*80}")
    print(f"{'Model':<20} {'Condition':<18} {'Accuracy':>10} {'Macro F1':>10} {'Flip Rate':>10}")
    print("-" * 68)

    for key, data in summary.items():
        for cond in CONDITIONS:
            cond_data = data["conditions"].get(cond, {})
            acc = cond_data.get("accuracy", "-")
            f1 = cond_data.get("macro_f1", "-")

            flip = "-"
            comp_key = f"original_vs_{cond}"
            if comp_key in data.get("comparisons", {}):
                flip = data["comparisons"][comp_key]["flip_rate"]["flip_rate"]

            acc_str = f"{acc:.4f}" if isinstance(acc, float) else acc
            f1_str = f"{f1:.4f}" if isinstance(f1, float) else f1
            flip_str = f"{flip:.4f}" if isinstance(flip, float) else flip

            print(f"{key:<20} {cond:<18} {acc_str:>10} {f1_str:>10} {flip_str:>10}")
        print()


if __name__ == "__main__":
    main()
