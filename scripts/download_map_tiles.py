"""
Download and stitch Serebii map tiles for the Landmark Seed Finder.

Run once from the project root:
    python3 scripts/download_map_tiles.py

Output: resources/maps/{serebii_name}_z{0,1,2}.png  (15 images total)

Tile URL format: https://www.serebii.net/pokearth/hisui/{location}/tile_{z}-{x}-{y}.png
Zoom layout:
  z=0 → 2×2 tiles  → 512×512  stitched image
  z=1 → 4×4 tiles  → 1024×1024 stitched image
  z=2 → 8×8 tiles  → 2048×2048 stitched image
"""

import os
import sys
import urllib.request
from io import BytesIO

# Allow running from project root without installing as package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtWidgets import QApplication

BASE_URL = "https://www.serebii.net/pokearth/hisui"
TILE_PX = 256  # each tile is 256×256 pixels

# tiles_per_side = 2^(z+1)
ZOOM_CONFIG = {
    0: {"tiles_per_side": 2,  "img_size": 512},
    1: {"tiles_per_side": 4,  "img_size": 1024},
    2: {"tiles_per_side": 8,  "img_size": 2048},
}

SEREBII_NAMES = [
    "obsidianfieldlands",
    "crimsonmirelands",
    "cobaltcoastlands",
    "coronethighlands",
    "alabastericelands",
]

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "resources", "maps")


def fetch_pixmap(url: str):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        pm = QPixmap()
        pm.loadFromData(data)
        return pm if not pm.isNull() else None
    except Exception as e:
        print(f"  ✗ Failed to fetch {url}: {e}")
        return None


def stitch_tiles(location: str, zoom: int, tiles_per_side: int, img_size: int) -> QPixmap:
    canvas = QPixmap(img_size, img_size)
    canvas.fill(Qt.GlobalColor.black)
    painter = QPainter(canvas)
    total = tiles_per_side * tiles_per_side
    fetched = 0
    for y in range(tiles_per_side):
        for x in range(tiles_per_side):
            url = f"{BASE_URL}/{location}/tile_{zoom}-{x}-{y}.png"
            pm = fetch_pixmap(url)
            if pm:
                painter.drawPixmap(x * TILE_PX, y * TILE_PX, pm)
                fetched += 1
            else:
                print(f"  Missing tile: tile_{zoom}-{x}-{y}.png")
    painter.end()
    print(f"  Stitched {fetched}/{total} tiles for zoom {zoom}")
    return canvas


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    os.makedirs(OUT_DIR, exist_ok=True)

    for location in SEREBII_NAMES:
        print(f"\n{'='*50}")
        print(f"Map: {location}")

        # Quick check that the location name is correct using zoom-0 tile_0-0-0
        probe_url = f"{BASE_URL}/{location}/tile_0-0-0.png"
        print(f"  Checking: {probe_url}")
        probe = fetch_pixmap(probe_url)
        if probe is None:
            print(f"  ✗ Location '{location}' not found on Serebii — skipping.")
            print(f"    Try checking the URL manually: {probe_url}")
            continue

        for zoom, cfg in ZOOM_CONFIG.items():
            out_path = os.path.join(OUT_DIR, f"{location}_z{zoom}.png")
            if os.path.exists(out_path):
                print(f"  zoom {zoom}: already exists, skipping ({out_path})")
                continue
            print(f"  zoom {zoom}: downloading {cfg['tiles_per_side']}×{cfg['tiles_per_side']} tiles…")
            stitched = stitch_tiles(location, zoom, cfg["tiles_per_side"], cfg["img_size"])
            if stitched.save(out_path, "PNG"):
                print(f"  zoom {zoom}: saved → {out_path}")
            else:
                print(f"  ✗ Failed to save {out_path} (QPixmap.save returned False)")

    print("\nDone! Run python3 main.py to launch the app with real map images.")


if __name__ == "__main__":
    main()
