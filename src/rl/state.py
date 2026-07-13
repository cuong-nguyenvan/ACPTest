"""
State discretisation for tabular Q-learning.

5-dimensional continuous state → discrete index via equal-width binning.
See REPRODUCIBILITY.md §4 for full specification.

Dimensions:
    0  cov       [0, 1]  Current cumulative path coverage
    1  fd        [0, 1]  Current cumulative fault-detection rate
    2  red       [0, 1]  Current redundancy ratio
    3  cb_dist   [0, 1]  Normalised distance to nearest case
    4  budget    [0, 1]  Remaining budget fraction
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass


@dataclass
class StateConfig:
    """Configuration for state discretisation."""
    num_dimensions: int = 5
    bins_per_dimension: int = 10  # B

    @property
    def total_states(self) -> int:
        """|S| = B^D"""
        return self.bins_per_dimension ** self.num_dimensions


def discretise(continuous_state: np.ndarray, config: StateConfig) -> int:
    """Map a continuous state vector to a discrete state index.

    bin_k(x) = min(floor(x * B), B - 1)
    s = sum_{k=0}^{D-1}  bin_k(x_k) * B^k

    Args:
        continuous_state: Array of shape (D,) with values in [0, 1].
        config: Discretisation configuration.

    Returns:
        Integer state index in [0, B^D - 1].
    """
    B = config.bins_per_dimension
    D = config.num_dimensions
    assert len(continuous_state) == D, (
        f"Expected {D}-dim state, got {len(continuous_state)}"
    )

    # Clip to [0, 1] for safety
    clipped = np.clip(continuous_state, 0.0, 1.0)

    # Bin each dimension
    bins = np.minimum(np.floor(clipped * B).astype(int), B - 1)

    # Composite index: polynomial encoding
    index = 0
    for k in range(D):
        index += int(bins[k]) * (B ** k)

    return index


def state_to_bins(state_index: int, config: StateConfig) -> np.ndarray:
    """Inverse: decompose a discrete index back into per-dimension bins."""
    B = config.bins_per_dimension
    D = config.num_dimensions
    bins = np.zeros(D, dtype=int)
    remainder = state_index
    for k in range(D):
        bins[k] = remainder % B
        remainder //= B
    return bins


def make_state_vector(
    coverage: float,
    fault_detection: float,
    redundancy: float,
    cb_distance: float,
    budget_remaining: float,
) -> np.ndarray:
    """Convenience constructor for the 5-D state vector."""
    return np.array([
        coverage,
        fault_detection,
        redundancy,
        cb_distance,
        budget_remaining,
    ], dtype=np.float64)
