"""
Exhaustive first-order mutant generator.

Applies all 7 operators to every applicable site in the policy,
then runs the 3-stage equivalence pipeline.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from .operators import (
    Mutant, MutantOperator, ALTERNATIVE_COMBINERS,
    apply_effect_flip, apply_condition_removal, apply_condition_negation,
    apply_rule_removal, apply_rule_duplication, apply_combiner_change,
    apply_target_narrowing,
)
from .equivalence import detect_equivalent


def generate_all_mutants(
    policy: dict,
    operators: List[str] | None = None,
) -> List[Mutant]:
    """Generate all first-order mutants for a policy.

    Args:
        policy: Parsed policy structure.
        operators: List of operator IDs to apply (default: all 7).

    Returns:
        List of Mutant objects.
    """
    operators = operators or ["M1", "M2", "M3", "M4", "M5", "M6", "M7"]
    mutants: List[Mutant] = []

    all_rules = _collect_rules(policy)
    all_policy_sets = _collect_policy_sets(policy)

    for rule_id, rule in all_rules:
        if "M1" in operators:
            mutants.append(apply_effect_flip(policy, rule_id))

        if "M2" in operators:
            for i in range(len(rule.get("conditions", []))):
                mutants.append(apply_condition_removal(policy, rule_id, i))

        if "M3" in operators:
            for i in range(len(rule.get("conditions", []))):
                mutants.append(apply_condition_negation(policy, rule_id, i))

        if "M4" in operators:
            mutants.append(apply_rule_removal(policy, rule_id))

        if "M5" in operators:
            mutants.append(apply_rule_duplication(policy, rule_id))

        if "M7" in operators:
            mutants.append(apply_target_narrowing(policy, rule_id))

    if "M6" in operators:
        for ps_id, ps in all_policy_sets:
            current = ps.get("combiner", "")
            for alt in ALTERNATIVE_COMBINERS:
                if alt != current:
                    mutants.append(apply_combiner_change(policy, ps_id, alt))

    return mutants


def generate_and_filter(
    policy: dict,
    detect_equiv: bool = True,
    z3_timeout: int = 30,
    sym_depth: int = 20,
    rand_samples: int = 100000,
) -> List[Mutant]:
    """Generate mutants and optionally run equivalence detection."""
    mutants = generate_all_mutants(policy)

    if detect_equiv:
        for m in mutants:
            m.is_equivalent = detect_equivalent(
                original=policy,
                mutant=m.policy,
                z3_timeout=z3_timeout,
                sym_depth=sym_depth,
                rand_samples=rand_samples,
            )

    return mutants


def write_manifest(mutants: List[Mutant], output_dir: Path) -> None:
    """Write mutant manifest CSV and individual policy JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows = []

    for m in mutants:
        # Save individual mutant
        with open(output_dir / f"{m.mutant_id}.json", "w") as f:
            json.dump(m.policy, f, indent=2)

        manifest_rows.append({
            "mutant_id": m.mutant_id,
            "operator": m.operator.value,
            "site": m.site,
            "description": m.description,
            "is_equivalent": m.is_equivalent,
        })

    with open(output_dir / "manifest.csv", "w") as f:
        import csv
        writer = csv.DictWriter(
            f, fieldnames=["mutant_id", "operator", "site", "description", "is_equivalent"]
        )
        writer.writeheader()
        writer.writerows(manifest_rows)


def _collect_rules(policy: dict) -> list:
    """Recursively collect all (rule_id, rule_dict) pairs."""
    results = []
    for rule in policy.get("rules", []):
        results.append((rule["rule_id"], rule))
    for ps in policy.get("policy_sets", []):
        results.extend(_collect_rules(ps))
    return results


def _collect_policy_sets(policy: dict) -> list:
    """Recursively collect all (ps_id, ps_dict) pairs."""
    results = []
    ps_id = policy.get("policy_set_id")
    if ps_id:
        results.append((ps_id, policy))
    for ps in policy.get("policy_sets", []):
        results.extend(_collect_policy_sets(ps))
    return results


# ── CLI entry point ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate first-order mutants")
    parser.add_argument("--policy", required=True, help="Path to policy JSON/XML")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--operators", nargs="*", default=None)
    parser.add_argument("--detect-equivalent", action="store_true")
    parser.add_argument("--z3-timeout", type=int, default=30)
    parser.add_argument("--sym-depth", type=int, default=20)
    parser.add_argument("--rand-samples", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    with open(args.policy) as f:
        policy = json.load(f)

    mutants = generate_and_filter(
        policy,
        detect_equiv=args.detect_equivalent,
        z3_timeout=args.z3_timeout,
        sym_depth=args.sym_depth,
        rand_samples=args.rand_samples,
    )

    write_manifest(mutants, Path(args.output_dir))

    total = len(mutants)
    equiv = sum(1 for m in mutants if m.is_equivalent)
    print(f"Generated {total} mutants, {equiv} equivalent, {total - equiv} killable")


if __name__ == "__main__":
    main()
