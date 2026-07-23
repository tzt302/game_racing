import math
import config as cfg

class Vehicle:
    def __init__(self, x=0, y=0, heading=-math.pi/2):
        self.x = x
        self.y = y
        self.heading = heading
        self.speed = 0.0          # m/s
        self.steer_angle = 0.0    # radians
        self.throttle = 0.0
        self.brake = 0.0
        self.crashed = False

    def reset(self, x, y, heading=-math.pi/2):
        self.x = x
        self.y = y
        self.heading = heading
        self.speed = 0.0
        self.steer_angle = 0.0
        self.throttle = 0.0
        self.brake = 0.0
        self.crashed = False

    def update(self, dt, steer_input, throttle_input, brake_input):
        if self.crashed:
            self.speed *= 0.95
            if self.speed < 0.1:
                self.speed = 0
            self.x += self.speed * math.cos(self.heading) * dt
            self.y += self.speed * math.sin(self.heading) * dt
            return

        steer_input = max(-1.0, min(1.0, steer_input))
        throttle_input = max(0.0, min(1.0, throttle_input))
        brake_input = max(0.0, min(1.0, brake_input))

        self.throttle = throttle_input
        self.brake = brake_input

        # Steering with lag
        target_steer = steer_input * cfg.MAX_STEER_ANGLE
        steer_diff = target_steer - self.steer_angle
        max_steer_delta = cfg.STEER_SPEED * dt
        self.steer_angle += max(-max_steer_delta, min(max_steer_delta, steer_diff))

        # Acceleration
        accel = throttle_input * cfg.ACCEL_FORCE
        decel = brake_input * cfg.BRAKE_FORCE

        # Drag
        drag = cfg.DRAG_COEF * self.speed * abs(self.speed)
        rolling = cfg.ROLLING_RESISTANCE

        # Update speed
        self.speed += (accel - decel - drag - rolling) * dt
        self.speed = max(0.0, min(self.speed, cfg.MAX_SPEED_MS))

        # Bicycle model yaw rate
        if abs(self.speed) > 0.5:
            yaw_rate = self.speed * math.tan(self.steer_angle) / cfg.WHEELBASE
            self.heading += yaw_rate * dt

        # Position update
        self.x += self.speed * math.cos(self.heading) * dt
        self.y += self.speed * math.sin(self.heading) * dt

    def get_speed_kmh(self):
        return self.speed * 3.6

    def get_rect_px(self, cam_x, cam_y):
        cx = (self.x - cam_x) * cfg.PX_PER_M
        cy = (self.y - cam_y) * cfg.PX_PER_M
        return (cx - cfg.CAR_WIDTH_PX//2, cy - cfg.CAR_LENGTH_PX//2,
                cx + cfg.CAR_WIDTH_PX//2, cy + cfg.CAR_LENGTH_PX//2)

    def get_front_pos(self):
        return (self.x + (cfg.CAR_LENGTH/2) * math.cos(self.heading),
                self.y + (cfg.CAR_LENGTH/2) * math.sin(self.heading))
