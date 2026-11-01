"""
Горный байкер — Kivy-версия (сборка под Android).
"""
import os
import math

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Rectangle, Ellipse, Line
from kivy.clock import Clock

import gz_core as G

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")


class GameArea(Widget):
    """Отрисовка и логика поля картинки."""

    GROUND_OFF = 120  # сколько px от низа окна до уровня terrain_y=~470 на ПК

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bike = G.Bike()
        self.state = "menu"
        self.level = 1
        self.meters = 0.0
        self.points = 0
        self.cam_x = 0.0
        self.gas = self.brake = self.lb = self.lf = False
        self.bind(size=self.redraw)

    def start(self):
        self.bike = G.Bike()
        G.TERRAIN_LEVEL = 1
        self.level = 1
        self.meters = 0.0
        self.points = 0
        self.state = "play"
        self.redraw()

    def crash(self):
        self.state = "over"
        self.redraw()

    def screen_y(self, world_y):
        # world_y: terrain_y+ смещение вниз; GROUND_OFF маппит 470 -> низ
        return self.height - (world_y - 350.0)

    def tick(self, dt):
        if self.state != "play":
            return
        ok = self.bike.step(self.gas, self.brake, self.lb, self.lf, dt)
        new_level = G.level_of((self.bike.x - 150.0) / G.PX_PER_METER)
        if new_level > self.level:
            self.level = new_level
            G.TERRAIN_LEVEL = self.level
            self.points += 20
        self.points += int(self.bike.vx) // 400
        if not ok:
            self.crash()
        self.redraw()

    def redraw(self, *a):
        self.canvas.clear()
        w, h = self.width, self.height
        cam = self.bike.x - w * 0.35
        self.cam_x = cam
        with self.canvas:
            # небо
            Color(0.22, 0.27, 0.38)
            Rectangle(pos=(0, 0), size=(w, h))
            # горизонт-холмы
            Color(0.30, 0.22, 0.18)
            self.draw_hills(w, h, cam)
            # земля (заливка)
            self.draw_ground(w, h, cam)
            # байк
            if self.state in ("play", "over"):
                self.draw_bike(w, h, cam)
            # проигрыш
            if self.state == "over":
                Color(0.5, 0.1, 0.1, 0.5)
                Rectangle(pos=(0, 0), size=(w, h))

    def draw_hills(self, w, h, cam):
        pts = [0, h - 40]
        seg = 30
        for i in range(0, int(w) + 1, seg):
            wx = (cam + i) * 0.2
            yy = h - 60 - math.sin(wx / 120.0) * 40
            pts += [i, yy]
        pts += [w, h, 0, h]
        Line(points=pts, width=1)

    def draw_ground(self, w, h, cam):
        cols = int(w / 8) + 2
        surf = []
        for i in range(cols + 1):
            x = int(cam) - 8 + i * 8
            sy = self.screen_y(G.terrain_y(x))
            surf += [x - cam, sy]
        # замкнутый многоугольник: поверхность -> низ -> лево
        poly = list(surf)
        poly += [surf[-2], h + 5, -8, h + 5]
        Color(0.34, 0.22, 0.13)
        Line(points=poly, width=2.0, joint="bevel")
        # тёмный гребень сверху
        Color(0.10, 0.08, 0.06, 0.6)
        Line(points=surf, width=4, joint="bevel")

    def draw_bike(self, w, h, cam):
        b = self.bike
        cx = b.x - cam
        frame_y = self.screen_y(b.frame_y())
        # тень
        gy = self.screen_y(b.ground_y())
        Color(0, 0, 0, 0.35)
        Ellipse(pos=(cx - 20, gy + 4), size=(40, 8))
        # колёса
        for dx in (-G.WHEELBASE / 2, G.WHEELBASE / 2):
            ax = math.cos(b.angle) * dx
            ay = math.sin(b.angle) * dx
            wx = cx + ax
            wy = frame_y + ay
            Color(0.08, 0.08, 0.10)
            Ellipse(pos=(wx - G.WHEEL_R, wy - G.WHEEL_R), size=(G.WHEEL_R * 2, G.WHEEL_R * 2))
            Color(0.5, 0.5, 0.55, 0.6)
            Ellipse(pos=(wx - 4, wy - 4), size=(8, 8))
        # рама
        Color(0.9, 0.35, 0.12, 1)
        Line(points=[cx - 30, frame_y, cx + 30, frame_y - 8], width=5)
        # гонщик (простая фигура)
        Color(0.15, 0.4, 0.9, 1)
        Line(points=[cx + 12, frame_y - 8, cx + 26, frame_y - 34], width=6)   # торс
        Color(0.95, 0.8, 0.3, 1)
        Ellipse(pos=(cx + 20, frame_y - 48), size=(14, 12))                    # шлем
        # руль
        Color(0.2, 0.2, 0.2, 1)
        Line(points=[cx + 40, frame_y - 10, cx + 48, frame_y - 22], width=4)


class MultiKivyApp(App):
    def build(self):
        root = FloatLayout()
        self.area = GameArea()
        root.add_widget(self.area)

        self.hud = Label(text="", pos_hint={"center_x": 0.5, "top": 0.96},
                         size_hint=(None, None), font_size=26, bold=True,
                         color=(1, 0.9, 0.3, 1))
        self.hud.size = (500, 40)
        root.add_widget(self.hud)

        def mk(text, hint, color):
            b = Button(text=text, size_hint=(0.2, 0.16),
                       pos_hint=hint, font_size=22, bold=True,
                       background_color=color, background_normal="")
            return b

        self.btn_gas = mk("ГАЗ", {"right": 0.99, "y": 0.04}, (0.2, 0.55, 0.25, 0.9))
        self.btn_brk = mk("ТОРМОЗ", {"right": 0.77, "y": 0.04}, (0.6, 0.2, 0.2, 0.9))
        self.btn_lb = mk("НАЗАД", {"x": 0.02, "y": 0.04}, (0.4, 0.4, 0.6, 0.9))
        self.btn_lf = mk("ВПЕРЁД", {"x": 0.24, "y": 0.04}, (0.4, 0.6, 0.4, 0.9))
        for b in (self.btn_gas, self.btn_brk, self.btn_lb, self.btn_lf):
            root.add_widget(b)

        map_attr = {"gas": self.btn_gas, "brake": self.btn_brk,
                    "lb": self.btn_lb, "lf": self.btn_lf}
        for attr, btn in map_attr.items():
            btn.bind(on_press=lambda i, b=btn, a=attr: setattr(self.area, a, True))
            btn.bind(on_release=lambda i, b=btn, a=attr: setattr(self.area, a, False))

        self.menu_label = Label(text="ГОРНЫЙ БАЙКЕР\nнажми, чтобы ехать",
                                pos_hint={"center_x": 0.5, "center_y": 0.55},
                                size_hint=(None, None), font_size=34, bold=True,
                                color=(1, 1, 1, 1))
        self.menu_label.size = (500, 160)
        root.add_widget(self.menu_label)

        self.btn_start = Button(text="СТАРТ", size_hint=(0.4, 0.16),
                                pos_hint={"center_x": 0.5, "center_y": 0.35},
                                font_size=30, bold=True,
                                background_color=(0.2, 0.6, 0.3, 0.95),
                                background_normal="")
        self.btn_start.bind(on_press=self.start_game)
        root.add_widget(self.btn_start)
        self.btn_start.opacity = 1 if self.area.state == "menu" else 0

        Clock.schedule_interval(self._tick, 1 / 60)
        return root

    def start_game(self, *a):
        self.area.start()
        self.menu_label.opacity = 0
        self.btn_start.opacity = 0

    def _tick(self, dt):
        self.area.tick(min(dt, 1 / 30))
        if self.area.state == "over":
            self.btn_start.text = "ЕЩЁ РАЗ"
            self.btn_start.opacity = 1
            self.menu_label.text = "ПАДЕНИЕ!\nДистанция %.0f м" % self.area.meters
            self.menu_label.opacity = 1
        self.hud.text = "УРОВЕНЬ %d   %d м   очки %d" % (
            self.area.level, int(self.area.meters), self.area.points)


if __name__ == "__main__":
    MultiKivyApp().run()