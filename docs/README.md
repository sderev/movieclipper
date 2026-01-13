# MovieClipper documentation

## Overview

MovieClipper is a CLI for creating video clips from movie files with ffmpeg and fuzzy title
matching. It stores configuration in a local TOML file and can cache movie scans for faster
repeated runs.

## Installation

Requirements:

- Python 3.10 or later
- ffmpeg (required)
- ffprobe (optional, enables):
  - Audio language selection
  - Audio stream detection
  - Audio codec information
  - Audio channel count detection

MovieClipper continues without ffprobe, but audio metadata features are limited.

Install with uv:

```bash
uv tool install movieclipper
```

Optional: use a bundled ffmpeg binary via `imageio-ffmpeg`:

```bash
uv tool install "movieclipper[ffmpeg]"
```

## Quick start

```bash
movieclipper --setup
movieclipper "Movie Title" --start 00:01:00 --duration 20
```

## Configuration

The configuration file lives at:

```
~/.config/movieclipper/movieclipper.toml
```

The setup flow suggests a movies directory based on `~/Videos`, then `~/Movies`, and falls back
to the current working directory. Clips default to a `clips/` subdirectory in the selected movies
folder.

Use these overrides when needed:

- `--ffmpeg-path` and `--ffprobe-path`
- `MOVIECLIPPER_FFMPEG` and `MOVIECLIPPER_FFPROBE`

## Usage

Select by fuzzy title and create a clip:

```bash
movieclipper "Spirited Away" --start 00:42:10 --duration 15
```

Choose an audio language when ffprobe is available:

```bash
movieclipper "Spirited Away" --start 00:42:10 --duration 15 --audio-lang jpn
```

Keep all audio tracks:

```bash
movieclipper "Spirited Away" --start 00:42:10 --duration 15 --preserve-audio
```

Write output to a test folder:

```bash
movieclipper "Spirited Away" --start 00:42:10 --duration 15 --test
```

## Cache

Movie scans can be cached to speed up repeated runs.

```bash
movieclipper --cache-info
movieclipper --clear-cache
```

## Troubleshooting

- ffmpeg not found: install ffmpeg or use `movieclipper[ffmpeg]`.
- ffprobe not found: audio metadata features are limited; install ffprobe to enable audio
  language selection, audio stream detection, audio codec information, and audio channel count
  detection.
- Config errors: run `movieclipper --setup` to regenerate the config.
