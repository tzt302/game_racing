import math
import pygame
import config as cfg

class HUD:
    def __init__(self, font_small, font_medium, font_large):
        self.fs = font_small
        self.fm = font_medium
        self.fl = font_large

    def draw(self, surf, vehicle, ai, lap, total_laps, position):
        W, H = cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT
        # Bottom HUD bar
        pygame.draw.rect(surf, cfg.HUD_BG, (0, H - 90, W, 90))
        pygame.draw.line(surf, cfg.WHITE, (0, H - 90), (W, H - 90), 2)

        speed = vehicle.get_speed_kmh()

        # Speed
        self._label(surf, 20, H - 78, 'SPEED', self.fs)
        self._text(surf, 20, H - 58, f'{int(speed)}', self.fl)
        self._text(surf, 115, H - 55, 'km/h', self.fs, cfg.HUD_LABEL)

        # Speed bar
        sx, sy = 190, H - 62
        sw, sh = 160, 10
        pygame.draw.rect(surf, cfg.DARK_GRAY, (sx, sy, sw, sh))
        fill = int(sw * min(speed / cfg.MAX_SPEED, 1.0))
        pygame.draw.rect(surf, cfg.WHITE, (sx, sy, fill, sh))

        # RPM
        self._label(surf, 400, H - 78, 'RPM', self.fs)
        rpm_pct = min(speed / cfg.MAX_SPEED, 1.0)
        for i in range(10):
            bx = 390 + i * 20
            bh = 4 + int(i * 2.5)
            on = i / 10.0 < rpm_pct
            clr = cfg.WHITE if on else cfg.DARK_GRAY
            if on and i >= 8:
                clr = cfg.MID_GRAY
            pygame.draw.rect(surf, clr, (bx, H - 58 - bh, 14, bh))

        # Gear (simulated)
        self._label(surf, 620, H - 78, 'GEAR', self.fs)
        gear = self._calc_gear(speed)
        self._text(surf, 630, H - 58, str(gear), self.fm)

        # Lap
        self._label(surf, 780, H - 78, 'LAP', self.fs)
        self._text(surf, 780, H - 58, f'{lap} / {total_laps}', self.fm)

        # Position
        self._label(surf, 960, H - 78, 'POS', self.fs)
        pos_txt = {1: '1st', 2: '2nd', 3: '3rd'}
        self._text(surf, 960, H - 58, pos_txt.get(position, f'{position}th'), self.fm)

        # Gas / Brake indicators
        gx = W - 90
        pygame.draw.rect(surf, cfg.DARK_GRAY, (gx, H - 70, 30, 50))
        gh = int(50 * vehicle.throttle)
        pygame.draw.rect(surf, cfg.WHITE, (gx, H - 20 - gh, 30, gh))
        self._text(surf, gx - 2, H - 16, 'GAS', self.fs)

        bx = W - 40
        pygame.draw.rect(surf, cfg.DARK_GRAY, (bx, H - 70, 30, 50))
        bh = int(50 * vehicle.brake)
        pygame.draw.rect(surf, cfg.WHITE, (bx, H - 20 - bh, 30, bh))
        self._text(surf, bx, H - 16, 'BRK', self.fs)

        # Top-left info
        self._text(surf, 20, 15, 'RACING LINE PRO', self.fm)
        self._text(surf, 20, 50, 'B/W GP CIRCUIT', self.fs, cfg.HUD_LABEL)

    def _calc_gear(self, speed):
        gears = [0, 60, 120, 180, 240, 300, 400]
        for i, g in enumerate(gears):
            if speed < g:
                return max(1, i)
        return 6

    def _text(self, surf, x, y, txt, font, color=None):
        s = font.render(txt, True, color or cfg.WHITE)
        surf.blit(s, (x, y))

    def _label(self, surf, x, y, txt, font):
        s = font.render(txt, True, cfg.HUD_LABEL)
        surf.blit(s, (x, y))
