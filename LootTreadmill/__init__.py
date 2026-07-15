"""Build-oriented world, dedicated-boss, and firmware loot profiles for BL4."""

from __future__ import annotations

import random
from typing import Any

from mods_base import BoolOption, SpinnerOption, build_mod, get_pc, hook, keybind
from unrealsdk import find_class, logging
from unrealsdk.hooks import Type
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

from .boss_pools import BOSS_POOL_RECORDS, CLASS_MOD_POOLS, FIRMWARE_DONOR_POOLS
from .profiles import (
    DEDICATED_BONUS_ROLLS,
    FIRMWARE_DONOR_ROLLS,
    PROFILE_DESCRIPTIONS,
    PROFILE_MULTIPLIERS,
    compute_targets,
    filter_dedicated_pools,
    resolve_boss_pools,
    resolve_class_mod_pools,
    roll_count,
)

__version__ = "0.1.0"

_gameplay_statics = find_class("GameplayStatics").ClassDefaultObject
_item_pool_store = find_class("NexusConfigStoreItemPool").ClassDefaultObject

_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "common": ("CommonModifier",),
    "uncommon": ("UncommonModifier",),
    "rare": ("RareModifier",),
    "epic": ("VeryRareModifier", "EpicModifier"),
    "legendary": ("LegendaryModifier",),
    "pearlescent": ("PearlescentModifier", "PearlModifier"),
}

_baseline_by_state: dict[int, dict[str, float]] = {}
_field_by_state: dict[int, dict[str, str]] = {}
_warned_missing: set[str] = set()
_armed_encore_machines: set[str] = set()
_rng = random.Random()


def _current_context() -> tuple[Any, Any, int] | None:
    pc = get_pc()
    if not pc or not getattr(pc, "PlayerState", None):
        return None

    game_state = _gameplay_statics.GetGameState(pc)
    if not game_state or not getattr(game_state, "RarityState", None):
        return None

    try:
        player_level = int(pc.PlayerState.ExperienceState[0].ExperienceLevel)
    except (AttributeError, IndexError, TypeError, ValueError):
        player_level = 1

    return game_state, game_state.RarityState, player_level


def _state_key(rarity_state: Any) -> int:
    try:
        return int(rarity_state._get_address())
    except (AttributeError, TypeError, ValueError):
        return id(rarity_state)


def _discover_fields(rarity_state: Any) -> dict[str, str]:
    fields: dict[str, str] = {}
    for rarity, aliases in _FIELD_ALIASES.items():
        for field_name in aliases:
            try:
                modifier = getattr(rarity_state, field_name)
                float(modifier.Value)
                fields[rarity] = field_name
                break
            except (AttributeError, TypeError, ValueError):
                continue

        if rarity not in fields and rarity not in _warned_missing:
            logging.warning(
                f"[Loot Treadmill] Build adapter could not find the {rarity} rarity modifier."
            )
            _warned_missing.add(rarity)
    return fields


def _capture_baseline(rarity_state: Any) -> tuple[int, dict[str, float], dict[str, str]]:
    state_key = _state_key(rarity_state)
    if state_key not in _baseline_by_state:
        fields = _discover_fields(rarity_state)
        _field_by_state[state_key] = fields
        _baseline_by_state[state_key] = {
            rarity: float(getattr(rarity_state, field_name).Value)
            for rarity, field_name in fields.items()
        }
        logging.info(
            f"[Loot Treadmill] Captured vanilla rarity state: {_baseline_by_state[state_key]}"
        )
    return state_key, _baseline_by_state[state_key], _field_by_state[state_key]


def apply_profile(option: Any = None, new_value: Any = None, *_: Any) -> None:
    context = _current_context()
    if context is None:
        return

    _, rarity_state, player_level = context
    _, baseline, fields = _capture_baseline(rarity_state)
    preset = (
        str(new_value)
        if getattr(option, "identifier", None) == "Loot Profile"
        else preset_option.value
    )
    filter_low = (
        bool(new_value)
        if getattr(option, "identifier", None) == "Level-Based Low-Rarity Filter"
        else filter_low_option.value
    )
    reduce_rare = (
        bool(new_value)
        if getattr(option, "identifier", None) == "Reduce Rare at Level 50"
        else reduce_rare_option.value
    )
    targets = compute_targets(baseline, preset, player_level, filter_low, reduce_rare)

    for rarity, value in targets.items():
        getattr(rarity_state, fields[rarity]).Value = value
    logging.info(f"[Loot Treadmill] Applied '{preset}' at level {player_level}: {targets}")


def restore_baseline() -> None:
    context = _current_context()
    if context is None:
        return

    _, rarity_state, _ = context
    state_key = _state_key(rarity_state)
    baseline = _baseline_by_state.get(state_key)
    fields = _field_by_state.get(state_key)
    if not baseline or not fields:
        return

    for rarity, value in baseline.items():
        getattr(rarity_state, fields[rarity]).Value = value
    logging.info(f"[Loot Treadmill] Restored vanilla rarity state: {baseline}")


def _boss_candidates(machine: UObject) -> tuple[object, ...]:
    fight = getattr(machine, "BossFightInfo", None)
    candidates: list[object] = [
        getattr(machine, "BossDisplayName", ""),
        getattr(fight, "BossFightName", ""),
    ]
    try:
        candidates.extend(fight.ScriptData.Scripts)
    except (AttributeError, TypeError):
        pass
    return tuple(candidates)


def _spawn_pool(pool_name: str) -> bool:
    context = _current_context()
    if context is None:
        return False
    _, _, player_level = context
    pc = get_pc()
    pawn = getattr(pc, "Pawn", None)
    if not pawn:
        return False

    try:
        _item_pool_store.SpawnInventoryFromItemPool(
            pc,
            pawn.K2_GetActorTransform(),
            player_level,
            pool_name,
        )
        return True
    except (AttributeError, RuntimeError, TypeError, ValueError) as ex:
        logging.error(f"[Loot Treadmill] Could not spawn pool '{pool_name}': {ex}")
        return False


def _class_mod_pools() -> tuple[str, ...]:
    pc = get_pc()
    candidates = (
        getattr(pc, "Pawn", ""),
        getattr(getattr(pc, "Pawn", None), "Class", ""),
        getattr(pc, "PlayerState", ""),
        getattr(getattr(pc, "PlayerState", None), "Class", ""),
    )
    pools = resolve_class_mod_pools(candidates, CLASS_MOD_POOLS)
    if not pools:
        logging.warning(
            "[Loot Treadmill] Could not identify the active Vault Hunter; "
            "class-mod donors and dedicated class-mod bonuses will be skipped."
        )
    return pools


def _donor_pools(focus: str) -> tuple[str, ...]:
    class_mods = _class_mod_pools() if focus in ("All", "Class Mods") else ()
    if focus == "Class Mods":
        return class_mods
    if focus == "All":
        equipment = tuple(
            pool
            for pools in FIRMWARE_DONOR_POOLS.values()
            for pool in pools
        )
        return (*class_mods, *equipment)
    return tuple(FIRMWARE_DONOR_POOLS.get(focus, ()))


def _pay_encore_bonus(machine: UObject) -> None:
    preset = preset_option.value
    dedicated_expected = DEDICATED_BONUS_ROLLS[dedicated_bonus_option.value]
    donor_expected = FIRMWARE_DONOR_ROLLS[preset]
    pools = (
        resolve_boss_pools(_boss_candidates(machine), BOSS_POOL_RECORDS)
        if dedicated_expected > 0
        else ()
    )

    spawned_dedicated = 0
    all_class_mod_pools = {
        pool for class_pools in CLASS_MOD_POOLS.values() for pool in class_pools
    }
    active_class_mod_pools = _class_mod_pools() if any(
        pool_name in all_class_mod_pools for pool_name, _gear_type in pools
    ) else ()
    eligible_pools = filter_dedicated_pools(
        pools, tuple(all_class_mod_pools), active_class_mod_pools
    )
    for pool_name, _gear_type in eligible_pools:
        for _ in range(roll_count(dedicated_expected, _rng)):
            spawned_dedicated += int(_spawn_pool(pool_name))

    focus = firmware_focus_option.value
    donor_pools = _donor_pools(focus) if donor_expected > 0 else ()
    spawned_donors = 0
    if donor_pools:
        for _ in range(roll_count(donor_expected, _rng)):
            spawned_donors += int(_spawn_pool(_rng.choice(donor_pools)))

    boss_name = str(getattr(machine, "BossDisplayName", "Unknown boss"))
    if not pools and dedicated_expected > 0:
        logging.warning(
            f"[Loot Treadmill] No v1.8 dedicated-pool match for {boss_name}; "
            "firmware donors were still processed."
        )
    logging.info(
        f"[Loot Treadmill] Paid prior Encore for {boss_name}: "
        f"{spawned_dedicated} dedicated bonus drop(s), {spawned_donors} donor drop(s)."
    )


@hook("/Script/Engine.PlayerController:ServerAcknowledgePossession", Type.POST)
def on_player_possession(
    obj: UObject,
    args: WrappedStruct,
    ret: Any,
    func: BoundFunction,
) -> None:
    apply_profile()


@hook("/Script/OakGame.OakCharacter:BroadcastLevelUp", Type.POST)
def on_player_level_up(
    obj: UObject,
    args: WrappedStruct,
    ret: Any,
    func: BoundFunction,
) -> None:
    if obj.IsPlayerControlled():
        apply_profile()


@hook(
    "/Game/InteractiveObjects/GameSystemMachines/BossReplay/Script_BossReplay."
    "Script_BossReplay_C:GbxActorScriptEvt__UsableActorState_K2_OnUsed",
    Type.PRE,
)
def on_encore_used(
    obj: UObject,
    args: WrappedStruct,
    ret: Any,
    func: BoundFunction,
) -> None:
    machine_key = str(obj)
    if machine_key in _armed_encore_machines:
        _pay_encore_bonus(obj)
    else:
        _armed_encore_machines.add(machine_key)
        logging.info(
            f"[Loot Treadmill] Armed Encore tracking for {getattr(obj, 'BossDisplayName', obj)}. "
            "The next activation pays this run's bonus."
        )


@keybind("Reapply Loot Profile")
def reapply_keybind() -> None:
    apply_profile()


profile_description = "\n\n".join(
    f"{name}: {description}" for name, description in PROFILE_DESCRIPTIONS.items()
)

preset_option = SpinnerOption(
    "Loot Profile",
    "Treadmill Balanced",
    list(PROFILE_MULTIPLIERS),
    description=profile_description,
    on_change_while_enabled=apply_profile,
)

firmware_focus_option = SpinnerOption(
    "Firmware Donor Focus",
    "All",
    ["Off", "All", "Class Mods", *FIRMWARE_DONOR_POOLS],
    description=(
        "Adds generated Legendary firmware-capable donor gear to completed Encore payouts. "
        "Firmware remains random and the donor must be sacrificed at the transfer machine. "
        "All rotates across the active Vault Hunter's class mods, shields, repkits, and ordnance. "
        "Class Mods automatically follows the active Vault Hunter."
    ),
)

dedicated_bonus_option = SpinnerOption(
    "Dedicated Boss Bonus",
    "Off",
    list(DEDICATED_BONUS_ROLLS),
    description=(
        "Adds direct rolls from the completed boss's dedicated item pools to the next "
        "Encore activation. Off leaves the boss's normal corpse drops untouched. Gentle "
        "adds 0.08 expected rolls per pool, Balanced adds 0.45, and Loot Shower adds one "
        "guaranteed roll plus a 50% chance at a second."
    ),
)

filter_low_option = BoolOption(
    "Level-Based Low-Rarity Filter",
    True,
    "On",
    "Off",
    description="Stops Common at level 15 and Uncommon at level 25.",
    on_change_while_enabled=apply_profile,
)

reduce_rare_option = BoolOption(
    "Reduce Rare at Level 50",
    True,
    "On",
    "Off",
    description="Halves Rare weight at level 50, replacing Rarity Remover.",
    on_change_while_enabled=apply_profile,
)


def on_disable() -> None:
    restore_baseline()
    _armed_encore_machines.clear()


mod = build_mod(
    options=[
        preset_option,
        dedicated_bonus_option,
        firmware_focus_option,
        filter_low_option,
        reduce_rare_option,
    ],
    keybinds=[reapply_keybind],
    on_enable=apply_profile,
    on_disable=on_disable,
)
