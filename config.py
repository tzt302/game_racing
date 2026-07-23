"""Shared configuration for Racing Line Pro."""

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS = 60
VSYNC = 1

# World scale.  The original 40 px/m view made a 15 m circuit almost fill the
# screen and hid the racing line.  12 px/m keeps the car readable while giving
# the driver enough look-ahead to judge a corner.
PX_PER_M = 12.0
TRACK_WIDTH = 15.0
KERB_WIDTH = 1.25
RUNOFF_WIDTH = 5.0

CAR_WIDTH = 2.0
CAR_LENGTH = 5.55
CAR_WIDTH_PX = int(CAR_WIDTH * PX_PER_M)
CAR_LENGTH_PX = int(CAR_LENGTH * PX_PER_M)

MAX_SPEED = 390.0
MAX_SPEED_MS = MAX_SPEED / 3.6
ACCEL_FORCE = 16.8
BRAKE_FORCE = 28.0
DRAG_COEF = 0.00095
ROLLING_RESISTANCE = 0.20
WHEELBASE = 3.6

# Steering is speed-sensitive: enough lock for Monaco's hairpin at low speed,
# but only a small, stable steering range at 300 km/h.
STEER_LOCK_LOW = 0.48
STEER_LOCK_HIGH = 0.145
STEER_RESPONSE_LOW = 3.2
STEER_RESPONSE_HIGH = 1.70
STEER_RETURN_RATE = 4.8
STEER_INPUT_EXPONENT = 1.55

# Mechanical grip dominates slow corners while downforce restores front-axle
# authority through medium and high-speed bends.  The previous aero value left
# the car at roughly 2.3 g near 300 km/h, so steering input saturated too early.
TYRE_GRIP = 2.04
AERO_GRIP = 0.00019
BRAKE_TURN_IN_GRIP = 0.10
YAW_RESPONSE = 10.4
BRAKE_YAW_RESPONSE = 2.2
SLIP_BUILD_RATE = 6.4
SLIP_FROM_EXCESS = 0.052
MAX_SLIP_ANGLE = 0.105
LOOK_AHEAD = 0.70

BLACK = (12, 15, 18)
WHITE = (245, 247, 249)
LIGHT_GRAY = (205, 211, 216)
MID_GRAY = (118, 126, 134)
DARK_GRAY = (45, 51, 57)
TRACK_COLOR = (63, 68, 73)
TRACK_BORDER = (21, 24, 27)
GRASS_COLOR = (42, 83, 52)
GRASS_STRIPE = (47, 91, 57)
RUNOFF_COLOR = (115, 109, 91)
KERB_RED = (220, 37, 45)
KERB_WHITE = (245, 245, 238)
ROAD_CENTER = (92, 98, 104)
RACING_LINE_COLOR = (32, 214, 230)
RACING_LINE_BRAKE = (255, 72, 55)
RACING_LINE_LIFT = (255, 190, 45)
BRAKE_POINT_COLOR = (255, 55, 45)
CAR_COLOR = (230, 35, 45)
AI_CAR_COLOR = (50, 120, 255)
HUD_BG = (9, 12, 15)
HUD_TEXT = WHITE
HUD_LABEL = (145, 154, 163)
MENU_ACCENT = (32, 214, 230)

AI_SPEED_FACTOR = 0.94
AI_STEER_SMOOTH = 0.12
AI_LOOKAHEAD = 55.0
GAMEPAD_DEADZONE = 0.12
