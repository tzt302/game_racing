"""Gymnasium environment that reuses the game's Track and Vehicle simulation."""

from collections import deque
import math
from pathlib import Path
import sys

import gymnasium as gym
from gymnasium import spaces
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import config as cfg
from physics.vehicle import Vehicle
from track.layouts import TRACK_ORDER
from track.track import Track


LOOKAHEAD_METRES = (10, 25, 50, 80, 120, 180)
OBSERVATION_SIZE = 14 + len(LOOKAHEAD_METRES) * 4
CONTROL_DT = 1.0 / 30.0
PHYSICS_SUBSTEPS = 2


def angle_delta(a, b):
    return (a - b + math.pi) % (2.0 * math.pi) - math.pi


class RacingEnv(gym.Env):
    """Single-car time-trial environment; construction/reset never auto-trains."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        track_ids=None,
        curriculum_stage=1,
        max_episode_seconds=160.0,
        seed=None,
    ):
        super().__init__()
        self.track_ids = tuple(track_ids or TRACK_ORDER)
        self.curriculum_stage = int(curriculum_stage)
        self.max_episode_steps = int(max_episode_seconds / CONTROL_DT)
        self.action_space = spaces.Box(-1.0, 1.0, shape=(3,), dtype=np.float32)
        self.observation_space = spaces.Box(
            -1.0, 1.0, shape=(OBSERVATION_SIZE,), dtype=np.float32
        )
        self.np_random = np.random.default_rng(seed)
        self.track = None
        self.car = None
        self.index = 0
        self.previous_index = 0
        self.unwrapped_progress = 0.0
        self.previous_action = np.zeros(3, dtype=np.float32)
        self.surface_time = 0.0
        self.no_progress_time = 0.0
        self.elapsed = 0.0
        self.track_limit_count = 0
        self.trajectory = []

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self.np_random = np.random.default_rng(seed)
        options = options or {}
        track_id = options.get("track_id") or self.np_random.choice(self.track_ids)
        self.track = Track(str(track_id))
        count = len(self.track.center_points)
        if "start_index" in options:
            start_index = int(options["start_index"]) % count
        elif self.curriculum_stage >= 2:
            start_index = int(self.np_random.integers(0, count))
        else:
            start_index = 0
        x, y, heading, _ = self.track.center_points[start_index]
        self.car = Vehicle(x, y, heading)
        self.car.speed = float(options.get("start_speed_ms", 0.0))
        self.index = self.previous_index = start_index
        self.unwrapped_progress = 0.0
        self.previous_action = np.zeros(3, dtype=np.float32)
        self.surface_time = self.no_progress_time = self.elapsed = 0.0
        self.track_limit_count = 0
        self.trajectory = []
        return self._observation(), self._info()

    def step(self, action):
        raw = np.clip(np.asarray(action, dtype=np.float32), -1.0, 1.0)
        steer = float(raw[0])
        throttle = float((raw[1] + 1.0) * 0.5)
        brake = float((raw[2] + 1.0) * 0.5)
        throttle *= 1.0 - 0.85 * brake
        if self.curriculum_stage == 1:
            throttle = min(throttle, 0.65)

        for _ in range(PHYSICS_SUBSTEPS):
            surface, _, _ = self.track.surface_at(self.car.x, self.car.y)
            self.car.set_surface(surface)
            self.car.update(CONTROL_DT / PHYSICS_SUBSTEPS, steer, throttle, brake)

        self.elapsed += CONTROL_DT
        self.previous_index = self.index
        surface, self.index, distance = self.track.surface_at(self.car.x, self.car.y)
        self.car.set_surface(surface)
        count = len(self.track.center_points)
        index_delta = (self.index - self.previous_index + count // 2) % count - count // 2
        progress_metres = index_delta * self.track.SAMPLE_METRES
        self.unwrapped_progress += progress_metres

        if progress_metres <= 0.05:
            self.no_progress_time += CONTROL_DT
        else:
            self.no_progress_time = 0.0
        if surface in ("runoff", "grass"):
            if self.surface_time == 0.0:
                self.track_limit_count += 1
            self.surface_time += CONTROL_DT
        else:
            self.surface_time = 0.0

        action_change = float(np.square(raw - self.previous_action).mean())
        reward = progress_metres * 0.12 - 0.025 - action_change * 0.015
        if surface == "kerb":
            reward -= 0.01
        elif surface == "runoff":
            reward -= 0.25
        elif surface == "grass":
            reward -= 0.75
        if index_delta < -1:
            reward -= 1.0

        completed_lap = self.unwrapped_progress >= self.track.total_length * 0.985
        terminated = completed_lap or self.surface_time > 2.0 or self.no_progress_time > 5.0
        truncated = self.elapsed >= self.max_episode_steps * CONTROL_DT
        if completed_lap:
            reward += 120.0 + max(
                -20.0, (self.track.reference_lap_time - self.elapsed) * 1.5
            )
        elif terminated:
            reward -= 20.0

        self.previous_action = raw
        self.trajectory.append(
            {
                "time": self.elapsed,
                "index": self.index,
                "x": self.car.x,
                "y": self.car.y,
                "speed_kmh": self.car.get_speed_kmh(),
                "steer": steer,
                "throttle": throttle,
                "brake": brake,
                "surface": surface,
            }
        )
        info = self._info()
        info["completed_lap"] = completed_lap
        info["distance_from_center"] = distance
        return self._observation(), float(reward), terminated, truncated, info

    def _observation(self):
        point = self.track.center_points[self.index]
        dx, dy = self.car.x - point[0], self.car.y - point[1]
        nx, ny = -math.sin(point[2]), math.cos(point[2])
        lateral = (dx * nx + dy * ny) / max(self.track.width * 0.5, 1.0)
        progress = self.index / len(self.track.center_points)
        surfaces = [
            1.0 if self.car.surface == name else 0.0
            for name in ("asphalt", "kerb", "runoff", "grass")
        ]
        values = [
            self.car.speed / cfg.MAX_SPEED_MS,
            self.car.steer_angle / max(cfg.STEER_LOCK_LOW, 0.01),
            self.car.slip_angle / max(cfg.MAX_SLIP_ANGLE, 0.01),
            self.car.yaw_rate / 4.0,
            self.car.throttle,
            self.car.brake,
            lateral,
            angle_delta(self.car.heading, point[2]) / math.pi,
            math.sin(progress * 2.0 * math.pi),
            math.cos(progress * 2.0 * math.pi),
            *surfaces,
        ]
        count = len(self.track.center_points)
        base_elevation = self.track.reference_elevation[self.index]
        teacher_hints = self.curriculum_stage <= 2
        for metres in LOOKAHEAD_METRES:
            future = (self.index + int(metres / self.track.SAMPLE_METRES)) % count
            curve = self.track.center_points[future][3]
            values.extend(
                [
                    curve / 0.05,
                    self.track.reference_speed[future] / cfg.MAX_SPEED
                    if teacher_hints
                    else 0.0,
                    float(self.track.reference_brake[future]) if teacher_hints else 0.0,
                    (self.track.reference_elevation[future] - base_elevation) / 30.0,
                ]
            )
        return np.clip(np.asarray(values, dtype=np.float32), -1.0, 1.0)

    def _info(self):
        return {
            "track_id": self.track.track_id,
            "lap_time": self.elapsed,
            "progress_metres": self.unwrapped_progress,
            "track_limit_count": self.track_limit_count,
            "surface": self.car.surface,
        }
