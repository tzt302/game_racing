import math
import config as cfg
from physics.vehicle import Vehicle

class AIOpponent(Vehicle):
    def __init__(self, track, x=0, y=0, heading=-math.pi/2):
        super().__init__(x, y, heading)
        self.track = track
        self.target_speed = 0.0
        self.difficulty = 'NORMAL'
        self.smooth_steer = 0.0

    def update(self, dt, _):
        if self.crashed:
            super().update(dt, 0, 0, 0)
            return

        ai_idx, ai_dist = self.track.find_nearest(self.x, self.y)
        c = self.track.center_points

        max_v = cfg.MAX_SPEED_MS * cfg.AI_SPEED_FACTOR
        if self.difficulty == 'EASY':
            max_v *= 0.75
        elif self.difficulty == 'HARD':
            max_v *= 1.05

        # Dynamic lookahead based on speed
        lookahead_dist = max(20.0, self.speed * 1.5)
        look_steps = int(lookahead_dist / 2.5)
        look_idx = min(ai_idx + look_steps, len(c) - 1)
        target = c[look_idx]
        dx = target[0] - self.x
        dy = target[1] - self.y
        target_heading = math.atan2(dy, dx)

        angle_diff = target_heading - self.heading
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi

        steer = max(-1.0, min(1.0, angle_diff * 2.5))

        # Look ahead for curvature
        max_curve = 0.0
        for j in range(ai_idx, min(ai_idx + 40, len(c))):
            max_curve = max(max_curve, abs(c[j][3]))
        speed_factor = 1.0
        if max_curve > 0.002:
            speed_factor = max(0.35, 0.5 - max_curve * 25)

        target_v = max_v * speed_factor

        throttle = 0.0
        brake = 0.0
        if self.speed < target_v * 0.95:
            throttle = min(1.0, (target_v - self.speed) / 8.0)
        elif self.speed > target_v * 1.02:
            brake = min(1.0, (self.speed - target_v) / 12.0)

        super().update(dt, steer, throttle, brake)