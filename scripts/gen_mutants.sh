#!/usr/bin/env bash
# =============================================================================
#  Generate mutant pool for the main experiment policy set.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

POLICY_DIR="data/policies"
OUTPUT_DIR="data/mutants"
SEED=42

echo "Generating first-order mutants …"

if [ -d "$POLICY_DIR" ] && [ "$(ls -A $POLICY_DIR 2>/dev/null)" ]; then
    for policy_file in "$POLICY_DIR"/*.xml "$POLICY_DIR"/*.json; do
        [ -f "$policy_file" ] || continue
        basename=$(basename "$policy_file" | sed 's/\.[^.]*$//')
        echo "  Processing: $basename"
        python -m src.mutation.generator \
            --policy "$policy_file" \
            --output-dir "${OUTPUT_DIR}/${basename}" \
            --operators M1 M2 M3 M4 M5 M6 M7 \
            --detect-equivalent \
            --z3-timeout 30 \
            --sym-depth 20 \
            --rand-samples 100000 \
            --seed $SEED
    done
else
    echo "  No policies found in $POLICY_DIR — skipping."
    echo "  (Run the case study instead: bash scripts/run_case_study.sh)"
fi

echo "Done."
