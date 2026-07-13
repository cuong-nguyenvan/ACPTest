"""
Discrete action space for the Q-learning agent.
See REPRODUCIBILITY.md §4.5.
"""

from enum import IntEnum


class Action(IntEnum):
    REUSE = 0       # Retrieve and reuse highest-similarity test case as-is
    ADAPT = 1       # Retrieve nearest case and adapt it to the new policy
    GENERATE = 2    # Invoke from-scratch test generator
    STOP = 3        # Terminate test suite early (budget remains unspent)


NUM_ACTIONS = len(Action)

ACTION_NAMES = {a: a.name for a in Action}
