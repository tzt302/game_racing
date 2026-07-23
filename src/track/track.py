import math
import config as cfg

class Track:
    def __init__(self):
        self.center_points = []  # list of (x, y, heading, curvature)
        self.left_edges = []
        self.right_edges = []
        self.total_length = 0.0
        self.sectors = []
        self.brake_zones = []
        self.racing_line = []
        self._generate()

    def _generate(self):
        pts = []
        segs = [
            ('straight', 200.0),
            ('curve', 50.0, math.radians(90)),   # r=50m, 90deg right
            ('straight', 80.0),
            ('curve', 40.0, math.radians(90)),   # r=40m, 90deg right
            ('straight', 160.0),
            ('curve', 55.0, -math.radians(90)),  # r=55m, 90deg left
            ('straight', 80.0),
            ('curve', 45.0, -math.radians(90)),  # r=45m, 90deg left
            ('straight', 30.0),
        ]

        x, y, h = 0.0, 0.0, -math.pi/2
        for seg in segs:
            if seg[0] == 'straight':
                length = seg[1]
                steps = max(2, int(length / 2.0))
                for i in range(steps):
                    frac = (i + 1) / steps
                    px = x + frac * length * math.cos(h)
                    py = y + frac * length * math.sin(h)
                    pts.append((px, py, h, 0.0))
                x += length * math.cos(h)
                y += length * math.sin(h)
            elif seg[0] == 'curve':
                radius, angle = seg[1], seg[2]
                steps = max(4, int(abs(angle) * radius / 2.0))
                for i in range(steps):
                    frac = (i + 1) / steps
                    theta = angle * frac
                    if angle > 0:  # right turn
                        cx = x - radius * math.sin(h)
                        cy = y + radius * math.cos(h)
                        new_h = h + theta
                        px = cx + radius * math.sin(new_h)
                        py = cy - radius * math.cos(new_h)
                    else:  # left turn
                        cx = x + radius * math.sin(h)
                        cy = y - radius * math.cos(h)
                        new_h = h + theta
                        px = cx - radius * math.sin(new_h)
                        py = cy + radius * math.cos(new_h)
                    pts.append((px, py, new_h, 1.0 / radius if radius > 0 else 0))
                if angle > 0:
                    x = cx + radius * math.sin(h + angle)
                    y = cy - radius * math.cos(h + angle)
                    h = h + angle
                else:
                    x = cx - radius * math.sin(h + angle)
                    y = cy + radius * math.cos(h + angle)
                    h = h + angle

        self.center_points = pts
        hw = cfg.TRACK_WIDTH / 2.0
        self.left_edges = []
        self.right_edges = []
        for p in pts:
            nx = math.cos(p[2] + math.pi/2)
            ny = math.sin(p[2] + math.pi/2)
            self.left_edges.append((p[0] + nx * hw, p[1] + ny * hw))
            self.right_edges.append((p[0] - nx * hw, p[1] - ny * hw))

        self.total_length = self._calc_length(pts)
        self._calc_racing_line()
        self._calc_brake_zones()

    def _calc_length(self, pts):
        total = 0.0
        for i in range(1, len(pts)):
            dx = pts[i][0] - pts[i-1][0]
            dy = pts[i][1] - pts[i-1][1]
            total += math.sqrt(dx*dx + dy*dy)
        return total

    def _calc_racing_line(self):
        self.racing_line = []
        c = self.center_points
        for i in range(len(c)):
            p = c[i]
            cp = abs(p[3])
            offset = 0.0
            if cp > 0.003:
                offset = 2.0 * (1.0 if p[3] > 0 else -1.0)
            nx = math.cos(p[2] + math.pi/2) * offset
            ny = math.sin(p[2] + math.pi/2) * offset
            self.racing_line.append((p[0] + nx, p[1] + ny))

    def _calc_brake_zones(self):
        self.brake_zones = []
        c = self.center_points
        for i in range(1, len(c)):
            prev_c = c[i-1][3]
            curr_c = c[i][3]
            if abs(curr_c) > 0.005 and abs(prev_c) < 0.001:
                self.brake_zones.append((c[i][0], c[i][1], c[i][2], abs(curr_c)))

    def find_nearest(self, x, y):
        best_i, best_d = 0, float('inf')
        for i, p in enumerate(self.center_points):
            dx = p[0] - x
            dy = p[1] - y
            d = dx*dx + dy*dy
            if d < best_d:
                best_d = d
                best_i = i
        return best_i, math.sqrt(best_d)

    def get_progress(self, x, y):
        idx, _ = self.find_nearest(x, y)
        return idx / len(self.center_points)
