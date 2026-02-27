# MovieClipper

Create video clips from movie files with ffmpeg and fuzzy title matching.

## Requirements

- Python 3.11 or later
- ffmpeg (required)
- ffprobe (optional, enables audio language selection, audio stream detection, audio codec information, and audio channel count detection; without it, audio metadata features run in degraded mode)

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

Movies and clips directories are chosen during setup. Clips default to `clips/` inside the movies directory. Symlinks are followed by default on Linux and in WSL, including when the movies directory is on the Windows filesystem.

Environment variables set ffmpeg/ffprobe paths when CLI flags (`--ffmpeg-path`, `--ffprobe-path`) are absent. CLI flags take precedence. There is no config file option for these paths.

- `MOVIECLIPPER_FFMPEG`
- `MOVIECLIPPER_FFPROBE`

## Usage

### Movie selection

Select movies by fuzzy title matching:

```bash
movieclipper "Spirited Away" --start 00:42:10 --duration 15
```

Or provide a full path:

```bash
movieclipper ~/Movies/film.mkv --start 00:01:00 --duration 30
```

### Time formats

Times can be specified as:

- Seconds: `90`, `90.5`
- Minutes:seconds: `1:30`, `1:30.5`
- Hours:minutes:seconds: `01:02:03`

### Audio options

Select a preferred audio language (requires ffprobe):

```bash
movieclipper "Title" --start 0 --duration 10 --audio-lang jpn
```

Keep all audio tracks with PCM encoding:

```bash
movieclipper "Title" --start 0 --duration 10 --preserve-audio
```

Force stereo downmix or preserve original channels:

```bash
movieclipper "Title" --start 0 --duration 10 --stereo
movieclipper "Title" --start 0 --duration 10 --no-stereo
```

### Output

Output files are named `{Title}_{start}_to_{end}.mp4` in the clips directory.

Write to a test directory (`clips_testing/`) instead:

```bash
movieclipper "Title" --start 0 --duration 10 --test
```

## Key options

- `--check` verifies ffmpeg and configuration
- `--ffmpeg-path` and `--ffprobe-path` override binaries
- `--cache-info`, `--clear-cache`, and `--refresh-cache` manage the scan cache

## Cache

Movie scans are cached for faster repeated runs. The default cache TTL is 7 days. If a cached movie is not found, the cache is automatically refreshed.

```bash
movieclipper --cache-info
movieclipper --refresh-cache
movieclipper --clear-cache
```

## Troubleshooting

- ffmpeg not found: install ffmpeg or use `movieclipper[ffmpeg]`.
- ffprobe not found: install ffprobe for full audio metadata support.
- Config errors: run `movieclipper --setup` to regenerate the config.
