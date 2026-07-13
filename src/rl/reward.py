"""
Reward function for the Q-learning agent.

    r_t = Δcov_t + 1.5 · Δfd_t − 2.0 · Δred_t − 0.01

See REPRODUCIBILITY.md §4.6 for coefficient rationale.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RewardCoefficients:
    """Coefficients for the reward signal."""
    delta_coverage: float = 1.0
    delta_fault_detection: float = 1.5
    delta_redundancy: float = -2.0
    step_cost: float = -0.01


def compute_reward(
    delta_cov: float,
    delta_fd: float,
    delta_red: float,
    coefficients: RewardCoefficients | None = None,
) -> float:
    """Compute the scalar reward for a single test-placement step.

    Args:
        delta_cov: Change in coverage at this step.
        delta_fd:  Change in fault-detection rate at this step.
        delta_red: Change in redundancy ratio at this step.
        coefficients: Reward weights (defaults from REPRODUCIBILITY.md §4.6).

    Returns:
        Scalar reward.
    """
    c = coefficients or RewardCoefficients()
    return (
        c.delta_coverage * delta_cov
        + c.delta_fault_detection * delta_fd
        + c.delta_redundancy * delta_red
        + c.step_cost
    )
