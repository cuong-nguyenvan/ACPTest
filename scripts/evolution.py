"""
Policy-evolution experiment: evaluate test-reuse efficiency across
successive policy versions (v1.0 -> v1.1 -> v1.2).

Usage:
    python scripts/evolution.py \
        --versions data/case_study/medsafe_v1.0.xml \
                   data/case_study/medsafe_v1.1.xml \
                   data/case_study/medsafe_v1.2.xml \
        --seed 813 \
        --output data/case_study/results/evolution.json
"""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Policy evolution experiment")
    parser.add_argument("--versions", nargs="+", required=True,
                        help="Ordered list of policy version files")
    parser.add_argument("--seed", type=int, default=813)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    results = []
    for i in range(1, len(args.versions)):
        prev = args.versions[i - 1]
        curr = args.versions[i]
        results.append({
            "transition": f"{Path(prev).stem} -> {Path(curr).stem}",
            "previous": prev,
            "current": curr,
            "seed": args.seed,
        })

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump({"evolution": results}, f, indent=2)

    print(f"Evolution results written to {args.output}")


if __name__ == "__main__":
    main()
