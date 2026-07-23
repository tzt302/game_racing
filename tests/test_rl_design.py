import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai.rl_policy import (
    DIFFICULTY_PROFILES,
    DifficultyController,
    NumpyMLPPolicy,
    shape_action,
)


class ConstantPolicy:
    def __init__(self, action):
        self.action = np.asarray(action, dtype=np.float32)
        self.calls = 0

    def predict(self, observation):
        self.calls += 1
        return self.action


class DifficultyTests(unittest.TestCase):
    def test_harder_profiles_have_more_response_and_throttle(self):
        self.assertLess(
            DIFFICULTY_PROFILES["hard"].policy_interval,
            DIFFICULTY_PROFILES["easy"].policy_interval,
        )
        self.assertGreater(
            DIFFICULTY_PROFILES["hard"].throttle_cap,
            DIFFICULTY_PROFILES["easy"].throttle_cap,
        )
        self.assertLess(
            DIFFICULTY_PROFILES["hard"].reaction_frames,
            DIFFICULTY_PROFILES["easy"].reaction_frames,
        )

    def test_brake_priority_prevents_full_throttle_and_brake(self):
        output = shape_action([0.0, 1.0, 1.0], "hard")
        self.assertEqual(output[2], 1.0)
        self.assertLess(output[1], 0.2)

    def test_easy_policy_updates_less_often_than_hard(self):
        observation = np.zeros(38, dtype=np.float32)
        easy_policy = ConstantPolicy([0.0, 0.0, -1.0])
        hard_policy = ConstantPolicy([0.0, 0.0, -1.0])
        easy = DifficultyController(easy_policy, "easy")
        hard = DifficultyController(hard_policy, "hard")
        for _ in range(8):
            easy.act(observation)
            hard.act(observation)
        self.assertEqual(easy_policy.calls, 2)
        self.assertEqual(hard_policy.calls, 8)


class PolicyTests(unittest.TestCase):
    def test_numpy_policy_validates_observation_size(self):
        policy = NumpyMLPPolicy(
            [(np.zeros((3, 4), dtype=np.float32), np.zeros(3, dtype=np.float32))],
            observation_size=4,
        )
        with self.assertRaises(ValueError):
            policy.predict(np.zeros(3, dtype=np.float32))
        action = policy.predict(np.zeros(4, dtype=np.float32))
        self.assertEqual(action.shape, (3,))


if __name__ == "__main__":
    unittest.main()
