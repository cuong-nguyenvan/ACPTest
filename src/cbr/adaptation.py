"""
Test-case adaptation operators.

Given a retrieved test case and a new target policy, adaptation modifies
the test inputs and expected outcomes to match the new policy structure.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Dict, List


def adapt_test_case(
    source_test: dict,
    source_policy: dict,
    target_policy: dict,
    operators: List[str] | None = None,
) -> dict:
    """Adapt a source test case to a target policy.

    Operators (applied in order):
        input_mutate    — remap attribute values to match target policy targets
        outcome_flip    — recalculate expected decision under target policy
        condition_remap — adjust condition values for changed condition sets
    """
    operators = operators or ["input_mutate", "outcome_flip", "condition_remap"]
    adapted = deepcopy(source_test)

    for op in operators:
        if op == "input_mutate":
            adapted = _adapt_inputs(adapted, source_policy, target_policy)
        elif op == "outcome_flip":
            adapted = _adapt_outcome(adapted, target_policy)
        elif op == "condition_remap":
            adapted = _adapt_conditions(adapted, source_policy, target_policy)

    adapted["provenance"] = "adapted"
    adapted["source_case_id"] = source_test.get("case_id", "unknown")
    return adapted


def _adapt_inputs(test: dict, source: dict, target: dict) -> dict:
    """Remap subject/resource/action attributes to valid values in target."""
    request = test.get("request", {})

    # If target has different valid roles, map to the closest equivalent
    target_roles = target.get("valid_roles", set())
    source_role = request.get("subject", {}).get("role", "")
    if target_roles and source_role not in target_roles:
        request["subject"]["role"] = _closest_role(source_role, target_roles)

    test["request"] = request
    return test


def _adapt_outcome(test: dict, target_policy: dict) -> dict:
    """Recalculate expected decision by evaluating request against target."""
    # Placeholder — in production this calls policy.evaluator.evaluate()
    test["expected_decision"] = None  # Will be computed by evaluator
    test["outcome_needs_recompute"] = True
    return test


def _adapt_conditions(test: dict, source: dict, target: dict) -> dict:
    """Adjust environment/condition attributes for changed condition sets."""
    source_conditions = set(source.get("condition_attributes", []))
    target_conditions = set(target.get("condition_attributes", []))

    new_conditions = target_conditions - source_conditions
    removed_conditions = source_conditions - target_conditions

    request = test.get("request", {})
    env = request.get("environment", {})

    # Remove attributes no longer in target
    for attr in removed_conditions:
        env.pop(attr, None)

    # Add default values for new conditions
    for attr in new_conditions:
        env[attr] = target.get("condition_defaults", {}).get(attr, "unknown")

    request["environment"] = env
    test["request"] = request
    return test


def _closest_role(role: str, valid_roles: set) -> str:
    """Simple string-similarity fallback for role mapping."""
    # In production: use a role-hierarchy ontology mapping
    # Here: return the first valid role as a conservative fallback
    return next(iter(valid_roles)) if valid_roles else role
