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

        # Progressive input requests a fraction of the currently available
        # lateral acceleration. The road-wheel angle is then derived from the
        # bicycle geometry, preserving full mechanical lock only at low speed.
        shaped = math.copysign(
            math.sin(abs(steer_input) * math.pi * 0.5) ** cfg.STEER_INPUT_EXPONENT,
            steer_input,
        )
        base_lateral_limit = self.get_lateral_grip_limit(0.0, 0.0)
        control_speed = max(self.speed, cfg.STEER_LOW_SPEED_BLEND_MS)
        requested_accel = shaped * base_lateral_limit * cfg.STEER_G_DEMAND
        effective_wheelbase = (
            cfg.WHEELBASE + cfg.UNDERSTEER_GRADIENT * self.speed * self.speed
        )
        target_steer = math.atan(
            requested_accel * effective_wheelbase / (control_speed * control_speed)
        )
        low_speed_blend = 1.0 - _clamp(
            self.speed / cfg.STEER_LOW_SPEED_BLEND_MS, 0.0, 1.0
        )
        target_steer += (
            shaped * cfg.STEER_LOCK - target_steer
        ) * low_speed_blend
        target_steer = _clamp(target_steer, -cfg.STEER_LOCK, cfg.STEER_LOCK)

        rack_rate = cfg.STEER_RACK_RATE_LOW + (
            cfg.STEER_RACK_RATE_HIGH - cfg.STEER_RACK_RATE_LOW
        ) * speed_ratio
        if abs(steer_input) < 0.02:
            rack_rate = cfg.STEER_RETURN_RATE
        delta = _clamp(
            target_steer - self.steer_angle,
            -rack_rate * dt,
            rack_rate * dt,
        )
        self.steer_angle += delta

        engine_fade = 1.0 - 0.42 * speed_ratio ** 1.7
        engine = throttle_input * cfg.ACCEL_FORCE * engine_fade * surface["drive"]
        if self.shift_timer > 0.0:
            engine *= 0.25
        braking = brake_input * cfg.BRAKE_FORCE * (0.88 + 0.12 * surface["grip"])
        engine_braking = self.get_engine_braking(throttle_input)
        aero_drag = cfg.DRAG_COEF * self.speed * self.speed
        rolling = cfg.ROLLING_RESISTANCE * surface["rolling"]
        self.speed += (
            engine - braking - engine_braking - aero_drag - rolling
        ) * dt
        self.speed = _clamp(self.speed, 0.0, cfg.MAX_SPEED_MS)
        self._update_gearbox()

        if self.speed > 0.35:
            effective_wheelbase = (
                cfg.WHEELBASE + cfg.UNDERSTEER_GRADIENT * self.speed * self.speed
            )
            demanded_yaw = (
                self.speed * math.tan(self.steer_angle) / effective_wheelbase
            )
            demanded_yaw *= 1.0 + cfg.TRAIL_BRAKE_ROTATION * brake_input
            lateral_accel_limit = self.get_lateral_grip_limit(
                brake_input, throttle_input
            )
            yaw_limit = lateral_accel_limit / max(self.speed, 3.0)
            target_yaw = _clamp(demanded_yaw, -yaw_limit, yaw_limit)

            # Pneumatic tyres build lateral force over distance. This
            # first-order relaxation avoids instant rotation while naturally
            # responding faster as speed rises.
            relaxation_time = _clamp(
                cfg.TYRE_RELAXATION_LENGTH / max(self.speed, 5.0),
                0.04,
                0.24,
            )
            yaw_alpha = 1.0 - math.exp(
                -surface["grip"] * dt / relaxation_time
            )
            self.yaw_rate += (target_yaw - self.yaw_rate) * yaw_alpha

            excess = demanded_yaw - target_yaw
            kinematic_slip = math.atan(0.48 * math.tan(self.steer_angle))
            grip_utilisation = abs(target_yaw) / max(yaw_limit, 0.001)
            target_slip = _clamp(
                kinematic_slip * max(0.0, 1.0 - grip_utilisation * grip_utilisation)
                - excess * cfg.SLIP_FROM_EXCESS,
                -cfg.MAX_SLIP_ANGLE,
                cfg.MAX_SLIP_ANGLE,
            )
            self.slip_angle += (target_slip - self.slip_angle) * min(
                1.0, cfg.SLIP_BUILD_RATE * dt
            )
            self.heading = (self.heading + self.yaw_rate * dt + math.pi) % (2 * math.pi) - math.pi
        else:
            self.yaw_rate *= max(0.0, 1.0 - 8.0 * dt)
            self.slip_angle *= max(0.0, 1.0 - 6.0 * dt)

        travel_heading = self.heading + self.slip_angle
        self.x += self.speed * math.cos(travel_heading) * dt
        self.y += self.speed * math.sin(travel_heading) * dt

    def get_lateral_grip_limit(self, brake_input=None, throttle_input=None):
        """Return available lateral acceleration after friction-circle usage."""
        brake = self.brake if brake_input is None else float(brake_input or 0.0)
        throttle = (
            self.throttle if throttle_input is None else float(throttle_input or 0.0)
        )
        surface_grip = self.SURFACE[self.surface]["grip"]
        base_grip = (
            cfg.TYRE_GRIP + cfg.AERO_GRIP * self.speed * self.speed
        ) * surface_grip * 9.81
        longitudinal_usage = _clamp(
            brake * cfg.BRAKE_GRIP_USAGE
            + throttle * cfg.THROTTLE_GRIP_USAGE,
            0.0,
            0.98,
        )
        return base_grip * math.sqrt(max(0.0, 1.0 - longitudinal_usage ** 2))

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

    def get_engine_braking(self, throttle_input=None):
        """Return lift-off power-unit deceleration in metres per second squared."""
        throttle = self.throttle if throttle_input is None else float(throttle_input or 0.0)
        cutoff = max(cfg.ENGINE_BRAKE_THROTTLE_CUTOFF, 0.001)
        lift = _clamp((cutoff - throttle) / cutoff, 0.0, 1.0)
        if lift <= 0.0 or self.speed <= 0.0:
            return 0.0
        rpm_ratio = _clamp((self.rpm - 4000.0) / 9000.0, 0.0, 1.0)
        gear_multiplier = 1.0 + max(0, 8 - self.gear) * cfg.ENGINE_BRAKE_GEAR_GAIN
        low_speed_fade = _clamp(
            self.speed / max(cfg.ENGINE_BRAKE_LOW_SPEED_MS, 0.1), 0.0, 1.0
        )
        return (
            lift
            * (cfg.ENGINE_BRAKE_BASE + cfg.ENGINE_BRAKE_RPM_GAIN * rpm_ratio)
            * gear_multiplier
            * low_speed_fade
        )

    def get_speed_kmh(self):
        return self.speed * 3.6

    def get_front_pos(self):
        return (
            self.x + (cfg.CAR_LENGTH / 2) * math.cos(self.heading),
            self.y + (cfg.CAR_LENGTH / 2) * math.sin(self.heading),
        )
