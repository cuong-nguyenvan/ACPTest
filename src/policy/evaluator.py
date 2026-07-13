"""
Policy evaluation engine.

Evaluates an access-control request against a parsed policy tree
and returns the decision (Permit / Deny / NotApplicable / Indeterminate).
"""

from __future__ import annotations

from typing import Dict


COMBINING_ALGORITHMS = {
    "deny-overrides",
    "permit-overrides",
    "first-applicable",
    "only-one-applicable",
    "ordered-deny-overrides",
    "ordered-permit-overrides",
}


def evaluate(policy: dict, request: dict) -> str:
    """Evaluate a request against a policy tree.

    Args:
        policy: Parsed policy structure (from parser.py).
        request: Access-control request with subject/action/resource/environment.

    Returns:
        One of: "Permit", "Deny", "NotApplicable", "Indeterminate".
    """
    p_type = policy.get("type", "")
    if p_type == "PolicySet":
        return _evaluate_policy_set(policy, request)
    elif p_type == "Policy":
        return _evaluate_policy(policy, request)
    else:
        return "Indeterminate"


def _evaluate_policy_set(policy_set: dict, request: dict) -> str:
    """Evaluate a PolicySet using its combining algorithm."""
    combiner = policy_set.get("combiner", "deny-overrides")
    children = policy_set.get("policy_sets", [])

    decisions = []
    for child in children:
        decision = evaluate(child, request)
        decisions.append(decision)

        # Short-circuit for first-applicable
        if combiner == "first-applicable" and decision in ("Permit", "Deny"):
            return decision

    return _combine(decisions, combiner)


def _evaluate_policy(policy: dict, request: dict) -> str:
    """Evaluate a Policy's rules using its combining algorithm."""
    combiner = policy.get("combiner", "first-applicable")
    rules = policy.get("rules", [])

    decisions = []
    for rule in rules:
        decision = _evaluate_rule(rule, request)
        decisions.append(decision)

        if combiner == "first-applicable" and decision in ("Permit", "Deny"):
            return decision

    return _combine(decisions, combiner)


def _evaluate_rule(rule: dict, request: dict) -> str:
    """Evaluate a single rule against a request."""
    # Check target match
    if not _target_matches(rule.get("target", {}), request):
        return "NotApplicable"

    # Check conditions
    for condition in rule.get("conditions", []):
        if not _condition_holds(condition, request):
            return "NotApplicable"

    return rule.get("effect", "Deny")


def _target_matches(target: dict, request: dict) -> bool:
    """Check if the request matches the rule's target.
    Simplified: assumes match if target is empty or not specified."""
    if not target or not target.get("raw_xml"):
        return True
    # Full implementation would parse AnyOf/AllOf/Match from raw_xml
    return True


def _condition_holds(condition: dict, request: dict) -> bool:
    """Check if a condition evaluates to true.
    Simplified: assumes true if not negated."""
    negated = condition.get("negated", False)
    # Full implementation would evaluate the Apply function
    return not negated


def _combine(decisions: list, combiner: str) -> str:
    """Apply a combining algorithm to a list of decisions."""
    if combiner == "deny-overrides":
        if "Deny" in decisions:
            return "Deny"
        if "Permit" in decisions:
            return "Permit"
        return "NotApplicable"

    elif combiner == "permit-overrides":
        if "Permit" in decisions:
            return "Permit"
        if "Deny" in decisions:
            return "Deny"
        return "NotApplicable"

    elif combiner in ("first-applicable", "ordered-deny-overrides",
                       "ordered-permit-overrides"):
        for d in decisions:
            if d in ("Permit", "Deny"):
                return d
        return "NotApplicable"

    elif combiner == "only-one-applicable":
        applicable = [d for d in decisions if d != "NotApplicable"]
        if len(applicable) == 1:
            return applicable[0]
        elif len(applicable) == 0:
            return "NotApplicable"
        else:
            return "Indeterminate"

    return "Indeterminate"
