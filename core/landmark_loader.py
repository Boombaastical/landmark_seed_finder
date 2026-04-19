import importlib
import importlib.resources
import json
import os

import numpy as np
from numba_pokemon_prngs.data import SPECIES_EN
from numba_pokemon_prngs.data.encounter import ENCOUNTER_INFORMATION_LA
from numba_pokemon_prngs.data.encounter.encounter_area_la import SlotLA

import resources

MAPS = [
    "obsidianfieldlands",
    "crimsonmirelands",
    "cobaltcoastlands",
    "coronethighlands",
    "alabastericelands",
]

# Serebii URL names that match the tile download naming convention
SEREBII_NAMES = [
    "obsidianfieldlands",
    "crimsonmirelands",
    "cobaltcoastlands",
    "coronethighlands",
    "alabastericelands",
]

_MAPS_DIR = os.path.join(os.path.dirname(__file__), "..", "resources", "maps")

# Paths to stitched map tile images per map per zoom level (0, 1, 2).
# Falls back to placeholder in MapCanvas when a file doesn't exist.
MAP_TILE_IMAGES = [
    [
        os.path.join(_MAPS_DIR, f"{name}_z{z}.png")
        for z in range(3)
    ]
    for name in SEREBII_NAMES
]

MAP_DISPLAY_NAMES = [
    "Obsidian Fieldlands",
    "Crimson Mirelands",
    "Cobalt Coastlands",
    "Coronet Highlands",
    "Alabaster Icelands",
]

WORLD_MIN = 0.0
WORLD_MAX = 1024.0

_ROCK_KEYWORDS = {"tumblestone", "chunk", "ore", "stardust", "star piece", "nugget"}


def _load_map_json(map_index: int) -> dict:
    with (importlib.resources.files(resources) / f"{MAPS[map_index]}.json").open("r") as f:
        return json.load(f)


def load_landmark(map_index: int, identifier: str) -> dict:
    return _load_map_json(map_index)[identifier]


def get_all_landmarks(map_index: int) -> dict[str, dict]:
    return _load_map_json(map_index)


def world_to_pixel(
    x: float, z: float, img_w: int, img_h: int, padding: int = 20
) -> tuple[int, int]:
    usable_w = img_w - 2 * padding
    usable_h = img_h - 2 * padding
    px = padding + int((x - WORLD_MIN) / (WORLD_MAX - WORLD_MIN) * usable_w)
    py = padding + int((z - WORLD_MIN) / (WORLD_MAX - WORLD_MIN) * usable_h)
    return px, py


def classify_landmark(data: dict) -> str:
    for reward in data.get("rewardTable", []):
        item = reward.get("item", "").lower()
        if any(kw in item for kw in _ROCK_KEYWORDS):
            return "rock"
    return "tree"


def get_name_en(species: int, form: int = 0, is_alpha: bool = False) -> str:
    return (
        f"{'Alpha ' if is_alpha else ''}"
        f"{SPECIES_EN[species]}"
        f"{f'-{form}' if form else ''}"
    )


def get_all_landmark_species() -> list[int]:
    """Collect every unique species that can appear at any landmark across all maps."""
    species_set: set[int] = set()
    for map_index in range(len(MAPS)):
        try:
            landmarks = get_all_landmarks(map_index)
        except Exception:
            continue
        for data in landmarks.values():
            try:
                enc_table = ENCOUNTER_INFORMATION_LA[map_index + 1][
                    np.uint64(data["encounterTable"])
                ]
                for slot in enc_table.slots:
                    slot_rec = np.rec.array(slot, dtype=SlotLA.dtype)
                    species_set.add(int(slot_rec.species))
            except Exception:
                pass
    return sorted(species_set, key=lambda s: SPECIES_EN[s])
