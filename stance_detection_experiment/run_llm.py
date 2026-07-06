"""Tier 3: Qwen2.5-14B-Instruct in BF16 — 3-class and 5-class prompted classification."""

import json
import re
import sys
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    MODEL_LLM, CONDITIONED_DIR, RESULTS_DIR,
    LLM_SYSTEM_PROMPT, LLM_USER_PROMPT_3CLASS, LLM_USER_PROMPT_5CLASS,
    LABEL_3CLASS, LABEL_5CLASS,
)

CONDITIONS = ["original", "stripped", "swapped_cross", "swapped_same"]


def load_completed(output_file):
    done = set()
    if output_file.exists():
        with open(output_file) as f:
            for line in f:
                r = json.loads(line)
                done.add((r["article_id"], r["condition"]))
    return done


def truncate_for_llm(text, tokenizer, max_len=30000):
    tokens = tokenizer(text, add_special_tokens=False)["input_ids"]
    if len(tokens) <= max_len:
        return text
    return tokenizer.decode(tokens[:max_len], skip_special_tokens=True)


def parse_label(response_text, valid_labels):
    cleaned = response_text.strip().lower().strip(".,!? \n\t\"'")
    if cleaned in valid_labels:
        return cleaned
    for label in valid_labels:
        if label in cleaned:
            return label
    return cleaned


def classify_article_llm(text, prompt_template, valid_labels, model, tokenizer, device):
    user_msg = prompt_template.format(article_text=text)

    messages = [
        {"role": "system", "content": LLM_SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(input_text, return_tensors="pt", truncation=True, max_length=32000).to(device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=10,
            temperature=0.0,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        )

    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
    response = tokenizer.decode(new_tokens, skip_special_tokens=True)
    pred_label = parse_label(response, valid_labels)
    return pred_label, response.strip()


def run_llm(n_classes, prompt_template, valid_labels, gt_key, output_file, model, tokenizer, device):
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

            for art in tqdm(pending, desc=f"llm-{n_classes}/{cond_name}"):
                text = truncate_for_llm(art["text"], tokenizer)
                pred_label, raw_response = classify_article_llm(
                    text, prompt_template, valid_labels, model, tokenizer, device,
                )

                gt = art[gt_key].replace(" ", "_")
                result = {
                    "article_id": art["article_id"],
                    "condition": cond_name,
                    "model": "llm",
                    "n_classes": n_classes,
                    "predicted_label": pred_label,
                    "raw_response": raw_response,
                    "ground_truth": gt,
                    "correct": pred_label == gt,
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

    print(f"Loading {MODEL_LLM} in BF16...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_LLM)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_LLM,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    model.eval()
    print(f"  Model loaded. Memory: {torch.cuda.memory_allocated()/1e9:.1f}GB")

    print("\nRunning 3-class LLM...")
    run_llm(
        n_classes=3,
        prompt_template=LLM_USER_PROMPT_3CLASS,
        valid_labels=LABEL_3CLASS,
        gt_key="ground_truth_3class",
        output_file=RESULTS_DIR / "llm_3class.jsonl",
        model=model, tokenizer=tokenizer, device=device,
    )

    print("\nRunning 5-class LLM...")
    run_llm(
        n_classes=5,
        prompt_template=LLM_USER_PROMPT_5CLASS,
        valid_labels=LABEL_5CLASS,
        gt_key="ground_truth_5class",
        output_file=RESULTS_DIR / "llm_5class.jsonl",
        model=model, tokenizer=tokenizer, device=device,
    )

    print("\nAll LLM runs complete.")


if __name__ == "__main__":
    main()
