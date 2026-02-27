# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

<!-- scriv-insert-here -->

<a id='changelog-0.1.0'></a>
## 0.1.0 - 2026-02-27

Added
-----
* Add `--refresh-cache` flag to manually rebuild the movie scan cache.
* Auto-refresh cache when a cached movie is not found.
* `--version` flag to print the installed version.
* `--setup` now warns when ffmpeg is not found.
* WSL-aware default directory detection (prefers Windows `~/Videos` or `~/Movies`).

Changed
-------
* Set the default cache TTL to 7 days.
* Minimum Python version raised from 3.10 to 3.11.
* Replaced abandoned `toml` package with stdlib `tomllib` + `tomli-w`.
