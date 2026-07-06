"""Analyze AllSides results: accuracy by short/long, per-source, confusion matrices. Saves all metrics to JSON."""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from config import RESULTS_DIR, ANALYSIS_DIR

LABELS = ["left", "center", "right"]
RESULT_FILES = {
    "encoder": RESULTS_DIR / "allsides_encoder_3class.jsonl",
    "nli": RESULTS_DIR / "allsides_nli_3class.jsonl",
    "llm": RESULTS_DIR / "allsides_llm_3class.jsonl",
}


def load_results(fpath):
    records = []
    if not fpath.exists():
        return records
    with open(fpath) as f:
        for line in f:
            records.append(json.loads(line))
    return records


def confusion_matrix(records):
    cm = np.zeros((3, 3), dtype=int)
    for r in records:
        gt = r["ground_truth"]
        pred = r["predicted_label"]
        if gt in LABELS and pred in LABELS:
            cm[LABELS.index(gt)][LABELS.index(pred)] += 1
    return cm


def metrics_from_cm(cm):
    total = cm.sum()
    correct = sum(cm[i][i] for i in range(len(LABELS)))
    acc = correct / total * 100 if total else 0

    f1s = []
    per_class = {}
    for i, lbl in enumerate(LABELS):
        tp = cm[i][i]
        fp = cm[:, i].sum() - tp
        fn = cm[i, :].sum() - tp
        prec = tp / (tp + fp) if (tp + fp) else 0
        rec = tp / (tp + fn) if (tp + fn) else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
        f1s.append(f1)
        per_class[lbl] = {
            "precision": round(prec * 100, 1),
            "recall": round(rec * 100, 1),
            "f1": round(f1 * 100, 1),
            "support": int(cm[i].sum()),
        }

    return {
        "accuracy": round(acc, 1),
        "macro_f1": round(np.mean(f1s) * 100, 1),
        "total": int(total),
        "correct": int(correct),
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
    }


def analyze_model(model_name, records):
    result = {"model": model_name, "total_predictions": len(records)}

    # Overall
    cm = confusion_matrix(records)
    result["overall"] = metrics_from_cm(cm)

    # By length tag
    by_tag = defaultdict(list)
    for r in records:
        by_tag[r.get("length_tag", "unknown")].append(r)

    result["by_length"] = {}
    for tag, recs in sorted(by_tag.items()):
        cm_tag = confusion_matrix(recs)
        m = metrics_from_cm(cm_tag)
        m["count"] = len(recs)
        result["by_length"][tag] = m

    # By source (top 20)
    by_source = defaultdict(list)
    for r in records:
        by_source[r["domain"]].append(r)

    source_metrics = []
    for src, recs in by_source.items():
        cm_src = confusion_matrix(recs)
        m = metrics_from_cm(cm_src)
        m["source"] = src
        m["count"] = len(recs)
        source_metrics.append(m)

    source_metrics.sort(key=lambda x: -x["count"])
    result["by_source_top20"] = source_metrics[:20]

    # By char_len buckets
    buckets = {"<100": [], "100-500": [], "500-2000": [], "2000-5000": [], "5000+": []}
    for r in records:
        cl = r.get("char_len", 0)
        if cl < 100:
            buckets["<100"].append(r)
        elif cl < 500:
            buckets["100-500"].append(r)
        elif cl < 2000:
            buckets["500-2000"].append(r)
        elif cl < 5000:
            buckets["2000-5000"].append(r)
        else:
            buckets["5000+"].append(r)

    result["by_char_bucket"] = {}
    for bucket, recs in buckets.items():
        if recs:
            cm_b = confusion_matrix(recs)
            m = metrics_from_cm(cm_b)
            m["count"] = len(recs)
            result["by_char_bucket"][bucket] = m

    return result


def main():
    all_metrics = {}

    for model_name, fpath in RESULT_FILES.items():
        records = load_results(fpath)
        if not records:
            print(f"{model_name}: no results found at {fpath}")
            continue

        print(f"\n{'='*60}")
        print(f"  {model_name.upper()} — {len(records)} predictions")
        print(f"{'='*60}")

        metrics = analyze_model(model_name, records)
        all_metrics[model_name] = metrics

        ov = metrics["overall"]
        print(f"  Overall: {ov['accuracy']}% acc, {ov['macro_f1']}% F1")
        print(f"  CM: {ov['confusion_matrix']}")

        print(f"\n  By length:")
        for tag, m in metrics["by_length"].items():
            print(f"    {tag:>6}: {m['accuracy']:5.1f}% acc, {m['macro_f1']:5.1f}% F1  (n={m['count']})")

        print(f"\n  By char bucket:")
        for bucket, m in metrics["by_char_bucket"].items():
            print(f"    {bucket:>10}: {m['accuracy']:5.1f}% acc, {m['macro_f1']:5.1f}% F1  (n={m['count']})")

        print(f"\n  Top 10 sources:")
        for s in metrics["by_source_top20"][:10]:
            print(f"    {s['source']:<40} {s['accuracy']:5.1f}% acc  (n={s['count']})")

    # Save all metrics
    out_path = ANALYSIS_DIR / "allsides_metrics.json"
    with open(out_path, "w") as f:
        json.dump(all_metrics, f, indent=2, ensure_ascii=False)
    print(f"\nSaved all metrics to {out_path}")

    # Also save a compact CSV-like summary
    summary_path = ANALYSIS_DIR / "allsides_summary.jsonl"
    with open(summary_path, "w") as f:
        for model_name, metrics in all_metrics.items():
            for tag, m in metrics.get("by_length", {}).items():
                row = {
                    "model": model_name, "split": f"length_{tag}",
                    "accuracy": m["accuracy"], "macro_f1": m["macro_f1"],
                    "count": m["count"], "confusion_matrix": m["confusion_matrix"],
                }
                f.write(json.dumps(row) + "\n")
            for bucket, m in metrics.get("by_char_bucket", {}).items():
                row = {
                    "model": model_name, "split": f"chars_{bucket}",
                    "accuracy": m["accuracy"], "macro_f1": m["macro_f1"],
                    "count": m["count"], "confusion_matrix": m["confusion_matrix"],
                }
                f.write(json.dumps(row) + "\n")
    print(f"Saved summary to {summary_path}")


if __name__ == "__main__":
    main()
