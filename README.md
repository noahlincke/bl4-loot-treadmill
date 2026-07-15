# Loot Treadmill

Loot Treadmill is an open-source Borderlands 4 SDK mod that turns build farming into a configurable progression loop. It changes reversible world-rarity weights and can generate firmware-capable donor gear without editing saves. Direct dedicated-boss bonuses are available as a separate, opt-in setting.

This is an unofficial community project and is not affiliated with or endorsed by Gearbox Software or 2K. Borderlands and related trademarks belong to their respective owners.

## Features

- Four world-loot profiles, from Vanilla through Loot Shower.
- Independent dedicated-boss bonus, disabled by default.
- Firmware donors targeting all supported categories, class mods, shields, repkits, or ordnance.
- Class-mod donors and dedicated bonuses automatically follow supported Vault Hunters.
- Optional level-based low-rarity filtering.
- Host-side co-op support.

## Loot profiles

The hour estimates assume a complete endgame build with named gear, useful class-mod passives, weapon attachments, and firmware. They are directional targets rather than guarantees; kill speed and the exact attachment or passive combination dominate the final chase.

- **Vanilla** - Captured game rarity values and no firmware donors. Rough target: 30-60 hours assembled; 150+ hours refined.
- **Gentle** - World multipliers Common .8x, Uncommon 2x, Rare 8x, Epic 12x, Legendary 100x, Pearlescent 50x. Firmware focus receives 0.25 expected donor rolls per completed Encore. Rough target: 20-40 hours assembled; 100+ hours refined.
- **Treadmill Balanced** - World multipliers Common .6x, Uncommon 4.17x, Rare 71.43x, Epic 88.89x, Legendary 3000x, Pearlescent 500x. Firmware focus receives one donor per completed Encore. Rough target: 8-20 hours assembled; 40-100 hours for strong multi-roll gear.
- **Loot Shower** - World multipliers Common .25x, Uncommon 4.17x, Rare 178.57x, Epic 444.44x, Legendary 15000x, Pearlescent 2500x. Firmware focus receives four donors per completed Encore. Rough target: 2-8 hours assembled; 15-50 hours for several near-perfect pieces. Literal perfection remains unbounded RNG.

The default level filter stops Common drops at level 15, stops Uncommon drops at 25, and halves the Rare weight at 50.

## Dedicated boss bonus

This setting is independent of the world-loot profile and defaults to **Off**. The available modes are:

- **Off** - No generated dedicated drops. Normal boss corpse loot is untouched.
- **Gentle** - Each dedicated pool receives 0.08 expected bonus rolls per completed Encore.
- **Balanced** - Each dedicated pool receives 0.45 expected bonus rolls.
- **Loot Shower** - Each dedicated pool receives one guaranteed roll plus a 50% chance at a second.

BL4's boss loot runs through native NCS code that the SDK cannot reliably intercept. The mod therefore uses the replay machine's Blueprint event:

1. The first Encore activation for a machine arms tracking.
2. Defeat the boss normally.
3. The next activation pays the previous run's configured bonus beside the player, then starts the next fight.

The replay machine cannot be activated during its fight, which gates the payout behind a completed run. The final run of a session has an unpaid carry-over unless another Encore is started. The generated table covers 91 boss-source records from the v1.8 reference manifest. Unknown future bosses retain their normal loot and still receive configured firmware donors.

## Firmware focus

Choose **All**, **Class Mods**, **Shields**, **Repkits**, **Ordnance**, or **Off**. **All** selects from every supported donor pool, while **Class Mods** follows the active Vault Hunter when supported pool data is available. If the character cannot be identified, class-mod payouts are safely skipped.

C4SH support follows the same six-pool `RoboDealer` naming convention used by every base Vault Hunter. Those pool names are convention-based until they appear in the public reference manifest.

Donors are newly generated Legendary items, firmware remains random, and BL4's transfer machine still destroys the donor. This is target farming, not item manufacturing: the mod never selects a named firmware, rewrites a dropped item, or edits a save.

## Requirements and installation

1. Install the Borderlands 4 Python SDK.
2. Download `LootTreadmill.sdkmod` from the release assets.
3. Copy it into the game's `sdk_mods` folder.
4. Disable Rarity Remover to avoid overlapping world-rarity writes.
5. In game, open the SDK console with tilde twice, enter `mods`, and configure **Loot Treadmill**.

## Compatibility

- Captures the live `GameRarityState` baseline and restores it when disabled.
- Reapplies the selected world profile on player possession and level-up.
- Host-side in co-op; the host must run the mod.
- Live-tested with BL4 SDK v0.3 and game build 23744902 (v1.8).
- Generated boss data comes from the `monokrome/bl4` v1.8 drop manifest.

Back up saves before using any game mod. Game updates may change runtime fields or item-pool names.

## Development

Run the tests and build the SDK package:

```powershell
python -m unittest discover -s tests -v
powershell -ExecutionPolicy Bypass -File build.ps1
```

`boss_pools.py` is checked in so ordinary builds do not require the reference manifest. To regenerate it, place a compatible `drops.json` manifest at `../bl4-reference/share/manifest/drops.json` or provide its path explicitly:

```powershell
powershell -ExecutionPolicy Bypass -File generate_boss_pools.ps1 -ManifestPath C:\path\to\drops.json
```

Runtime behavior was independently verified through public SDK APIs, in-game reflection, and the BSD-licensed `monokrome/bl4` reverse-engineering documentation. No third-party mod source code or game assets are included.

## License

MIT. See [LICENSE](LICENSE).
