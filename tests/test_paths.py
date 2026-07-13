"""Unit tests for evaluation-path enumeration."""

import pytest
from src.policy.paths import (
    enumerate_paths_exhaustive,
    enumerate_paths_pruned,
    enumerate_paths,
    _count_rules,
    feasibility_prune,
)


def _simple_policy(num_rules=5):
    return {
        "type": "PolicySet",
        "policy_set_id": "PS1",
        "combiner": "deny-overrides",
        "rules": [{"rule_id": f"R{i}", "effect": "Permit", "conditions": []}
                  for i in range(num_rules)],
        "policy_sets": [],
    }


class TestExhaustive:
    def test_empty_policy(self):
        policy = {"policy_set_id": "PS", "rules": [], "policy_sets": []}
        paths = enumerate_paths_exhaustive(policy)
        assert len(paths) == 1  # Just the root node

    def test_flat_rules(self):
        policy = _simple_policy(3)
        paths = enumerate_paths_exhaustive(policy)
        assert len(paths) == 3

    def test_nested(self):
        child = {
            "type": "PolicySet",
            "policy_set_id": "Child",
            "combiner": "first-applicable",
            "rules": [{"rule_id": "RC1"}, {"rule_id": "RC2"}],
            "policy_sets": [],
        }
        parent = {
            "type": "PolicySet",
            "policy_set_id": "Parent",
            "combiner": "deny-overrides",
            "rules": [{"rule_id": "RP1"}],
            "policy_sets": [child],
        }
        paths = enumerate_paths_exhaustive(parent)
        assert len(paths) >= 3


class TestPruned:
    def test_first_applicable_prunes(self):
        policy = {
            "type": "PolicySet",
            "policy_set_id": "PS",
            "combiner": "first-applicable",
            "rules": [
                {"rule_id": "R1", "conditions": [{"type": "cond"}]},
                {"rule_id": "R2", "conditions": []},  # Unconditional → stop
                {"rule_id": "R3", "conditions": []},
            ],
            "policy_sets": [],
        }
        paths = enumerate_paths_pruned(policy)
        rule_ids = {p[-1] for p in paths}
        assert "R3" not in rule_ids  # Pruned


class TestCountRules:
    def test_flat(self):
        assert _count_rules(_simple_policy(7)) == 7


class TestFeasibilityPrune:
    def test_contradictory_removed(self):
        paths = [["root", "R1", "R2"], ["root", "R1", "R3"]]
        role_map = {"R1": "DOC", "R2": "ADM", "R3": "DOC"}
        feasible = feasibility_prune(paths, role_map)
        assert len(feasible) == 1  # R1+R3 survives, R1+R2 contradicts
