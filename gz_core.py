"""
Горный байкер — ядро игры (чистый Python, без графики).
Упрощённая физика горного байка: рама-балка, два колеса на рельефе,
газ/тормоз/наклон, кувырки, уровни.
Тест:  python gz_core.py
"""
import math

PX_PER_METER = 40.0
WHEEL_R = 17.0
WHEELBASE = 74.0
HEAD_H = 46.0
LEVEL_METERS = 50.0

GRAVITY = 900.0
ACCEL = 380.0          # px/s^2 при газе
ROLL = 0.16            # трение качения
MAX_SPEED = 520.0      # px/s max скорость по склону

TERRAIN_LEVEL = 1


def terrain_y(x):
    base = 400.0
    t = max(0.0, x - 500.0)
    ramp = min(1.0, t / 7000.0)
    lvl = TERRAIN_LEVEL if TERRAIN_LEVEL > 1 else 1
    pk = 1.0 + 0.16 * (lvl - 1)
    amp = (18 + 50 * ramp) * pk
    y = (amp * math.sin(t / 170.0)
         + amp * 0.25 * math.sin(t / 80.0 + 1.3)
         + (30 + 12 * (lvl - 1)) * ramp * math.sin(t / 420.0))
    blend = min(1.0, max(0.0, (x - 350.0) / 300.0))
    return base + y * blend - t * 0.02 * blend


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
        self.flips = 0
        self.air_time = 0.0
        self.air_start_angle = 0.0

    def ground_y(self):
        return terrain_y(self.x)

    def frame_y(self):
        return self.ground_y() - WHEEL_R - 5.0

    def head(self):
        return self.x, self.frame_y() - HEAD_H

    def wheel_y(self):
        # координата осей колес от земли: обе лежат на раме (жёсткая балка)
        return self.frame_y()

    def step(self, gas, brake, lean_back, lean_fwd, dt):
        slope_ang = math.atan(terrain_slope(self.x))
        # скорость вдоль склона
        gx = GRAVITY * math.sin(slope_ang)          # ускорение под уклон
        ax = gx
        if gas:
            ax += ACCEL
        if brake:
            ax -= ACCEL * 1.2
        self.vx += ax * dt
        self.vx *= (1.0 - ROLL * dt)
        self.vx = max(-MAX_SPEED, min(MAX_SPEED, self.vx))
        self.x += self.vx * dt

        # вертикальный профиль: после гребня можем оторваться
        gy = self.ground_y()
        frame = self.frame_y()
        if frame > gy - WHEEL_R - 0.1:  # над землёй
            if self.grounded:
                self.air_vy = 40.0
                self.air_time = 0.0
                self.air_start_angle = self.angle
            self.grounded = False
            self.air_time += dt
            # в воздухе раму подбрасывает по инерции, приземляемся по terrain
            self.air_vy = self.air_vy - GRAVITY * dt
        else:
            self.grounded = True
            self.air_vy = 0.0

        # наклон: следуем склону + управление наклонами
        lean = (1.0 if lean_back else 0.0) - (1.0 if lean_fwd else 0.0)
        self.angle += lean * 3.0 * dt
        self.angle += (slope_ang - self.angle) * min(1.0, 4.0 * dt)

        # кувырки
        if not self.grounded:
            self.flips = int(abs(self.angle) // (2 * math.pi))

        # посадка: при опускании рамы к земле считаем приземление
        if not self.grounded and self.frame_y() <= self.ground_y() - WHEEL_R:
            self.grounded = True
            self.air_vy = 0.0
            if self.air_time > 0.3 and int(abs(self.angle - self.air_start_angle) // (2 * math.pi)) >= 1:
                self.flips = int(abs(self.angle - self.air_start_angle) // (2 * math.pi))

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
        gas = t < 8.0
        crashed = not bike.step(gas, False, False, False, dt)
        dist = (bike.x - 150.0) / PX_PER_METER
        max_dist = max(max_dist, dist)
        TERRAIN_LEVEL = level_of(dist)
        t += dt
    return {"crashed": crashed, "max_dist_m": round(max_dist, 1),
            "level": TERRAIN_LEVEL, "vx": round(bike.vx, 1)}


if __name__ == "__main__":
    print(simulate(30.0))