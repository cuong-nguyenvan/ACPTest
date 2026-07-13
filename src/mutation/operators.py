"""
Seven first-order mutation operators for access-control policies.
See REPRODUCIBILITY.md §5.2 and CASE_STUDY.md §4.1.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import List


class MutantOperator(Enum):
    M1_EFFECT_FLIP = "M1"
    M2_CONDITION_REMOVAL = "M2"
    M3_CONDITION_NEGATION = "M3"
    M4_RULE_REMOVAL = "M4"
    M5_RULE_DUPLICATION = "M5"
    M6_COMBINER_CHANGE = "M6"
    M7_TARGET_NARROWING = "M7"


@dataclass
class Mutant:
    """A mutated policy with provenance."""
    mutant_id: str
    operator: MutantOperator
    site: str               # Rule or PolicySet ID that was mutated
    description: str
    policy: dict             # The mutated policy structure
    is_equivalent: bool | None = None  # Set by equivalence detection


ALTERNATIVE_COMBINERS = [
    "first-applicable",
    "deny-overrides",
    "permit-overrides",
    "only-one-applicable",
]


def apply_effect_flip(policy: dict, rule_id: str) -> Mutant:
    """M1: Flip Permit ↔ Deny for a single rule."""
    mutated = deepcopy(policy)
    rule = _find_rule(mutated, rule_id)
    original = rule["effect"]
    rule["effect"] = "Deny" if original == "Permit" else "Permit"
    return Mutant(
        mutant_id=f"m_{rule_id}_M1",
        operator=MutantOperator.M1_EFFECT_FLIP,
        site=rule_id,
        description=f"Rule {rule_id} effect {original} → {rule['effect']}",
        policy=mutated,
    )


def apply_condition_removal(policy: dict, rule_id: str, cond_index: int) -> Mutant:
    """M2: Remove one condition from a rule."""
    mutated = deepcopy(policy)
    rule = _find_rule(mutated, rule_id)
    removed = rule["conditions"].pop(cond_index)
    return Mutant(
        mutant_id=f"m_{rule_id}_M2_{cond_index}",
        operator=MutantOperator.M2_CONDITION_REMOVAL,
        site=rule_id,
        description=f"Rule {rule_id} condition[{cond_index}] '{removed}' removed",
        policy=mutated,
    )


def apply_condition_negation(policy: dict, rule_id: str, cond_index: int) -> Mutant:
    """M3: Negate the boolean value of one condition."""
    mutated = deepcopy(policy)
    rule = _find_rule(mutated, rule_id)
    rule["conditions"][cond_index]["negated"] = not rule["conditions"][cond_index].get("negated", False)
    return Mutant(
        mutant_id=f"m_{rule_id}_M3_{cond_index}",
        operator=MutantOperator.M3_CONDITION_NEGATION,
        site=rule_id,
        description=f"Rule {rule_id} condition[{cond_index}] negated",
        policy=mutated,
    )


def apply_rule_removal(policy: dict, rule_id: str) -> Mutant:
    """M4: Delete an entire rule from the policy set."""
    mutated = deepcopy(policy)
    _remove_rule(mutated, rule_id)
    return Mutant(
        mutant_id=f"m_{rule_id}_M4",
        operator=MutantOperator.M4_RULE_REMOVAL,
        site=rule_id,
        description=f"Rule {rule_id} removed entirely",
        policy=mutated,
    )


def apply_rule_duplication(policy: dict, rule_id: str) -> Mutant:
    """M5: Duplicate a rule (tests combiner sensitivity)."""
    mutated = deepcopy(policy)
    rule = _find_rule(mutated, rule_id)
    dup = deepcopy(rule)
    dup["rule_id"] = rule_id + "_dup"
    _insert_rule_after(mutated, rule_id, dup)
    return Mutant(
        mutant_id=f"m_{rule_id}_M5",
        operator=MutantOperator.M5_RULE_DUPLICATION,
        site=rule_id,
        description=f"Rule {rule_id} duplicated",
        policy=mutated,
    )


def apply_combiner_change(policy: dict, policy_set_id: str, new_combiner: str) -> Mutant:
    """M6: Replace the combining algorithm of one policy set."""
    mutated = deepcopy(policy)
    ps = _find_policy_set(mutated, policy_set_id)
    original = ps["combiner"]
    ps["combiner"] = new_combiner
    return Mutant(
        mutant_id=f"m_{policy_set_id}_M6_{new_combiner[:4]}",
        operator=MutantOperator.M6_COMBINER_CHANGE,
        site=policy_set_id,
        description=f"PolicySet {policy_set_id} combiner {original} → {new_combiner}",
        policy=mutated,
    )


def apply_target_narrowing(policy: dict, rule_id: str) -> Mutant:
    """M7: Narrow the target match expression."""
    mutated = deepcopy(policy)
    rule = _find_rule(mutated, rule_id)
    rule["target"]["extra_constraint"] = "narrowed"
    return Mutant(
        mutant_id=f"m_{rule_id}_M7",
        operator=MutantOperator.M7_TARGET_NARROWING,
        site=rule_id,
        description=f"Rule {rule_id} target narrowed",
        policy=mutated,
    )


# ── Internal helpers ────────────────────────────────────────────────────────

def _find_rule(policy: dict, rule_id: str) -> dict:
    for rule in policy.get("rules", []):
        if rule.get("rule_id") == rule_id:
            return rule
    for ps in policy.get("policy_sets", []):
        result = _find_rule(ps, rule_id)
        if result:
            return result
    raise KeyError(f"Rule {rule_id} not found")


def _remove_rule(policy: dict, rule_id: str) -> None:
    rules = policy.get("rules", [])
    policy["rules"] = [r for r in rules if r.get("rule_id") != rule_id]
    for ps in policy.get("policy_sets", []):
        _remove_rule(ps, rule_id)


def _insert_rule_after(policy: dict, after_id: str, new_rule: dict) -> None:
    rules = policy.get("rules", [])
    for i, r in enumerate(rules):
        if r.get("rule_id") == after_id:
            rules.insert(i + 1, new_rule)
            return
    for ps in policy.get("policy_sets", []):
        _insert_rule_after(ps, after_id, new_rule)


def _find_policy_set(policy: dict, ps_id: str) -> dict:
    if policy.get("policy_set_id") == ps_id:
        return policy
    for ps in policy.get("policy_sets", []):
        result = _find_policy_set(ps, ps_id)
        if result:
            return result
    raise KeyError(f"PolicySet {ps_id} not found")
