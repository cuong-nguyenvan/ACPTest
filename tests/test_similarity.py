"""Unit tests for CBR similarity engine."""

import pytest
from src.cbr.similarity import (
    SimilarityEngine, PolicyFeatures, NormParams,
    jaccard_distance, numeric_distance, ordinal_distance, categorical_distance,
)


class TestDistanceFunctions:
    def test_jaccard_identical(self):
        assert jaccard_distance({"a", "b"}, {"a", "b"}) == 0.0

    def test_jaccard_disjoint(self):
        assert jaccard_distance({"a"}, {"b"}) == 1.0

    def test_jaccard_partial(self):
        assert abs(jaccard_distance({"a", "b", "c"}, {"a", "b"}) - 1 / 3) < 1e-6

    def test_jaccard_empty(self):
        assert jaccard_distance(set(), set()) == 0.0

    def test_numeric_same(self):
        assert numeric_distance(5.0, 5.0, 0.0, 10.0) == 0.0

    def test_numeric_max(self):
        assert numeric_distance(0.0, 10.0, 0.0, 10.0) == 1.0

    def test_ordinal(self):
        assert ordinal_distance(1, 3, 5) == 0.5

    def test_categorical_same(self):
        assert categorical_distance("a", "a") == 0.0

    def test_categorical_diff(self):
        assert categorical_distance("a", "b") == 1.0


class TestSimilarityEngine:
    def test_self_similarity(self):
        engine = SimilarityEngine()
        f = PolicyFeatures(rule_set={"R1", "R2"}, subject_depth=2,
                           num_conditions=5)
        assert engine.similarity(f, f) == 1.0

    def test_weights_sum_validation(self):
        with pytest.raises(ValueError):
            SimilarityEngine(weights={"rule_set_jaccard": 0.5})

    def test_distance_range(self):
        engine = SimilarityEngine()
        f1 = PolicyFeatures(rule_set={"R1"}, default_effect="Permit")
        f2 = PolicyFeatures(rule_set={"R99"}, default_effect="Deny")
        d = engine.distance(f1, f2)
        assert 0.0 <= d <= 1.0

    def test_norm_refresh(self):
        norm = NormParams(last_refresh_size=4)
        assert norm.should_refresh(8) is True
        assert norm.should_refresh(7) is False
