"""
Tabular Q-learning agent for test-suite construction.

Hyperparameters are documented in REPRODUCIBILITY.md §4.4.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple

from .actions import Action, NUM_ACTIONS
from .state import StateConfig, discretise
from .reward import compute_reward, RewardCoefficients


@dataclass
class QLearningConfig:
    """All hyperparameters for the Q-learning agent."""
    alpha: float = 0.10
    gamma: float = 0.95
    epsilon_start: float = 1.00
    epsilon_min: float = 0.05
    epsilon_decay_episodes: int = 3000
    training_episodes: int = 5000
    convergence_threshold: float = 0.005
    convergence_window: int = 200
    max_steps_per_episode: int = 50

    state_config: StateConfig = None
    reward_coefficients: RewardCoefficients = None

    def __post_init__(self):
        if self.state_config is None:
            self.state_config = StateConfig()
        if self.reward_coefficients is None:
            self.reward_coefficients = RewardCoefficients()


class QLearningAgent:
    """Tabular Q-learning agent with ε-greedy exploration."""

    def __init__(self, config: QLearningConfig, seed: int = 42):
        self.config = config
        self.rng = np.random.RandomState(seed)

        # Q-table: |S| × |A|, initialised to zero
        num_states = config.state_config.total_states
        self.q_table = np.zeros((num_states, NUM_ACTIONS), dtype=np.float64)

        # Tracking
        self.episode = 0
        self.td_errors: List[float] = []

    @property
    def epsilon(self) -> float:
        """Current ε (linear decay schedule)."""
        c = self.config
        if self.episode >= c.epsilon_decay_episodes:
            return c.epsilon_min
        return max(
            c.epsilon_min,
            c.epsilon_start
            - self.episode * (c.epsilon_start - c.epsilon_min) / c.epsilon_decay_episodes,
        )

    def select_action(self, state: np.ndarray) -> Action:
        """ε-greedy action selection."""
        s = discretise(state, self.config.state_config)
        if self.rng.random() < self.epsilon:
            return Action(self.rng.randint(NUM_ACTIONS))
        else:
            # Greedy; break ties randomly
            q_values = self.q_table[s]
            max_q = q_values.max()
            best_actions = np.where(np.isclose(q_values, max_q))[0]
            return Action(self.rng.choice(best_actions))

    def update(
        self,
        state: np.ndarray,
        action: Action,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> float:
        """Single Q-learning update.  Returns the TD error magnitude."""
        s = discretise(state, self.config.state_config)
        s_next = discretise(next_state, self.config.state_config)

        target = reward
        if not done:
            target += self.config.gamma * self.q_table[s_next].max()

        td_error = target - self.q_table[s, action]
        self.q_table[s, action] += self.config.alpha * td_error

        self.td_errors.append(abs(td_error))
        return abs(td_error)

    def has_converged(self) -> bool:
        """Check convergence: mean |TD-error| < threshold over window."""
        w = self.config.convergence_window
        if len(self.td_errors) < w:
            return False
        recent = self.td_errors[-w:]
        return np.mean(recent) < self.config.convergence_threshold

    def end_episode(self) -> None:
        """Increment episode counter."""
        self.episode += 1

    def save(self, path: str) -> None:
        """Save Q-table to disk."""
        np.save(path, self.q_table)

    def load(self, path: str) -> None:
        """Load Q-table from disk."""
        self.q_table = np.load(path)
