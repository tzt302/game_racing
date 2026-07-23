import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(1, str(ROOT / "src"))

import config as cfg
from physics.vehicle import Vehicle
from audio.engine import EngineAudio
from game.input import InputHandler
from game.loop import AI_PROFILES, VIEW_RANGES, GameLoop
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
                self.assertEqual(
                    len(track.reference_elapsed), len(track.center_points)
                )
                self.assertAlmostEqual(track.reference_elapsed[0], 0.0, places=3)
                self.assertAlmostEqual(
                    track.reference_elapsed[-1],
                    track.reference_lap_time,
                    places=2,
                )

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

    def test_circuits_are_not_mirrored_on_the_pygame_screen(self):
        # These five circuits run clockwise in their standard map
        # orientation. With Pygame's downward-positive Y axis that produces a
        # positive shoelace area. A forgotten FastF1 Y-axis conversion flips
        # every circuit and makes this value negative.
        for track_id in TRACK_ORDER:
            with self.subTest(track=track_id):
                points = Track(track_id).center_points
                signed_area = sum(
                    point[0] * points[(index + 1) % len(points)][1]
                    - points[(index + 1) % len(points)][0] * point[1]
                    for index, point in enumerate(points)
                )
                self.assertGreater(signed_area, 0.0)

    def test_racing_line_runs_outside_apex_outside(self):
        for track_id in TRACK_ORDER:
            with self.subTest(track=track_id):
                track = Track(track_id)
                apex = max(
                    range(len(track.center_points)),
                    key=lambda index: abs(track.center_points[index][3]),
                )
                turn = 1.0 if track.center_points[apex][3] > 0.0 else -1.0
                count = len(track.center_points)
                entry = track.racing_line_offsets[(apex - 18) % count] * turn
                inside = track.racing_line_offsets[apex] * turn
                exit_offset = track.racing_line_offsets[(apex + 16) % count] * turn
                self.assertLess(entry, 0.0)
                self.assertGreater(inside, 0.0)
                self.assertLess(exit_offset, 0.0)
                self.assertGreater(
                    max(abs(value) for value in track.racing_line_offsets),
                    track.width * 0.20,
                )


class VehicleTests(unittest.TestCase):
    def test_high_speed_steering_has_less_lock(self):
        low = Vehicle()
        high = Vehicle()
        high.speed = 80.0
        for _ in range(60):
            low.update(1 / 60, 1.0, 0.0, 0.0)
            high.update(1 / 60, 1.0, 0.0, 0.0)
        self.assertGreater(abs(low.steer_angle), abs(high.steer_angle) * 2.0)
        self.assertLess(abs(high.steer_angle), 0.23)

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

    def test_full_throttle_top_speed_exceeds_360_kmh(self):
        car = Vehicle()
        for _ in range(60 * 35):
            car.update(1 / 60, 0.0, 1.0, 0.0)
        self.assertGreater(car.get_speed_kmh(), 360.0)
        self.assertLessEqual(car.get_speed_kmh(), cfg.MAX_SPEED)


class AudioModelTests(unittest.TestCase):
    def test_v6_firing_frequency_and_equal_power_crossfade(self):
        self.assertEqual(EngineAudio.firing_frequency(12000), 600.0)
        weights = EngineAudio.band_weights(8200)
        self.assertEqual(len(weights), 6)
        self.assertAlmostEqual(sum(value * value for value in weights), 1.0)
        self.assertEqual(sum(value > 0.0 for value in weights), 2)


class RaceFormatTests(unittest.TestCase):
    def test_grand_prix_grid_contains_player_and_nine_ai(self):
        self.assertEqual(len(AI_PROFILES), 9)
        game = GameLoop.__new__(GameLoop)
        game.track = Track("spa")
        cars = [Vehicle() for _ in range(10)]
        indices = [game._place_on_grid(car, slot) for slot, car in enumerate(cars)]
        positions = {(round(car.x, 2), round(car.y, 2)) for car in cars}
        self.assertEqual(len(positions), 10)
        self.assertEqual(len(set(indices)), 5)
        for row in range(5):
            self.assertEqual(indices[row * 2], indices[row * 2 + 1])

    def test_five_red_lights_illuminate_in_sequence(self):
        game = GameLoop.__new__(GameLoop)
        game.lights_out = False
        expected = [(0.0, 0), (0.75, 1), (1.50, 2), (2.25, 3), (3.0, 4), (3.75, 5)]
        for elapsed, count in expected:
            game.start_sequence_time = elapsed
            self.assertEqual(game._illuminated_start_lights(), count)
        game.lights_out = True
        self.assertEqual(game._illuminated_start_lights(), 0)

    def test_view_range_options_expand_the_visible_world(self):
        scales = [option["scale"] for option in VIEW_RANGES]
        self.assertEqual(len(scales), 3)
        self.assertGreater(scales[0], scales[1])
        self.assertGreater(scales[1], scales[2])

    def test_live_delta_compares_player_with_reference_point_time(self):
        game = GameLoop.__new__(GameLoop)
        game.track = Track("monza")
        game.player_has_started_lap = True
        game.lap_start_reference_index = 0
        game.session_best_lap = float("inf")
        game.session_fastest_driver = "---"
        index = 240
        game.lap_timer = game.track.reference_elapsed[index] + 0.375
        self.assertAlmostEqual(game._calculate_live_delta(index), 0.375, places=3)

    def test_track_limits_count_excursions_and_penalize_third(self):
        game = GameLoop.__new__(GameLoop)
        game.track = Track("monza")
        game.player = Vehicle()
        game.player.speed = 40.0
        game.lights_out = True
        game.track_limit_warnings = 0
        game.time_penalty = 0.0
        game._outside_track_limits = False
        game.penalty_message_time = 0.0
        game.penalty_message = ""
        x, y, heading, _ = game.track.center_points[100]
        nx, ny = -math.sin(heading), math.cos(heading)
        outside = game.track.width * 0.5 + cfg.KERB_WIDTH + 1.0

        for excursion in range(3):
            game.player.x, game.player.y = x + nx * outside, y + ny * outside
            game._update_track_limits()
            game._update_track_limits()
            if excursion < 2:
                self.assertEqual(game.track_limit_warnings, excursion + 1)
            game.player.x, game.player.y = x, y
            game._update_track_limits()

        self.assertEqual(game.track_limit_warnings, 0)
        self.assertEqual(game.time_penalty, 5.0)
        self.assertEqual(game.penalty_message, "5 SECOND TIME PENALTY")

    def test_standings_include_player_and_all_nine_ai(self):
        game = GameLoop.__new__(GameLoop)
        game.track = Track("spa")
        game.lap = 1
        game.player_progress = 0.50
        game.time_penalty = 0.0
        game.livery_index = 0
        game.session_best_lap = float("inf")
        game.session_fastest_driver = "---"
        game.player = Vehicle()
        game.player.grid_position = 9
        game.ai_cars = []
        for index, profile in enumerate(AI_PROFILES):
            ai = Vehicle()
            ai.driver_name = profile["name"]
            ai.color = profile["color"]
            ai.grid_position = index
            ai.lap = 1
            ai.progress = 0.45 + index * 0.01
            game.ai_cars.append(ai)

        entries = game._standings_payload()
        self.assertEqual(len(entries), 10)
        self.assertEqual([entry["score"] for entry in entries], sorted(
            (entry["score"] for entry in entries), reverse=True
        ))
        self.assertEqual(sum(entry["player"] for entry in entries), 1)


if __name__ == "__main__":
    unittest.main()
