import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, QEvent, Qt
from PySide6.QtGui import QMouseEvent, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from pet import PETS_DIR, Pet, PetWindow


class PetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.emotions = Pet(PETS_DIR / "puppy-emotions/pet.json")
        cls.puppy = Pet(PETS_DIR / "puppy/pet.json")

    def test_bundled_sheets_and_frame_timing(self):
        animation = self.emotions.animations["idle"]
        self.assertEqual(len(animation.frames), 20)
        self.assertEqual(animation.frames[0].size().toTuple(), (304, 304))
        self.assertTrue(animation.frames[0].hasAlphaChannel())
        self.assertEqual(animation.durations[:4], [2000, 650, 650, 2000])
        sheet = QPixmap(str(self.puppy.path.parent / "spritesheet.png"))
        self.assertEqual(self.puppy.animations["running"].frames[0].toImage(),
                         sheet.copy(0, 512, 384, 512).toImage())
        for pet in (self.emotions, self.puppy):
            hula = pet.animations["hula"]
            self.assertEqual(len(hula.frames), 1)
            self.assertEqual(hula.frames[0].size().toTuple(), (313, 313))
            self.assertTrue(hula.frames[0].hasAlphaChannel())
            self.assertEqual(hula.motion, "hula")
            hula_sheet = QPixmap(str(pet.path.parent / "hula.png"))
            self.assertEqual(hula.frames[0].toImage(), hula_sheet.copy(0, 0, 313, 313).toImage())

    @patch("pet.monotonic")
    def test_playback_pause_switch_size_and_menu_actions(self, clock):
        clock.return_value = 100.0
        window = PetWindow([self.emotions, self.puppy])
        try:
            self.assertEqual(window.timer.interval(), 16)
            clock.return_value = 102.05
            window.render_frame()
            self.assertEqual(window.frame_index, 1)
            clock.return_value = 100 + sum(self.emotions.animations["idle"].durations) / 1000 + .01
            window.render_frame()
            self.assertEqual(window.frame_index, 0)
            window.toggle_pause()
            self.assertFalse(window.timer.isActive())
            frozen_time = window.animation_time()
            clock.return_value += 10
            self.assertEqual(window.animation_time(), frozen_time)
            window.change_pet(self.puppy)
            self.assertFalse(window.timer.isActive())
            window.set_animation("running")
            self.assertEqual(window.frame_index, 0)
            window.toggle_pause()
            self.assertEqual(window.timer.interval(), 16)
            clock.return_value += 2.6
            window.render_frame()
            self.assertEqual(window.frame_index, 1)
            menu = window.create_menu()
            sizes = next(action.menu() for action in menu.actions() if action.text() == "크기")
            next(action for action in sizes.actions() if action.text() == "256 px").trigger()
            self.assertEqual(window.width(), 256)
            self.assertEqual(window.height(), round(256 * 512 / 384))
            pets = next(action.menu() for action in menu.actions() if action.text() == "펫 선택")
            pets.actions()[0].trigger()
            self.assertIs(window.pet, self.emotions)
            self.assertEqual(window.height(), 256)
            updated_menu = window.create_menu()
            animations = next(action.menu() for action in updated_menu.actions() if action.text() == "동작")
            next(action for action in animations.actions() if action.text() == "훌라춤").trigger()
            self.assertEqual(window.animation_name, "hula")
            self.assertEqual(window.width(), 256)
            self.assertEqual(window.height(), 256)
            self.assertTrue(window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
            self.assertTrue(window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
            menu.deleteLater()
            updated_menu.deleteLater()
        finally:
            window.close()

    def test_hula_motion_loop_is_continuous(self):
        hula = self.emotions.animations["hula"]
        self.assertEqual(hula.sample(0), (0, 0, 0))
        self.assertEqual(hula.sample(2400), (0, 0, 0))
        window = PetWindow([self.emotions])
        try:
            window.set_animation("hula")
            window.render_frame(2399)
            before = bytes(window.pixmap().toImage().constBits())
            window.render_frame(2400)
            after = bytes(window.pixmap().toImage().constBits())
            difference = sum(abs(a - b) for a, b in zip(before, after)) / len(before)
            self.assertLess(difference, 2, "The loop jumps at its boundary")
            window.render_frame(60)
            between = bytes(window.pixmap().toImage().constBits())
            self.assertNotEqual(between, after)
        finally:
            window.close()

    @patch("pet.monotonic")
    def test_hula_catches_up_after_delayed_tick_and_resumes_without_jumping(self, clock):
        clock.return_value = 10.0
        window = PetWindow([self.emotions])
        try:
            window.set_animation("hula")
            clock.return_value = 10.55
            window.render_frame()
            delayed = window.pixmap().toImage()
            window.render_frame(550)
            self.assertEqual(window.pixmap().toImage(), delayed)
            window.toggle_pause()
            frozen = window.animation_time()
            window.render_frame()
            before = window.pixmap().toImage()
            clock.return_value = 30.55
            window.render_frame()
            self.assertEqual(window.pixmap().toImage(), before)
            window.toggle_pause()
            self.assertAlmostEqual(window.animation_time(), frozen)
            clock.return_value += .12
            window.render_frame()
            self.assertAlmostEqual(window.animation_time(), 670)
            self.assertNotEqual(window.pixmap().toImage(), before)
        finally:
            window.close()

    def test_drag_and_recovery_from_offscreen_position(self):
        window = PetWindow([self.emotions])
        try:
            window.move(100, 100)
            press = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(20, 20), QPointF(120, 120),
                                Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
            window.mousePressEvent(press)
            move = QMouseEvent(QEvent.Type.MouseMove, QPointF(50, 60), QPointF(150, 160),
                               Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
            window.mouseMoveEvent(move)
            self.assertEqual(window.pos(), QPoint(130, 140))
            window.move(-10000, -10000)
            release = QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(0, 0), QPointF(-10000, -10000),
                                  Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
            window.mouseReleaseEvent(release)
            self.assertIsNone(window.drag_offset)
            self.assertTrue(self.app.primaryScreen().availableGeometry().contains(window.geometry()))
        finally:
            window.close()

    def test_invalid_pet_is_rejected_and_fps_fallback_works(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            image = QPixmap(4, 2)
            image.fill(Qt.GlobalColor.transparent)
            image.save(str(folder / "spritesheet.png"))
            data = {"frame": {"width": 2, "height": 2}, "fps": 10,
                    "animations": {"idle": {"row": 0, "frames": 2}}}
            path = folder / "pet.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(Pet(path).animations["idle"].durations, [100, 100])
            invalid_changes = [
                {"frame": {"width": 0, "height": 2}},
                {"fps": 0},
                {"animations": {"idle": {"row": 1, "frames": 2}}},
                {"animations": {"idle": {"row": 0, "frames": 3}}},
                {"animations": {"idle": {"row": 0, "frames": 2, "frameDurationsMs": [100]}}},
                {"animations": {"idle": {"row": 0, "frames": 2, "columns": 0}}},
                {"animations": {"idle": {"row": 0, "frames": 3, "columns": 2}}},
                {"animations": {"idle": {"row": 0, "frames": 2, "spritesheetPath": "../outside.png"}}},
                {"animations": {"idle": {"row": 0, "frames": 2, "interpolate": "yes"}}},
                {"defaultAnimation": "missing"},
                {"spritesheetPath": "../outside.png"},
            ]
            for change in invalid_changes:
                with self.subTest(change=change):
                    path.write_text(json.dumps(data | change), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        Pet(path)
            image = QPixmap(4, 4)
            painter = QPainter(image)
            colors = (Qt.GlobalColor.red, Qt.GlobalColor.green, Qt.GlobalColor.blue, Qt.GlobalColor.yellow)
            for index, color in enumerate(colors):
                painter.fillRect((index % 2) * 2, (index // 2) * 2, 2, 2, color)
            painter.end()
            image.save(str(folder / "spritesheet.png"))
            data["animations"] = {"idle": {"row": 0, "frames": 4, "columns": 2}}
            path.write_text(json.dumps(data), encoding="utf-8")
            loaded = Pet(path).animations["idle"]
            self.assertEqual([frame.toImage().pixelColor(0, 0) for frame in loaded.frames],
                             [image.toImage().pixelColor((i % 2) * 2, (i // 2) * 2) for i in range(4)])


if __name__ == "__main__":
    unittest.main()
