#!/bin/bash
set -e

cd "$(dirname "$0")"
export CUDA_VISIBLE_DEVICES=3

echo "=========================================="
echo "Stage 1+2: Prepare data & conditions"
echo "=========================================="
python prepare_data.py

echo ""
echo "=========================================="
echo "Stage 4a: Encoder (Tier 1) — 3-class"
echo "=========================================="
python run_encoder.py

echo ""
echo "=========================================="
echo "Stage 4b: NLI (Tier 2) — 3+5-class"
echo "=========================================="
python run_nli.py

echo ""
echo "=========================================="
echo "Stage 4c: LLM (Tier 3) — 3+5-class"
echo "=========================================="
python run_llm.py

echo ""
echo "=========================================="
echo "Stage 5: Evaluation"
echo "=========================================="
python evaluate.py

echo ""
echo "All done!"
