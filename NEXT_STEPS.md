# Next Steps

## Datasets

- [x] **multi_source_scrape** — 2,897 articles from 15 publishers. Full pipeline complete (4 conditions × 3 models × 3-class + 5-class).
- [x] **AllSides CSV** — 21,754 articles from 465 sources, 3-class only (original condition). Running with short/long tags (short = <200 chars, 18.6% of dataset). Results include `length_tag` and `char_len` for length-based analysis.
- [ ] Check if multi_source_scrape articles overlap with AllSides CSV.

## Continue

- [ ] **Run evaluate.py** — `stance_detection_experiment/evaluate.py` is written but hasn't been executed. It computes McNemar's test (paired condition comparison) and binomial test (flip rate significance). Generates `metrics_summary.json`.
- [ ] **Per-domain accuracy breakdown** — which publishers does each model get right vs wrong? Are there publishers where stripping/swapping causes the biggest flips?
- [ ] **Analyze LLM raw responses** — `llm_3class.jsonl` and `llm_5class.jsonl` contain `raw_response` field. Check for parsing failures (labels that didn't match valid set).
- [ ] **AllSides CSV experiment** — adapt `prepare_data.py` to ingest the CSV format. Challenge: 465 sources means the publisher registry (currently 15 entries) needs expansion, or limit to the top ~20 sources that overlap with the registry.
- [ ] **Write paper section** — results are ready for the publisher-stripping finding: encoder is most susceptible to publisher identity (10.4% cross-swap flip rate, −8.8pp accuracy drop), LLM is most robust (2.5% flip rate, −3.2pp drop). Center class is universally hard. 5-class is at chance.
- [ ] **Qualitative examples** — pull specific articles where cross-swap flipped the prediction. The conditioned text is saved in `data/conditioned/*.jsonl` for manual inspection.
- [ ] **Inter-model agreement** — do all three models agree on easy cases? Where do they disagree? Articles where all models flip on cross-swap are the strongest evidence of publisher-signal leakage.
