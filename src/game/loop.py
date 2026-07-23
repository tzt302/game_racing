import math

import pygame

import config as cfg
from ai.opponent import AIOpponent
from audio.engine import EngineAudio
from game.input import InputHandler
from physics.vehicle import Vehicle
from track.layouts import TRACK_ORDER
from track.track import Track
from ui.hud import HUD


CAR_LIVERIES = [
    {"name": "SCARLET", "body": (225, 35, 45), "accent": (255, 212, 55)},
    {"name": "PAPAYA", "body": (244, 112, 22), "accent": (45, 60, 75)},
    {"name": "SILVER", "body": (42, 185, 174), "accent": (225, 225, 225)},
    {"name": "ROYAL BLUE", "body": (42, 82, 210), "accent": (235, 45, 55)},
]
MODES = ["TIME TRIAL", "RACE VS AI"]
DIFFICULTIES = ["EASY", "NORMAL", "HARD"]
VIEW_RANGES = [
    {"name": "STANDARD", "scale": 12.0},
    {"name": "WIDE", "scale": 9.5},
    {"name": "ULTRA WIDE", "scale": 7.5},
]
AI_PROFILES = [
    {"name": "NOVA", "skill": 0.96, "aggression": 0.74, "consistency": 0.96, "color": (55, 115, 245)},
    {"name": "APEX", "skill": 0.93, "aggression": 0.88, "consistency": 0.91, "color": (245, 130, 30)},
    {"name": "VOLT", "skill": 0.90, "aggression": 0.58, "consistency": 0.94, "color": (45, 190, 165)},
    {"name": "ORBIT", "skill": 0.87, "aggression": 0.66, "consistency": 0.86, "color": (175, 75, 225)},
    {"name": "ROOK", "skill": 0.84, "aggression": 0.42, "consistency": 0.82, "color": (230, 215, 55)},
    {"name": "CRIMSON", "skill": 0.91, "aggression": 0.79, "consistency": 0.89, "color": (205, 35, 48)},
    {"name": "ARROW", "skill": 0.89, "aggression": 0.61, "consistency": 0.93, "color": (225, 230, 235)},
    {"name": "ZENITH", "skill": 0.86, "aggression": 0.71, "consistency": 0.85, "color": (65, 205, 95)},
    {"name": "PHANTOM", "skill": 0.88, "aggression": 0.52, "consistency": 0.90, "color": (90, 95, 105)},
]


class GameLoop:
    def __init__(self, screen, clock):
        self.screen = screen
        self.clock = clock
        font_name = "microsoftyahei"
        self.font_s = pygame.font.SysFont(font_name, 14, bold=True)
        self.font_m = pygame.font.SysFont(font_name, 22, bold=True)
        self.font_l = pygame.font.SysFont(font_name, 42, bold=True)
        self.font_xl = pygame.font.SysFont(font_name, 68, bold=True)
        self.hud = HUD(self.font_s, self.font_m, self.font_l)
        self.input = InputHandler()

        self.track_index = 0
        self.mode_index = 0
        self.difficulty_index = 1
        self.view_range_index = 1
        self.livery_index = 0
        self.menu_row = 0
        self.state = "menu"
        self.show_racing_line = True
        self.show_brake_zones = True

        self.track = None
        self.player = None
        self.ai = None
        self.ai_cars = []
        self.audio = EngineAudio()
        self.mode = MODES[self.mode_index]
        self.total_laps = 3
        self.lap = 1
        self.lap_timer = 0.0
        self.player_best_lap = float("inf")
        self.player_last_lap = 0.0
        self.player_progress = 0.0
        self.ai_progress = 0.0
        self.last_player_idx = 0
        self.race_message_time = 0.0
        self.sector_times = [None, None, None]
        self.sector_status = [None, None, None]
        self.personal_best_sectors = [float("inf")] * 3
        self.session_best_sectors = [float("inf")] * 3
        self.current_sector = 1
        self.session_best_lap = float("inf")
        self.session_fastest_driver = "---"
        self.start_sequence_time = 0.0
        self.lights_out = True
        self.lights_out_flash = 0.0
        self.lights_out_elapsed = 0.0
        self.player_has_started_lap = True
        self.lap_start_reference_index = 0
        self.live_delta = None
        self.track_limit_warnings = 0
        self.time_penalty = 0.0
        self._outside_track_limits = False
        self.penalty_message_time = 0.0
        self.penalty_message = ""
        self._load_track()

    def run(self):
        running = True
        dt = 1.0 / cfg.FPS
        while running:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
            if not running:
                break

            if self.state == "menu":
                self.audio.silence()
                self._handle_menu(events)
            elif self.state == "guide":
                self.audio.silence()
                self._handle_guide(events)
            elif self.state == "race":
                self._handle_race(events, dt)
            elif self.state == "paused":
                self._handle_paused(events)
            elif self.state == "results":
                self._handle_results(events)

            self._render()
            pygame.display.flip()
            dt = min(0.05, self.clock.tick(cfg.FPS) / 1000.0)

    def _load_track(self):
        track_id = TRACK_ORDER[self.track_index]
        self.track = Track(track_id)
        self.player = Vehicle()
        self.ai_cars = [AIOpponent(self.track, profile) for profile in AI_PROFILES]
        for ai in self.ai_cars:
            ai.difficulty = DIFFICULTIES[self.difficulty_index]
        self.ai = self.ai_cars[0]
        self.total_laps = self.track.default_laps
        self._reset_race()

    def _reset_race(self):
        count = len(self.track.center_points)
        if self.mode == "RACE VS AI":
            player_idx = self._place_on_grid(self.player, 9)
            self.player.grid_position = 9
        else:
            player_idx = 6
            p = self.track.center_points[player_idx]
            self.player.reset(p[0], p[1], p[2])
        for grid_position, ai in enumerate(self.ai_cars):
            ai.grid_position = grid_position
            if self.mode == "RACE VS AI":
                ai_idx = self._place_on_grid(ai, grid_position)
            else:
                ai_idx = (count - 8 - grid_position * 5) % count
                a = self.track.center_points[ai_idx]
                ai.reset(a[0], a[1], a[2])
            ai.progress = ai_idx / count
            ai.lap = 0
            ai.best_lap = float("inf")
            ai.last_lap = 0.0
            ai._last_idx = ai_idx
            ai._lap_timer = 0.0
            ai._sector_times = [None, None, None]
            ai._personal_best_sectors = [float("inf")] * 3
        self.lap = 1
        self.lap_timer = 0.0
        self.player_best_lap = float("inf")
        self.player_last_lap = 0.0
        self.player_progress = player_idx / count
        self.ai_progress = self.ai.progress
        self.last_player_idx = player_idx
        self.race_message_time = 4.0
        self.sector_times = [None, None, None]
        self.sector_status = [None, None, None]
        self.personal_best_sectors = [float("inf")] * 3
        self.session_best_sectors = [float("inf")] * 3
        self.current_sector = 1
        self.session_best_lap = float("inf")
        self.session_fastest_driver = "---"
        self.start_sequence_time = 0.0
        self.lights_out = self.mode != "RACE VS AI"
        self.lights_out_flash = 0.0
        self.lights_out_elapsed = 0.0
        self.player_has_started_lap = self.mode != "RACE VS AI"
        self.lap_start_reference_index = player_idx
        self.live_delta = None
        self.track_limit_warnings = 0
        self.time_penalty = 0.0
        self._outside_track_limits = False
        self.penalty_message_time = 0.0
        self.penalty_message = ""

    def _place_on_grid(self, vehicle, grid_position):
        """Place a car on a two-column, five-row starting grid."""
        count = len(self.track.center_points)
        row = grid_position // 2
        index = (count - 2 - row * 2) % count
        point = self.track.center_points[index]
        normal_x, normal_y = -math.sin(point[2]), math.cos(point[2])
        lane_offset = min(2.6, self.track.width * 0.20)
        side = -1.0 if grid_position % 2 == 0 else 1.0
        vehicle.reset(
            point[0] + normal_x * lane_offset * side,
            point[1] + normal_y * lane_offset * side,
            point[2],
        )
        return index

    def _handle_menu(self, events):
        for event in events:
            key = None
            if event.type == pygame.KEYDOWN:
                key = event.key
            elif event.type == pygame.JOYHATMOTION:
                if event.value[1] > 0:
                    key = pygame.K_UP
                elif event.value[1] < 0:
                    key = pygame.K_DOWN
                elif event.value[0] < 0:
                    key = pygame.K_LEFT
                elif event.value[0] > 0:
                    key = pygame.K_RIGHT
            elif event.type == pygame.JOYBUTTONDOWN and event.button == 0:
                key = pygame.K_RETURN

            if key == pygame.K_UP:
                self.menu_row = (self.menu_row - 1) % 6
            elif key == pygame.K_DOWN:
                self.menu_row = (self.menu_row + 1) % 6
            elif key in (pygame.K_LEFT, pygame.K_RIGHT):
                direction = -1 if key == pygame.K_LEFT else 1
                self._change_menu_value(direction)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.menu_row == 5:
                    self.mode = MODES[self.mode_index]
                    self._load_track()
                    self.state = "guide"
                else:
                    self._change_menu_value(1)
            elif key == pygame.K_h:
                self.state = "guide"

    def _change_menu_value(self, direction):
        if self.menu_row == 0:
            self.track_index = (self.track_index + direction) % len(TRACK_ORDER)
            self._load_track()
        elif self.menu_row == 1:
            self.mode_index = (self.mode_index + direction) % len(MODES)
        elif self.menu_row == 2:
            self.difficulty_index = (self.difficulty_index + direction) % len(DIFFICULTIES)
            for ai in self.ai_cars:
                ai.difficulty = DIFFICULTIES[self.difficulty_index]
        elif self.menu_row == 3:
            self.view_range_index = (self.view_range_index + direction) % len(VIEW_RANGES)
        elif self.menu_row == 4:
            self.livery_index = (self.livery_index + direction) % len(CAR_LIVERIES)

    def _change_view_range(self, direction):
        self.view_range_index = max(
            0,
            min(len(VIEW_RANGES) - 1, self.view_range_index + direction),
        )

    def _illuminated_start_lights(self):
        if self.lights_out:
            return 0
        if self.start_sequence_time < 0.75:
            return 0
        return min(5, int((self.start_sequence_time - 0.75) / 0.75) + 1)

    def _handle_guide(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._reset_race()
                    self.state = "race"
                elif event.key == pygame.K_ESCAPE:
                    self.state = "menu"
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button == 0:
                    self._reset_race()
                    self.state = "race"
                elif event.button == 1:
                    self.state = "menu"

    def _handle_race(self, events, dt):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = "paused"
                elif event.key == pygame.K_F1:
                    self.state = "guide"
                elif event.key == pygame.K_l:
                    self.show_racing_line = not self.show_racing_line
                elif event.key == pygame.K_b:
                    self.show_brake_zones = not self.show_brake_zones
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS, pygame.K_LEFTBRACKET):
                    self._change_view_range(1)
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_RIGHTBRACKET):
                    self._change_view_range(-1)
            elif event.type == pygame.MOUSEWHEEL:
                self._change_view_range(-1 if event.y > 0 else 1)
            elif event.type == pygame.JOYBUTTONDOWN and event.button == 7:
                self.state = "paused"
        if self.state != "race":
            return

        self.input.update(events)
        if self.input.reset_pressed:
            self._recover_player()
        self._update(dt)

    def _handle_paused(self, events):
        self.audio.silence()
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = "race"
                elif event.key == pygame.K_m:
                    self.state = "menu"
                elif event.key == pygame.K_r:
                    self._reset_race()
                    self.state = "race"
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button == 7:
                    self.state = "race"
                elif event.button == 1:
                    self.state = "menu"

    def _handle_results(self, events):
        self.audio.silence()
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self._reset_race()
                    self.state = "race"
                elif event.key in (pygame.K_m, pygame.K_ESCAPE):
                    self.state = "menu"
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button == 0:
                    self._reset_race()
                    self.state = "race"
                elif event.button == 1:
                    self.state = "menu"

    def _update(self, dt):
        if not self.lights_out:
            self.start_sequence_time += dt
            if self.start_sequence_time >= 5.25:
                self.lights_out = True
                self.lights_out_flash = 1.0
                self.lights_out_elapsed = 0.0
                self.race_message_time = 0.0
            self.player.speed = 0.0
            for ai in self.ai_cars:
                ai.speed = 0.0
            self.audio.silence()
            return

        self.lights_out_elapsed += dt
        self.lights_out_flash = max(0.0, self.lights_out_flash - dt)
        player_surface, _, _ = self.track.surface_at(self.player.x, self.player.y)
        self.player.set_surface(player_surface)
        self.player.update(dt, self.input.steer, self.input.throttle, self.input.brake)
        self._apply_world_limits(self.player)
        self._update_track_limits()

        if self.mode == "RACE VS AI":
            all_cars = [self.player] + self.ai_cars
            for ai in self.ai_cars:
                ai_surface, _, _ = self.track.surface_at(ai.x, ai.y)
                ai.set_surface(ai_surface)
                ai.update(dt, all_cars)
                self._apply_world_limits(ai)
            self._resolve_car_contacts(all_cars)

        pi, _ = self.track.find_nearest(self.player.x, self.player.y)
        self.player_progress = pi / len(self.track.center_points)
        if self.mode == "RACE VS AI":
            for ai in self.ai_cars:
                ai_idx, _ = self.track.find_nearest(ai.x, ai.y)
                ai.progress = ai_idx / len(self.track.center_points)
                self._update_ai_timing(ai, ai_idx, dt)
            self.ai_progress = self.ai.progress

        self.lap_timer += dt
        self.race_message_time = max(0.0, self.race_message_time - dt)
        self.penalty_message_time = max(0.0, self.penalty_message_time - dt)
        count = len(self.track.center_points)
        sector_one, sector_two = self.track.sector_indices
        if self.current_sector == 1 and self._crossed_marker(self.last_player_idx, pi, sector_one, count):
            self._record_player_sector(0, self.lap_timer)
            self.current_sector = 2
        if self.current_sector == 2 and self._crossed_marker(self.last_player_idx, pi, sector_two, count):
            elapsed = self.lap_timer - (self.sector_times[0] or 0.0)
            self._record_player_sector(1, elapsed)
            self.current_sector = 3

        crossed_line = self.last_player_idx > count * 0.85 and pi < count * 0.15
        if crossed_line and self.player.speed > 5.0 and not self.player_has_started_lap:
            self.player_has_started_lap = True
        elif crossed_line and self.player.speed > 5.0:
            elapsed = self.lap_timer - sum(value or 0.0 for value in self.sector_times[:2])
            self._record_player_sector(2, elapsed)
            self.player_last_lap = self.lap_timer
            self.player_best_lap = min(self.player_best_lap, self.player_last_lap)
            if self.player_last_lap < self.session_best_lap:
                self.session_best_lap = self.player_last_lap
                self.session_fastest_driver = "YOU"
            self.lap_timer = 0.0
            self.lap_start_reference_index = 0
            self.current_sector = 1
            if self.lap >= self.total_laps:
                self.state = "results"
            else:
                self.lap += 1
        self.last_player_idx = pi
        self.live_delta = self._calculate_live_delta(pi)
        self.audio.update(self.player, cockpit=False)

    def _update_track_limits(self):
        _, _, distance = self.track.surface_at(self.player.x, self.player.y)
        limit = self.track.width * 0.5 + cfg.KERB_WIDTH + 0.15
        outside = distance > limit
        if (
            outside
            and not self._outside_track_limits
            and self.player.speed > 5.0
            and self.lights_out
        ):
            self.track_limit_warnings += 1
            self.penalty_message_time = 2.4
            if self.track_limit_warnings >= 3:
                self.track_limit_warnings = 0
                self.time_penalty += 5.0
                self.penalty_message = "5 SECOND TIME PENALTY"
            else:
                self.penalty_message = (
                    f"TRACK LIMITS WARNING {self.track_limit_warnings}/3"
                )
        self._outside_track_limits = outside

    def _benchmark_lap(self):
        if self.session_best_lap < self.track.reference_lap_time:
            return self.session_best_lap, self.session_fastest_driver
        return self.track.reference_lap_time, self.track.reference_driver

    def _calculate_live_delta(self, index):
        if not self.player_has_started_lap or not self.track.reference_elapsed:
            return None
        reference = self.track.reference_elapsed
        start = self.lap_start_reference_index % len(reference)
        if index >= start:
            target_elapsed = reference[index] - reference[start]
        else:
            target_elapsed = (
                self.track.reference_lap_time - reference[start] + reference[index]
            )
        benchmark_lap, _ = self._benchmark_lap()
        target_elapsed *= benchmark_lap / self.track.reference_lap_time
        return self.lap_timer - target_elapsed

    @staticmethod
    def _crossed_marker(previous, current, marker, count):
        forward_steps = (current - previous) % count
        if forward_steps <= 0 or forward_steps > count * 0.20:
            return False
        marker_steps = (marker - previous) % count
        return 0 < marker_steps <= forward_steps

    def _record_player_sector(self, sector_index, elapsed):
        previous_personal = self.personal_best_sectors[sector_index]
        previous_session = self.session_best_sectors[sector_index]
        if elapsed < previous_session:
            status = "purple"
        elif elapsed < previous_personal:
            status = "green"
        else:
            status = "yellow"
        self.sector_times[sector_index] = elapsed
        self.sector_status[sector_index] = status
        self.personal_best_sectors[sector_index] = min(previous_personal, elapsed)
        self.session_best_sectors[sector_index] = min(previous_session, elapsed)

    def _update_ai_timing(self, ai, index, dt):
        count = len(self.track.center_points)
        ai._lap_timer += dt
        crossed_line = ai._last_idx > count * 0.85 and index < count * 0.15
        if ai.lap == 0:
            if crossed_line:
                ai.lap = 1
                ai._lap_timer = 0.0
                ai._current_sector = 1
                ai._sector_times = [None, None, None]
            ai._last_idx = index
            return

        sector_one, sector_two = self.track.sector_indices
        if ai._current_sector == 1 and self._crossed_marker(ai._last_idx, index, sector_one, count):
            self._record_ai_sector(ai, 0, ai._lap_timer)
            ai._current_sector = 2
        if ai._current_sector == 2 and self._crossed_marker(ai._last_idx, index, sector_two, count):
            elapsed = ai._lap_timer - (ai._sector_times[0] or 0.0)
            self._record_ai_sector(ai, 1, elapsed)
            ai._current_sector = 3
        if crossed_line and ai.speed > 5.0:
            elapsed = ai._lap_timer - sum(value or 0.0 for value in ai._sector_times[:2])
            self._record_ai_sector(ai, 2, elapsed)
            ai.last_lap = ai._lap_timer
            ai.best_lap = min(ai.best_lap, ai.last_lap)
            if ai.last_lap < self.session_best_lap:
                self.session_best_lap = ai.last_lap
                self.session_fastest_driver = ai.driver_name
            ai.lap += 1
            ai._lap_timer = 0.0
            ai._current_sector = 1
        ai._last_idx = index

    def _record_ai_sector(self, ai, sector_index, elapsed):
        ai._sector_times[sector_index] = elapsed
        ai._personal_best_sectors[sector_index] = min(
            ai._personal_best_sectors[sector_index], elapsed
        )
        self.session_best_sectors[sector_index] = min(
            self.session_best_sectors[sector_index], elapsed
        )

    @staticmethod
    def _resolve_car_contacts(cars):
        minimum = cfg.CAR_WIDTH * 1.15
        for first_index, first in enumerate(cars):
            for second in cars[first_index + 1 :]:
                dx, dy = second.x - first.x, second.y - first.y
                distance = math.hypot(dx, dy)
                if not 0.001 < distance < minimum:
                    continue
                overlap = (minimum - distance) * 0.5
                nx, ny = dx / distance, dy / distance
                first.x -= nx * overlap
                first.y -= ny * overlap
                second.x += nx * overlap
                second.y += ny * overlap
                relative_speed = abs(first.speed - second.speed)
                if relative_speed > 4.0:
                    slower = min(first.speed, second.speed)
                    impact_speed = slower + relative_speed * 0.38
                    if first.speed > second.speed:
                        first.speed = impact_speed
                    else:
                        second.speed = impact_speed

    def _race_position(self):
        player_score = self._player_race_score()
        ahead = 0
        for ai in self.ai_cars:
            ai_score = self._ai_race_score(ai)
            if ai_score > player_score:
                ahead += 1
        return ahead + 1

    def _player_race_score(self):
        benchmark_lap, _ = self._benchmark_lap()
        return (
            (self.lap - 1)
            + self.player_progress
            - self.time_penalty / max(benchmark_lap, 1.0)
            - getattr(self.player, "grid_position", 9) * 0.000001
        )

    @staticmethod
    def _ai_race_score(ai):
        return (
            max(0, ai.lap - 1)
            + ai.progress
            - getattr(ai, "grid_position", 0) * 0.000001
        )

    def _standings_payload(self):
        benchmark_lap, _ = self._benchmark_lap()
        player_score = self._player_race_score()
        entries = [
            {
                "name": "YOU",
                "score": player_score,
                "gap": 0.0,
                "color": CAR_LIVERIES[self.livery_index]["body"],
                "player": True,
            }
        ]
        for ai in self.ai_cars:
            score = self._ai_race_score(ai)
            entries.append(
                {
                    "name": ai.driver_name[:3],
                    "score": score,
                    "gap": (player_score - score) * benchmark_lap,
                    "color": ai.color,
                    "player": False,
                }
            )
        entries.sort(key=lambda entry: entry["score"], reverse=True)
        return entries

    def _timing_payload(self):
        return {
            "sector_times": self.sector_times,
            "sector_status": self.sector_status,
            "current_sector": self.current_sector,
            "personal_best_lap": self.player_best_lap,
            "session_best_lap": self.session_best_lap,
            "fastest_driver": self.session_fastest_driver,
            "delta": self.live_delta,
            "delta_target": self._benchmark_lap()[1],
        }

    def _apply_world_limits(self, vehicle):
        surface, idx, distance = self.track.surface_at(vehicle.x, vehicle.y)
        vehicle.set_surface(surface)
        guard_distance = (
            self.track.width / 2.0 + cfg.KERB_WIDTH + cfg.RUNOFF_WIDTH + 3.0
        )
        if distance <= guard_distance:
            vehicle.crashed = False
            return
        p = self.track.center_points[idx]
        dx, dy = vehicle.x - p[0], vehicle.y - p[1]
        length = max(math.hypot(dx, dy), 0.001)
        recovery_distance = (
            self.track.width / 2.0 + cfg.KERB_WIDTH + cfg.RUNOFF_WIDTH - 0.5
        )
        vehicle.x = p[0] + dx / length * recovery_distance
        vehicle.y = p[1] + dy / length * recovery_distance
        vehicle.speed *= 0.62
        vehicle.yaw_rate *= 0.4
        heading_error = (p[2] - vehicle.heading + math.pi) % (2 * math.pi) - math.pi
        vehicle.heading += heading_error * 0.45
        vehicle.crashed = True

    def _recover_player(self):
        idx, _ = self.track.find_nearest(self.player.x, self.player.y)
        p = self.track.center_points[idx]
        self.player.reset(p[0], p[1], p[2])
        self.last_player_idx = idx
        self._outside_track_limits = False

    def _render(self):
        if self.state == "menu":
            self._render_menu()
            return
        if self.state == "guide":
            self._render_guide()
            return

        self._render_race_world()
        if self.state == "paused":
            self._render_overlay(
                "PAUSED",
                ["ESC / START  Resume", "R  Restart session", "M / B  Main menu"],
            )
        elif self.state == "results":
            best = self._fmt_time(self.player_best_lap)
            lines = [f"BEST LAP  {best}"]
            if self.time_penalty:
                lines.append(f"TIME PENALTY  +{self.time_penalty:.1f}s")
            lines.extend(["R / A  Race again", "M / B  Main menu"])
            self._render_overlay(
                "SESSION COMPLETE",
                lines,
            )

    def _render_race_world(self):
        self._draw_grass()
        self._draw_track()
        if self.show_racing_line:
            self._draw_racing_line()
        if self.show_brake_zones:
            self._draw_brake_markers()
        self._draw_start_line()
        self._draw_sector_lines()

        livery = CAR_LIVERIES[self.livery_index]
        self._draw_f1_car(self.player, livery["body"], livery["accent"], "")
        if self.mode == "RACE VS AI":
            for ai in self.ai_cars:
                self._draw_f1_car(ai, ai.color, (245, 245, 245), ai.driver_name[:3])

        self._draw_minimap()
        position = self._race_position() if self.mode == "RACE VS AI" else 1
        self.hud.draw(
            self.screen,
            self.player,
            self.lap,
            self.total_laps,
            position,
            self.track,
            self.mode,
            self._timing_payload(),
        )
        if self.mode == "RACE VS AI":
            self._draw_leaderboard()

        if self.player_last_lap > 0:
            self._text(
                self.screen,
                cfg.WINDOW_WIDTH - 310,
                82,
                f"LAST {self._fmt_time(self.player_last_lap)}   BEST {self._fmt_time(self.player_best_lap)}",
                self.font_s,
                cfg.WHITE,
            )
        if self.race_message_time > 0:
            alpha = min(220, int(self.race_message_time * 90))
            panel = pygame.Surface((510, 46), pygame.SRCALPHA)
            panel.fill((5, 8, 11, alpha))
            self.screen.blit(panel, (cfg.WINDOW_WIDTH // 2 - 255, 92))
            self._center_text(
                self.screen,
                "Follow CYAN • Brake on RED • F1 opens guide",
                103,
                self.font_s,
                cfg.WHITE,
            )
        if self.penalty_message_time > 0:
            panel = pygame.Surface((390, 44), pygame.SRCALPHA)
            panel.fill((85, 16, 12, 225))
            self.screen.blit(panel, (cfg.WINDOW_WIDTH // 2 - 195, 158))
            self._center_text(
                self.screen,
                self.penalty_message,
                168,
                self.font_m,
                (255, 215, 205),
            )
        if self.mode == "RACE VS AI" and (not self.lights_out or self.lights_out_flash > 0):
            self._draw_start_lights()

    def _draw_leaderboard(self):
        entries = self._standings_payload()
        x, y, width = 14, 90, 278
        row_height = 29
        height = 56 + len(entries) * row_height + 47
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        panel.fill((5, 8, 11, 218))
        self.screen.blit(panel, (x, y))
        pygame.draw.rect(
            self.screen, (62, 68, 75), (x, y, width, height), 1, border_radius=5
        )
        self._text(self.screen, x + 13, y + 9, "STANDINGS", self.font_m, cfg.WHITE)
        self._text(
            self.screen, x + 180, y + 15, "GAP TO YOU", self.font_s, cfg.HUD_LABEL
        )
        for position, entry in enumerate(entries, 1):
            row_y = y + 43 + (position - 1) * row_height
            if entry["player"]:
                pygame.draw.rect(
                    self.screen,
                    (*entry["color"], 68),
                    (x + 5, row_y - 2, width - 10, row_height - 2),
                    border_radius=3,
                )
            pygame.draw.rect(
                self.screen, entry["color"], (x + 10, row_y + 5, 5, 16)
            )
            self._text(
                self.screen, x + 24, row_y + 2, f"{position:>2}", self.font_s, cfg.HUD_LABEL
            )
            self._text(
                self.screen, x + 55, row_y + 2, entry["name"], self.font_s, cfg.WHITE
            )
            gap = "YOU" if entry["player"] else f"{entry['gap']:+.3f}"
            gap_color = cfg.WHITE if entry["player"] else (
                (42, 220, 112) if entry["gap"] >= 0.0 else (255, 88, 72)
            )
            self._text(
                self.screen, x + 190, row_y + 2, gap, self.font_s, gap_color
            )
        footer_y = y + 49 + len(entries) * row_height
        warnings = f"TRACK LIMITS  {self.track_limit_warnings}/3"
        penalty = f"PENALTY  +{self.time_penalty:.0f}s"
        self._text(self.screen, x + 13, footer_y, warnings, self.font_s, cfg.HUD_LABEL)
        self._text(
            self.screen,
            x + 159,
            footer_y,
            penalty,
            self.font_s,
            (255, 170, 90) if self.time_penalty else cfg.HUD_LABEL,
        )

    def _draw_start_lights(self):
        panel = pygame.Rect(cfg.WINDOW_WIDTH // 2 - 205, 98, 410, 102)
        pygame.draw.rect(self.screen, (5, 7, 9), panel, border_radius=14)
        pygame.draw.rect(self.screen, (70, 76, 82), panel, 3, border_radius=14)
        illuminated = self._illuminated_start_lights()
        for index in range(5):
            center = (panel.x + 57 + index * 74, panel.y + 42)
            pygame.draw.circle(self.screen, (30, 32, 34), center, 24)
            pygame.draw.circle(
                self.screen,
                (242, 24, 38) if index < illuminated else (70, 18, 22),
                center,
                18,
            )
            if index < illuminated:
                pygame.draw.circle(self.screen, (255, 115, 105), (center[0] - 5, center[1] - 6), 5)
        message = "LIGHTS OUT" if self.lights_out else "HOLD THE BRAKE"
        color = cfg.WHITE if self.lights_out else cfg.HUD_LABEL
        self._center_text(self.screen, message, panel.y + 72, self.font_s, color)

    def _draw_cockpit_world(self):
        width, height = cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT
        horizon = 172
        # Layered sky and distant silhouettes give depth without changing the
        # underlying 2D physics or circuit data.
        for y in range(horizon):
            blend = y / max(horizon, 1)
            color = (
                int(48 + 62 * blend),
                int(83 + 70 * blend),
                int(122 + 72 * blend),
            )
            pygame.draw.line(self.screen, color, (0, y), (width, y))
        pygame.draw.polygon(
            self.screen,
            (42, 58, 65),
            [(0, horizon), (0, 138), (170, 105), (330, 145), (510, 112), (690, 148), (910, 102), (1100, 142), (1280, 118), (1280, horizon)],
        )
        pygame.draw.rect(self.screen, cfg.GRASS_COLOR, (0, horizon, width, height - horizon))
        for y in range(horizon, 630, 34):
            pygame.draw.line(self.screen, cfg.GRASS_STRIPE, (0, y), (width, y), 14)

        sections = self._cockpit_sections()
        for section_index in range(len(sections) - 1, 0, -1):
            far = sections[section_index]
            near = sections[section_index - 1]
            self._draw_perspective_strip(near, far, "runoff", cfg.RUNOFF_COLOR)
            kerb_color = cfg.KERB_RED if section_index % 2 else cfg.KERB_WHITE
            self._draw_perspective_strip(near, far, "kerb", kerb_color)
            self._draw_perspective_strip(near, far, "road", cfg.TRACK_COLOR)

            pygame.draw.line(
                self.screen,
                cfg.TRACK_BORDER,
                (near["x"] - near["runoff"], near["y"]),
                (far["x"] - far["runoff"], far["y"]),
                max(1, int(near["scale"] * 0.25)),
            )
            pygame.draw.line(
                self.screen,
                cfg.TRACK_BORDER,
                (near["x"] + near["runoff"], near["y"]),
                (far["x"] + far["runoff"], far["y"]),
                max(1, int(near["scale"] * 0.25)),
            )

            if self.show_racing_line:
                idx = near["idx"]
                if idx in self.track.brake_zone_indices:
                    line_color = cfg.RACING_LINE_BRAKE
                elif idx in self.track.lift_zone_indices:
                    line_color = cfg.RACING_LINE_LIFT
                else:
                    line_color = cfg.RACING_LINE_COLOR
                pygame.draw.line(
                    self.screen,
                    line_color,
                    (near["x"], near["y"]),
                    (far["x"], far["y"]),
                    max(2, int(near["scale"] * 0.42)),
                )

        if self.show_brake_zones:
            brake_starts = {zone["index"]: zone for zone in self.track.brake_zones}
            for section in sections:
                zone = brake_starts.get(section["idx"])
                if not zone:
                    continue
                road_half = section["road"]
                pygame.draw.line(
                    self.screen,
                    cfg.BRAKE_POINT_COLOR,
                    (section["x"] - road_half, section["y"]),
                    (section["x"] + road_half, section["y"]),
                    max(3, int(section["scale"] * 0.8)),
                )
                if section["y"] > horizon + 25:
                    label = self.font_s.render(
                        f"BRAKE  {zone['target_kmh']} KM/H", True, cfg.WHITE
                    )
                    box = label.get_rect(center=(section["x"], section["y"] - 22))
                    pygame.draw.rect(
                        self.screen,
                        cfg.BRAKE_POINT_COLOR,
                        box.inflate(12, 7),
                        border_radius=4,
                    )
                    self.screen.blit(label, box)

        for sector_number, marker in enumerate(self.track.sector_indices, start=2):
            section = min(
                sections,
                key=lambda item: min(
                    (item["idx"] - marker) % len(self.track.center_points),
                    (marker - item["idx"]) % len(self.track.center_points),
                ),
            )
            delta = min(
                (section["idx"] - marker) % len(self.track.center_points),
                (marker - section["idx"]) % len(self.track.center_points),
            )
            if delta > 1:
                continue
            pygame.draw.line(
                self.screen,
                cfg.MENU_ACCENT,
                (section["x"] - section["road"], section["y"]),
                (section["x"] + section["road"], section["y"]),
                4,
            )
            label = self.font_s.render(f"SECTOR {sector_number}", True, cfg.WHITE)
            self.screen.blit(
                label,
                label.get_rect(center=(section["x"], section["y"] - 14)),
            )

        if self.mode == "RACE VS AI":
            self._draw_cockpit_rivals()
        self._draw_tcam_frame()

    def _cockpit_sections(self):
        current_idx, _ = self.track.find_nearest(self.player.x, self.player.y)
        count = len(self.track.center_points)
        player_elevation = self.track.reference_elevation[current_idx]
        forward_x, forward_y = math.cos(self.player.heading), math.sin(self.player.heading)
        right_x, right_y = -forward_y, forward_x
        sections = []
        view_distance = 410.0
        for steps in range(2, int(view_distance / self.track.SAMPLE_METRES), 2):
            idx = (current_idx + steps) % count
            point = self.track.center_points[idx]
            dx, dy = point[0] - self.player.x, point[1] - self.player.y
            lateral = dx * right_x + dy * right_y
            distance = steps * self.track.SAMPLE_METRES
            perspective = (distance / view_distance) ** 0.58
            elevation = self.track.reference_elevation[idx] - player_elevation
            elevation_shift = elevation / (distance + 35.0) * 520.0
            y = int(172 + (1.0 - perspective) * 445 - elevation_shift)
            x = int(cfg.WINDOW_WIDTH / 2 + lateral / (distance + 28.0) * 760.0)
            scale = 920.0 / (distance + 30.0)
            sections.append(
                {
                    "idx": idx,
                    "x": x,
                    "y": y,
                    "scale": scale,
                    "road": max(8, int(self.track.width * 0.5 * scale)),
                    "kerb": max(10, int((self.track.width * 0.5 + cfg.KERB_WIDTH) * scale)),
                    "runoff": max(
                        13,
                        int(
                            (
                                self.track.width * 0.5
                                + cfg.KERB_WIDTH
                                + cfg.RUNOFF_WIDTH
                            )
                            * scale
                        ),
                    ),
                }
            )
        return sections

    def _draw_perspective_strip(self, near, far, key, color):
        pygame.draw.polygon(
            self.screen,
            color,
            [
                (near["x"] - near[key], near["y"]),
                (near["x"] + near[key], near["y"]),
                (far["x"] + far[key], far["y"]),
                (far["x"] - far[key], far["y"]),
            ],
        )

    def _draw_cockpit_rivals(self):
        player_idx, _ = self.track.find_nearest(self.player.x, self.player.y)
        count = len(self.track.center_points)
        right_x, right_y = -math.sin(self.player.heading), math.cos(self.player.heading)
        visible = []
        for ai in self.ai_cars:
            ai_idx, _ = self.track.find_nearest(ai.x, ai.y)
            steps = (ai_idx - player_idx) % count
            distance = steps * self.track.SAMPLE_METRES
            if not 12.0 < distance < 390.0:
                continue
            dx, dy = ai.x - self.player.x, ai.y - self.player.y
            lateral = dx * right_x + dy * right_y
            perspective = (distance / 410.0) ** 0.58
            y = int(172 + (1.0 - perspective) * 445)
            x = int(cfg.WINDOW_WIDTH / 2 + lateral / (distance + 28.0) * 760.0)
            scale = max(0.18, min(1.4, 42.0 / distance))
            visible.append((distance, x, y, scale, ai))
        for _, x, y, scale, ai in sorted(visible, reverse=True):
            car_width = max(8, int(36 * scale))
            car_height = max(10, int(58 * scale))
            pygame.draw.rect(
                self.screen,
                (8, 9, 11),
                (x - car_width // 2 - 4, y - car_height, car_width + 8, car_height),
                border_radius=max(1, int(4 * scale)),
            )
            pygame.draw.polygon(
                self.screen,
                ai.color,
                [
                    (x, y - car_height),
                    (x + car_width // 2, y - int(car_height * 0.28)),
                    (x + car_width // 3, y),
                    (x - car_width // 3, y),
                    (x - car_width // 2, y - int(car_height * 0.28)),
                ],
            )
            if scale > 0.42:
                tag = self.font_s.render(ai.driver_name, True, cfg.WHITE)
                self.screen.blit(tag, tag.get_rect(center=(x, y - car_height - 10)))

    def _draw_cockpit_frame(self):
        width = cfg.WINDOW_WIDTH
        livery = CAR_LIVERIES[self.livery_index]
        body = livery["body"]
        # Cockpit rim, steering wheel, front tyres and central halo pillar.
        pygame.draw.polygon(
            self.screen,
            body,
            [(0, 570), (265, 535), (470, 590), (810, 590), (1015, 535), (width, 570), (width, 630), (0, 630)],
        )
        pygame.draw.ellipse(self.screen, (10, 12, 15), (475, 500, 330, 180))
        pygame.draw.ellipse(self.screen, (55, 61, 67), (510, 520, 260, 135), 12)
        pygame.draw.rect(self.screen, (16, 19, 22), (596, 525, 88, 57), border_radius=8)
        pygame.draw.rect(self.screen, livery["accent"], (605, 535, 70, 6), border_radius=3)
        self._center_text(
            self.screen,
            f"{self.player.gear}     {int(self.player.get_speed_kmh()):03d}",
            547,
            self.font_m,
            cfg.WHITE,
        )
        pygame.draw.polygon(
            self.screen,
            (18, 21, 24),
            [(632, 0), (648, 0), (654, 520), (626, 520)],
        )
        pygame.draw.rect(self.screen, (8, 10, 12), (0, 535, 195, 95), border_radius=30)
        pygame.draw.rect(self.screen, (8, 10, 12), (1085, 535, 195, 95), border_radius=30)

    def _draw_tcam_frame(self):
        """High Halo/T-Cam view with the front axle and cockpit in frame."""
        width = cfg.WINDOW_WIDTH
        livery = CAR_LIVERIES[self.livery_index]
        body = livery["body"]
        accent = livery["accent"]
        carbon = (12, 15, 18)
        carbon_hi = (43, 48, 53)

        # Open-wheel silhouette.  The wheels deliberately occupy the lower
        # corners, matching the sight picture of an onboard camera above the
        # driver's helmet while keeping the apex visible.
        for wheel_x in (214, 914):
            pygame.draw.ellipse(self.screen, (5, 6, 7), (wheel_x, 420, 154, 235))
            pygame.draw.ellipse(self.screen, (31, 34, 36), (wheel_x + 12, 438, 130, 199), 5)
            pygame.draw.line(
                self.screen,
                (76, 78, 76),
                (wheel_x + 26, 469),
                (wheel_x + 128, 575),
                3,
            )

        # Front suspension wishbones and sidepod shoulders.
        for points in (
            [(305, 490), (507, 535), (446, 555), (318, 516)],
            [(975, 490), (773, 535), (834, 555), (962, 516)],
        ):
            pygame.draw.polygon(self.screen, carbon, points)
            pygame.draw.lines(self.screen, carbon_hi, True, points, 2)
        pygame.draw.polygon(
            self.screen,
            body,
            [(405, 720), (470, 535), (558, 474), (611, 352), (640, 326),
             (669, 352), (722, 474), (810, 535), (875, 720)],
        )
        pygame.draw.polygon(
            self.screen,
            accent,
            [(614, 720), (625, 374), (640, 341), (655, 374), (666, 720)],
        )
        pygame.draw.polygon(
            self.screen,
            carbon,
            [(506, 720), (526, 552), (575, 498), (705, 498), (754, 552), (774, 720)],
        )

        # Mirrors and stalks.
        pygame.draw.line(self.screen, carbon_hi, (470, 493), (322, 470), 11)
        pygame.draw.line(self.screen, carbon_hi, (810, 493), (958, 470), 11)
        for mirror_x in (232, 952):
            pygame.draw.rect(self.screen, carbon, (mirror_x, 440, 96, 49), border_radius=12)
            pygame.draw.rect(self.screen, (88, 113, 126), (mirror_x + 9, 449, 78, 31), border_radius=7)
            pygame.draw.line(
                self.screen,
                (185, 205, 215),
                (mirror_x + 16, 473),
                (mirror_x + 78, 453),
                2,
            )

        # Steering wheel, display and gloved hands.
        pygame.draw.ellipse(self.screen, (5, 6, 8), (525, 538, 230, 142))
        pygame.draw.rect(self.screen, carbon_hi, (551, 561, 178, 80), border_radius=23)
        pygame.draw.rect(self.screen, (8, 11, 13), (594, 570, 92, 51), border_radius=7)
        pygame.draw.rect(self.screen, accent, (604, 579, 72, 5), border_radius=2)
        pygame.draw.ellipse(self.screen, (211, 218, 224), (505, 576, 69, 93))
        pygame.draw.ellipse(self.screen, (211, 218, 224), (706, 576, 69, 93))
        self._center_text(
            self.screen,
            f"{self.player.gear}   {int(self.player.get_speed_kmh()):03d}",
            587,
            self.font_m,
            cfg.WHITE,
        )

        # Helmet crown and the three-dimensional Halo arch.  Drawing the arch
        # last makes it read as a safety structure in front of the camera.
        pygame.draw.ellipse(self.screen, (190, 196, 201), (572, 624, 136, 112))
        pygame.draw.arc(self.screen, carbon, (327, 382, 626, 278), math.pi, math.tau, 30)
        pygame.draw.arc(self.screen, carbon_hi, (331, 386, 618, 270), math.pi, math.tau, 4)
        pygame.draw.line(self.screen, carbon, (640, 496), (640, 632), 27)
        pygame.draw.line(self.screen, carbon_hi, (634, 498), (634, 625), 3)

    def _draw_grass(self):
        self.screen.fill(cfg.GRASS_COLOR)
        for x in range(-cfg.WINDOW_HEIGHT, cfg.WINDOW_WIDTH + cfg.WINDOW_HEIGHT, 80):
            pygame.draw.line(
                self.screen,
                cfg.GRASS_STRIPE,
                (x, 0),
                (x + cfg.WINDOW_HEIGHT, cfg.WINDOW_HEIGHT),
                34,
            )

    def _draw_track(self):
        points = [self._world_to_screen(p[0], p[1]) for p in self.track.center_points]
        scale = VIEW_RANGES[self.view_range_index]["scale"]
        outer_width = int(
            (self.track.width + 2 * (cfg.KERB_WIDTH + cfg.RUNOFF_WIDTH)) * scale
        )
        kerb_width = int((self.track.width + 2 * cfg.KERB_WIDTH) * scale)
        road_width = int(self.track.width * scale)
        pygame.draw.lines(self.screen, cfg.TRACK_BORDER, True, points, outer_width + 8)
        pygame.draw.lines(self.screen, cfg.RUNOFF_COLOR, True, points, outer_width)
        pygame.draw.lines(self.screen, cfg.KERB_WHITE, True, points, kerb_width)
        pygame.draw.lines(self.screen, cfg.TRACK_COLOR, True, points, road_width)

        left = [self._world_to_screen(*p) for p in self.track.left_edges]
        right = [self._world_to_screen(*p) for p in self.track.right_edges]
        for edge in (left, right):
            for i in range(0, len(edge), 4):
                j = (i + 4) % len(edge)
                color = cfg.KERB_RED if (i // 4) % 2 == 0 else cfg.KERB_WHITE
                pygame.draw.line(self.screen, color, edge[i], edge[j], max(4, int(cfg.KERB_WIDTH * scale)))

    def _draw_racing_line(self):
        line = [self._world_to_screen(*p) for p in self.track.racing_line]
        count = len(line)
        for i in range(count):
            next_i = (i + 1) % count
            if i in self.track.brake_zone_indices:
                color = cfg.RACING_LINE_BRAKE
                width = 7
            elif i in self.track.lift_zone_indices:
                color = cfg.RACING_LINE_LIFT
                width = 6
            else:
                color = cfg.RACING_LINE_COLOR
                width = 5
            pygame.draw.line(self.screen, color, line[i], line[next_i], width)

    def _draw_brake_markers(self):
        count = len(self.track.center_points)
        for zone in self.track.brake_zones:
            idx = zone["index"]
            left = self._world_to_screen(*self.track.left_edges[idx])
            right = self._world_to_screen(*self.track.right_edges[idx])
            if not self._segment_near_screen(left, right, 100):
                continue
            pygame.draw.line(self.screen, cfg.BRAKE_POINT_COLOR, left, right, 5)
            center = self._world_to_screen(*zone["point"])
            label = self.font_s.render(
                f"BRAKE  {zone['target_kmh']} KM/H", True, cfg.WHITE
            )
            box = label.get_rect(center=(center[0], center[1] - 20))
            pygame.draw.rect(self.screen, cfg.BRAKE_POINT_COLOR, box.inflate(12, 8), border_radius=4)
            self.screen.blit(label, box)

    def _draw_start_line(self):
        left = self._world_to_screen(*self.track.left_edges[0])
        right = self._world_to_screen(*self.track.right_edges[0])
        pygame.draw.line(self.screen, cfg.WHITE, left, right, 8)
        pygame.draw.line(self.screen, cfg.BLACK, left, right, 3)

    def _draw_sector_lines(self):
        for sector_number, idx in enumerate(self.track.sector_indices, start=1):
            left = self._world_to_screen(*self.track.left_edges[idx])
            right = self._world_to_screen(*self.track.right_edges[idx])
            if not self._segment_near_screen(left, right, 80):
                continue
            pygame.draw.line(self.screen, cfg.MENU_ACCENT, left, right, 4)
            center = ((left[0] + right[0]) // 2, (left[1] + right[1]) // 2)
            label = self.font_s.render(f"SECTOR {sector_number + 1}", True, cfg.WHITE)
            box = label.get_rect(center=(center[0], center[1] - 15))
            pygame.draw.rect(self.screen, cfg.HUD_BG, box.inflate(8, 4), border_radius=3)
            self.screen.blit(label, box)

    def _draw_f1_car(self, vehicle, body, accent, label):
        center = self._world_to_screen(vehicle.x, vehicle.y)
        if not (-100 < center[0] < cfg.WINDOW_WIDTH + 100 and -100 < center[1] < cfg.WINDOW_HEIGHT + 100):
            return
        view_scale = VIEW_RANGES[self.view_range_index]["scale"]
        width = max(20, int((cfg.CAR_WIDTH + 0.65) * view_scale))
        length = max(45, int((cfg.CAR_LENGTH + 0.5) * view_scale))
        car = pygame.Surface((width + 14, length + 12), pygame.SRCALPHA)
        cx = car.get_width() // 2

        tyre = (10, 11, 13)
        for y in (14, length - 14):
            pygame.draw.rect(car, tyre, (3, y - 9, 8, 18), border_radius=3)
            pygame.draw.rect(car, tyre, (car.get_width() - 11, y - 9, 8, 18), border_radius=3)

        # Front/rear wings, tapered nose, sidepods, cockpit and halo.
        pygame.draw.rect(car, body, (2, 5, car.get_width() - 4, 5), border_radius=2)
        pygame.draw.rect(car, body, (4, length + 2, car.get_width() - 8, 6), border_radius=2)
        pygame.draw.polygon(
            car,
            body,
            [
                (cx - 3, 7),
                (cx + 3, 7),
                (cx + 7, 28),
                (cx + 12, 39),
                (cx + 10, length - 9),
                (cx - 10, length - 9),
                (cx - 12, 39),
                (cx - 7, 28),
            ],
        )
        pygame.draw.polygon(
            car,
            accent,
            [(cx - 4, 10), (cx + 4, 10), (cx + 3, length - 7), (cx - 3, length - 7)],
        )
        pygame.draw.ellipse(car, (20, 24, 29), (cx - 7, 29, 14, 23))
        pygame.draw.arc(car, cfg.LIGHT_GRAY, (cx - 9, 27, 18, 19), 0, math.pi, 3)
        pygame.draw.circle(car, (245, 210, 165), (cx, 36), 4)

        relative = (vehicle.heading - self.player.heading + math.pi) % (2 * math.pi) - math.pi
        rotated = pygame.transform.rotate(car, -math.degrees(relative))
        self.screen.blit(rotated, rotated.get_rect(center=center))
        if label:
            tag = self.font_s.render(label, True, cfg.WHITE)
            self.screen.blit(tag, tag.get_rect(center=(center[0], center[1] - length // 2 - 12)))

    def _draw_minimap(self):
        rect = pygame.Rect(cfg.WINDOW_WIDTH - 250, 95, 225, 150)
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        panel.fill((5, 8, 11, 210))
        self.screen.blit(panel, rect)
        pygame.draw.rect(self.screen, self.track.accent, rect, 2, border_radius=8)

        xs = [p[0] for p in self.track.center_points]
        ys = [p[1] for p in self.track.center_points]
        span_x = max(xs) - min(xs)
        span_y = max(ys) - min(ys)
        scale = min((rect.width - 28) / span_x, (rect.height - 28) / span_y)
        ox = rect.centerx - (min(xs) + max(xs)) * 0.5 * scale
        oy = rect.centery - (min(ys) + max(ys)) * 0.5 * scale
        mini = [(int(ox + x * scale), int(oy + y * scale)) for x, y, *_ in self.track.center_points]
        pygame.draw.lines(self.screen, cfg.MID_GRAY, True, mini, 4)
        pygame.draw.lines(self.screen, cfg.WHITE, True, mini, 1)
        px, py = int(ox + self.player.x * scale), int(oy + self.player.y * scale)
        pygame.draw.circle(self.screen, CAR_LIVERIES[self.livery_index]["body"], (px, py), 5)
        if self.mode == "RACE VS AI":
            for ai in self.ai_cars:
                ax, ay = int(ox + ai.x * scale), int(oy + ai.y * scale)
                pygame.draw.circle(self.screen, ai.color, (ax, ay), 4)

    def _world_to_screen(self, x, y):
        dx, dy = x - self.player.x, y - self.player.y
        forward_x, forward_y = math.cos(self.player.heading), math.sin(self.player.heading)
        right_x, right_y = -forward_y, forward_x
        lateral = dx * right_x + dy * right_y
        forward = dx * forward_x + dy * forward_y
        scale = VIEW_RANGES[self.view_range_index]["scale"]
        return (
            int(cfg.WINDOW_WIDTH / 2 + lateral * scale),
            int(cfg.WINDOW_HEIGHT * cfg.LOOK_AHEAD - forward * scale),
        )

    def _render_menu(self):
        self.screen.fill(cfg.HUD_BG)
        pygame.draw.circle(self.screen, self.track.accent, (1080, 90), 300, 2)
        pygame.draw.circle(self.screen, cfg.DARK_GRAY, (1080, 90), 245, 1)
        self._text(self.screen, 70, 55, "RACING LINE", self.font_xl, cfg.WHITE)
        self._text(self.screen, 73, 126, "PRO  •  GRAND PRIX EDITION", self.font_m, self.track.accent)
        self._text(
            self.screen,
            73,
            165,
            "Five circuits from 2025 qualifying telemetry • progressive F1 handling",
            self.font_s,
            cfg.HUD_LABEL,
        )

        values = [
            ("CIRCUIT", f"{self.track.name}  /  {self.track.country}"),
            ("MODE", MODES[self.mode_index]),
            ("AI DIFFICULTY", DIFFICULTIES[self.difficulty_index]),
            ("VIEW RANGE", VIEW_RANGES[self.view_range_index]["name"]),
            ("LIVERY", CAR_LIVERIES[self.livery_index]["name"]),
            ("START SESSION", "PRESS ENTER / A"),
        ]
        start_y = 220
        for i, (label, value) in enumerate(values):
            y = start_y + i * 65
            selected = i == self.menu_row
            if selected:
                pygame.draw.rect(
                    self.screen,
                    (25, 32, 38),
                    (58, y - 8, 560, 53),
                    border_radius=8,
                )
                pygame.draw.rect(
                    self.screen,
                    self.track.accent,
                    (58, y - 8, 6, 53),
                    border_radius=3,
                )
            self._text(self.screen, 78, y - 2, label, self.font_s, cfg.HUD_LABEL)
            value_color = self.track.accent if selected else cfg.WHITE
            self._text(self.screen, 225, y - 9, value, self.font_m, value_color)

        self._draw_track_preview(pygame.Rect(690, 225, 510, 360))
        self._center_text(
            self.screen,
            f"{self.track.total_length / 1000:.3f} KM  •  {self.track.description}",
            610,
            self.font_s,
            cfg.HUD_LABEL,
            center_x=945,
        )
        self._center_text(
            self.screen,
            (
                f"2025 QUALIFYING REFERENCE  {self.track.reference_driver}  "
                f"{self._fmt_time(self.track.reference_lap_time)}  •  "
                + " / ".join(f"{value:.3f}" for value in self.track.reference_sector_times)
            ),
            636,
            self.font_s,
            self.track.accent,
            center_x=945,
        )
        self._text(
            self.screen,
            70,
            cfg.WINDOW_HEIGHT - 40,
            "↑↓ SELECT    ←→ CHANGE    ENTER CONFIRM    H GUIDE",
            self.font_s,
            cfg.HUD_LABEL,
        )

    def _draw_track_preview(self, rect):
        xs = [p[0] for p in self.track.center_points]
        ys = [p[1] for p in self.track.center_points]
        scale = min((rect.width - 60) / (max(xs) - min(xs)), (rect.height - 60) / (max(ys) - min(ys)))
        ox = rect.centerx - (min(xs) + max(xs)) * 0.5 * scale
        oy = rect.centery - (min(ys) + max(ys)) * 0.5 * scale
        points = [(int(ox + p[0] * scale), int(oy + p[1] * scale)) for p in self.track.center_points]
        pygame.draw.lines(self.screen, cfg.DARK_GRAY, True, points, 14)
        pygame.draw.lines(self.screen, self.track.accent, True, points, 4)
        start = points[0]
        pygame.draw.circle(self.screen, cfg.WHITE, start, 7)

    def _render_guide(self):
        self.screen.fill(cfg.HUD_BG)
        self._center_text(self.screen, "DRIVER BRIEFING", 48, self.font_xl, cfg.WHITE)
        self._center_text(
            self.screen,
            f"{self.track.name}  •  {MODES[self.mode_index]}",
            126,
            self.font_m,
            self.track.accent,
        )
        cards = [
            ("1  CONTROL", "W / ↑ throttle     S / ↓ brake     A D / ← → steer\nController: left stick + linear LT / RT     - / + changes view range"),
            ("2  READ THE LINE", "CYAN = full throttle     YELLOW = lift / prepare\nRED = brake now; target speed is shown at the marker"),
            ("3  USE THE ROAD", "Red-white kerb is driveable but unsettles the car.\nRunoff and grass reduce grip; barriers return the car safely."),
            ("4  DRIVE SMOOTHLY", "Steering lock reduces with speed. Brake in a straight line,\nrelease the brake, then turn toward the apex."),
        ]
        y = 190
        for title, body in cards:
            pygame.draw.rect(self.screen, (22, 27, 33), (140, y, 1000, 88), border_radius=10)
            pygame.draw.rect(self.screen, self.track.accent, (140, y, 6, 88), border_radius=3)
            self._text(self.screen, 170, y + 13, title, self.font_m, cfg.WHITE)
            for line_index, line in enumerate(body.split("\n")):
                self._text(self.screen, 430, y + 14 + line_index * 28, line, self.font_s, cfg.HUD_LABEL)
            y += 105
        self._center_text(
            self.screen,
            "ENTER / A  START SESSION        ESC / B  BACK",
            cfg.WINDOW_HEIGHT - 55,
            self.font_m,
            self.track.accent,
        )

    def _render_overlay(self, title, lines):
        shade = pygame.Surface((cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 185))
        self.screen.blit(shade, (0, 0))
        rect = pygame.Rect(cfg.WINDOW_WIDTH // 2 - 300, 190, 600, 310)
        pygame.draw.rect(self.screen, cfg.HUD_BG, rect, border_radius=14)
        pygame.draw.rect(self.screen, self.track.accent, rect, 3, border_radius=14)
        self._center_text(self.screen, title, 225, self.font_l, cfg.WHITE)
        for i, line in enumerate(lines):
            self._center_text(
                self.screen,
                line,
                320 + i * 45,
                self.font_m if i == 0 else self.font_s,
                self.track.accent if i == 0 else cfg.HUD_LABEL,
            )

    @staticmethod
    def _segment_near_screen(a, b, margin):
        return not (
            max(a[0], b[0]) < -margin
            or min(a[0], b[0]) > cfg.WINDOW_WIDTH + margin
            or max(a[1], b[1]) < -margin
            or min(a[1], b[1]) > cfg.WINDOW_HEIGHT + margin
        )

    @staticmethod
    def _fmt_time(value):
        if value == float("inf"):
            return "--:--.---"
        return f"{int(value // 60)}:{value % 60:06.3f}"

    @staticmethod
    def _text(surface, x, y, text, font, color):
        surface.blit(font.render(str(text), True, color), (x, y))

    @staticmethod
    def _center_text(surface, text, y, font, color, center_x=None):
        rendered = font.render(str(text), True, color)
        center = cfg.WINDOW_WIDTH // 2 if center_x is None else center_x
        surface.blit(rendered, rendered.get_rect(center=(center, y + rendered.get_height() // 2)))
