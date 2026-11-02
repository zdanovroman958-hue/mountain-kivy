"""
Горный байкер — ядро игры для Kivy-версии (чистый Python).
Поведение близко к настольной версии: едем вниз, уровень растёт,
рельеф становится круче, за кувырки очки.
"""
import math

PX_PER_METER = 40.0
WHEEL_R = 17.0
WHEELBASE = 76.0
HEAD_H = 46.0
LEVEL_METERS = 45.0
CHECKPOINT_METERS = 25.0

GRAVITY = 1000.0
ACCEL = 360.0
ROLL = 0.14
MAX_SPEED = 560.0

TERRAIN_LEVEL = 1


def terrain_y(x):
    base = 400.0
    t = max(0.0, x - 500.0)
    ramp = min(1.0, t / 7000.0)
    lvl = TERRAIN_LEVEL if TERRAIN_LEVEL > 1 else 1
    pk = 1.0 + 0.15 * (lvl - 1)
    amp = (20 + 52 * ramp) * pk
    y = (amp * math.sin(t / 160.0)
         + amp * 0.3 * math.sin(t / 70.0 + 1.3)
         + (34 + 12 * (lvl - 1)) * ramp * math.sin(t / 380.0))
    blend = min(1.0, max(0.0, (x - 350.0) / 300.0))
    return base + y * blend + t * 0.02 * blend  # общий спуск вниз


def terrain_slope(x):
    h = 1.5
    return (terrain_y(x + h) - terrain_y(x - h)) / (2 * h)


class Bike:
    def __init__(self, x=150.0):
        self.x = x
        self.vx = 0.0
        self.angle = 0.0
        self.grounded = True
        self.air_vy = 0.0
        self.air_time = 0.0
        self.air_start_angle = 0.0
        self.wheel_angle = 0.0
        self.flips = 0

    def frame_y(self):
        return terrain_y(self.x) - WHEEL_R - 6.0

    def head(self):
        return self.x, self.frame_y() - HEAD_H

    def step(self, gas, brake, lean_back, lean_fwd, dt):
        slope_ang = math.atan(terrain_slope(self.x))
        ax = GRAVITY * math.sin(slope_ang)
        if gas:
            ax += ACCEL
        if brake:
            ax -= ACCEL * 1.3
        self.vx += ax * dt
        self.vx *= (1.0 - ROLL * dt)
        self.vx = max(-MAX_SPEED, min(MAX_SPEED, self.vx))
        self.x += self.vx * dt
        self.wheel_angle += (self.vx / WHEEL_R) * dt

        # вертикаль / отрыв
        cam = max(0.0, abs(self.vx) * dt * 0.018)
        gy = terrain_y(self.x)
        frame = gy - WHEEL_R - 6.0
        if not self.grounded:
            self.air_vy = self.air_vy - GRAVITY * dt
            self.air_time += dt
            # приземление
            if frame <= terrain_y(self.x) - WHEEL_R:
                self.grounded = True
                self.air_vy = 0.0
                rot = abs(self.angle - self.air_start_angle)
                if self.air_time > 0.35 and int(rot // (2 * math.pi)) >= 1:
                    self.flips = int(rot // (2 * math.pi))
        else:
            # проверяем отрыв по «выпуклости» склона
            if cam > 0.6 and (gy - terrain_y(self.x + 8)) > 6:  # поднялись над гребнем
                self.grounded = False
                self.air_vy = 120.0
                self.air_time = 0.0
                self.air_start_angle = self.angle

        lean = (1.0 if lean_back else 0.0) - (1.0 if lean_fwd else 0.0)
        self.angle += lean * 3.4 * dt
        self.angle += (slope_ang - self.angle) * min(1.0, 4.0 * dt)

        hx, hy = self.head()
        if hy + 8 > terrain_y(hx):
            return False
        return True


def level_of(dist_m):
    return int(dist_m / LEVEL_METERS) + 1


def simulate(seconds=30.0):
    bike = Bike()
    global TERRAIN_LEVEL
    TERRAIN_LEVEL = 1
    dt = 1 / 60
    t = 0.0
    crashed = False
    max_dist = 0.0
    while t < seconds and not crashed:
        crashed = not bike.step(True, False, False, False, dt)
        dist = (bike.x - 150.0) / PX_PER_METER
        max_dist = max(max_dist, dist)
        TERRAIN_LEVEL = level_of(dist)
        t += dt
    return {"crashed": crashed, "max_dist_m": round(max_dist, 1),
            "level": TERRAIN_LEVEL, "vx": round(bike.vx, 1)}


if __name__ == "__main__":
    print(simulate(30.0))