import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(1, str(ROOT / "src"))

import config as cfg
from physics.vehicle import Vehicle
from game.input import InputHandler
from track.layouts import TRACK_ORDER, TRACKS
from track.track import Track


class TrackTests(unittest.TestCase):
    def test_all_real_world_layouts_generate_closed_tracks(self):
        for track_id in TRACK_ORDER:
            with self.subTest(track=track_id):
                track = Track(track_id)
                self.assertGreater(len(track.center_points), 600)
                self.assertAlmostEqual(track.total_length, TRACKS[track_id]["length_m"])
                first = track.center_points[0]
                last = track.center_points[-1]
                self.assertLess(math.hypot(first[0] - last[0], first[1] - last[1]), 8.0)
                self.assertGreater(len(track.brake_zones), 3)
                self.assertEqual(len(track.sector_indices), 2)
                self.assertLess(track.sector_indices[0], track.sector_indices[1])
                self.assertEqual(len(track.reference_sector_times), 3)
                self.assertGreater(track.reference_lap_time, 60.0)

    def test_surface_layers_are_driveable_and_ordered(self):
        track = Track("monza")
        x, y, heading, _ = track.center_points[100]
        nx, ny = -math.sin(heading), math.cos(heading)
        half = track.width / 2.0
        samples = [
            ("asphalt", half - 0.2),
            ("kerb", half + cfg.KERB_WIDTH * 0.5),
            ("runoff", half + cfg.KERB_WIDTH + 1.0),
            ("grass", half + cfg.KERB_WIDTH + cfg.RUNOFF_WIDTH + 2.0),
        ]
        for expected, offset in samples:
            with self.subTest(surface=expected):
                surface, _, _ = track.surface_at(x + nx * offset, y + ny * offset)
                self.assertEqual(surface, expected)


class VehicleTests(unittest.TestCase):
    def test_high_speed_steering_has_less_lock(self):
        low = Vehicle()
        high = Vehicle()
        high.speed = 80.0
        for _ in range(60):
            low.update(1 / 60, 1.0, 0.0, 0.0)
            high.update(1 / 60, 1.0, 0.0, 0.0)
        self.assertGreater(abs(low.steer_angle), abs(high.steer_angle) * 2.5)
        self.assertLess(abs(high.steer_angle), 0.20)

    def test_kerb_does_not_mark_vehicle_as_crashed(self):
        car = Vehicle()
        car.set_surface("kerb")
        car.speed = 30.0
        car.update(1 / 60, 0.2, 0.4, 0.0)
        self.assertFalse(car.crashed)
        self.assertGreater(car.speed, 0.0)

    def test_linear_trigger_uses_full_physical_travel(self):
        self.assertEqual(InputHandler.linear_trigger(-1.0), 0.0)
        self.assertAlmostEqual(InputHandler.linear_trigger(-0.5), 0.25)
        self.assertAlmostEqual(InputHandler.linear_trigger(0.0), 0.5)
        self.assertAlmostEqual(InputHandler.linear_trigger(0.5), 0.75)
        self.assertEqual(InputHandler.linear_trigger(1.0), 1.0)

    def test_automatic_f1_gearbox_reaches_high_gears(self):
        car = Vehicle()
        car.speed = 82.0
        for _ in range(80):
            car.update(1 / 60, 0.0, 1.0, 0.0)
        self.assertGreaterEqual(car.gear, 7)
        self.assertGreater(car.rpm, 4000)


if __name__ == "__main__":
    unittest.main()
