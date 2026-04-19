"""Map canvas — QGraphicsView with clickable landmark icons, fade-out preview, and 3-level zoom."""

import os

from PyQt6.QtCore import (
    QObject,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
    QSizePolicy,
    QToolButton,
)

from core.landmark_loader import MAP_TILE_IMAGES, classify_landmark, world_to_pixel

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
LANDMARKS_DIR = os.path.join(ASSETS_DIR, "landmarks")

# Icon sizes per zoom level — tune these to taste
ICON_SIZE_DEFAULT  = {0: 18, 1: 30, 2: 50}
ICON_SIZE_SELECTED = {0: 32, 1: 55, 2: 85}

# Shadow per zoom level — tune these to taste
SHADOW_BLUR   = {0: 5,  1: 8,  2: 12}
SHADOW_OFFSET = {0: 1,  1: 2,  2: 3}

# Number badge — top-left corner offset from icon center; tune to taste
BADGE_OFFSET_X_TREE = {0: -10, 1: -15, 2: -22}
BADGE_OFFSET_Y_TREE = {0: -7,  1: -9,  2: -12}
BADGE_OFFSET_X_ROCK = {0: -10, 1: -13, 2: -19}
BADGE_OFFSET_Y_ROCK = {0: 0,  1: 1,  2: 3}
BADGE_SIZE_W        = {0: 20,  1: 28,  2: 42}
BADGE_SIZE_H        = {0: 14,  1: 20,  2: 30}

# Stitched image sizes per zoom level
ZOOM_IMAGE_SIZES = {0: 512, 1: 1024, 2: 2048}

# Black border the user can pan into beyond the map edge
SCENE_MARGIN = 300

# Placeholder map colors per map index
_MAP_COLORS = [
    QColor("#3d6b3d"),  # Obsidian Fieldlands
    QColor("#6b3d2a"),  # Crimson Mirelands
    QColor("#2a5f7a"),  # Cobalt Coastlands
    QColor("#5a4a7a"),  # Coronet Highlands
    QColor("#7a9fc0"),  # Alabaster Icelands
]

_COLOR_TREE_DEFAULT = QColor("#F5C518")
_COLOR_TREE_SELECTED = QColor("#44CC44")
_COLOR_ROCK_DEFAULT = QColor("#C8A46E")
_COLOR_ROCK_SELECTED = QColor("#66BB66")


def _make_circle_pixmap(size: int, color: QColor) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QBrush(color))
    p.setPen(QPen(color.darker(130), 1))
    p.drawEllipse(1, 1, size - 2, size - 2)
    p.end()
    return pm


def _load_or_placeholder(path: str, size: int, color: QColor) -> QPixmap:
    if os.path.exists(path):
        return QPixmap(path).scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    return _make_circle_pixmap(size, color)


class LandmarkIconItem(QGraphicsItem):
    def __init__(self, identifier: str, landmark_type: str, canvas: "MapCanvas"):
        super().__init__()
        self._identifier = identifier
        self._type = landmark_type
        self._canvas = canvas
        self._order = None  # int or None
        self._zoom = 0
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        shadow = QGraphicsDropShadowEffect()
        shadow.setColor(QColor(0, 0, 0, 200))
        self.setGraphicsEffect(shadow)
        self._refresh_pixmap()
        self._refresh_shadow()

    @property
    def identifier(self) -> str:
        return self._identifier

    def set_order(self, order):
        self._order = order
        self._refresh_pixmap()
        self.update()

    def set_zoom(self, zoom: int):
        self._zoom = zoom
        self._refresh_pixmap()
        self._refresh_shadow()
        self.update()

    def _refresh_shadow(self):
        shadow = self.graphicsEffect()
        if shadow:
            shadow.setBlurRadius(SHADOW_BLUR[self._zoom])
            shadow.setOffset(SHADOW_OFFSET[self._zoom], SHADOW_OFFSET[self._zoom])

    def _refresh_pixmap(self):
        selected = self._order is not None
        size = ICON_SIZE_SELECTED[self._zoom] if selected else ICON_SIZE_DEFAULT[self._zoom]
        if self._type == "rock":
            color = _COLOR_ROCK_SELECTED if selected else _COLOR_ROCK_DEFAULT
        else:
            color = _COLOR_TREE_SELECTED if selected else _COLOR_TREE_DEFAULT
        state = "selected" if selected else "default"
        path = os.path.join(ASSETS_DIR, f"{self._type}_{state}.png")
        self._pixmap = _load_or_placeholder(path, size, color)

    def boundingRect(self) -> QRectF:
        s = self._pixmap.width()
        return QRectF(-s / 2, -s / 2, s, s)

    def paint(self, painter: QPainter, option, widget=None):
        pm = self._pixmap
        half = pm.width() / 2
        painter.drawPixmap(int(-half), int(-half), pm)

        if self._order is not None:
            font = QFont()
            font.setPointSize(max(6, ICON_SIZE_SELECTED[self._zoom] // 3))
            font.setBold(True)
            painter.setFont(font)
            text = str(self._order)
            ox = (BADGE_OFFSET_X_TREE if self._type == "tree" else BADGE_OFFSET_X_ROCK)[self._zoom]
            oy = (BADGE_OFFSET_Y_TREE if self._type == "tree" else BADGE_OFFSET_Y_ROCK)[self._zoom]
            r = QRectF(ox, oy, BADGE_SIZE_W[self._zoom], BADGE_SIZE_H[self._zoom])
            painter.setPen(QPen(Qt.GlobalColor.black))
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                painter.drawText(r.translated(dx, dy), Qt.AlignmentFlag.AlignCenter, text)
            painter.setPen(QPen(Qt.GlobalColor.white))
            painter.drawText(r, Qt.AlignmentFlag.AlignCenter, text)

    def mousePressEvent(self, event):
        self._canvas.toggle_landmark(self._identifier)


class _OpacityHelper(QObject):
    def __init__(self, label: QLabel):
        super().__init__(label)
        self._label = label
        self._opacity = 1.0

    def get_opacity(self) -> float:
        return self._opacity

    def set_opacity(self, value: float):
        self._opacity = value
        effect = self._label.graphicsEffect()
        if effect:
            effect.setOpacity(value)

    opacity = pyqtProperty(float, fget=get_opacity, fset=set_opacity)


class MapCanvas(QGraphicsView):
    landmark_selected = pyqtSignal(str, int)  # (identifier, map_index)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self._scene.setBackgroundBrush(QBrush(Qt.GlobalColor.black))
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self._map_index: int = 0
        self._zoom_level: int = 0
        self._filter_type: str = "both"  # "both", "trees", "rocks"
        self._landmark_items: dict = {}  # identifier -> LandmarkIconItem
        self._selected_order: list = []
        self._landmark_positions: dict = {}  # identifier -> (game_x, game_z)

        # Fade-out preview overlay (top-right)
        self._preview_label = QLabel(self)
        self._preview_label.setFixedSize(160, 120)
        self._preview_label.setScaledContents(True)
        self._preview_label.hide()
        self._preview_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        self._opacity_effect = QGraphicsOpacityEffect(self._preview_label)
        self._preview_label.setGraphicsEffect(self._opacity_effect)
        self._opacity_helper = _OpacityHelper(self._preview_label)

        self._fade_anim = QPropertyAnimation(self._opacity_helper, b"opacity")
        self._fade_anim.setDuration(3000)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self._preview_label.hide)

        # Zoom overlay buttons (top-left)
        self._zoom_in_btn = QToolButton(self)
        self._zoom_in_btn.setText("+")
        self._zoom_in_btn.setFixedSize(28, 28)
        self._zoom_in_btn.clicked.connect(self._zoom_in)

        self._zoom_out_btn = QToolButton(self)
        self._zoom_out_btn.setText("−")
        self._zoom_out_btn.setFixedSize(28, 28)
        self._zoom_out_btn.clicked.connect(self._zoom_out)

        self._zoom_label = QLabel("1×", self)
        self._zoom_label.setFixedWidth(28)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._reposition_overlays()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_overlays()

    def _reposition_overlays(self):
        margin = 8
        # Zoom buttons top-left
        self._zoom_out_btn.move(margin, margin)
        self._zoom_label.move(margin + 30, margin + 6)
        self._zoom_in_btn.move(margin + 60, margin)
        # Preview top-right
        self._preview_label.move(
            self.width() - self._preview_label.width() - margin, margin
        )

    def _zoom_in(self):
        if self._zoom_level < 2:
            self._do_zoom(self._zoom_level + 1, self.viewport().rect().center())

    def _zoom_out(self):
        if self._zoom_level > 0:
            self._do_zoom(self._zoom_level - 1, self.viewport().rect().center())

    def wheelEvent(self, event: QWheelEvent):
        if event.angleDelta().y() > 0:
            if self._zoom_level < 2:
                self._do_zoom(self._zoom_level + 1, event.position().toPoint())
        else:
            if self._zoom_level > 0:
                self._do_zoom(self._zoom_level - 1, self.viewport().rect().center())

    def _do_zoom(self, new_level: int, focus_vp):
        cs = self.mapToScene(focus_vp)
        ce = self.mapToScene(self.viewport().rect().center())
        old_size = ZOOM_IMAGE_SIZES[self._zoom_level]
        self._zoom_level = new_level
        sf = ZOOM_IMAGE_SIZES[new_level] / old_size
        self._apply_zoom()
        if self._zoom_level > 0:
            self.centerOn(
                ce.x() + cs.x() * (sf - 1),
                ce.y() + cs.y() * (sf - 1),
            )

    def _apply_zoom(self):
        self._zoom_label.setText(f"{self._zoom_level + 1}×")
        self._zoom_in_btn.setEnabled(self._zoom_level < 2)
        self._zoom_out_btn.setEnabled(self._zoom_level > 0)

        img_size = ZOOM_IMAGE_SIZES[self._zoom_level]
        bg_pixmap = self._load_map_pixmap(self._map_index, self._zoom_level, img_size)

        # Update background pixmap item (first item in scene)
        items = self._scene.items()
        bg_items = [i for i in items if i.zValue() == 0]
        for item in bg_items:
            self._scene.removeItem(item)
        bg_item = self._scene.addPixmap(bg_pixmap)
        bg_item.setZValue(0)
        m = SCENE_MARGIN
        self._scene.setSceneRect(-m, -m, img_size + 2 * m, img_size + 2 * m)

        # Reposition all landmark icons
        for identifier, item in self._landmark_items.items():
            item.set_zoom(self._zoom_level)
            game_x, game_z = self._landmark_positions.get(identifier, (512, 512))
            px, py = world_to_pixel(game_x, game_z, img_size, img_size, padding=0)
            item.setPos(px, py)

        if self._zoom_level == 0:
            self.fitInView(QRectF(0, 0, img_size, img_size), Qt.AspectRatioMode.KeepAspectRatio)

    def _load_map_pixmap(self, map_index: int, zoom: int, size: int) -> QPixmap:
        try:
            tile_path = MAP_TILE_IMAGES[map_index][zoom]
            if os.path.exists(tile_path):
                return QPixmap(tile_path).scaled(
                    size, size,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
        except (IndexError, Exception):
            pass
        # Placeholder
        pm = QPixmap(size, size)
        pm.fill(_MAP_COLORS[map_index % len(_MAP_COLORS)])
        return pm

    def load_map(self, map_index: int):
        self._map_index = map_index
        self._zoom_level = 0
        self._selected_order.clear()
        self._landmark_items.clear()
        self._landmark_positions.clear()
        self._scene.clear()

        img_size = ZOOM_IMAGE_SIZES[0]
        bg_pixmap = self._load_map_pixmap(map_index, 0, img_size)
        bg_item = self._scene.addPixmap(bg_pixmap)
        bg_item.setZValue(0)
        m = SCENE_MARGIN
        self._scene.setSceneRect(-m, -m, img_size + 2 * m, img_size + 2 * m)

        from core.landmark_loader import get_all_landmarks
        landmarks = get_all_landmarks(map_index)
        for identifier, data in landmarks.items():
            pos = data.get("position", [512, 0, 512])
            game_x, game_z = float(pos[0]), float(pos[2])
            self._landmark_positions[identifier] = (game_x, game_z)
            px, py = world_to_pixel(game_x, game_z, img_size, img_size, padding=0)
            ltype = classify_landmark(data)
            item = LandmarkIconItem(identifier, ltype, self)
            item.setPos(px, py)
            item.setZValue(1)
            self._scene.addItem(item)
            self._landmark_items[identifier] = item

        self.fitInView(QRectF(0, 0, img_size, img_size), Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom_label.setText("1×")
        self._zoom_in_btn.setEnabled(True)
        self._zoom_out_btn.setEnabled(False)
        self._reposition_overlays()
        self._apply_filter_visibility()

    def set_landmark_filter(self, filter_type: str):
        self._filter_type = filter_type
        self._apply_filter_visibility()
        # Deselect landmarks that are now hidden
        hidden = [id for id in self._selected_order
                  if not self._landmark_items[id].isVisible()]
        for id in hidden:
            self._selected_order.remove(id)
        if hidden:
            self._refresh_orders()

    def _apply_filter_visibility(self):
        for identifier, item in self._landmark_items.items():
            if self._filter_type == "trees":
                item.setVisible(item._type == "tree")
            elif self._filter_type == "rocks":
                item.setVisible(item._type == "rock")
            else:
                item.setVisible(True)

    def toggle_landmark(self, identifier: str):
        if identifier in self._selected_order:
            self._selected_order.remove(identifier)
        else:
            self._selected_order.append(identifier)
        self._refresh_orders()
        self.landmark_selected.emit(identifier, self._map_index)
        self._show_landmark_preview(identifier)

    def _refresh_orders(self):
        for ident, item in self._landmark_items.items():
            if ident in self._selected_order:
                item.set_order(self._selected_order.index(ident) + 1)
            else:
                item.set_order(None)

    def _show_landmark_preview(self, identifier: str):
        map_names = [
            "obsidianfieldlands", "crimsonmirelands", "cobaltcoastlands",
            "coronethighlands", "alabastericelands",
        ]
        map_name = map_names[self._map_index]
        img_path = os.path.join(LANDMARKS_DIR, map_name, f"{identifier}.png")
        if not os.path.exists(img_path):
            return
        self._fade_anim.stop()
        self._opacity_effect.setOpacity(1.0)
        self._opacity_helper._opacity = 1.0
        self._preview_label.setPixmap(QPixmap(img_path))
        self._preview_label.show()
        self._reposition_overlays()
        QTimer.singleShot(1000, self._start_fade)

    def _start_fade(self):
        if self._preview_label.isVisible():
            self._fade_anim.start()

    def clear_selection(self):
        self._selected_order.clear()
        self._refresh_orders()

    def get_selected_order(self) -> list:
        return list(self._selected_order)

    @property
    def map_index(self) -> int:
        return self._map_index
