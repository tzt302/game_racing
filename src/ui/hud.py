import pygame

import config as cfg


class HUD:
    def __init__(self, font_small, font_medium, font_large):
        self.fs = font_small
        self.fm = font_medium
        self.fl = font_large

    def draw(self, surf, vehicle, lap, total_laps, position, track, mode, timing=None):
        width, height = cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT
        panel = pygame.Surface((width, 92), pygame.SRCALPHA)
        panel.fill((*cfg.HUD_BG, 232))
        surf.blit(panel, (0, height - 92))
        pygame.draw.line(surf, track.accent, (0, height - 92), (width, height - 92), 3)

        speed = vehicle.get_speed_kmh()
        self._label(surf, 20, height - 80, "SPEED")
        self._text(surf, 20, height - 61, f"{int(speed):03d}", self.fl)
        self._text(surf, 112, height - 52, "KM/H", self.fs, cfg.HUD_LABEL)

        self._label(surf, 205, height - 80, "STEERING")
        cx, cy = 262, height - 43
        pygame.draw.line(surf, cfg.DARK_GRAY, (220, cy), (304, cy), 5)
        steer_norm = vehicle.steer_angle / max(cfg.STEER_LOCK_LOW, 0.01)
        marker = int(cx + max(-1, min(1, steer_norm)) * 40)
        pygame.draw.circle(surf, track.accent, (marker, cy), 7)

        self._label(surf, 345, height - 80, "GEAR")
        self._text(surf, 355, height - 58, str(vehicle.gear), self.fm)
        rpm_width = 66
        pygame.draw.rect(surf, cfg.DARK_GRAY, (333, height - 27, rpm_width, 6))
        pygame.draw.rect(
            surf,
            track.accent,
            (333, height - 27, int(rpm_width * min(vehicle.rpm / 12600, 1.0)), 6),
        )

        self._label(surf, 445, height - 80, "LAP")
        self._text(surf, 445, height - 58, f"{lap} / {total_laps}", self.fm)

        self._label(surf, 590, height - 80, "POSITION")
        pos_text = "SOLO" if mode == "TIME TRIAL" else f"P{position}"
        self._text(surf, 590, height - 58, pos_text, self.fm)

        surface_colors = {
            "asphalt": cfg.WHITE,
            "kerb": cfg.KERB_RED,
            "runoff": cfg.RACING_LINE_LIFT,
            "grass": (115, 220, 120),
        }
        self._label(surf, 735, height - 80, "SURFACE")
        self._text(
            surf,
            735,
            height - 58,
            vehicle.surface.upper(),
            self.fm,
            surface_colors.get(vehicle.surface, cfg.WHITE),
        )

        self._pedal(surf, width - 125, height - 76, vehicle.throttle, "THR", track.accent)
        self._pedal(surf, width - 65, height - 76, vehicle.brake, "BRK", cfg.BRAKE_POINT_COLOR)

        # Upper information strip deliberately contrasts the circuit.
        top = pygame.Surface((340, 62), pygame.SRCALPHA)
        top.fill((5, 8, 11, 205))
        surf.blit(top, (14, 14))
        self._text(surf, 28, 23, track.name, self.fm)
        self._text(
            surf,
            28,
            51,
            f"{track.country}  •  {track.total_length / 1000:.3f} KM  •  {mode}",
            self.fs,
            cfg.HUD_LABEL,
        )

        # Persistent legend makes the previously hidden assists self-explanatory.
        legend_x = width - 310
        pygame.draw.line(surf, cfg.RACING_LINE_COLOR, (legend_x, 30), (legend_x + 34, 30), 5)
        self._text(surf, legend_x + 44, 20, "IDEAL LINE", self.fs)
        pygame.draw.line(surf, cfg.RACING_LINE_BRAKE, (legend_x, 56), (legend_x + 34, 56), 5)
        self._text(surf, legend_x + 44, 46, "BRAKE ZONE", self.fs)
        if timing:
            self._draw_timing(surf, timing, track)

    def _pedal(self, surf, x, y, amount, label, color):
        pygame.draw.rect(surf, cfg.DARK_GRAY, (x, y, 34, 52), border_radius=4)
        fill = int(48 * max(0.0, min(1.0, amount)))
        if fill:
            pygame.draw.rect(surf, color, (x + 3, y + 49 - fill, 28, fill), border_radius=3)
        self._text(surf, x - 1, y + 56, label, self.fs, cfg.HUD_LABEL)

    def _draw_timing(self, surf, timing, track):
        colors = {
            "purple": (191, 77, 255),
            "green": (42, 220, 112),
            "yellow": (255, 205, 55),
            None: cfg.HUD_LABEL,
        }
        panel = pygame.Surface((600, 66), pygame.SRCALPHA)
        panel.fill((5, 8, 11, 210))
        x = 355
        surf.blit(panel, (x, 14))
        for index in range(3):
            sector_x = x + 14 + index * 100
            value = timing["sector_times"][index]
            status = timing["sector_status"][index]
            label = f"S{index + 1}"
            if timing["current_sector"] == index + 1 and value is None:
                label += " •"
            self._text(surf, sector_x, 24, label, self.fs, colors.get(status, cfg.HUD_LABEL))
            self._text(
                surf,
                sector_x,
                47,
                "--.---" if value is None else f"{value:.3f}",
                self.fs,
                cfg.WHITE,
            )
        self._text(surf, x + 318, 24, "PERSONAL BEST", self.fs, cfg.HUD_LABEL)
        self._text(
            surf,
            x + 318,
            46,
            self._format_lap(timing["personal_best_lap"]),
            self.fs,
            cfg.WHITE,
        )
        fastest = timing.get("fastest_driver", "---")
        self._text(surf, x + 458, 24, f"FASTEST {fastest}", self.fs, track.accent)
        self._text(
            surf,
            x + 458,
            46,
            self._format_lap(timing["session_best_lap"]),
            self.fs,
            cfg.WHITE,
        )

    @staticmethod
    def _format_lap(value):
        if value == float("inf"):
            return "--:--.---"
        return f"{int(value // 60)}:{value % 60:06.3f}"

    def _text(self, surf, x, y, text, font, color=None):
        surf.blit(font.render(str(text), True, color or cfg.HUD_TEXT), (x, y))

    def _label(self, surf, x, y, text):
        self._text(surf, x, y, text, self.fs, cfg.HUD_LABEL)
