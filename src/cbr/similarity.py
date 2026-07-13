"""
Weighted heterogeneous similarity function for CBR retrieval.

    sim(p, c_i)  =  1  -  sum_k  w_k * d_k(p_k, c_{i,k})

See REPRODUCIBILITY.md §1 for weight rationale and §2 for normalisation.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Set

# ── Default weights (REPRODUCIBILITY.md §1.2) ──────────────────────────────

DEFAULT_WEIGHTS: Dict[str, float] = {
    "rule_set_jaccard": 0.30,
    "subject_depth": 0.15,
    "object_depth": 0.15,
    "num_conditions": 0.15,
    "conflict_resolution": 0.10,
    "default_effect": 0.05,
    "combination_algorithm": 0.10,
}

FEATURE_ORDER: List[str] = list(DEFAULT_WEIGHTS.keys())

# ── Per-feature distance functions (REPRODUCIBILITY.md §1.4) ───────────────

def jaccard_distance(a: Set[str], b: Set[str]) -> float:
    """1 − |A ∩ B| / |A ∪ B|.  Returns 1.0 if both sets are empty."""
    if not a and not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return 1.0 - intersection / union


def numeric_distance(a: float, b: float, range_min: float, range_max: float) -> float:
    """Range-normalised absolute difference, clipped to [0, 1]."""
    if range_max <= range_min:
        return 0.0
    return min(1.0, abs(a - b) / (range_max - range_min))


def ordinal_distance(a: int, b: int, num_levels: int) -> float:
    """|rank(a) − rank(b)| / (L − 1)."""
    if num_levels <= 1:
        return 0.0
    return abs(a - b) / (num_levels - 1)


def categorical_distance(a: str, b: str) -> float:
    """0 if identical, 1 otherwise."""
    return 0.0 if a == b else 1.0


# ── Feature vector ─────────────────────────────────────────────────────────

@dataclass
class PolicyFeatures:
    """Extracted features of an access-control policy for CBR retrieval."""
    rule_set: Set[str] = field(default_factory=set)
    subject_depth: int = 1
    object_depth: int = 1
    num_conditions: int = 0
    conflict_resolution: str = "deny-overrides"
    default_effect: str = "Deny"
    combination_algorithm: str = "deny-overrides"


# ── Normalisation parameters ───────────────────────────────────────────────

@dataclass
class NormParams:
    """Min-max ranges and ordinal level counts, computed from the case base.
    Updated lazily at power-of-two boundaries (REPRODUCIBILITY.md §2.3)."""
    num_conditions_min: float = 0.0
    num_conditions_max: float = 15.0
    subject_depth_levels: int = 5
    object_depth_levels: int = 5
    winsor_lower: float = 0.02
    winsor_upper: float = 0.98
    last_refresh_size: int = 0

    def should_refresh(self, case_base_size: int) -> bool:
        if case_base_size <= 0:
            return False
        # Refresh at powers of two: 8, 16, 32, 64, …
        import math
        if case_base_size < 8:
            return False
        pot = 2 ** int(math.log2(case_base_size))
        return pot > self.last_refresh_size


# ── Main similarity computation ────────────────────────────────────────────

class SimilarityEngine:
    """Computes sim(query, case) using the weighted heterogeneous distance."""

    def __init__(
        self,
        weights: Dict[str, float] | None = None,
        norm_params: NormParams | None = None,
    ):
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        self.norm = norm_params or NormParams()

        # Validate weights sum to 1.0
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Weights must sum to 1.0, got {total:.6f}")

    def distance(self, query: PolicyFeatures, case: PolicyFeatures) -> float:
        """Weighted distance in [0, 1].  Lower = more similar."""
        d = {}
        d["rule_set_jaccard"] = jaccard_distance(query.rule_set, case.rule_set)
        d["subject_depth"] = ordinal_distance(
            query.subject_depth, case.subject_depth, self.norm.subject_depth_levels
        )
        d["object_depth"] = ordinal_distance(
            query.object_depth, case.object_depth, self.norm.object_depth_levels
        )
        d["num_conditions"] = numeric_distance(
            query.num_conditions, case.num_conditions,
            self.norm.num_conditions_min, self.norm.num_conditions_max,
        )
        d["conflict_resolution"] = categorical_distance(
            query.conflict_resolution, case.conflict_resolution
        )
        d["default_effect"] = categorical_distance(
            query.default_effect, case.default_effect
        )
        d["combination_algorithm"] = categorical_distance(
            query.combination_algorithm, case.combination_algorithm
        )

        weighted_dist = sum(self.weights[k] * d[k] for k in FEATURE_ORDER)
        return weighted_dist

    def similarity(self, query: PolicyFeatures, case: PolicyFeatures) -> float:
        """sim ∈ [0, 1].  Higher = more similar."""
        return 1.0 - self.distance(query, case)

    def update_norm_params(self, case_features_list: List[PolicyFeatures]) -> None:
        """Recompute normalisation parameters from the full case base."""
        if not case_features_list:
            return
        conditions = [f.num_conditions for f in case_features_list]

        # Winsorise (REPRODUCIBILITY.md §2.2)
        lo = np.percentile(conditions, self.norm.winsor_lower * 100)
        hi = np.percentile(conditions, self.norm.winsor_upper * 100)
        self.norm.num_conditions_min = lo
        self.norm.num_conditions_max = hi

        self.norm.subject_depth_levels = max(
            f.subject_depth for f in case_features_list
        )
        self.norm.object_depth_levels = max(
            f.object_depth for f in case_features_list
        )
        self.norm.last_refresh_size = len(case_features_list)
