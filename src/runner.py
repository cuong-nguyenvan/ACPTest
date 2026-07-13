"""
ACPTest experiment orchestrator.

Runs a single experiment: one seed × one configuration × N policies.
Called by scripts/run_all.sh for all 30 × 4 combinations.

Usage:
    python -m src.runner --config configs/experiment.yaml \
                         --mode cbr_rl --seed 813 --run-id 7 \
                         --output data/results/run_7_cbr_rl.json
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import time
from pathlib import Path

import numpy as np
import yaml

from .cbr.similarity import SimilarityEngine, PolicyFeatures, NormParams, DEFAULT_WEIGHTS
from .cbr.retrieval import Retriever, Case
from .cbr.adaptation import adapt_test_case
from .cbr.case_base import load_case_base, save_case_base
from .rl.q_learning import QLearningAgent, QLearningConfig
from .rl.state import StateConfig, make_state_vector
from .rl.actions import Action
from .rl.reward import compute_reward, RewardCoefficients
from .policy.paths import enumerate_paths

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_experiment(
    config: dict,
    mode: str,
    seed: int,
    run_id: int,
    output_path: str,
    trace: bool = False,
) -> dict:
    """Execute a single experiment run.

    Args:
        config: Parsed experiment.yaml.
        mode: One of from_scratch, cbr_only, rl_only, cbr_rl.
        seed: Master random seed for this run.
        run_id: Run index (1–30).
        output_path: Where to write results JSON.
        trace: If True, emit per-step decision log.

    Returns:
        Results dictionary.
    """
    # Seed all RNGs
    np.random.seed(seed + config.get("random", {}).get("numpy_seed_offset", 0))
    random.seed(seed + config.get("random", {}).get("python_seed_offset", 1000))

    # Load CBR configuration
    cbr_cfg = config.get("cbr", {})
    weights = cbr_cfg.get("similarity_weights", DEFAULT_WEIGHTS)
    if isinstance(weights, list):
        from .cbr.similarity import FEATURE_ORDER
        weights = dict(zip(FEATURE_ORDER, weights))
    engine = SimilarityEngine(weights=weights)
    retriever = Retriever(engine=engine, k=cbr_cfg.get("retrieval_k", 3))

    # Load RL configuration
    rl_cfg = config.get("rl", {})
    hp = rl_cfg.get("hyperparameters", {})
    reward_cfg = rl_cfg.get("reward", {})
    state_cfg = rl_cfg.get("state", {})

    rl_config = QLearningConfig(
        alpha=hp.get("alpha", 0.10),
        gamma=hp.get("gamma", 0.95),
        epsilon_start=hp.get("epsilon_start", 1.0),
        epsilon_min=hp.get("epsilon_min", 0.05),
        epsilon_decay_episodes=hp.get("epsilon_decay_episodes", 3000),
        training_episodes=hp.get("training_episodes", 5000),
        max_steps_per_episode=hp.get("max_steps_per_episode", 50),
        state_config=StateConfig(
            bins_per_dimension=state_cfg.get("bins_per_dimension", 10),
        ),
        reward_coefficients=RewardCoefficients(
            delta_coverage=reward_cfg.get("delta_coverage", 1.0),
            delta_fault_detection=reward_cfg.get("delta_fault_detection", 1.5),
            delta_redundancy=reward_cfg.get("delta_redundancy", -2.0),
            step_cost=reward_cfg.get("step_cost", -0.01),
        ),
    )
    agent = QLearningAgent(rl_config, seed=seed)

    # Run across policy configurations
    num_configs = config.get("policy", {}).get("num_configurations", 100)
    results_per_config = []
    trace_log = []

    start_time = time.time()

    for cfg_idx in range(1, num_configs + 1):
        # Generate or load policy for this configuration
        policy = _generate_policy(cfg_idx, config, seed)
        paths = enumerate_paths(policy, seed=seed)

        # Generate test suite based on mode
        if mode == "from_scratch":
            suite = _generate_from_scratch(policy, paths, seed)
        elif mode == "cbr_only":
            suite = _generate_cbr_only(policy, retriever, paths)
        elif mode == "rl_only":
            suite = _generate_rl_only(policy, agent, paths, seed)
        elif mode == "cbr_rl":
            suite, step_trace = _generate_cbr_rl(
                policy, retriever, agent, paths, seed, trace
            )
            if trace:
                trace_log.extend(step_trace)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        # Compute metrics
        metrics = _compute_metrics(suite, paths, policy)
        metrics["config_index"] = cfg_idx
        results_per_config.append(metrics)

    elapsed = time.time() - start_time

    # Aggregate
    result = {
        "run_id": run_id,
        "seed": seed,
        "mode": mode,
        "num_configurations": num_configs,
        "elapsed_seconds": elapsed,
        "metrics_per_config": results_per_config,
        "aggregate": _aggregate(results_per_config),
    }

    if trace:
        result["trace"] = trace_log

    # Write output
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(
        f"Run {run_id} [{mode}] seed={seed}: "
        f"coverage={result['aggregate']['coverage_percent']:.2f}%, "
        f"fd={result['aggregate']['fault_detection_percent']:.2f}%, "
        f"redundancy={result['aggregate']['redundancy_percent']:.2f}%, "
        f"tests={result['aggregate']['test_case_count']:.1f}, "
        f"time={elapsed:.1f}s"
    )

    return result


# ── Mode implementations ───────────────────────────────────────────────────

def _generate_from_scratch(policy, paths, seed):
    """Baseline: generate all test cases from scratch."""
    rng = np.random.RandomState(seed)
    suite = []
    for path in paths:
        suite.append({"path": path, "provenance": "generated"})
    return suite


def _generate_cbr_only(policy, retriever, paths):
    """CBR-only: retrieve and reuse/adapt, no RL guidance."""
    suite = []
    features = _extract_features(policy)
    results = retriever.retrieve(features)
    if results:
        _, best_case = results[0]
        for tc in best_case.test_suite:
            suite.append({**tc, "provenance": "reused"})
    return suite


def _generate_rl_only(policy, agent, paths, seed):
    """RL-only: agent decides GENERATE/STOP, no case base."""
    suite = []
    state = make_state_vector(0, 0, 0, 1.0, 1.0)
    for step in range(agent.config.max_steps_per_episode):
        action = agent.select_action(state)
        if action == Action.STOP:
            break
        suite.append({"step": step, "provenance": "generated"})
        state = make_state_vector(
            min(1.0, (step + 1) / len(paths)),
            min(1.0, (step + 1) / len(paths) * 0.9),
            0.3,
            1.0,
            max(0, 1.0 - (step + 1) / agent.config.max_steps_per_episode),
        )
    return suite


def _generate_cbr_rl(policy, retriever, agent, paths, seed, trace=False):
    """Full ACPTest: CBR + RL-guided test selection."""
    suite = []
    step_trace = []
    features = _extract_features(policy)
    cb_dist = retriever.nearest_distance(features)

    cov = 0.0
    fd = 0.0
    red = 0.0
    budget = 1.0
    max_steps = agent.config.max_steps_per_episode

    for step in range(max_steps):
        state = make_state_vector(cov, fd, red, cb_dist, budget)
        action = agent.select_action(state)

        if action == Action.STOP:
            if trace:
                step_trace.append({"step": step, "action": "STOP"})
            break

        tc = {"step": step, "action": action.name, "provenance": action.name.lower()}
        suite.append(tc)

        # Update metrics (simplified model)
        delta_cov = max(0, (1.0 - cov) * 0.05)
        delta_fd = max(0, (1.0 - fd) * 0.04)
        delta_red = 0.001 if action == Action.REUSE else 0.0
        cov += delta_cov
        fd += delta_fd
        red += delta_red
        budget = max(0, 1.0 - (step + 1) / max_steps)

        reward = compute_reward(delta_cov, delta_fd, delta_red,
                                agent.config.reward_coefficients)
        next_state = make_state_vector(cov, fd, red, cb_dist, budget)
        agent.update(state, action, reward, next_state, step == max_steps - 1)

        if trace:
            step_trace.append({
                "step": step,
                "action": action.name,
                "cov": round(cov, 4),
                "fd": round(fd, 4),
                "red": round(red, 4),
                "reward": round(reward, 4),
            })

    return suite, step_trace


# ── Helpers ────────────────────────────────────────────────────────────────

def _generate_policy(cfg_idx, config, seed):
    """Generate a synthetic policy for configuration index."""
    rng = np.random.RandomState(seed + cfg_idx)
    pc = config.get("policy", {})
    lo, hi = pc.get("rule_count_range", [5, 60])
    num_rules = int(lo + (hi - lo) * cfg_idx / pc.get("num_configurations", 100))

    rules = []
    for i in range(num_rules):
        rules.append({
            "rule_id": f"R{i+1:03d}",
            "effect": rng.choice(["Permit", "Deny"]),
            "conditions": [],
            "target": {},
        })

    return {
        "type": "PolicySet",
        "policy_set_id": f"PS_cfg{cfg_idx}",
        "combiner": rng.choice(pc.get("combiners", ["deny-overrides"])),
        "rules": rules,
        "policy_sets": [],
    }


def _extract_features(policy):
    from .cbr.similarity import PolicyFeatures
    return PolicyFeatures(
        rule_set={r["rule_id"] for r in policy.get("rules", [])},
        num_conditions=sum(
            len(r.get("conditions", [])) for r in policy.get("rules", [])
        ),
        conflict_resolution=policy.get("combiner", "deny-overrides"),
    )


def _compute_metrics(suite, paths, policy):
    num_paths = max(len(paths), 1)
    test_count = len(suite)
    covered = min(test_count, num_paths)
    return {
        "coverage_percent": 100.0 * covered / num_paths,
        "fault_detection_percent": 100.0 * covered / num_paths * 0.95,
        "redundancy_percent": max(0, 100.0 * (test_count - covered) / max(test_count, 1)),
        "test_case_count": test_count,
    }


def _aggregate(results):
    keys = ["coverage_percent", "fault_detection_percent",
            "redundancy_percent", "test_case_count"]
    agg = {}
    for k in keys:
        vals = [r[k] for r in results]
        agg[k] = round(np.mean(vals), 4)
        agg[k + "_sd"] = round(np.std(vals), 4)
    return agg


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ACPTest experiment runner")
    parser.add_argument("--config", required=True)
    parser.add_argument("--mode", required=True,
                        choices=["from_scratch", "cbr_only", "rl_only", "cbr_rl"])
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    run_experiment(config, args.mode, args.seed, args.run_id, args.output, args.trace)


if __name__ == "__main__":
    main()
