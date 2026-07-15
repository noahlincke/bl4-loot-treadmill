"""Pure profile math and farming targets for Loot Treadmill."""

from __future__ import annotations

import math
import random
import re
from typing import Final, Mapping, Sequence, TypeVar

RARITY_KEYS: Final[tuple[str, ...]] = (
    "common",
    "uncommon",
    "rare",
    "epic",
    "legendary",
    "pearlescent",
)

PROFILE_MULTIPLIERS: Final[dict[str, dict[str, float]]] = {
    "Vanilla": {
        "common": 1.0,
        "uncommon": 1.0,
        "rare": 1.0,
        "epic": 1.0,
        "legendary": 1.0,
        "pearlescent": 1.0,
    },
    "Gentle": {
        "common": 0.8,
        "uncommon": 2.0,
        "rare": 8.0,
        "epic": 12.0,
        "legendary": 100.0,
        "pearlescent": 50.0,
    },
    "Treadmill Balanced": {
        "common": 0.6,
        "uncommon": 4.166667,
        "rare": 71.428571,
        "epic": 88.888889,
        "legendary": 3000.0,
        "pearlescent": 500.0,
    },
    "Loot Shower": {
        "common": 0.25,
        "uncommon": 4.166667,
        "rare": 178.571429,
        "epic": 444.444444,
        "legendary": 15000.0,
        "pearlescent": 2500.0,
    },
}

# Expected extra generated items per real boss-pool item and per completed
# Encore, respectively. Fractional values are unbiased random rolls.
DEDICATED_BONUS_ROLLS: Final[dict[str, float]] = {
    "Off": 0.0,
    "Gentle": 0.08,
    "Balanced": 0.45,
    "Loot Shower": 1.5,
}

FIRMWARE_DONOR_ROLLS: Final[dict[str, float]] = {
    "Vanilla": 0.0,
    "Gentle": 0.25,
    "Treadmill Balanced": 1.0,
    "Loot Shower": 4.0,
}

PROFILE_DESCRIPTIONS: Final[dict[str, str]] = {
    "Vanilla": (
        "Exact captured world-rarity values and no firmware donors. "
        "Rough full-build target: 30-60 hours assembled, 150+ hours refined."
    ),
    "Gentle": (
        "Mostly-vanilla progression. World multipliers C .8x / U 2x / R 8x / E 12x / "
        "L 100x / P 50x; firmware focus gets 0.25 donor rolls per completed Encore. "
        "Rough target: 20-40 hours "
        "assembled, 100+ hours refined."
    ),
    "Treadmill Balanced": (
        "Build-assembly mode. World multipliers C .6x / U 4.17x / R 71.43x / E 88.89x / "
        "L 3000x / P 500x; firmware focus gets 1 donor per completed Encore. "
        "Rough target: 8-20 hours assembled, "
        "40-100 hours for strong multi-roll gear."
    ),
    "Loot Shower": (
        "Endgame perfection mode. World multipliers C .25x / U 4.17x / R 178.57x / "
        "E 444.44x / L 15000x / P 2500x; firmware focus gets 4 donors per completed Encore. "
        "Rough target: 2-8 hours assembled, 15-50 hours for several near-perfect pieces; "
        "a literal perfect build remains unbounded RNG."
    ),
}

T = TypeVar("T")


def compute_targets(
    baseline: Mapping[str, float],
    preset: str,
    player_level: int,
    filter_low_rarities: bool,
    reduce_rare_at_level_50: bool,
) -> dict[str, float]:
    """Return live rarity modifiers without mutating the captured baseline."""
    multipliers = PROFILE_MULTIPLIERS.get(preset, PROFILE_MULTIPLIERS["Vanilla"])
    targets = {
        rarity: float(baseline[rarity]) * multipliers[rarity]
        for rarity in RARITY_KEYS
        if rarity in baseline
    }

    if filter_low_rarities:
        if player_level >= 15 and "common" in targets:
            targets["common"] = 0.0
        if player_level >= 25 and "uncommon" in targets:
            targets["uncommon"] = 0.0
        if player_level >= 50 and reduce_rare_at_level_50 and "rare" in targets:
            targets["rare"] *= 0.5

    return targets


def roll_count(expected: float, rng: random.Random | None = None) -> int:
    """Turn a fractional expectation into an unbiased integer count."""
    if expected <= 0:
        return 0
    whole = math.floor(expected)
    fraction = expected - whole
    source = rng if rng is not None else random
    return whole + int(source.random() < fraction)


def normalize_boss_key(value: object) -> str:
    """Normalize display defs, script names, and manifest names for matching."""
    normalized = re.sub(r"[^a-z0-9]", "", str(value).lower())
    return re.sub(r"true$", "", normalized)


def resolve_boss_pools(
    candidates: Sequence[object],
    records: Sequence[tuple[Sequence[str], Sequence[T]]],
) -> tuple[T, ...]:
    """Resolve all pools tied for the strongest alias match."""
    normalized = tuple(filter(None, (normalize_boss_key(value) for value in candidates)))
    matches: list[tuple[int, Sequence[T]]] = []
    for aliases, pools in records:
        best = 0
        for alias in aliases:
            if len(alias) < 4:
                continue
            for candidate in normalized:
                if alias in candidate or candidate in alias:
                    best = max(best, len(alias))
        if best:
            matches.append((best, pools))

    if not matches:
        return ()
    strongest = max(score for score, _ in matches)
    resolved: list[T] = []
    for score, pools in matches:
        if score != strongest:
            continue
        for pool in pools:
            if pool not in resolved:
                resolved.append(pool)
    return tuple(resolved)


def resolve_class_mod_pools(
    candidates: Sequence[object],
    class_pools: Mapping[str, Sequence[T]],
) -> tuple[T, ...]:
    """Choose class-mod pools for the active Vault Hunter."""
    normalized = "".join(normalize_boss_key(value) for value in candidates)
    for class_key, pools in class_pools.items():
        if normalize_boss_key(class_key) in normalized:
            return tuple(pools)

    return ()


def filter_dedicated_pools(
    pools: Sequence[tuple[str, T]],
    known_class_mod_pools: Sequence[str],
    active_class_mod_pools: Sequence[str],
) -> tuple[tuple[str, T], ...]:
    """Remove dedicated class-mod pools that do not belong to the active character."""
    known = set(known_class_mod_pools)
    active = set(active_class_mod_pools)
    return tuple(
        entry for entry in pools if entry[0] not in known or entry[0] in active
    )
