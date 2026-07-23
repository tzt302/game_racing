"""Run a deterministic, hands-free gameplay showcase for video capture."""

import math
import sys
import time
from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config as cfg
from game.loop import GameLoop, MODES
from track.layouts import TRACK_ORDER


def angle_delta(target, current):
    return (target - current + math.pi) % (2.0 * math.pi) - math.pi


def drive_player(game):
    track = game.track
    car = game.player
    index, distance = track.find_nearest(car.x, car.y)
    count = len(track.center_points)
    look_steps = max(5, int((20.0 + car.speed * 0.55) / track.SAMPLE_METRES))
    target_index = (index + look_steps) % count
    line_target = track.racing_line[target_index]
    center_target = track.center_points[target_index]
    line_weight = 0.82 if distance < track.width * 0.42 else 0.32
    target_x = center_target[0] + (line_target[0] - center_target[0]) * line_weight
    target_y = center_target[1] + (line_target[1] - center_target[1]) * line_weight
    target_heading = math.atan2(target_y - car.y, target_x - car.x)
    game.input.steer = max(
        -1.0, min(1.0, angle_delta(target_heading, car.heading) * 2.18)
    )

    preview = [
        track.recommended_speeds[(index + step) % count]
        for step in range(5, max(6, int(170 / track.SAMPLE_METRES)))
    ]
    target_speed = min(preview) / 3.6 * 1.01
    speed_error = target_speed - car.speed
    game.input.throttle = max(0.0, min(1.0, speed_error / 9.0 + 0.24))
    game.input.brake = max(0.0, min(1.0, -speed_error / 11.0))
    if game.input.brake > 0.04:
        game.input.throttle = 0.0


def main():
    pygame.init()
    screen = pygame.display.set_mode((cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT))
    pygame.display.set_caption("Racing Line Pro Promo")
    clock = pygame.time.Clock()
    game = GameLoop(screen, clock)
    game.track_index = TRACK_ORDER.index("monza")
    game.mode_index = MODES.index("RACE VS AI")
    game.mode = MODES[game.mode_index]
    game.view_range_index = 2
    game._load_track()

    start = time.perf_counter()
    race_started = False
    running = True
    while running:
        elapsed = time.perf_counter() - start
        if elapsed >= 30.0:
            break
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        if elapsed < 2.8:
            game.state = "menu"
            game.menu_row = 5
        elif elapsed < 4.8:
            game.state = "guide"
        else:
            if not race_started:
                game._reset_race()
                game.state = "race"
                game.audio.play_startup()
                race_started = True
            if game.lights_out:
                drive_player(game)
            game._update(1.0 / cfg.FPS)

        game._render()
        pygame.display.flip()
        clock.tick(cfg.FPS)

    game.audio.silence()
    game.audio.stop_startup()
    pygame.quit()


if __name__ == "__main__":
    main()
