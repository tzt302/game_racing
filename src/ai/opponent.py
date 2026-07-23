import math
import random

import config as cfg
from physics.vehicle import Vehicle


def _angle_delta(a, b):
    return (a - b + math.pi) % (2.0 * math.pi) - math.pi


class AIOpponent(Vehicle):
    def __init__(self, track, profile=None, x=0, y=0, heading=-math.pi / 2):
        super().__init__(x, y, heading)
        self.track = track
        profile = profile or {}
        self.driver_name = profile.get("name", "AI")
        self.skill = float(profile.get("skill", 0.88))
        self.aggression = float(profile.get("aggression", 0.55))
        self.consistency = float(profile.get("consistency", 0.90))
        self.color = tuple(profile.get("color", cfg.AI_CAR_COLOR))
        self.target_speed = 0.0
        self.difficulty = "NORMAL"
        self.smooth_steer = 0.0
        self.progress = 0.0
        self.lap = 1
        self.best_lap = float("inf")
        self.last_lap = 0.0
        self._rng = random.Random(self.driver_name)
        self._variation = 0.0
        self._variation_timer = 0.0
        self._mistake_timer = 0.0
        self._steer_bias = 0.0
        self._overtake_side = 0.0

    def update(self, dt, rivals=None):
        idx, distance = self.track.find_nearest(self.x, self.y)
        count = len(self.track.center_points)
        self.progress = idx / count

        self._variation_timer -= dt
        if self._variation_timer <= 0:
            spread = (1.0 - self.consistency) * 0.16
            self._variation = self._rng.uniform(-spread, spread)
            self._variation_timer = self._rng.uniform(0.8, 2.4)
        self._mistake_timer = max(0.0, self._mistake_timer - dt)
        if self._mistake_timer <= 0 and self._rng.random() < (1.0 - self.consistency) * dt * 0.09:
            self._mistake_timer = self._rng.uniform(0.45, 1.15)
            self._steer_bias = self._rng.uniform(-0.22, 0.22)
        elif self._mistake_timer <= 0:
            self._steer_bias *= max(0.0, 1.0 - dt * 3.0)

        self._overtake_side *= max(0.0, 1.0 - dt * 0.7)
        for rival in rivals or []:
            if rival is self:
                continue
            rival_idx, _ = self.track.find_nearest(rival.x, rival.y)
            gap_steps = (rival_idx - idx) % count
            if 0 < gap_steps < int(42 / self.track.SAMPLE_METRES):
                side = -1.0 if (hash(self.driver_name) & 1) else 1.0
                self._overtake_side = side * self.aggression * self.track.width * 0.24
                break

        lookahead_m = 18.0 + self.speed * 0.55
        look_steps = max(4, int(lookahead_m / self.track.SAMPLE_METRES))
        target_idx = (idx + look_steps) % count
        racing_target = self.track.racing_line[target_idx]
        center_target = self.track.center_points[target_idx]
        # Keep a safety margin that a human can choose to spend on the kerb.
        # The blend tightens toward the centre when the AI is already wide.
        line_weight = 0.72 if distance < self.track.width * 0.38 else 0.25
        target = (
            center_target[0] + (racing_target[0] - center_target[0]) * line_weight,
            center_target[1] + (racing_target[1] - center_target[1]) * line_weight,
        )
        target_heading_path = center_target[2]
        nx, ny = -math.sin(target_heading_path), math.cos(target_heading_path)
        target = (
            target[0] + nx * self._overtake_side,
            target[1] + ny * self._overtake_side,
        )
        target_heading = math.atan2(target[1] - self.y, target[0] - self.x)
        heading_error = _angle_delta(target_heading, self.heading)
        steer = max(-1.0, min(1.0, heading_error * 2.05 + self._steer_bias))
        self.smooth_steer += (steer - self.smooth_steer) * min(1.0, 7.0 * dt)

        preview = [
            self.track.recommended_speeds[(idx + j) % count]
            for j in range(5, max(6, int(175 / self.track.SAMPLE_METRES)))
        ]
        target_kmh = min(preview)
        difficulty = {"EASY": 0.90, "NORMAL": 1.0, "HARD": 1.045}.get(
            self.difficulty, 1.0
        )
        factor = (0.78 + self.skill * 0.18 + self._variation) * difficulty
        if self.track.width < 12.0:
            factor *= 0.90
        self.target_speed = min(cfg.MAX_SPEED_MS * factor, target_kmh / 3.6 * factor)
        if distance > self.track.width * 0.42:
            self.target_speed *= 0.72

        error = self.target_speed - self.speed
        throttle = max(0.0, min(1.0, error / 10.0 + 0.18))
        brake = max(0.0, min(1.0, -error / 13.0))
        if brake > 0.05:
            throttle = 0.0
        super().update(dt, self.smooth_steer, throttle, brake)
