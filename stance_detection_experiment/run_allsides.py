"""Run all 3 model tiers on the AllSides dataset (original condition only, 3-class)."""

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, AutoModelForCausalLM
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    MODEL_ENCODER, MODEL_NLI, MODEL_LLM, RESULTS_DIR, DATA_DIR,
    NLI_HYPOTHESES_3CLASS, LLM_SYSTEM_PROMPT, LLM_USER_PROMPT_3CLASS, LABEL_3CLASS,
)
from chunking import semantic_chunk, aggregate_logits

ALLSIDES_FILE = DATA_DIR / "allsides" / "original.jsonl"
RESULTS_PREFIX = "allsides"


def load_articles():
    articles = []
    with open(ALLSIDES_FILE) as f:
        for line in f:
            articles.append(json.loads(line))
    return articles


def load_completed(output_file):
    done = set()
    if output_file.exists():
        with open(output_file) as f:
            for line in f:
                r = json.loads(line)
                done.add(r["article_id"])
    return done


def run_encoder(articles, device):
    output_file = RESULTS_DIR / f"{RESULTS_PREFIX}_encoder_3class.jsonl"
    completed = load_completed(output_file)
    pending = [a for a in articles if a["article_id"] not in completed]
    print(f"\n[Encoder 3-class] {len(completed)} done, {len(pending)} pending")
    if not pending:
        return

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ENCODER)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_ENCODER).to(device)
    model.eval()
    label_map = {0: "left", 1: "center", 2: "right"}

    with open(output_file, "a") as out_f:
        for art in tqdm(pending, desc="encoder"):
            chunks = semantic_chunk(art["text"], tokenizer, max_chunk_tokens=510)
            all_logits = []
            for chunk in chunks:
                inputs = tokenizer(chunk, return_tensors="pt", truncation=True, max_length=512, padding=False).to(device)
                with torch.no_grad():
                    logits = model(**inputs).logits.cpu().numpy()[0]
                all_logits.append(logits)

            pred_idx, mean_logits = aggregate_logits(all_logits)
            pred_label = label_map[pred_idx]

            result = {
                "article_id": art["article_id"],
                "model": "encoder", "n_classes": 3,
                "predicted_label": pred_label,
                "ground_truth": art["ground_truth_3class"],
                "correct": pred_label == art["ground_truth_3class"],
                "length_tag": art["length_tag"],
                "char_len": art["char_len"],
                "domain": art["domain"],
                "n_chunks": len(chunks),
            }
            out_f.write(json.dumps(result, ensure_ascii=False) + "\n")
            out_f.flush()

    del model, tokenizer
    torch.cuda.empty_cache()
    print("  Encoder done.")


def run_nli(articles, device):
    output_file = RESULTS_DIR / f"{RESULTS_PREFIX}_nli_3class.jsonl"
    completed = load_completed(output_file)
    pending = [a for a in articles if a["article_id"] not in completed]
    print(f"\n[NLI 3-class] {len(completed)} done, {len(pending)} pending")
    if not pending:
        return

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NLI)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NLI).to(device)
    model.eval()
    ent_idx = model.config.label2id.get("entailment", 0)
    hypotheses = NLI_HYPOTHESES_3CLASS

    with open(output_file, "a") as out_f:
        for art in tqdm(pending, desc="nli"):
            chunks = semantic_chunk(art["text"], tokenizer, max_chunk_tokens=400)
            all_logits = []
            for chunk in chunks:
                scores = []
                for label_name, hypothesis in hypotheses.items():
                    inputs = tokenizer(chunk, hypothesis, return_tensors="pt",
                                       truncation="only_first", max_length=512, padding=False).to(device)
                    with torch.no_grad():
                        logits = model(**inputs).logits.cpu().numpy()[0]
                    scores.append(logits[ent_idx])
                all_logits.append(np.array(scores))

            pred_idx, mean_logits = aggregate_logits(all_logits)
            label_names = list(hypotheses.keys())
            pred_label = label_names[pred_idx]

            result = {
                "article_id": art["article_id"],
                "model": "nli", "n_classes": 3,
                "predicted_label": pred_label,
                "ground_truth": art["ground_truth_3class"],
                "correct": pred_label == art["ground_truth_3class"],
                "length_tag": art["length_tag"],
                "char_len": art["char_len"],
                "domain": art["domain"],
                "n_chunks": len(chunks),
            }
            out_f.write(json.dumps(result, ensure_ascii=False) + "\n")
            out_f.flush()

    del model, tokenizer
    torch.cuda.empty_cache()
    print("  NLI done.")


def run_llm(articles, device):
    output_file = RESULTS_DIR / f"{RESULTS_PREFIX}_llm_3class.jsonl"
    completed = load_completed(output_file)
    pending = [a for a in articles if a["article_id"] not in completed]
    print(f"\n[LLM 3-class] {len(completed)} done, {len(pending)} pending")
    if not pending:
        return

    tokenizer = AutoTokenizer.from_pretrained(MODEL_LLM)
    model = AutoModelForCausalLM.from_pretrained(MODEL_LLM, torch_dtype=torch.bfloat16, device_map="auto")
    model.eval()

    def parse_label(text):
        cleaned = text.strip().lower().strip(".,!? \n\t\"'")
        if cleaned in LABEL_3CLASS:
            return cleaned
        for label in LABEL_3CLASS:
            if label in cleaned:
                return label
        return cleaned

    with open(output_file, "a") as out_f:
        for art in tqdm(pending, desc="llm"):
            tokens = tokenizer(art["text"], add_special_tokens=False)["input_ids"]
            text = art["text"]
            if len(tokens) > 30000:
                text = tokenizer.decode(tokens[:30000], skip_special_tokens=True)

            user_msg = LLM_USER_PROMPT_3CLASS.format(article_text=text)
            messages = [
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ]
            input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer(input_text, return_tensors="pt", truncation=True, max_length=32000).to(device)

            with torch.no_grad():
                outputs = model.generate(
                    **inputs, max_new_tokens=10, temperature=0.0, do_sample=False,
                    pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                    output_scores=True, return_dict_in_generate=True,
                )
            new_tokens = outputs.sequences[0][inputs["input_ids"].shape[1]:]
            response = tokenizer.decode(new_tokens, skip_special_tokens=True)
            pred_label = parse_label(response)

            first_token_probs = None
            if outputs.scores:
                logits_first = outputs.scores[0][0]
                probs = torch.softmax(logits_first, dim=-1)
                label_probs = {}
                for lbl in LABEL_3CLASS:
                    tid = tokenizer.encode(lbl, add_special_tokens=False)[0]
                    label_probs[lbl] = round(probs[tid].item(), 4)
                first_token_probs = label_probs

            result = {
                "article_id": art["article_id"],
                "model": "llm", "n_classes": 3,
                "predicted_label": pred_label,
                "raw_response": response.strip(),
                "ground_truth": art["ground_truth_3class"],
                "correct": pred_label == art["ground_truth_3class"],
                "length_tag": art["length_tag"],
                "char_len": art["char_len"],
                "domain": art["domain"],
                "label_probs": first_token_probs,
            }
            out_f.write(json.dumps(result, ensure_ascii=False) + "\n")
            out_f.flush()

    del model, tokenizer
    torch.cuda.empty_cache()
    print("  LLM done.")


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    articles = load_articles()
    print(f"Loaded {len(articles)} AllSides articles")

    run_encoder(articles, device)
    run_nli(articles, device)
    run_llm(articles, device)

    print("\nAll AllSides runs complete.")


if __name__ == "__main__":
    main()
