"""A small desktop pet player for PNG sprite sheets and pet.json files."""

import json
import math
from dataclasses import dataclass
from pathlib import Path
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QFileDialog, QLabel, QMenu, QMessageBox


ROOT = Path(__file__).resolve().parent
# A pets folder next to the executable takes precedence over bundled assets.
EXTERNAL_PETS = Path(sys.executable).parent / "pets"
PETS_DIR = EXTERNAL_PETS if getattr(sys, "frozen", False) and EXTERNAL_PETS.is_dir() else ROOT / "pets"
ANIMATION_NAMES = {
    "idle": "쉬기", "running": "움직이기", "waiting": "기다리기",
    "review": "살펴보기", "waving": "인사", "jumping": "신나게 움직이기",
    "running-right": "오른쪽 동작", "running-left": "왼쪽 동작", "failed": "시무룩",
}


@dataclass
class Animation:
    frames: list[QPixmap]
    durations: list[int]


class Pet:
    def __init__(self, path: Path):
        self.path = path.resolve()
        data = json.loads(self.path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("pet.json의 최상위 값은 객체여야 합니다.")
        self.name = data.get("displayName", self.path.parent.name)
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("displayName은 비어 있지 않은 문자열이어야 합니다.")
        frame = data.get("frame", {})
        width, height = frame.get("width"), frame.get("height")
        if any(type(value) is not int or value <= 0 for value in (width, height)):
            raise ValueError("frame.width와 frame.height는 양의 정수여야 합니다.")
        image_path = (self.path.parent / data.get("spritesheetPath", "spritesheet.png")).resolve()
        if not image_path.is_relative_to(self.path.parent):
            raise ValueError("펫 이미지는 pet.json과 같은 폴더 또는 하위 폴더에 두세요.")
        sheet = QPixmap(str(image_path))
        if sheet.isNull():
            raise ValueError(f"펫 이미지를 읽을 수 없습니다: {image_path.name}")
        fps = data.get("fps", 8)
        if isinstance(fps, bool) or not isinstance(fps, (int, float)) or not math.isfinite(fps) or fps <= 0:
            raise ValueError("fps는 0보다 큰 유한한 숫자여야 합니다.")
        definitions = data.get("animations")
        if not isinstance(definitions, dict) or not definitions:
            raise ValueError("animations에 동작이 하나 이상 필요합니다.")
        self.animations = {}
        for name, definition in definitions.items():
            if not isinstance(definition, dict):
                raise ValueError(f"동작 설정이 올바르지 않습니다: {name}")
            row, count = definition.get("row"), definition.get("frames")
            if type(row) is not int or row < 0 or type(count) is not int or count <= 0:
                raise ValueError(f"동작의 row 또는 frames가 올바르지 않습니다: {name}")
            if (row + 1) * height > sheet.height() or count * width > sheet.width():
                raise ValueError(f"동작이 이미지 범위를 벗어납니다: {name}")
            durations = definition.get("frameDurationsMs", [max(1, round(1000 / fps))] * count)
            if (not isinstance(durations, list) or len(durations) != count
                    or any(type(value) is not int or not 0 < value <= 2_147_483_647 for value in durations)):
                raise ValueError(f"frameDurationsMs는 프레임 수와 같은 길이의 양의 정수 목록이어야 합니다: {name}")
            frames = [sheet.copy(column * width, row * height, width, height) for column in range(count)]
            self.animations[name] = Animation(frames, durations)
        self.default_animation = data.get("defaultAnimation", next(iter(self.animations)))
        if self.default_animation not in self.animations:
            raise ValueError("defaultAnimation이 animations에 없습니다.")


class PetWindow(QLabel):
    def __init__(self, pets: list[Pet]):
        super().__init__()
        self.pets = pets
        self.display_width = 192
        self.paused = False
        self.drag_offset = None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.advance_frame)
        self.set_pet(pets[0])
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - 24, screen.bottom() - self.height() - 24)
        self.keep_on_screen()

    def set_pet(self, pet: Pet):
        self.pet = pet
        self.setWindowTitle(f"MyPets - {pet.name}")
        self.setToolTip(f"{pet.name}\n드래그: 위치 이동 / 우클릭: 메뉴")
        self.setWindowIcon(QIcon(pet.animations[pet.default_animation].frames[0]))
        self.set_animation(pet.default_animation)

    def set_animation(self, name: str):
        self.animation_name = name
        self.frame_index = 0
        self.render_frame()
        self.schedule_frame()

    def render_frame(self):
        frame = self.pet.animations[self.animation_name].frames[self.frame_index]
        scaled = frame.scaledToWidth(self.display_width, Qt.TransformationMode.SmoothTransformation)
        self.setFixedSize(scaled.size())
        self.setPixmap(scaled)

    def schedule_frame(self):
        self.timer.stop()
        if not self.paused:
            self.timer.start(self.pet.animations[self.animation_name].durations[self.frame_index])

    def advance_frame(self):
        animation = self.pet.animations[self.animation_name]
        self.frame_index = (self.frame_index + 1) % len(animation.frames)
        self.render_frame()
        self.schedule_frame()

    def set_display_width(self, width: int):
        self.display_width = width
        self.render_frame()
        self.keep_on_screen()

    def toggle_pause(self):
        self.paused = not self.paused
        self.schedule_frame()

    def keep_on_screen(self):
        screen = QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        self.move(max(area.left(), min(self.x(), area.right() - self.width() + 1)),
                  max(area.top(), min(self.y(), area.bottom() - self.height() + 1)))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.keep_on_screen()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        menu = self.create_menu()
        menu.exec(event.globalPos())
        menu.deleteLater()

    def create_menu(self):
        menu = QMenu(self)
        title = menu.addAction(self.pet.name)
        title.setEnabled(False)
        menu.addSeparator()
        pets_menu = menu.addMenu("펫 선택")
        for pet in self.pets:
            action = pets_menu.addAction(pet.name)
            action.setCheckable(True)
            action.setChecked(pet is self.pet)
            action.triggered.connect(lambda checked=False, selected=pet: self.change_pet(selected))
        pets_menu.addSeparator()
        pets_menu.addAction("다른 pet.json 열기…", self.open_pet)
        animations_menu = menu.addMenu("동작")
        for name in self.pet.animations:
            action = animations_menu.addAction(ANIMATION_NAMES.get(name, name))
            action.setCheckable(True)
            action.setChecked(name == self.animation_name)
            action.triggered.connect(lambda checked=False, selected=name: self.set_animation(selected))
        sizes_menu = menu.addMenu("크기")
        for width in (128, 192, 256, 320):
            action = sizes_menu.addAction(f"{width} px")
            action.setCheckable(True)
            action.setChecked(width == self.display_width)
            action.triggered.connect(lambda checked=False, selected=width: self.set_display_width(selected))
        menu.addAction("재생" if self.paused else "일시정지", self.toggle_pause)
        menu.addSeparator()
        menu.addAction("종료", self.close)
        return menu

    def change_pet(self, pet: Pet):
        self.set_pet(pet)
        self.keep_on_screen()

    def open_pet(self):
        filename, _ = QFileDialog.getOpenFileName(self, "펫 설정 열기", str(PETS_DIR), "Pet JSON (*.json)")
        if not filename:
            return
        try:
            pet = Pet(Path(filename))
        except (OSError, ValueError, TypeError, AttributeError) as error:
            QMessageBox.warning(self, "펫을 열 수 없습니다", str(error))
            return
        existing = next((item for item in self.pets if item.path == pet.path), None)
        if existing is None:
            self.pets.append(pet)
        self.change_pet(pet if existing is None else existing)

    def closeEvent(self, event):
        self.timer.stop()
        event.accept()
        QApplication.instance().quit()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MyPets")
    try:
        paths = sorted(PETS_DIR.glob("*/pet.json"), key=lambda path: (path.parent.name != "puppy-emotions", path.parent.name))
        if not paths:
            raise ValueError(f"펫을 찾을 수 없습니다. pets/이름/pet.json을 넣어 주세요.\n{PETS_DIR}")
        pets = [Pet(path) for path in paths]
    except (OSError, ValueError, TypeError, AttributeError) as error:
        QMessageBox.critical(None, "MyPets 실행 오류", str(error))
        return 1
    window = PetWindow(pets)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
