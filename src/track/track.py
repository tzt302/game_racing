import math
import json
from pathlib import Path

import config as cfg
from track.layouts import TRACKS


_TELEMETRY_PATH = Path(__file__).with_name("telemetry_layouts.json")
with _TELEMETRY_PATH.open(encoding="utf-8") as _telemetry_file:
    TELEMETRY_LAYOUTS = json.load(_telemetry_file)


def _angle_delta(a, b):
    return (a - b + math.pi) % (2.0 * math.pi) - math.pi


def _distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


class Track:
    """Smooth, closed circuit generated from a compact real-world layout."""

    SAMPLE_METRES = 5.0

    def __init__(self, track_id="spa"):
        if track_id not in TRACKS:
            track_id = "spa"
        self.track_id = track_id
        self.meta = TRACKS[track_id]
        self.name = self.meta["name"]
        self.country = self.meta["country"]
        self.description = self.meta["description"]
        self.accent = self.meta["accent"]
        self.width = float(self.meta["width"])
        self.total_length = float(self.meta["length_m"])
        self.default_laps = int(self.meta["laps"])

        self.center_points = []
        self.left_edges = []
        self.right_edges = []
        self.kerb_left_edges = []
        self.kerb_right_edges = []
        self.racing_line = []
        self.racing_line_offsets = []
        self.recommended_speeds = []
        self.brake_zones = []
        self.brake_zone_indices = set()
        self.lift_zone_indices = set()
        self.reference_speed = []
        self.reference_gear = []
        self.reference_throttle = []
        self.reference_brake = []
        self.reference_rpm = []
        self.reference_elevation = []
        self.reference_driver = ""
        self.reference_lap_time = 0.0
        self.reference_sector_times = []
        self.sector_indices = []
        self._generate()

    def _generate(self):
        telemetry = TELEMETRY_LAYOUTS[self.track_id]
        raw = telemetry["points"]
        points = [(float(p[0]), float(p[1])) for p in raw]
        self.total_length = float(telemetry["length_m"])
        self.width = float(telemetry["width"])
        self.default_laps = int(telemetry["laps"])
        self.reference_speed = [float(p[2]) for p in raw]
        self.reference_gear = [int(p[3]) for p in raw]
        self.reference_throttle = [float(p[4]) for p in raw]
        self.reference_brake = [bool(p[5]) for p in raw]
        self.reference_rpm = [int(p[6]) for p in raw]
        self.reference_elevation = [float(p[7]) if len(p) > 7 else 0.0 for p in raw]
        self.reference_driver = telemetry["driver"]
        self.reference_lap_time = float(telemetry["lap_time"])
        self.reference_sector_times = [float(v) for v in telemetry["sector_times"]]
        self.sector_indices = [int(v) for v in telemetry["sector_indices"]]

        count = len(points)
        headings = []
        for i in range(count):
            prev_p = points[(i - 1) % count]
            next_p = points[(i + 1) % count]
            headings.append(math.atan2(next_p[1] - prev_p[1], next_p[0] - prev_p[0]))

        curvatures = []
        for i in range(count):
            dh = _angle_delta(headings[(i + 2) % count], headings[(i - 2) % count])
            curvatures.append(dh / (4.0 * self.SAMPLE_METRES))

        # A small circular moving average removes spline sampling noise while
        # preserving the direction and severity of real corners.
        smooth_curves = []
        for i in range(count):
            values = [curvatures[(i + j) % count] for j in range(-3, 4)]
            smooth_curves.append(sum(values) / len(values))

        self.center_points = [
            (points[i][0], points[i][1], headings[i], smooth_curves[i])
            for i in range(count)
        ]
        self._build_edges()
        self._build_racing_line()
        self._build_brake_zones()

    @staticmethod
    def _catmull_rom_closed(anchors, samples):
        result = []
        n = len(anchors)
        for i in range(n):
            p0 = anchors[(i - 1) % n]
            p1 = anchors[i]
            p2 = anchors[(i + 1) % n]
            p3 = anchors[(i + 2) % n]
            for step in range(samples):
                t = step / samples
                t2 = t * t
                t3 = t2 * t
                x = 0.5 * (
                    2 * p1[0]
                    + (-p0[0] + p2[0]) * t
                    + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                    + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
                )
                y = 0.5 * (
                    2 * p1[1]
                    + (-p0[1] + p2[1]) * t
                    + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                    + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
                )
                result.append((x, y))
        return result

    @staticmethod
    def _resample_closed(points, spacing):
        loop = points + [points[0]]
        cumulative = [0.0]
        for i in range(1, len(loop)):
            cumulative.append(cumulative[-1] + _distance(loop[i - 1], loop[i]))
        total = cumulative[-1]
        output = []
        seg = 1
        target = 0.0
        while target < total:
            while seg < len(cumulative) - 1 and cumulative[seg] < target:
                seg += 1
            start_d = cumulative[seg - 1]
            end_d = cumulative[seg]
            frac = 0.0 if end_d == start_d else (target - start_d) / (end_d - start_d)
            a, b = loop[seg - 1], loop[seg]
            output.append((a[0] + (b[0] - a[0]) * frac, a[1] + (b[1] - a[1]) * frac))
            target += spacing
        return output

    def _build_edges(self):
        half = self.width / 2.0
        outer = half + cfg.KERB_WIDTH
        for x, y, heading, _ in self.center_points:
            nx, ny = -math.sin(heading), math.cos(heading)
            self.left_edges.append((x + nx * half, y + ny * half))
            self.right_edges.append((x - nx * half, y - ny * half))
            self.kerb_left_edges.append((x + nx * outer, y + ny * outer))
            self.kerb_right_edges.append((x - nx * outer, y - ny * outer))

    def _build_racing_line(self):
        # Build a continuous outside-apex-outside path. Candidate apexes are
        # curvature peaks from the real qualifying trace; Gaussian entry,
        # apex, and exit targets blend neighbouring corners without abrupt
        # lateral jumps.
        count = len(self.center_points)
        candidates = []
        for index, point in enumerate(self.center_points):
            curvature = abs(point[3])
            if curvature < 0.0035:
                continue
            neighbourhood = [
                abs(self.center_points[(index + delta) % count][3])
                for delta in range(-10, 11)
            ]
            if curvature >= max(neighbourhood):
                candidates.append((curvature, index))

        apexes = []
        minimum_gap = max(12, int(70.0 / self.SAMPLE_METRES))
        for strength, index in sorted(candidates, reverse=True):
            if all(
                min((index - other) % count, (other - index) % count) >= minimum_gap
                for _, other in apexes
            ):
                apexes.append((strength, index))

        usable_half_width = max(
            1.0,
            self.width * 0.5 - cfg.CAR_WIDTH * 0.5 - 0.65,
        )
        offsets = [0.0] * count

        def circular_delta(index, center):
            delta = (index - center) % count
            return delta - count if delta > count * 0.5 else delta

        def gaussian(delta, sigma):
            return math.exp(-0.5 * (delta / sigma) ** 2)

        for strength, apex in apexes:
            turn = 1.0 if self.center_points[apex][3] > 0.0 else -1.0
            severity = max(0.42, min(1.0, strength / 0.030))
            entry = (apex - 18) % count
            exit_index = (apex + 16) % count
            inside_amount = usable_half_width * (0.58 + severity * 0.20)
            outside_amount = usable_half_width * (0.42 + severity * 0.16)
            for index in range(count):
                offsets[index] += turn * (
                    inside_amount * gaussian(circular_delta(index, apex), 7.0)
                    - outside_amount * gaussian(circular_delta(index, entry), 10.0)
                    - outside_amount * gaussian(circular_delta(index, exit_index), 10.0)
                )

        # Circular smoothing provides a steering-friendly line through linked
        # corners while the clamp keeps the car inside the usable road.
        for _ in range(4):
            offsets = [
                sum(offsets[(index + delta) % count] for delta in range(-2, 3)) / 5.0
                for index in range(count)
            ]
        self.racing_line_offsets = [
            max(-usable_half_width, min(usable_half_width, offset))
            for offset in offsets
        ]
        self.racing_line = []
        for point, offset in zip(self.center_points, self.racing_line_offsets):
            normal_x, normal_y = -math.sin(point[2]), math.cos(point[2])
            self.racing_line.append(
                (point[0] + normal_x * offset, point[1] + normal_y * offset)
            )
        self.recommended_speeds = list(self.reference_speed)
        self.lift_zone_indices = {
            i
            for i, (throttle, brake) in enumerate(
                zip(self.reference_throttle, self.reference_brake)
            )
            if throttle < 0.94 and not brake
        }

    def _build_brake_zones(self):
        count = len(self.center_points)
        starts = []
        for i in range(count):
            previous = self.reference_brake[(i - 1) % count]
            if self.reference_brake[i] and not previous:
                run = 0
                while run < 12 and self.reference_brake[(i + run) % count]:
                    run += 1
                if run >= 2:
                    starts.append(i)

        for start in starts:
            end = start
            while self.reference_brake[end % count] and end - start < 80:
                self.brake_zone_indices.add(end % count)
                end += 1
            search = [(end + j) % count for j in range(0, 24)]
            apex = min(search, key=lambda idx: self.reference_speed[idx])
            p = self.center_points[start]
            self.brake_zones.append(
                {
                    "index": start,
                    "apex": apex,
                    "point": (p[0], p[1]),
                    "heading": p[2],
                    "target_kmh": int(self.reference_speed[apex]),
                }
            )

    def find_nearest(self, x, y):
        best_i, best_d2 = 0, float("inf")
        for i, p in enumerate(self.center_points):
            dx, dy = p[0] - x, p[1] - y
            d2 = dx * dx + dy * dy
            if d2 < best_d2:
                best_i, best_d2 = i, d2
        return best_i, math.sqrt(best_d2)

    def surface_at(self, x, y):
        idx, distance = self.find_nearest(x, y)
        half = self.width / 2.0
        if distance <= half:
            surface = "asphalt"
        elif distance <= half + cfg.KERB_WIDTH:
            surface = "kerb"
        elif distance <= half + cfg.KERB_WIDTH + cfg.RUNOFF_WIDTH:
            surface = "runoff"
        else:
            surface = "grass"
        return surface, idx, distance

    def get_progress(self, x, y):
        idx, _ = self.find_nearest(x, y)
        return idx / len(self.center_points)
