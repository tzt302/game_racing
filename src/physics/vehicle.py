import math

import config as cfg


def _clamp(value, low, high):
    return max(low, min(high, value))


class Vehicle:
    """Speed-sensitive single-track model with a lightweight tyre grip limit."""

    SURFACE = {
        "asphalt": {"grip": 1.00, "drive": 1.00, "rolling": 1.00},
        "kerb": {"grip": 0.88, "drive": 0.92, "rolling": 2.00},
        "runoff": {"grip": 0.72, "drive": 0.68, "rolling": 4.50},
        "grass": {"grip": 0.40, "drive": 0.32, "rolling": 9.00},
    }

    def __init__(self, x=0, y=0, heading=-math.pi / 2):
        self.x = x
        self.y = y
        self.heading = heading
        self.speed = 0.0
        self.steer_angle = 0.0
        self.slip_angle = 0.0
        self.yaw_rate = 0.0
        self.throttle = 0.0
        self.brake = 0.0
        self.surface = "asphalt"
        self.crashed = False
        self.off_track = False
        self.gear = 1
        self.rpm = 4000
        self.shift_timer = 0.0
        self.shift_event = False

    def reset(self, x, y, heading=-math.pi / 2):
        self.x = x
        self.y = y
        self.heading = heading
        self.speed = 0.0
        self.steer_angle = 0.0
        self.slip_angle = 0.0
        self.yaw_rate = 0.0
        self.throttle = 0.0
        self.brake = 0.0
        self.surface = "asphalt"
        self.crashed = False
        self.off_track = False
        self.gear = 1
        self.rpm = 4000
        self.shift_timer = 0.0
        self.shift_event = False

    def set_surface(self, surface):
        self.surface = surface if surface in self.SURFACE else "asphalt"
        self.off_track = self.surface not in ("asphalt", "kerb")

    def update(self, dt, steer_input, throttle_input, brake_input):
        steer_input = _clamp(float(steer_input or 0.0), -1.0, 1.0)
        throttle_input = _clamp(float(throttle_input or 0.0), 0.0, 1.0)
        brake_input = _clamp(float(brake_input or 0.0), 0.0, 1.0)
        self.throttle = throttle_input
        self.brake = brake_input
        self.shift_event = False
        self.shift_timer = max(0.0, self.shift_timer - dt)

        surface = self.SURFACE[self.surface]
        speed_ratio = _clamp(self.speed / cfg.MAX_SPEED_MS, 0.0, 1.0)

        # Progressive steering input removes the keyboard's abrupt full-lock
        # behaviour.  Available lock drops smoothly as aerodynamic speed rises.
        shaped = math.copysign(abs(steer_input) ** cfg.STEER_INPUT_EXPONENT, steer_input)
        lock_blend = speed_ratio ** 0.72
        max_lock = cfg.STEER_LOCK_LOW + (cfg.STEER_LOCK_HIGH - cfg.STEER_LOCK_LOW) * lock_blend
        target_steer = shaped * max_lock
        response = cfg.STEER_RESPONSE_LOW + (
            cfg.STEER_RESPONSE_HIGH - cfg.STEER_RESPONSE_LOW
        ) * speed_ratio
        if abs(steer_input) < 0.02:
            response = cfg.STEER_RETURN_RATE
        delta = _clamp(target_steer - self.steer_angle, -response * dt, response * dt)
        self.steer_angle += delta

        engine_fade = 1.0 - 0.42 * speed_ratio ** 1.7
        engine = throttle_input * cfg.ACCEL_FORCE * engine_fade * surface["drive"]
        if self.shift_timer > 0.0:
            engine *= 0.25
        braking = brake_input * cfg.BRAKE_FORCE * (0.88 + 0.12 * surface["grip"])
        aero_drag = cfg.DRAG_COEF * self.speed * self.speed
        rolling = cfg.ROLLING_RESISTANCE * surface["rolling"]
        self.speed += (engine - braking - aero_drag - rolling) * dt
        self.speed = _clamp(self.speed, 0.0, cfg.MAX_SPEED_MS)
        self._update_gearbox()

        if self.speed > 0.35:
            demanded_yaw = self.speed * math.tan(self.steer_angle) / cfg.WHEELBASE
            lateral_accel_limit = (
                cfg.TYRE_GRIP * surface["grip"] * 9.81
                + cfg.AERO_GRIP * surface["grip"] * self.speed * self.speed * 9.81
            )
            yaw_limit = lateral_accel_limit / max(self.speed, 3.0)
            target_yaw = _clamp(demanded_yaw, -yaw_limit, yaw_limit)

            # Tyres build force rather than snapping instantly.  Exceeding the
            # grip circle introduces visible, recoverable understeer/slip.
            yaw_response = 8.8 * surface["grip"]
            self.yaw_rate += (target_yaw - self.yaw_rate) * min(1.0, yaw_response * dt)
            excess = demanded_yaw - target_yaw
            target_slip = _clamp(excess * 0.075, -0.13, 0.13)
            self.slip_angle += (target_slip - self.slip_angle) * min(1.0, 5.4 * dt)
            self.heading = (self.heading + self.yaw_rate * dt + math.pi) % (2 * math.pi) - math.pi
        else:
            self.yaw_rate *= max(0.0, 1.0 - 8.0 * dt)
            self.slip_angle *= max(0.0, 1.0 - 6.0 * dt)

        travel_heading = self.heading + self.slip_angle
        self.x += self.speed * math.cos(travel_heading) * dt
        self.y += self.speed * math.sin(travel_heading) * dt

    def _update_gearbox(self):
        speed_kmh = self.get_speed_kmh()
        upper_bounds = [78, 122, 168, 216, 266, 314, 354, 398]
        lower_bounds = [0, 56, 96, 136, 178, 224, 272, 318]
        desired = self.gear
        while desired < 8 and speed_kmh > upper_bounds[desired - 1]:
            desired += 1
        while desired > 1 and speed_kmh < lower_bounds[desired - 1]:
            desired -= 1
        if desired != self.gear and self.shift_timer <= 0.0:
            self.gear = desired
            self.shift_timer = 0.13
            self.shift_event = True

        lower = lower_bounds[self.gear - 1]
        upper = upper_bounds[self.gear - 1]
        ratio = _clamp((speed_kmh - lower) / max(upper - lower, 1.0), 0.0, 1.0)
        self.rpm = int(4200 + ratio * 8800)

    def get_speed_kmh(self):
        return self.speed * 3.6

    def get_front_pos(self):
        return (
            self.x + (cfg.CAR_LENGTH / 2) * math.cos(self.heading),
            self.y + (cfg.CAR_LENGTH / 2) * math.sin(self.heading),
        )
