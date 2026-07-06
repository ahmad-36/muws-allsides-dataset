# Stance Detection with Publisher-Stripping Experiment

## Research Question
Does the model classify political stance from article **content** or **publisher identity**?

---

## Datasets

| Dataset | Articles | Stance Labels | Has Full Text |
|---------|----------|---------------|---------------|
| **multi_source_scrape** (`per_domain_clean`) | 2,897 across 15 domains | 5-class: left, lean left, center, lean right, right | Yes — full body |
| **AllSides CSV** (`allsides_balanced_news_headlines-texts.csv`) | 21,754 | 3-class: left, center, right | Partial — ~400 chars avg |

**multi_source_scrape is the primary dataset** — full article text with AllSides ratings per article.

### 5-class → 3-class Mapping
- left, lean left → **left**
- center → **center**  
- lean right, right → **right**

---

## Pipeline

### Stage 1: Load & Normalize
Read all JSON files from `per_domain_clean/`. Flatten into a unified list of records:
- `article_id`, `domain`, `source_name`, `ground_truth_5class`, `ground_truth_3class`, `headline`, `body_text`

Build a publisher name registry mapping each domain to display names, abbreviations, and regex patterns.

### Stage 2: Text Conditioning
Generate 4 variants of each article. All variants are pre-computed and **saved to disk as full text** (for manual inspection) before any model inference.

| Condition | Description |
|-----------|-------------|
| **Original** | Unmodified article text. Baseline for each model's accuracy. |
| **Stripped** | Regex-remove all publisher name variants, domain references, byline attributions. Replace with generic tokens. |
| **Swapped (cross-side)** | Replace publisher with an opposite-side outlet (CNN → Fox News, etc.) |
| **Swapped (same-side)** | Replace publisher with a same-side outlet (CNN → NBC News, etc.). Sanity check. |

### Stage 3: Truncation Strategy

#### Encoders (Tier 1 & Tier 2) — 512 token limit

**Semantic chunking with mean-logit aggregation.**

81.5% of articles exceed the 512-token limit. Instead of discarding content, we:

1. Split the article into sentences (regex sentence boundary detection)
2. Greedily pack consecutive sentences into chunks of ≤510 tokens each
3. No sentence is ever cut mid-way — every chunk is semantically coherent
4. Classify each chunk independently → raw logits
5. Final prediction = **argmax( mean(logits₁, logits₂, … logitsₙ) )**

```
Chunk 1: sentences 1–6  (~480 tok) → logits₁
Chunk 2: sentences 7–12 (~490 tok) → logits₂
Chunk N: sentences 25–29 (~350 tok) → logitsₙ

final = argmax( mean(logits₁, logits₂, … logitsₙ) )
```

- Articles under 510 tokens → single chunk (no aggregation)
- Average article (~809 tokens) → ~2 chunks
- P99 articles (~3,167 tokens) → ~7 chunks
- Every sentence contributes to the prediction. No information discarded.
- Encoder runtime: ~18 min (up from ~5 min with simple truncation)

#### LLM (Tier 3) — 32K token limit
No truncation needed. Longest article is ~17K tokens. All fit within Qwen2.5-14B's 32,768 context window. For the rare edge case, truncate at sentence boundary.

### Stage 4: Model Inference

| Model | Type | 3-class | 5-class | Method |
|-------|------|---------|---------|--------|
| `premsa/political-bias-prediction-allsides-DeBERTa` | Encoder | ✓ | — | Direct classification head. Semantic chunking + mean logits. |
| `MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli` | NLI | ✓ | ✓ | Zero-shot entailment scoring against candidate label hypotheses. Semantic chunking + mean logits. |
| `Qwen/Qwen2.5-14B-Instruct` | LLM (BF16) | ✓ | ✓ | Prompted classification. Constrained decoding to valid labels. |

**LLM prompt instructs:** *"Classify based solely on the content, framing, and word choice. Do not consider the publication source."*

#### NLI Hypotheses

3-class:
- "This article has a left-wing political perspective."
- "This article has a centrist political perspective."
- "This article has a right-wing political perspective."

5-class:
- "This article has a left-wing political perspective."
- "This article has a moderately left-leaning political perspective."
- "This article has a centrist political perspective."
- "This article has a moderately right-leaning political perspective."
- "This article has a right-wing political perspective."

#### LLM Prompt Template

```
SYSTEM: You are a political media analyst. Classify the political
stance of news articles based solely on content, framing,
word choice, and editorial perspective.
Do not consider the publication source.

USER: Classify this article's political stance.
Respond with exactly one label: left, center, or right.

Article:
{article_text}

Stance:
```

### Stage 5: Evaluation & Analysis

#### Core metrics per condition per model
- **Accuracy** — overall match rate against ground truth
- **Macro F1** — balanced across classes (important since class sizes differ)
- **Confusion matrix** — where does the model disagree, and in which direction?
- **Per-source accuracy** — breakdown by publisher domain

#### Key comparisons (the actual experiment)
- **Original → Stripped:** Accuracy drop = how much the model relied on publisher cues
- **Original → Swapped (cross):** Prediction flip rate = how much the model is swayed by publisher name alone
- **Original → Swapped (same):** Should stay stable — sanity check
- **Stripped vs Swapped (cross):** If stripped accuracy holds but swapped flips predictions, the model has learned source-name shortcuts

#### Statistical tests
- **McNemar's test** — paired comparison of correct/incorrect between Original and Stripped conditions
- **Flip rate significance** — binomial test on whether cross-swap flip rate exceeds chance

---

## Publisher Name Registry

| Domain | Stance | Name Variants (stripped) | Cross-Swap Target | Same-Swap Target |
|--------|--------|--------------------------|-------------------|------------------|
| cnn.com | lean left | CNN, Cable News Network, cnn.com | foxnews.com | nbcnews.com |
| foxnews.com | right | Fox News, Fox News Digital, foxnews.com | cnn.com | nypost.com |
| nytimes.com | lean left | New York Times, NYT, The Times, nytimes.com | nypost.com | washingtonpost.com |
| nypost.com | lean right | New York Post, NY Post, nypost.com | nytimes.com | washingtonexaminer.com |
| washingtonpost.com | lean left | Washington Post, WaPo, The Post, washingtonpost.com | washingtonexaminer.com | nytimes.com |
| washingtonexaminer.com | lean right | Washington Examiner, washingtonexaminer.com | washingtonpost.com | nypost.com |
| apnews.com | left | Associated Press, AP News, AP, apnews.com | foxnews.com | theguardian.com |
| theguardian.com | left | The Guardian, Guardian, theguardian.com | foxnews.com | apnews.com |
| nbcnews.com | lean left | NBC News, NBC, nbcnews.com | foxbusiness.com | cnn.com |
| politico.com | lean left | Politico, POLITICO, politico.com | washingtonexaminer.com | nbcnews.com |
| reuters.com | center | Reuters, reuters.com | reuters.com (kept) | bbc.com |
| bbc.com | center | BBC, BBC News, bbc.com | bbc.com (kept) | reuters.com |
| thehill.com | center | The Hill, thehill.com | thehill.com (kept) | newsweek.com |
| newsweek.com | center | Newsweek, newsweek.com | newsweek.com (kept) | thehill.com |
| foxbusiness.com | lean right | Fox Business, Fox Business Network, foxbusiness.com | nbcnews.com | washingtonexaminer.com |

**Center sources keep their identity in cross-swap** — no meaningful opposite. They still get stripped in the Stripped condition.

---

## Output Structure

```
stance_detection_experiment/
├── config.py                   # publisher registry, model paths, constants
├── prepare_data.py             # Stage 1+2: load, normalize, generate conditions
├── run_encoder.py              # Stage 4: Tier 1 (premsa DeBERTa)
├── run_nli.py                  # Stage 4: Tier 2 (NLI zero-shot)
├── run_llm.py                  # Stage 4: Tier 3 (Qwen2.5-14B BF16)
├── evaluate.py                 # Stage 5: metrics, comparisons, tests
├── run_all.sh                  # orchestrator script
├── data/
│   ├── articles.jsonl          # normalized dataset (full original text + metadata)
│   └── conditioned/            # each file has full article text for manual inspection
│       ├── original.jsonl      # original text (untouched)
│       ├── stripped.jsonl      # publisher names removed
│       ├── swapped_cross.jsonl # publisher replaced with opposite-side outlet
│       └── swapped_same.jsonl  # publisher replaced with same-side outlet
├── results/
│   ├── encoder_3class.jsonl
│   ├── nli_3class.jsonl
│   ├── nli_5class.jsonl
│   ├── llm_3class.jsonl
│   └── llm_5class.jsonl
└── analysis/
    ├── metrics_summary.json
    ├── confusion_matrices/
    └── figures/
```

---

## Execution Order & Time Estimate

| Step | Script | GPU? | Est. Time |
|------|--------|------|-----------|
| 1 | prepare_data.py | No | < 1 min |
| 2 | run_encoder.py (4 conditions × 3-class) | Yes | ~18 min |
| 3 | run_nli.py (4 conditions × 3+5-class) | Yes | ~40 min |
| 4 | run_llm.py (4 conditions × 3+5-class) | Yes (BF16) | ~2–3 hours |
| 5 | evaluate.py | No | < 1 min |

**Total runtime: ~3.5 hours | Cost: $0 (all local on H100)**

All inference scripts checkpoint per-article to JSONL. Re-running skips completed articles.
