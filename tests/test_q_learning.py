"""Unit tests for Q-learning agent."""

import numpy as np
import pytest
from src.rl.q_learning import QLearningAgent, QLearningConfig
from src.rl.state import StateConfig, discretise, make_state_vector
from src.rl.actions import Action, NUM_ACTIONS
from src.rl.reward import compute_reward, RewardCoefficients


class TestStateDiscretisation:
    def test_zero_state(self):
        cfg = StateConfig(bins_per_dimension=10)
        s = make_state_vector(0, 0, 0, 0, 0)
        assert discretise(s, cfg) == 0

    def test_max_state(self):
        cfg = StateConfig(bins_per_dimension=10)
        s = make_state_vector(1, 1, 1, 1, 1)
        assert discretise(s, cfg) == 99999

    def test_total_states(self):
        cfg = StateConfig(bins_per_dimension=10)
        assert cfg.total_states == 100_000

    def test_bin_boundaries(self):
        cfg = StateConfig(bins_per_dimension=10)
        s = make_state_vector(0.15, 0, 0, 0, 0)
        idx = discretise(s, cfg)
        assert idx == 1  # bin 1 for first dimension


class TestReward:
    def test_default_coefficients(self):
        r = compute_reward(0.1, 0.1, 0.0)
        assert abs(r - (0.1 + 0.15 + 0 - 0.01)) < 1e-6

    def test_redundancy_penalty(self):
        r = compute_reward(0, 0, 0.1)
        assert r < 0  # step_cost + redundancy penalty


class TestQLearningAgent:
    def test_initial_epsilon(self):
        agent = QLearningAgent(QLearningConfig(), seed=42)
        assert agent.epsilon == 1.0

    def test_epsilon_decay(self):
        agent = QLearningAgent(QLearningConfig(epsilon_decay_episodes=100), seed=42)
        agent.episode = 50
        assert 0.5 < agent.epsilon < 0.55

    def test_epsilon_floor(self):
        agent = QLearningAgent(QLearningConfig(), seed=42)
        agent.episode = 10000
        assert agent.epsilon == 0.05

    def test_q_table_shape(self):
        cfg = QLearningConfig()
        agent = QLearningAgent(cfg, seed=42)
        assert agent.q_table.shape == (100_000, NUM_ACTIONS)

    def test_update_changes_q(self):
        agent = QLearningAgent(QLearningConfig(), seed=42)
        s = make_state_vector(0.5, 0.5, 0, 0.5, 0.5)
        ns = make_state_vector(0.6, 0.6, 0, 0.5, 0.4)
        agent.update(s, Action.REUSE, 0.5, ns, False)
        idx = discretise(s, agent.config.state_config)
        assert agent.q_table[idx, Action.REUSE] > 0
