#!/usr/bin/env bash
# =============================================================================
#  ACPTest — MedSafe Hospital Case Study
#  Single-seed walkthrough with trace output.  ~5 minutes.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

CONFIG="configs/case_study.yaml"
SEED=813
RESULTS="data/case_study/results"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  ACPTest — MedSafe HIS Case Study (seed=$SEED)              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"

mkdir -p "$RESULTS"

# Step 1 — Generate mutants for MedSafe
echo ""
echo "=== Step 1: Generating MedSafe mutant pool ==="
python -m src.mutation.generator \
    --policy data/case_study/medsafe_root.xml \
    --output-dir data/case_study/mutants/ \
    --detect-equivalent \
    --z3-timeout 30 \
    --sym-depth 20 \
    --rand-samples 100000 \
    --seed $SEED

# Step 2 — Run all 4 modes for comparison
echo ""
echo "=== Step 2: Running all configurations ==="
for mode in from_scratch cbr_only rl_only cbr_rl; do
    echo "  [RUN] mode=${mode}"
    TRACE_FLAG=""
    if [ "$mode" = "cbr_rl" ]; then
        TRACE_FLAG="--trace"
    fi
    python -m src.runner \
        --config "$CONFIG" \
        --mode "$mode" \
        --seed $SEED \
        --run-id 1 \
        --output "${RESULTS}/${mode}.json" \
        $TRACE_FLAG
done

# Step 3 — Generate comparison table
echo ""
echo "=== Step 3: Generating comparison ==="
python scripts/analyse.py \
    --results-dir "$RESULTS" \
    --output-dir "$RESULTS" \
    --format markdown

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Done. Trace: data/case_study/results/cbr_rl.json           ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
