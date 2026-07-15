# Contributing

Bug reports and pull requests are welcome. Please include the Borderlands 4 game build, SDK version, selected mod settings, and relevant lines from `unrealsdk.log` when reporting runtime problems.

Before opening a pull request:

1. Keep runtime code compatible with the Python version bundled by the BL4 SDK.
2. Run `python -m unittest discover -s tests -v`.
3. Run `powershell -ExecutionPolicy Bypass -File build.ps1` and inspect the resulting archive.
4. Do not include game assets, proprietary data, saves, or decompiled third-party mod code.

Generated changes to `LootTreadmill/boss_pools.py` should identify the source manifest version in the pull request.
