#!/usr/bin/env bash
# =============================================================================
#  ACPTest — Full Reproduction Script
#  Runs 30 seeds × 4 configurations = 120 experiments.
#  Estimated wall-clock: ~14 hours on 64-core EPYC.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

SEEDS_FILE="configs/seeds.txt"
CONFIG_FILE="configs/experiment.yaml"
RESULTS_DIR="data/results"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  ACPTest — Full Reproduction (R=30 × 4 configurations)      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"

# Step 0 — Validate environment
python -c "import numpy, scipy, yaml, lxml; print('Dependencies OK')"

# Step 1 — Generate mutant pool (once)
echo ""
echo "=== Step 1: Generating mutant pool ==="
bash scripts/gen_mutants.sh

# Step 2 — Run 30 × 4 experiments
echo ""
echo "=== Step 2: Running experiments ==="
mkdir -p "$RESULTS_DIR"

mapfile -t SEEDS < "$SEEDS_FILE"

for r in $(seq 1 30); do
    SEED=${SEEDS[$((r - 1))]}
    for config in from_scratch cbr_only rl_only cbr_rl; do
        OUTPUT="${RESULTS_DIR}/run_${r}_${config}.json"
        if [ -f "$OUTPUT" ]; then
            echo "  [SKIP] Run ${r}, ${config} (output exists)"
            continue
        fi
        echo "  [RUN]  Run ${r}/30, config=${config}, seed=${SEED}"
        python -m src.runner \
            --config "$CONFIG_FILE" \
            --mode "$config" \
            --seed "$SEED" \
            --run-id "$r" \
            --output "$OUTPUT"
    done
done

# Step 3 — Aggregate & produce tables
echo ""
echo "=== Step 3: Aggregating results ==="
python scripts/analyse.py \
    --results-dir "$RESULTS_DIR" \
    --output-dir "$RESULTS_DIR/tables"

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Done. Results in data/results/tables/                      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
