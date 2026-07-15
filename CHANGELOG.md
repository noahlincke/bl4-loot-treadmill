# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-07-14

### Added

- Independent Dedicated Boss Bonus setting with Off, Gentle, Balanced, and Loot Shower modes.
- Generic firmware targeting for All, Class Mods, Shields, Repkits, and Ordnance.
- Automatic class-mod targeting for the active Vault Hunter.
- Convention-based C4SH class-mod pools matching the six-pool pattern used by base Vault Hunters.
- Reproducible PowerShell packaging script and GitHub Actions test workflow.
- MIT license.

### Changed

- Dedicated boss bonuses now default to Off.
- Dedicated class-mod bonuses skip pools for other Vault Hunters.
- Unknown Vault Hunters safely skip class-mod payouts instead of receiving off-class gear.

### Fixed

- Removed character- and build-specific wording.
- Repaired README text encoding.
