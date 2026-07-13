"""
XACML 3.0 policy parser.

Converts XACML XML into the internal dict representation used by
the evaluator, path enumerator, and mutation engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from lxml import etree

XACML_NS = "urn:oasis:names:tc:xacml:3.0:core:schema:wd-17"
NS = {"xacml": XACML_NS}


def parse_policy_file(path: str | Path) -> dict:
    """Parse an XACML 3.0 policy file into internal representation."""
    tree = etree.parse(str(path))
    root = tree.getroot()

    tag = etree.QName(root.tag).localname
    if tag == "PolicySet":
        return _parse_policy_set(root)
    elif tag == "Policy":
        return _parse_policy(root)
    else:
        raise ValueError(f"Unexpected root element: {tag}")


def _parse_policy_set(elem) -> dict:
    ps_id = elem.get("PolicySetId", "unknown")
    combiner_uri = elem.get("PolicyCombiningAlgId", "")
    combiner = _extract_combiner_name(combiner_uri)

    policy_sets = []
    policies = []
    rules = []

    for child in elem:
        tag = etree.QName(child.tag).localname
        if tag == "PolicySet":
            policy_sets.append(_parse_policy_set(child))
        elif tag == "Policy":
            parsed = _parse_policy(child)
            policies.append(parsed)
            rules.extend(parsed.get("rules", []))

    return {
        "type": "PolicySet",
        "policy_set_id": ps_id,
        "combiner": combiner,
        "policy_sets": policy_sets + policies,
        "rules": rules,
    }


def _parse_policy(elem) -> dict:
    policy_id = elem.get("PolicyId", "unknown")
    combiner_uri = elem.get("RuleCombiningAlgId", "")
    combiner = _extract_combiner_name(combiner_uri)

    rules = []
    for child in elem:
        tag = etree.QName(child.tag).localname
        if tag == "Rule":
            rules.append(_parse_rule(child))

    return {
        "type": "Policy",
        "policy_id": policy_id,
        "combiner": combiner,
        "rules": rules,
    }


def _parse_rule(elem) -> dict:
    rule_id = elem.get("RuleId", "unknown")
    effect = elem.get("Effect", "Deny")

    conditions = []
    target = {}
    for child in elem:
        tag = etree.QName(child.tag).localname
        if tag == "Condition":
            conditions.append(_parse_condition(child))
        elif tag == "Target":
            target = _parse_target(child)

    return {
        "rule_id": rule_id,
        "effect": effect,
        "conditions": conditions,
        "target": target,
    }


def _parse_condition(elem) -> dict:
    """Parse a Condition element into a simplified dict."""
    return {
        "type": "condition",
        "negated": False,
        "raw_xml": etree.tostring(elem, encoding="unicode"),
    }


def _parse_target(elem) -> dict:
    """Parse a Target element into a simplified dict."""
    return {
        "type": "target",
        "raw_xml": etree.tostring(elem, encoding="unicode"),
    }


def _extract_combiner_name(uri: str) -> str:
    """Extract human-readable combiner name from XACML URI."""
    parts = uri.rstrip().split(":")
    if parts:
        return parts[-1]
    return "unknown"
