"""Persistent statistics tracking across Generate runs."""

import json
from pathlib import Path

from core.seed_finder import AdvanceResult

STATS_FILE = Path(__file__).parent.parent / "statistics.json"

_DEFAULTS = {
    "total_batches": 0,
    "shinies_within_100": 0,
    "alphas_within_100": 0,
    "shiny_alphas_within_1000": 0,
}


def load_stats() -> dict:
    if STATS_FILE.exists():
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Fill any missing keys with defaults
            return {**_DEFAULTS, **data}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(_DEFAULTS)


def save_stats(stats: dict):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)


def update_stats(results: list) -> dict:
    """Increment counters based on results from one Generate run and persist."""
    stats = load_stats()
    stats["total_batches"] += 1
    for r in results:
        if r.is_shiny and r.advance <= 100:
            stats["shinies_within_100"] += 1
        if r.is_alpha and r.advance <= 100:
            stats["alphas_within_100"] += 1
        if r.is_shiny and r.is_alpha and r.advance <= 1000:
            stats["shiny_alphas_within_1000"] += 1
    save_stats(stats)
    return stats


def format_stats(stats: dict) -> str:
    return (
        f"Batches checked:         {stats['total_batches']:>6}\n"
        f"Shinies ≤ 100 adv:       {stats['shinies_within_100']:>6}\n"
        f"Alphas ≤ 100 adv:        {stats['alphas_within_100']:>6}\n"
        f"Shiny alphas ≤ 1000 adv: {stats['shiny_alphas_within_1000']:>6}"
    )
