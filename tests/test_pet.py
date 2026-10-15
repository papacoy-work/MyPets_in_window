import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, QEvent, Qt
from PySide6.QtGui import QMouseEvent, QPixmap
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

    def test_playback_pause_switch_size_and_menu_actions(self):
        window = PetWindow([self.emotions, self.puppy])
        try:
            self.assertEqual(window.timer.interval(), 2000)
            window.advance_frame()
            self.assertEqual((window.frame_index, window.timer.interval()), (1, 650))
            for _ in range(19):
                window.advance_frame()
            self.assertEqual(window.frame_index, 0)
            window.toggle_pause()
            self.assertFalse(window.timer.isActive())
            window.change_pet(self.puppy)
            self.assertFalse(window.timer.isActive())
            window.set_animation("running")
            self.assertEqual(window.frame_index, 0)
            window.toggle_pause()
            self.assertEqual(window.timer.interval(), 2500)
            menu = window.create_menu()
            sizes = next(action.menu() for action in menu.actions() if action.text() == "크기")
            next(action for action in sizes.actions() if action.text() == "256 px").trigger()
            self.assertEqual(window.width(), 256)
            self.assertEqual(window.height(), round(256 * 512 / 384))
            pets = next(action.menu() for action in menu.actions() if action.text() == "펫 선택")
            pets.actions()[0].trigger()
            self.assertIs(window.pet, self.emotions)
            self.assertEqual(window.height(), 256)
            self.assertTrue(window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
            self.assertTrue(window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
            menu.deleteLater()
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
                {"defaultAnimation": "missing"},
                {"spritesheetPath": "../outside.png"},
            ]
            for change in invalid_changes:
                with self.subTest(change=change):
                    path.write_text(json.dumps(data | change), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        Pet(path)


if __name__ == "__main__":
    unittest.main()
