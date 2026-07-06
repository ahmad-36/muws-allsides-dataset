# Stance Detection with Publisher-Stripping: Full Results

> **Experiment:** Do stance-detection models classify political stance from article content — or from publisher identity?

**Dataset:** 2,897 articles from 15 publishers (multi_source_scrape).  
**Ground truth:** AllSides media bias ratings.  
**Predictions:** Each article tested in 4 text conditions = 11,588 predictions per model configuration.  
**Truncation:** Semantic chunking (sentence-boundary-aligned, ≤510 tokens) with mean-logit aggregation for encoder/NLI.

---

## Text Conditions

| Condition | Description |
|-----------|-------------|
| **Original** | Unmodified article text, including publisher self-references (e.g. "CNN reports that...") |
| **Stripped** | All publisher name mentions removed via regex — tests content-only classification |
| **Swapped Cross** | Publisher name replaced with an **opposite-side** outlet (e.g. CNN → "Fox News reports...") — tests if predictions flip based on publisher identity |
| **Swapped Same** | Publisher name replaced with a **same-side** outlet (e.g. CNN → "MSNBC reports...") — control to confirm swaps only matter when political side changes |

## Model Tiers

| Tier | Model | Type | Classes |
|------|-------|------|---------|
| 1 | `premsa/political-bias-prediction-allsides-DeBERTa` | Purpose-built encoder, fine-tuned on AllSides data | 3-class |
| 2 | `MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli` | NLI zero-shot via entailment scoring against hypothesis templates | 3-class, 5-class |
| 3 | `Qwen/Qwen2.5-14B-Instruct` (BF16) | Instruction-tuned LLM, prompted classification | 3-class, 5-class |

---

## 3-Class Results (Left / Center / Right)

### Accuracy & Macro F1

| Model | Original | Stripped | Swapped Cross | Swapped Same |
|-------|----------|----------|---------------|--------------|
| **Encoder** | **65.7%** / 63.2% | 61.9% / 58.0% | 56.9% / 54.9% | 65.1% / 61.4% |
| **NLI** | 41.8% / 39.6% | 38.0% / 36.6% | 35.7% / 34.1% | 42.8% / 40.8% |
| **LLM** | 42.5% / 39.8% | 41.2% / 38.8% | 39.3% / 36.7% | 42.7% / 40.3% |

### Accuracy Drop from Original

| Model | → Stripped | → Swapped Cross | → Swapped Same |
|-------|-----------|-----------------|----------------|
| **Encoder** | −3.8 pp | −8.8 pp | −0.6 pp |
| **NLI** | −3.8 pp | −6.1 pp | +1.0 pp |
| **LLM** | −1.3 pp | −3.2 pp | +0.2 pp |

### Flip Rates (% of articles whose prediction changed)

| Model | Orig → Stripped | Orig → Swapped Cross | Orig → Swapped Same |
|-------|-----------------|----------------------|---------------------|
| **Encoder** | 8.6% | **10.4%** | 8.8% |
| **NLI** | 5.9% | **9.4%** | 4.2% |
| **LLM** | **2.5%** | 4.5% | 2.6% |

### 3-Class Confusion Matrices

#### Encoder — Original (65.7% acc)
```
              Predicted
              Left    Center  Right
Actual Left   635      71      78     (81.0% / 9.1% / 9.9%)
       Center 440     339     244     (43.0% / 33.1% / 23.8%)
       Right  153       8     929     (14.0% / 0.7% / 85.2%)
```

#### Encoder — Stripped (61.9% acc)
```
              Left    Center  Right
Actual Left   645      79      60     (82.3% / 10.1% / 7.7%)
       Center 461     234     328     (45.1% / 22.9% / 32.1%)
       Right  167       8     915     (15.3% / 0.7% / 83.9%)
```

#### Encoder — Swapped Cross (56.9% acc)
```
              Left    Center  Right
Actual Left   452      35     297     (57.7% / 4.5% / 37.9%)
       Center 440     339     244     (43.0% / 33.1% / 23.8%)
       Right  222      10     858     (20.4% / 0.9% / 78.7%)
```

#### Encoder — Swapped Same (65.1% acc)
```
              Left    Center  Right
Actual Left   696      44      44     (88.8% / 5.6% / 5.6%)
       Center 486     263     274     (47.5% / 25.7% / 26.8%)
       Right  155       8     927     (14.2% / 0.7% / 85.0%)
```

#### NLI — Original (41.8% acc)
```
              Left    Center  Right
Actual Left   223     287     274     (28.4% / 36.6% / 35.0%)
       Center 274     307     442     (26.8% / 30.0% / 43.2%)
       Right  169     239     682     (15.5% / 21.9% / 62.6%)
```

#### NLI — Stripped (38.0% acc)
```
              Left    Center  Right
Actual Left   223     274     287     (28.4% / 35.0% / 36.6%)
       Center 275     302     446     (26.9% / 29.5% / 43.6%)
       Right  217     296     577     (19.9% / 27.2% / 52.9%)
```

#### NLI — Swapped Cross (35.7% acc)
```
              Left    Center  Right
Actual Left   188     218     378     (24.0% / 27.8% / 48.2%)
       Center 274     307     442     (26.8% / 30.0% / 43.2%)
       Right  240     312     538     (22.0% / 28.6% / 49.4%)
```

#### NLI — Swapped Same (42.8% acc)
```
              Left    Center  Right
Actual Left   254     259     271     (32.4% / 33.0% / 34.6%)
       Center 273     303     447     (26.7% / 29.6% / 43.7%)
       Right  183     223     684     (16.8% / 20.5% / 62.8%)
```

#### LLM — Original (42.5% acc)
```
              Left    Center  Right
Actual Left   304     172     308     (38.8% / 21.9% / 39.3%)
       Center 310     208     505     (30.3% / 20.3% / 49.4%)
       Right  191     181     718     (17.5% / 16.6% / 65.9%)
```

#### LLM — Stripped (41.2% acc)
```
              Left    Center  Right
Actual Left   301     176     307     (38.4% / 22.4% / 39.2%)
       Center 315     203     505     (30.8% / 19.8% / 49.4%)
       Right  202     197     691     (18.5% / 18.1% / 63.4%)
```

#### LLM — Swapped Cross (39.3% acc)
```
              Left    Center  Right
Actual Left   258     151     375     (32.9% / 19.3% / 47.8%)
       Center 310     208     505     (30.3% / 20.3% / 49.4%)
       Right  209     209     672     (19.2% / 19.2% / 61.7%)
```

#### LLM — Swapped Same (42.7% acc)
```
              Left    Center  Right
Actual Left   329     162     293     (42.0% / 20.7% / 37.4%)
       Center 311     208     504     (30.4% / 20.3% / 49.3%)
       Right  197     192     701     (18.1% / 17.6% / 64.3%)
```

---

## 5-Class Results (Left / Lean Left / Center / Lean Right / Right)

### Accuracy & Macro F1

| Model | Original | Stripped | Swapped Cross | Swapped Same |
|-------|----------|----------|---------------|--------------|
| **NLI** | 25.9% / 23.9% | 23.1% / 21.5% | 18.6% / 17.4% | 27.1% / 25.1% |
| **LLM** | 25.2% / 21.9% | 25.4% / 22.1% | 23.7% / 20.7% | 25.7% / 22.2% |

### Flip Rates (5-class)

| Model | Orig → Stripped | Orig → Swapped Cross | Orig → Swapped Same |
|-------|-----------------|----------------------|---------------------|
| **NLI** | 8.7% | **12.9%** | 7.4% |
| **LLM** | 4.7% | 6.2% | 5.0% |

---

## Key Findings

### 1. The encoder relies heavily on publisher identity
- Highest 3-class accuracy (65.7%) but also the **largest accuracy drop** when publisher names are swapped cross-side (−8.8 pp → 56.9%)
- The **highest flip rate** on cross-swap (10.4%) — one in ten predictions changes when the publisher name switches political sides
- Swapped Same barely changes accuracy (−0.6 pp), confirming the effect is specifically about political-side association, not just text perturbation

### 2. The LLM is most robust to publisher manipulation
- Lowest flip rate across all comparisons (2.5% stripped, 4.5% cross-swap)
- Smallest accuracy drop on cross-swap (−3.2 pp)
- The system prompt explicitly instructs "do not consider the publication source" — this instruction appears to be effective

### 3. All models struggle with "center"
- The encoder predicts "center" very rarely (418/2,897 times) vs 1,023 actual center articles — only 33.1% center recall
- The NLI model has a right-leaning bias: 43.2% of center articles predicted as right
- The LLM shows a similar right-leaning pattern: 49.4% of center articles predicted as right
- **Center is the hardest class across all three models**, likely because centrist articles overlap in framing with both left and right content

### 4. 5-class is essentially at chance
- Both NLI (25.9%) and LLM (25.2%) barely exceed random baseline (20%) on 5-class
- Distinguishing "lean left" from "left" or "lean right" from "right" is extremely difficult for zero-shot/prompted models
- The encoder was not tested on 5-class (it was trained for 3-class only)

### 5. Stripping vs swapping reveals different signals
- **Stripping** removes publisher signal entirely → moderate accuracy drop
- **Cross-swapping** introduces *contradictory* publisher signal → larger accuracy drop
- **Same-swapping** introduces *consistent* publisher signal → accuracy stays flat or slightly improves
- This pattern is consistent across all three model tiers, confirming that publisher identity is a signal the models detect and use

---

## Experiment Details

- **GPU:** NVIDIA H100 96GB (CUDA_VISIBLE_DEVICES=3)
- **Encoder:** ~15 min for all 11,588 predictions (semantic chunking, mean-logit aggregation)
- **NLI 3-class:** ~45 min (entailment scoring per hypothesis per chunk)
- **NLI 5-class:** ~60 min (5 hypotheses instead of 3)
- **LLM 3-class:** ~21 min (Qwen2.5-14B in BF16, greedy decoding, max 10 new tokens)
- **LLM 5-class:** ~23 min
- **Publisher stripping:** 0 missed names in stripped condition; 58.4% of articles contain publisher name in body text
- **Checkpointing:** JSONL append with skip-completed on re-run for crash safety

---

## AllSides Dataset Results (21,754 articles, 465 sources, 3-class)

A broader validation on the full AllSides CSV — no publisher stripping/swapping (too many sources), just classification accuracy with **short vs long** analysis.

### Overall Accuracy

| Model | All (21,754) | Long ≥200 chars (17,704) | Short <200 chars (4,050) |
|-------|-------------|--------------------------|--------------------------|
| **Encoder** | **52.7%** / 49.0% | 52.6% / 49.7% | 52.9% / 44.0% |
| **NLI** | 33.5% / 33.5% | 34.2% / 34.1% | 30.7% / 30.7% |
| **LLM** | 37.9% / 37.2% | 39.0% / 38.3% | 33.4% / 32.7% |

### Accuracy by Article Length Bucket

| Model | <100 chars | 100–500 | 500–2000 |
|-------|-----------|---------|----------|
| **Encoder** | **62.7%** | 52.9% | 51.9% |
| **NLI** | 27.3% | 31.6% | 35.6% |
| **LLM** | 29.7% | 35.8% | 40.3% |

### Length Pattern

**The encoder and NLI/LLM show opposite trends with article length:**

- **Encoder performs BETTER on short text** (62.7% on <100 chars vs 51.9% on 500–2000). This suggests the encoder relies on headline-level cues (source framing, word choice) which are concentrated in short text. Longer articles dilute these signals with neutral reporting content.
- **NLI and LLM perform BETTER on long text** (NLI: 35.6% on 500–2000 vs 27.3% on <100; LLM: 40.3% vs 29.7%). These models need more context to build a stance signal — short headlines don't provide enough content for zero-shot inference.

### Top 10 Sources — Per-Model Accuracy

| Source | Encoder | NLI | LLM |
|--------|---------|-----|-----|
| Fox News (Online News) | **64.1%** | 34.4% | 43.2% |
| CNN (Online News) | 55.5% | 25.8% | 24.5% |
| Washington Post | 56.8% | 25.7% | 29.4% |
| New York Times (News) | **68.4%** | 27.7% | 29.2% |
| Washington Times | 60.8% | 37.8% | 44.1% |
| The Hill (center) | **17.5%** | 33.5% | 27.3% |
| Wall Street Journal (News) | 39.5% | **48.2%** | **44.3%** |
| HuffPost | 54.4% | 32.8% | 38.0% |
| Politico | 56.7% | 30.5% | 28.7% |
| Washington Examiner | 49.2% | 26.5% | 36.0% |

Notable: The encoder gets **17.5% on The Hill** (center-rated) — consistent with the multi_source_scrape finding that center is the hardest class. WSJ is the one source where NLI and LLM outperform the encoder.

### AllSides Confusion Matrices

#### Encoder (52.7% acc)
```
              Left    Center  Right
Actual Left   5900    1492    2883    (57.4% / 14.5% / 28.1%)
       Center 1727    1338    1188    (40.6% / 31.5% / 27.9%)
       Right  2147     856    4223    (29.7% / 11.8% / 58.4%)
```

#### NLI (33.5% acc)
```
              Left    Center  Right
Actual Left   2895    4859    2521    (28.2% / 47.3% / 24.5%)
       Center 1148    2034    1071    (27.0% / 47.8% / 25.2%)
       Right  1878    2982    2366    (26.0% / 41.3% / 32.7%)
```

#### LLM (37.9% acc)
```
              Left    Center  Right
Actual Left   3293    3879    3103    (32.1% / 37.8% / 30.2%)
       Center 1233    1694    1326    (29.0% / 39.8% / 31.2%)
       Right  1704    2254    3268    (23.6% / 31.2% / 45.2%)
```

### AllSides vs Multi-Source Comparison

| Model | Multi-Source (2,897 art, 15 pubs) | AllSides (21,754 art, 465 pubs) | Delta |
|-------|-----------------------------------|----------------------------------|-------|
| **Encoder** | 65.7% | 52.7% | −13.0 pp |
| **NLI** | 41.8% | 33.5% | −8.3 pp |
| **LLM** | 42.5% | 37.9% | −4.6 pp |

All models perform worse on AllSides — likely because: (1) AllSides has 465 sources (many unfamiliar to models), (2) 18.6% are short/headline-only, (3) class imbalance is stronger (47% left vs 20% center). The **LLM degrades the least** (−4.6 pp), consistent with it being the most content-driven classifier.

---

## Full Metrics

All computed metrics saved to:
- `analysis/allsides_metrics.json` — per-model accuracy, F1, confusion matrices, per-source and per-length-bucket breakdowns
- `analysis/allsides_summary.jsonl` — compact row-per-split format for downstream analysis

## Interactive Visualization

See the companion HTML artifact for interactive confusion matrix heatmaps with tooltips, filterable by model tier and class count.
