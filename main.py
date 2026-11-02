"""
Горный байкер — Kivy-версия (настоящая) для Android/ПК.
Использует готовые PNG-спрайты из assets/ и ядро gz_core.
Запуск: python main.py   (нужен Python 3.12/3.13 + pip install kivy)
"""
import os
import math
import random

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Rectangle, Ellipse, Line, PushMatrix, PopMatrix, Rotate
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window
from kivy.utils import get_color_from_hex

import gz_core as G

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")

AMBER = get_color_from_hex("#f0ac3c")
CREAM = get_color_from_hex("#e4ded2")
RED = get_color_from_hex("#d64632")


def tex(name):
    p = os.path.join(ASSETS, name + ".png")
    if not os.path.exists(p):
        return None
    img = CoreImage(p)
    return img.texture


def hrand(i, salt=0):
    n = (int(i) * 374761393 + salt * 668265263) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


class GameArea(Widget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.T = {n: tex(n) for n in
                  ("sky", "hills", "mtn_far", "mtn_mid", "dirt", "grass",
                   "wheel", "frame", "torso", "head", "thigh", "shin", "boot",
                   "shock", "fork_low", "fork_up", "seatstay", "rear_arm")}
        self.rocks = [tex("rock_%d" % i) for i in range(6)]
        self.trees = [tex("pine_%d_%d" % (l, h)) for l in (0, 1) for h in (58, 78, 100, 126, 152)]
        self.new_game()
        self.bind(size=self.redraw)

    def new_game(self):
        self.bike = G.Bike()
        G.TERRAIN_LEVEL = 1
        self.state = "menu"
        self.level = 1
        self.meters = 0.0
        self.speed = 0.0
        self.points = 0
        self.flips = 0
        self.checkpoints = 0
        self.best = 0.0
        self.cam_x = 0.0
        self.dust = []
        self.banner = ("", 0.0)
        self.gas = self.brake = self.sback = self.sfwd = False
        self.redraw()

    def start(self):
        self.bike = G.Bike()
        G.TERRAIN_LEVEL = 1
        self.level = 1
        self.meters = 0.0
        self.points = 0
        self.flips = 0
        self.checkpoints = 0
        self.dust = []
        self.crashes = getattr(self, "crashes", 0) + 0
        self.state = "play"
        self.banner = ("", 0.0)
        self.redraw()

    def crash(self):
        self.state = "over"
        self.best = max(self.best, self.meters)
        self.redraw()

    def screen_y(self, wy):
        # world y: terrain ~400..~800; маппим так, чтобы ~450 был у нижней трети экрана
        return self.height - (wy - 350.0)

    # ---------- логика ----------
    def tick(self, dt):
        if self.state != "play":
            return
        dt = min(dt, 1 / 30)
        ok = self.bike.step(self.gas, self.brake, self.sback, self.sfwd, dt)
        self.meters = max(0.0, (self.bike.x - 150.0) / G.PX_PER_METER)
        self.speed = self.bike.vx / G.PX_PER_METER * 3.6
        nlv = G.level_of(self.meters)
        if nlv > self.level:
            self.level = nlv
            G.TERRAIN_LEVEL = self.level
            self.points += 20
            self.banner = ("УРОВЕНЬ %d" % self.level, 1.6)
        # флаги-контрольные точки
        cp = int(self.meters // G.CHECKPOINT_METERS)
        if cp > self.checkpoints:
            self.checkpoints = cp
            self.points += 10
        if self.bike.flips:
            self.flips += self.bike.flips
            self.points += self.bike.flips * 15
            self.banner = ("Кувырок x%d!" % self.bike.flips, 1.2)
            self.bike.flips = 0
        # пыль
        if self.gas and random.random() < 0.3:
            self.dust.append([self.bike.x - 20 + random.uniform(-6, 6),
                              self.bike.frame_y(), random.uniform(-20, 10), random.uniform(-30, -10), 0.6])
        for d in self.dust:
            d[0] += d[2] * dt
            d[1] += d[3] * dt
            d[2] *= 0.9
            d[4] -= dt
        self.dust = [d for d in self.dust if d[4] > 0]

        if not ok:
            self.crash()
        self.redraw()

    # ---------- отрисовка ----------
    def redraw(self, *a):
        self.canvas.clear()
        w, h = self.width, self.height
        if w < 10 or h < 10:
            return
        cam = self.bike.x - w * 0.35
        self.cam_x = cam
        with self.canvas:
            self.draw_sky(w, h)
            self.draw_mountains(w, h, cam)
            self.draw_terrain(w, h, cam)
            self.draw_props(w, h, cam)
            self.draw_flags(w, h, cam)
            self.draw_dust(w, h, cam)
            if self.state in ("play", "over"):
                self.draw_bike(w, h, cam)
            if self.state == "over":
                Color(0.3, 0.05, 0.05, 0.55)
                Rectangle(pos=(0, 0), size=(w, h))

    def draw_sky(self, w, h):
        if self.T["sky"]:
            Color(1, 1, 1)
            Rectangle(texture=self.T["sky"], pos=(0, 0), size=(w, h))
        else:
            Color(0.2, 0.27, 0.4)
            Rectangle(pos=(0, 0), size=(w, h))

    def tiled(self, tex_, y, factor, hh, cam):
        if not tex_:
            return
        tw = tex_.width
        x = -((cam * factor) % tw)
        Color(1, 1, 1)
        while x < self.width:
            Rectangle(texture=tex_, pos=(x, y), size=(tw, hh))
            x += tw

    def draw_mountains(self, w, h, cam):
        self.tiled(self.T["mtn_far"], h - 420, 0.05, 400, cam)
        self.tiled(self.T["mtn_mid"], h - 330, 0.10, 320, cam)
        self.tiled(self.T["hills"], h - 260, 0.18, 240, cam)

    def draw_terrain(self, w, h, cam):
        n_d = self.T.get("dirt")
        if n_d:
            self.tiled(n_d, 0, 1.0, h, cam)
        # поверхность земли линией
        pts = []
        for i in range(0, int(w) + 1, 6):
            x = int(cam) + i
            pts += [i, self.screen_y(G.terrain_y(x))]
        if self.T["grass"]:
            Color(1, 1, 1)
            gw = self.T["grass"].width
            gx = -((cam) % gw)
            gy = self.screen_y(G.terrain_y(int(cam))) - 6
            # упрощённо: тянем траву по всему низу
            Rectangle(texture=self.T["grass"], pos=(0, gy), size=(w, self.height - gy))
        Color(0.12, 0.09, 0.07, 0.6)
        Line(points=pts, width=3, joint="bevel")

    def draw_props(self, w, h, cam):
        slot = 150
        k0 = int(cam // slot) - 1
        for k in range(k0, k0 + int(w // slot) + 3):
            wx = k * slot + hrand(k, 7) * slot
            if wx < 700:
                continue
            if hrand(k, 1) < 0.5:
                spr = self.trees[int(hrand(k, 2) * len(self.trees)) % len(self.trees)]
                if spr:
                    self.blit(spr, self.screen_x(wx, cam) - spr.width / 2,
                              self.screen_y(G.terrain_y(wx)) - spr.height)
            else:
                spr = self.rocks[int(hrand(k, 3) * len(self.rocks)) % len(self.rocks)]
                if spr:
                    self.blit(spr, self.screen_x(wx, cam) - spr.width / 2,
                              self.screen_y(G.terrain_y(wx)) - spr.height)

    def screen_x(self, wx, cam):
        return wx - cam

    def blit(self, spr, x, y):
        Color(1, 1, 1)
        Rectangle(texture=spr, pos=(x, y), size=(spr.width, spr.height))

    def draw_flags(self, w, h, cam):
        fl = tex("flag_red_0")
        fg = tex("flag_gold_0")
        for i in range(1, 12):
            wx = 150.0 + i * G.CHECKPOINT_METERS * G.PX_PER_METER
            if wx < cam - 60 or wx > cam + w + 60:
                continue
            spr = fg if i <= self.checkpoints else fl
            if spr:
                self.blit(spr, self.screen_x(wx, cam) - 8, self.screen_y(G.terrain_y(wx)) - spr.height + 8)

    def draw_dust(self, w, h, cam):
        for d in self.dust:
            a = max(0.0, d[4] / 0.6)
            Color(0.45, 0.37, 0.3, a * 0.5)
            Ellipse(pos=(self.screen_x(d[0], cam) - 5, self.screen_y(d[1]) - 5), size=(10, 10))

    def draw_bike(self, w, h, cam):
        b = self.bike
        cx = self.screen_x(b.x, cam)
        fy = self.screen_y(b.frame_y())
        gy = self.screen_y(G.terrain_y(b.x))
        # тень
        Color(0, 0, 0, 0.3)
        Ellipse(pos=(cx - 22, gy + 4), size=(44, 9))

        # колеса (вращаются)
        for dx in (-G.WHEELBASE / 2, G.WHEELBASE / 2):
            a = math.cos(b.angle) * dx
            s = math.sin(b.angle) * dx
            wx = cx + a
            wy = fy + s
            if self.T["wheel"]:
                r = self.T["wheel"].width / 2
                PushMatrix()
                Rotate(angle=-math.degrees(b.wheel_angle), origin=(wx, wy))
                Color(1, 1, 1)
                Rectangle(texture=self.T["wheel"], pos=(wx - r, wy - r), size=(r * 2, r * 2))
                PopMatrix()
            else:
                Color(0.1, 0.1, 0.12)
                Ellipse(pos=(wx - G.WHEEL_R, wy - G.WHEEL_R), size=(G.WHEEL_R * 2, G.WHEEL_R * 2))

        # рама + гонщик (вращаются по углу рамы)
        ang = -math.degrees(b.angle)
        def part(name, dx, dy, pa=0.0, scl=1.0):
            t = self.T.get(name)
            if not t:
                return
            r = t.width / 2
            PushMatrix()
            Rotate(angle=pa, origin=(cx + dx, fy + dy))
            Rotate(angle=ang, origin=(cx, fy))
            Color(1, 1, 1)
            Rectangle(texture=t, pos=(cx + dx - r, fy + dy - r), size=(t.width // scl, t.height // scl))
            PopMatrix()
        part("frame", 0, 0)
        part("seatstay", -14, 2)
        part("rear_arm", -26, 6, scl=3)
        part("shock", -8, -6, scl=2)
        part("fork_up", 22, -4, scl=2)
        part("fork_low", 26, 4, scl=2)
        # гонщик (простые позы)
        part("torso", 8, -14, scl=2)
        part("thigh", -2, -8, scl=2)
        part("shin", -6, 0, scl=2)
        part("boot", -8, 6, scl=2)
        part("head", 14, -30, scl=2)

    def controls_text(self):
        return ""


class GameApp(App):
    def build(self):
        Window.clearcolor = (0.1, 0.12, 0.15, 1)
        root = FloatLayout()
        self.area = GameArea()
        root.add_widget(self.area)

        self.hud = Label(text="", pos_hint={"center_x": 0.5, "top": 0.97},
                         size_hint=(None, None), font_size=24, bold=True, color=CREAM)
        self.hud.size = (620, 40)
        root.add_widget(self.hud)

        btn_cfg = {"ГАЗ": ("gas", 0.22, 0.2, 0.99, 0.04, (0.2, 0.55, 0.25, 0.9)),
                   "ТОРМОЗ": ("brake", 0.22, 0.2, 0.76, 0.04, (0.6, 0.2, 0.2, 0.9)),
                   "НАЗАД": ("sback", 0.16, 0.2, 0.20, 0.04, (0.4, 0.4, 0.6, 0.9)),
                   "ВПЕРЁД": ("sfwd", 0.16, 0.2, 0.02, 0.04, (0.4, 0.6, 0.4, 0.9))}
        self.buttons = {}
        for label, (attr, wx, wh, right, y, col) in btn_cfg.items():
            b = Button(text=label, size_hint=(wx, wh), pos_hint={"right": right, "y": y},
                       font_size=20, bold=True, background_color=col, background_normal="")
            b.bind(on_press=lambda i, a=attr: setattr(self.area, a, True))
            b.bind(on_release=lambda i, a=attr: setattr(self.area, a, False))
            root.add_widget(b)
            self.buttons[attr] = b

        self.btn_start = Button(text="ГОРНЫЙ БАЙКЕР\nСТАРТ", size_hint=(0.5, 0.24),
                                pos_hint={"center_x": 0.5, "center_y": 0.4},
                                font_size=28, bold=True,
                                background_color=(0.15, 0.5, 0.25, 0.95), background_normal="")
        self.btn_start.bind(on_press=self._on_start)
        root.add_widget(self.btn_start)

        self._kb = None
        Window.bind(on_key_down=self._on_key)
        Clock.schedule_interval(self._tick, 1 / 60)
        return root

    def _on_start(self, *a):
        if self.area.state == "over":
            self.area.start()
        elif self.area.state == "menu":
            self.area.start()
        self.btn_start.text = ""

    def _on_key(self, win, key, scancode, codepoint, modifiers):
        mapping = {119: "gas", 100: "gas", 97: "brake", 115: "sfwd", 32: "gas"}
        if codepoint in ("w", "W", "д", "Д"):
            setattr(self.area, "gas", True)
        elif codepoint in ("a", "A", "ф", "Ф"):
            setattr(self.area, "brake", True)
        elif codepoint in ("s", "S", "ы", "Ы"):
            setattr(self.area, "sfwd", True)
        elif codepoint in (" ",):
            setattr(self.area, "gas", True)

    def _tick(self, dt):
        a = self.area
        a.tick(min(dt, 1 / 30))
        if a.state == "menu":
            self.btn_start.text = "ГОРНЫЙ БАЙКЕР\nСТАРТ"
        elif a.state == "over":
            self.btn_start.text = "ПАДЕНИЕ!\n%.0f м  ·  ЕЩЁ РАЗ" % a.meters
            self.btn_start.opacity = 1
        else:
            self.btn_start.opacity = 0
        self.hud.text = "↑%d  %d м   %d км/ч   очки %d" % (
            a.level, int(a.meters), int(a.speed), a.points)
        t, dur = a.banner
        if t and dur > 0:
            a.banner = (t, dur - dt)
            self.hud.text = t


def main():
    GameApp().run()


if __name__ == "__main__":
    main()