# MovieClipper

Create video clips from movie files with ffmpeg and fuzzy title matching.

## Requirements

- Python 3.10 or later
- ffmpeg (required)
- ffprobe (optional, enables audio language selection)

## Install

Recommended:

```bash
uv tool install movieclipper
```

Optional: bundle an ffmpeg binary via `imageio-ffmpeg`:

```bash
uv tool install "movieclipper[ffmpeg]"
```

## Quick start

```bash
movieclipper --setup
movieclipper "Movie Title" --start 00:01:00 --duration 20
```

## Configuration

Configuration file:

```
~/.config/movieclipper/movieclipper.toml
```

Default setup suggestions prefer `~/Videos`, then `~/Movies`, then the current directory.
Clips are saved under `clips/` inside the chosen movies folder.

## Key options

- `--check` verifies ffmpeg and configuration
- `--ffmpeg-path` and `--ffprobe-path` override binaries
- `--audio-lang` selects a preferred audio language
- `--preserve-audio` keeps all audio tracks
- `--cache-info` and `--clear-cache` manage the scan cache
- `--test` writes output to `clips_testing/`

## Documentation

See `docs/README.md` for details.
