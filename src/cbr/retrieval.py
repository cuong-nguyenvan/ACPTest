"""
k-NN retrieval from the case base with tie-breaking.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Any, List, Tuple

from .similarity import PolicyFeatures, SimilarityEngine


@dataclass
class Case:
    """A stored case: policy features + associated test suite."""
    case_id: str
    features: PolicyFeatures
    test_suite: List[dict]
    metadata: dict | None = None


class Retriever:
    """Top-k retrieval engine backed by SimilarityEngine."""

    def __init__(self, engine: SimilarityEngine, k: int = 3):
        self.engine = engine
        self.k = k
        self.case_base: List[Case] = []

    def add_case(self, case: Case) -> None:
        self.case_base.append(case)

    def retrieve(self, query: PolicyFeatures) -> List[Tuple[float, Case]]:
        """Return top-k most similar cases as (similarity, Case) pairs,
        sorted descending by similarity.  Ties broken by case_id (stable)."""
        scored = []
        for case in self.case_base:
            sim = self.engine.similarity(query, case.features)
            # heapq is a min-heap; negate sim for max-k behaviour
            heapq.heappush(scored, (-sim, case.case_id, case))
            if len(scored) > self.k:
                heapq.heappop(scored)

        # Sort descending by similarity
        result = [(-neg_sim, c) for neg_sim, _, c in scored]
        result.sort(key=lambda x: (-x[0], x[1].case_id))
        return result

    def nearest_distance(self, query: PolicyFeatures) -> float:
        """Return the distance to the nearest case (for RL state cb_dist)."""
        if not self.case_base:
            return 1.0
        return min(
            self.engine.distance(query, c.features) for c in self.case_base
        )

    def maybe_refresh_norms(self) -> None:
        """Refresh normalisation params if case-base size crossed a
        power-of-two boundary (REPRODUCIBILITY.md §2.3)."""
        if self.engine.norm.should_refresh(len(self.case_base)):
            features = [c.features for c in self.case_base]
            self.engine.update_norm_params(features)
