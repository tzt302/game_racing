import math
import pygame
import config as cfg
from track.track import Track
from physics.vehicle import Vehicle
from ai.opponent import AIOpponent
from game.input import InputHandler
from ui.hud import HUD

class GameLoop:
    def __init__(self, screen, clock):
        self.screen = screen
        self.clock = clock
        self.font_s = pygame.font.SysFont('arial', 13, bold=True)
        self.font_m = pygame.font.SysFont('arial', 22, bold=True)
        self.font_l = pygame.font.SysFont('arial', 40, bold=True)
        self.font_xl = pygame.font.SysFont('arial', 60, bold=True)
        self.hud = HUD(self.font_s, self.font_m, self.font_l)
        self.input = InputHandler()

        self.track = Track()
        self.player = Vehicle()
        self.ai = AIOpponent(self.track)

        self.cam_x = 0.0
        self.cam_y = 0.0
        self.lap = 0
        self.total_laps = 5
        self.race_over = False
        self.paused = False
        self.show_racing_line = True
        self.show_brake_zones = True

        self.lap_timer = 0.0
        self.player_best_lap = float('inf')
        self.player_last_lap = 0.0
        self.player_progress = 0.0
        self.ai_progress = 0.0
        self.lap_start_idx = 0

        self._reset_positions()

    def _reset_positions(self):
        p = self.track.center_points[0]
        self.player.reset(p[0], p[1], p[2])
        p2 = self.track.center_points[min(40, len(self.track.center_points)-1)]
        self.ai.reset(p2[0], p2[1], p2[2])
        self.cam_x = p[0] - cfg.WINDOW_WIDTH / (2 * cfg.PX_PER_M)
        self.cam_y = p[1] - cfg.WINDOW_HEIGHT * cfg.LOOK_AHEAD / cfg.PX_PER_M

    def _update(self, dt):
        dt = min(dt, 0.05)

        self.player.update(dt, self.input.steer, self.input.throttle, self.input.brake)
        self.ai.update(dt, None)

        self._constrain_to_track(self.player)
        self._constrain_to_track(self.ai)

        self.cam_x = self.player.x - cfg.WINDOW_WIDTH / (2 * cfg.PX_PER_M)
        self.cam_y = self.player.y - cfg.WINDOW_HEIGHT * cfg.LOOK_AHEAD / cfg.PX_PER_M

        pi, _ = self.track.find_nearest(self.player.x, self.player.y)
        self.player_progress = pi / len(self.track.center_points)
        ai, _ = self.track.find_nearest(self.ai.x, self.ai.y)
        self.ai_progress = ai / len(self.track.center_points)

        self.lap_timer += dt
        if pi < 3 and self.player_progress > 0.85:
            if self.lap_start_idx >= pi or self.lap == 0:
                self.lap += 1
                if self.lap > 1:
                    self.player_last_lap = self.lap_timer
                    if self.player_last_lap < self.player_best_lap:
                        self.player_best_lap = self.player_last_lap
                self.lap_timer = 0.0
        self.lap_start_idx = pi

        if self.lap >= self.total_laps:
            self.race_over = True

        if self.input.reset_pressed and not self.race_over:
            self._reset_positions()
        if self.input.reset_pressed and self.race_over:
            self.lap = 0
            self.race_over = False
            self.lap_timer = 0.0
            self.player_best_lap = float('inf')
            self.player_last_lap = 0.0
            self._reset_positions()

    def _constrain_to_track(self, veh):
        idx, dist = self.track.find_nearest(veh.x, veh.y)
        half_w = cfg.TRACK_WIDTH / 2.0 - cfg.CAR_WIDTH / 2.0
        if dist > half_w:
            p = self.track.center_points[idx]
            dx = veh.x - p[0]
            dy = veh.y - p[1]
            d = math.sqrt(dx*dx + dy*dy)
            if d > 0.001:
                veh.x = p[0] + dx / d * half_w * 0.95
                veh.y = p[1] + dy / d * half_w * 0.95
            veh.speed *= 0.92  # speed penalty for grass running
            veh.crashed = True
        elif veh.crashed and dist < half_w * 0.5:
            veh.crashed = False

    def _render(self):
        surf = self.screen
        W, H = cfg.WINDOW_WIDTH, cfg.WINDOW_HEIGHT
        cx, cy = self.cam_x, self.cam_y

        surf.fill(cfg.GRASS_COLOR)
        self._draw_track(surf, cx, cy)

        if self.show_racing_line:
            self._draw_racing_line(surf, cx, cy)
        if self.show_brake_zones:
            self._draw_brake_zones(surf, cx, cy)

        self._draw_car(surf, cx, cy, self.player, cfg.CAR_COLOR, '')
        self._draw_car(surf, cx, cy, self.ai, cfg.AI_CAR_COLOR, 'AI')

        self._draw_minimap(surf)

        pos = 1 if self.player_progress > self.ai_progress else 2
        self.hud.draw(surf, self.player, self.ai,
                      min(self.lap + 1, self.total_laps), self.total_laps, pos)

        y = 15
        if self.player_last_lap > 0:
            s = self.font_s.render(f'LAST  {self._fmt_time(self.player_last_lap)}', True, cfg.HUD_LABEL)
            surf.blit(s, (W - 200, y)); y += 20
        if self.player_best_lap < float('inf'):
            s = self.font_s.render(f'BEST  {self._fmt_time(self.player_best_lap)}', True, cfg.WHITE)
            surf.blit(s, (W - 200, y))

        if self.paused:
            s = pygame.Surface((W, H))
            s.set_alpha(160)
            s.fill(cfg.BLACK)
            surf.blit(s, (0, 0))
            for txt, y in [('PAUSED', H//2-60), ('ESC to resume', H//2)]:
                t = (self.font_l if 'PAUSED' in txt else self.font_s).render(txt, True, cfg.WHITE)
                surf.blit(t, (W//2 - t.get_width()//2, y if 'PAUSED' in txt else H//2))

        if self.race_over:
            s = pygame.Surface((W, H))
            s.set_alpha(180)
            s.fill(cfg.BLACK)
            surf.blit(s, (0, 0))
            pos = 1 if self.player_progress > self.ai_progress else 2
            t = self.font_xl.render(f'{pos}{self._ord(pos)} PLACE!', True, cfg.WHITE)
            surf.blit(t, (W//2 - t.get_width()//2, H//2 - 80))
            t2 = self.font_s.render('Press R to restart', True, cfg.HUD_LABEL)
            surf.blit(t2, (W//2 - t2.get_width()//2, H//2 + 10))

    def _draw_track(self, surf, cx, cy):
        pts = self.track.center_points
        m = -200
        lv, rv = [], []
        for i in range(len(pts)):
            lp, rp = self.track.left_edges[i], self.track.right_edges[i]
            sl = (int((lp[0]-cx)*cfg.PX_PER_M), int((lp[1]-cy)*cfg.PX_PER_M))
            sr = (int((rp[0]-cx)*cfg.PX_PER_M), int((rp[1]-cy)*cfg.PX_PER_M))
            if (sl[0] > m and sl[0] < cfg.WINDOW_WIDTH+200 and sl[1] > m and sl[1] < cfg.WINDOW_HEIGHT+200):
                lv.append(sl)
                rv.append(sr)
        if len(lv) > 2:
            pygame.draw.polygon(surf, cfg.TRACK_COLOR, lv + rv[::-1])
            pygame.draw.lines(surf, cfg.BLACK, False, lv, 3)
            pygame.draw.lines(surf, cfg.BLACK, False, rv, 3)
            cv = [(int((p[0]-cx)*cfg.PX_PER_M), int((p[1]-cy)*cfg.PX_PER_M)) for p in pts
                  if -200 < int((p[0]-cx)*cfg.PX_PER_M) < cfg.WINDOW_WIDTH+200
                  and -200 < int((p[1]-cy)*cfg.PX_PER_M) < cfg.WINDOW_HEIGHT+200]
            for i in range(0, len(cv)-6, 6):
                if dist2(cv[i], cv[i+3]) > 400:
                    pygame.draw.line(surf, cfg.ROAD_CENTER, cv[i], cv[i+3], 1)

    def _draw_racing_line(self, surf, cx, cy):
        pts = self.track.racing_line
        sv = []
        for p in pts:
            sx, sy = int((p[0]-cx)*cfg.PX_PER_M), int((p[1]-cy)*cfg.PX_PER_M)
            if -100 < sx < cfg.WINDOW_WIDTH+100 and -100 < sy < cfg.WINDOW_HEIGHT+100:
                sv.append((sx, sy))
        for i in range(0, len(sv)-4, 4):
            if dist2(sv[i], sv[i+2]) > 200:
                pygame.draw.line(surf, cfg.RACING_LINE_COLOR, sv[i], sv[i+2], 1)

    def _draw_brake_zones(self, surf, cx, cy):
        for bz in self.track.brake_zones:
            sx, sy = int((bz[0]-cx)*cfg.PX_PER_M), int((bz[1]-cy)*cfg.PX_PER_M)
            if -50 < sx < cfg.WINDOW_WIDTH+50 and -50 < sy < cfg.WINDOW_HEIGHT+50:
                pygame.draw.circle(surf, cfg.BLACK, (sx, sy), 8, 2)
                t = self.font_s.render('BRK', True, cfg.BLACK)
                surf.blit(t, (sx - 14, sy - 18))

    def _draw_car(self, surf, cx, cy, veh, color, label):
        sx = int((veh.x-cx)*cfg.PX_PER_M)
        sy = int((veh.y-cy)*cfg.PX_PER_M)
        if sx < -200 or sx > cfg.WINDOW_WIDTH+200 or sy < -200 or sy > cfg.WINDOW_HEIGHT+200:
            return
        c = (200, 0, 0) if (veh.crashed and color == cfg.BLACK) else color
        cs = pygame.Surface((cfg.CAR_WIDTH_PX+4, cfg.CAR_LENGTH_PX+4), pygame.SRCALPHA)
        if veh.crashed and color == cfg.BLACK:
            pygame.draw.rect(cs, c, (2, 2, cfg.CAR_WIDTH_PX, cfg.CAR_LENGTH_PX))
            pygame.draw.rect(cs, cfg.BLACK, (2, 2, cfg.CAR_WIDTH_PX, cfg.CAR_LENGTH_PX), 2)
        else:
            pygame.draw.rect(cs, c, (2, 2, cfg.CAR_WIDTH_PX, cfg.CAR_LENGTH_PX))
            mid = cfg.CAR_WIDTH_PX//2 + 2
            pygame.draw.circle(cs, cfg.WHITE if c == cfg.BLACK else cfg.BLACK,
                              (mid, cfg.CAR_LENGTH_PX//2+2), 6)
        a = math.degrees(veh.heading) - 90
        rot = pygame.transform.rotate(cs, -a)
        surf.blit(rot, rot.get_rect(center=(sx, sy)))
        if label:
            t = self.font_s.render(label, True, cfg.DARK_GRAY)
            surf.blit(t, (sx - 8, sy - cfg.CAR_LENGTH_PX//2 - 16))

    def _draw_minimap(self, surf):
        ms = 100
        mx, my = cfg.WINDOW_WIDTH - ms - 15, 15
        pygame.draw.rect(surf, cfg.WHITE, (mx, my, ms, ms))
        pygame.draw.rect(surf, cfg.BLACK, (mx, my, ms, ms), 2)
        c = self.track.center_points
        sc = ms / 420.0
        ox, oy = mx+ms//2, my+ms//2
        l = [(int(ox+(p[0]-c[0][0])*sc), int(oy+(p[1]-c[0][1])*sc)) for p in self.track.left_edges[::5]]
        r = [(int(ox+(p[0]-c[0][0])*sc), int(oy+(p[1]-c[0][1])*sc)) for p in self.track.right_edges[::5]]
        if l and r:
            pygame.draw.polygon(surf, cfg.LIGHT_GRAY, l + r[::-1])
            pygame.draw.lines(surf, cfg.BLACK, True, l, 1)
            pygame.draw.lines(surf, cfg.BLACK, True, r, 1)
        px = int(ox+(self.player.x-c[0][0])*sc)
        py_ = int(oy+(self.player.y-c[0][1])*sc)
        pygame.draw.circle(surf, cfg.BLACK, (px, py_), 4)
        ax = int(ox+(self.ai.x-c[0][0])*sc)
        ay = int(oy+(self.ai.y-c[0][1])*sc)
        pygame.draw.circle(surf, cfg.DARK_GRAY, (ax, ay), 3)

    def _fmt_time(self, t):
        return f'{int(t//60)}:{t%60:05.2f}'

    def _ord(self, n):
        return 'st' if n == 1 else 'nd' if n == 2 else 'rd'

def dist2(a, b):
    dx = a[0]-b[0]
    dy = a[1]-b[1]
    return dx*dx + dy*dy