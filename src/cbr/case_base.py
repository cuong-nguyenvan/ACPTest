"""
Case-base management: persistence, insertion, and eviction.
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import List

from .retrieval import Case, Retriever
from .similarity import PolicyFeatures, SimilarityEngine, NormParams


def load_case_base(path: str | Path, engine: SimilarityEngine, k: int = 3) -> Retriever:
    """Load a JSON case base from disk and return a populated Retriever."""
    path = Path(path)
    retriever = Retriever(engine=engine, k=k)

    if path.is_file():
        with open(path, "r") as f:
            data = json.load(f)
        for entry in data.get("cases", []):
            features = PolicyFeatures(
                rule_set=set(entry.get("rule_set", [])),
                subject_depth=entry.get("subject_depth", 1),
                object_depth=entry.get("object_depth", 1),
                num_conditions=entry.get("num_conditions", 0),
                conflict_resolution=entry.get("conflict_resolution", "deny-overrides"),
                default_effect=entry.get("default_effect", "Deny"),
                combination_algorithm=entry.get("combination_algorithm", "deny-overrides"),
            )
            case = Case(
                case_id=entry["case_id"],
                features=features,
                test_suite=entry.get("test_suite", []),
                metadata=entry.get("metadata"),
            )
            retriever.add_case(case)

    retriever.maybe_refresh_norms()
    return retriever


def save_case_base(retriever: Retriever, path: str | Path) -> None:
    """Serialise the case base to JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    entries = []
    for case in retriever.case_base:
        entries.append({
            "case_id": case.case_id,
            "rule_set": sorted(case.features.rule_set),
            "subject_depth": case.features.subject_depth,
            "object_depth": case.features.object_depth,
            "num_conditions": case.features.num_conditions,
            "conflict_resolution": case.features.conflict_resolution,
            "default_effect": case.features.default_effect,
            "combination_algorithm": case.features.combination_algorithm,
            "test_suite": case.test_suite,
            "metadata": case.metadata,
        })

    with open(path, "w") as f:
        json.dump({"cases": entries, "size": len(entries)}, f, indent=2)


def policy_hash(policy_xml: str) -> str:
    """SHA-256 hash of canonicalised policy XML for path caching."""
    normalised = policy_xml.strip().encode("utf-8")
    return hashlib.sha256(normalised).hexdigest()
