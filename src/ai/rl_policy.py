"""Runtime helpers for exported reinforcement-learning driving policies.

The game can use these classes after a policy has been trained and exported.
This module deliberately has no dependency on PyTorch or Stable-Baselines3.
"""

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class DifficultyProfile:
    policy_interval: int
    throttle_cap: float
    brake_scale: float
    steering_scale: float
    action_smoothing: float
    reaction_frames: int
    deterministic_noise: float


DIFFICULTY_PROFILES = {
    "easy": DifficultyProfile(4, 0.88, 1.08, 0.92, 0.72, 3, 0.025),
    "normal": DifficultyProfile(2, 0.96, 1.03, 0.97, 0.48, 1, 0.010),
    "hard": DifficultyProfile(1, 1.00, 1.00, 1.00, 0.22, 0, 0.000),
}


def shape_action(action, difficulty, previous=None, noise_sample=None):
    """Convert the elite policy's action into a stable difficulty-specific action."""
    profile = DIFFICULTY_PROFILES[difficulty]
    current = np.clip(np.asarray(action, dtype=np.float32), -1.0, 1.0)
    steer = float(current[0]) * profile.steering_scale
    throttle = float((current[1] + 1.0) * 0.5) * profile.throttle_cap
    brake = float((current[2] + 1.0) * 0.5) * profile.brake_scale

    if noise_sample is not None and profile.deterministic_noise:
        steer += float(noise_sample) * profile.deterministic_noise

    # Brake has priority, avoiding an unrealistic full-throttle/full-brake state.
    brake = float(np.clip(brake, 0.0, 1.0))
    throttle = float(np.clip(throttle * (1.0 - 0.85 * brake), 0.0, 1.0))
    shaped = np.asarray([np.clip(steer, -1.0, 1.0), throttle, brake], dtype=np.float32)

    if previous is None:
        return shaped
    previous = np.asarray(previous, dtype=np.float32)
    alpha = profile.action_smoothing
    return (previous * alpha + shaped * (1.0 - alpha)).astype(np.float32)


class NumpyMLPPolicy:
    """Small dependency-free inference engine for an exported SAC actor."""

    def __init__(self, layers, observation_size, action_size=3):
        self.layers = layers
        self.observation_size = int(observation_size)
        self.action_size = int(action_size)

    @classmethod
    def load(cls, weights_path):
        weights_path = Path(weights_path)
        metadata_path = weights_path.with_suffix(".json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        archive = np.load(weights_path, allow_pickle=False)
        layers = []
        for index in range(int(metadata["layer_count"])):
            layers.append((archive[f"weight_{index}"], archive[f"bias_{index}"]))
        return cls(layers, metadata["observation_size"], metadata["action_size"])

    def predict(self, observation):
        value = np.asarray(observation, dtype=np.float32)
        if value.shape != (self.observation_size,):
            raise ValueError(
                f"Expected observation shape {(self.observation_size,)}, got {value.shape}"
            )
        for index, (weight, bias) in enumerate(self.layers):
            value = value @ weight.T + bias
            if index < len(self.layers) - 1:
                value = np.maximum(value, 0.0)
        return np.tanh(value).astype(np.float32)


class DifficultyController:
    """Apply reaction delay and action cadence around one learned elite policy."""

    def __init__(self, policy, difficulty="normal"):
        if difficulty not in DIFFICULTY_PROFILES:
            raise ValueError(f"Unknown difficulty: {difficulty}")
        self.policy = policy
        self.difficulty = difficulty
        self.profile = DIFFICULTY_PROFILES[difficulty]
        self.frame = 0
        self.last_action = np.zeros(3, dtype=np.float32)
        self.observations = []

    def reset(self):
        self.frame = 0
        self.last_action = np.zeros(3, dtype=np.float32)
        self.observations.clear()

    def act(self, observation, noise_sample=0.0):
        self.observations.append(np.asarray(observation, dtype=np.float32))
        maximum = self.profile.reaction_frames + 1
        if len(self.observations) > maximum:
            self.observations.pop(0)
        delayed = self.observations[0]
        if self.frame % self.profile.policy_interval == 0:
            elite_action = self.policy.predict(delayed)
            self.last_action = shape_action(
                elite_action,
                self.difficulty,
                previous=self.last_action,
                noise_sample=noise_sample,
            )
        self.frame += 1
        return self.last_action.copy()
