from __future__ import annotations

import unittest
import random
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_PROFILE_PATH = Path(__file__).parents[1] / "LootTreadmill" / "profiles.py"
_SPEC = spec_from_file_location("loot_treadmill_profiles", _PROFILE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_PROFILES = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PROFILES)

_BOSS_POOL_PATH = Path(__file__).parents[1] / "LootTreadmill" / "boss_pools.py"
_BOSS_SPEC = spec_from_file_location("loot_treadmill_boss_pools", _BOSS_POOL_PATH)
assert _BOSS_SPEC is not None and _BOSS_SPEC.loader is not None
_BOSS_POOLS = module_from_spec(_BOSS_SPEC)
_BOSS_SPEC.loader.exec_module(_BOSS_POOLS)

PROFILE_MULTIPLIERS = _PROFILES.PROFILE_MULTIPLIERS
RARITY_KEYS = _PROFILES.RARITY_KEYS
compute_targets = _PROFILES.compute_targets
filter_dedicated_pools = _PROFILES.filter_dedicated_pools
normalize_boss_key = _PROFILES.normalize_boss_key
resolve_boss_pools = _PROFILES.resolve_boss_pools
resolve_class_mod_pools = _PROFILES.resolve_class_mod_pools
roll_count = _PROFILES.roll_count


class ProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline = {rarity: 1.0 for rarity in RARITY_KEYS}

    def test_vanilla_preserves_baseline(self) -> None:
        self.assertEqual(
            compute_targets(self.baseline, "Vanilla", 1, False, False),
            self.baseline,
        )

    def test_balanced_uses_declared_multipliers(self) -> None:
        self.assertEqual(
            compute_targets(self.baseline, "Treadmill Balanced", 1, False, False),
            PROFILE_MULTIPLIERS["Treadmill Balanced"],
        )

    def test_level_filter_thresholds(self) -> None:
        level_24 = compute_targets(self.baseline, "Vanilla", 24, True, True)
        level_25 = compute_targets(self.baseline, "Vanilla", 25, True, True)
        level_50 = compute_targets(self.baseline, "Vanilla", 50, True, True)
        self.assertEqual(level_24["common"], 0.0)
        self.assertEqual(level_24["uncommon"], 1.0)
        self.assertEqual(level_25["uncommon"], 0.0)
        self.assertEqual(level_50["rare"], 0.5)

    def test_filter_can_be_disabled(self) -> None:
        targets = compute_targets(self.baseline, "Vanilla", 50, False, True)
        self.assertEqual(targets, self.baseline)

    def test_unknown_profile_falls_back_to_vanilla(self) -> None:
        targets = compute_targets(self.baseline, "Missing", 50, False, False)
        self.assertEqual(targets, self.baseline)

    def test_fractional_roll_count_is_deterministic_with_seed(self) -> None:
        self.assertEqual(roll_count(1.5, random.Random(1)), 2)
        self.assertEqual(roll_count(1.5, random.Random(2)), 1)
        self.assertEqual(roll_count(0.0, random.Random(1)), 0)

    def test_boss_pool_resolution_uses_display_and_internal_names(self) -> None:
        records = (
            (("battlewagon",), (("pool_a", "SHIELD"),)),
            (("unrelated",), (("pool_b", "SG"),)),
        )
        pools = resolve_boss_pools(
            ("Name_Beast_Battlewagon", "OakBossFight_Drill_BattleBeast"),
            records,
        )
        self.assertEqual(pools, (("pool_a", "SHIELD"),))

    def test_true_suffix_does_not_break_matching(self) -> None:
        self.assertEqual(normalize_boss_key("Bloomreaper_TRUE"), "bloomreaper")

    def test_class_mod_pools_follow_active_vault_hunter(self) -> None:
        pools = {
            "dark_siren": ("vex_pool",),
            "gravitar": ("grav_pool",),
        }
        self.assertEqual(
            resolve_class_mod_pools(("BPChar_Gravitar_C",), pools),
            ("grav_pool",),
        )

    def test_unknown_class_mod_pool_is_skipped(self) -> None:
        pools = {
            "dark_siren": ("vex_pool",),
            "gravitar": ("grav_pool",),
        }
        self.assertEqual(resolve_class_mod_pools(("UnknownCharacter",), pools), ())

    def test_dedicated_class_mod_pools_follow_active_character(self) -> None:
        pools = (
            ("weapon_pool", "AR"),
            ("vex_pool", "DARK_SIREN"),
            ("grav_pool", "GRAVITAR"),
        )
        self.assertEqual(
            filter_dedicated_pools(
                pools,
                ("vex_pool", "grav_pool"),
                ("grav_pool",),
            ),
            (("weapon_pool", "AR"), ("grav_pool", "GRAVITAR")),
        )

    def test_robodealer_uses_six_convention_based_class_mod_pools(self) -> None:
        pools = _BOSS_POOLS.CLASS_MOD_POOLS["robodealer"]
        self.assertEqual(len(pools), 6)
        self.assertEqual(
            pools,
            tuple(
                f"itempool_classmod_robodealer_05_legendary_{index:02d}_shiny"
                for index in range(1, 7)
            ),
        )


if __name__ == "__main__":
    unittest.main()
