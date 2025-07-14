# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a video processing project for the "One Second Per Movie" series. The project involves trimming movie files to extract specific short clips for video editing workflows, particularly for use in DaVinci Resolve.

## Git Workflow

This project uses git for version control. Always make commits when making significant changes to the codebase.

### Branch Management
- Use `main` branch for stable releases
- Use `dev` branch for development work
- Use feature branches for new features: `feature/audio-enhancement`, `feature/fuzzy-matching`
- Use modern git commands like `git switch` instead of `git checkout -b`

### Commit Guidelines
- Make atomic commits (one logical change per commit)
- Write clear, descriptive commit messages
- Include Claude Code attribution in commits
- Use conventional commit format when possible:
  - `feat:` for new features
  - `fix:` for bug fixes
  - `docs:` for documentation changes
  - `refactor:` for code refactoring
  - `test:` for adding or modifying tests

### Example Workflow
```bash
# Create feature branch
git switch -c feature/new-audio-options

# Make changes and commit
git add movieclipper
git commit -m "feat: add smart audio stream selection

- Add English preference with fallback to first stream
- Implement stereo mixing by default for DaVinci Resolve compatibility
- Add --preserve-audio flag for lossless workflows
- Include language detection via ffprobe

🤖 Generated with Claude Code (https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Switch back to main and merge
git switch main
git merge feature/new-audio-options
```

### Files to Track
- `movieclipper` - Main script
- `test_movieclipper.py` - Test suite
- `README.md` - Documentation
- `TODO.md` - Project management
- `CLAUDE.md` - This file
- `.gitignore` - Git ignore rules

### Files to Ignore
- `~/.config/movieclipper/movieclipper.toml` - User configuration (contains local paths)
- `clips_testing/` - Test output directory
- `<year>/clips/` - Generated clips (year directories are dynamic)
- Movie files (*.mkv, *.mp4, etc.) - Too large for git
- Python cache files (__pycache__/, *.pyc)

## Movie Clipper Script

The main automation script is `movieclipper` which provides:

### Key Features
- **Fuzzy movie matching**: Find movies by partial titles ("iron man" → "Iron.Man.2008.Multi.VF.1080p.Bluray.x264-BDHD.mkv")
- **Smart audio selection**: English preference with stereo mixing by default
- **DaVinci Resolve compatibility**: PCM audio output for maximum compatibility
- **Multi-language support**: Choose specific audio languages
- **Flexible time input**: HH:MM:SS, MM:SS, or seconds format
- **Testing mode**: Safe testing with separate directory
- **Configuration management**: First-run setup with validation

### Usage Examples
```bash
# Basic usage (English stereo by default)
uv run movieclipper "Iron Man" -s 15:35 -d 12

# Keep all audio tracks (original behavior)
uv run movieclipper "Iron Man" --preserve-audio -s 15:35 -d 12

# Select specific language
uv run movieclipper "Iron Man" --audio-lang fre -s 15:35 -d 12

# Testing mode
uv run movieclipper "Iron Man" --test -s 15:35 -d 12
```

### Configuration
- Configuration stored in `~/.config/movieclipper/movieclipper.toml` (auto-generated)
- Supports directory customization
- Audio preferences and settings
- Symlink handling options

## Directory Structure

* `<year>/` - Year-based organization (dynamic, defaults to current year)
  * `clips/` - Output directory for trimmed video clips
  * `clips_testing/` - Test output directory (when using --test flag)
  * `download/` - Source movie files (may be in subdirectories or directly in download/)
    * `converted/` - Movies with audio tracks converted for compatibility
    * `not_detected/` - Movies requiring manual processing
      * `converted/` - Processed versions of not_detected movies
      * `convert_all.sh` - Bulk audio conversion script

## Common Commands

### Creating Short Clips (Fast, Low-Memory, DaVinci Resolve Compatible)

```bash
# Fast, keyframe-based seek + duration + stream copy → mp4 with PCM audio for DaVinci Resolve
ffmpeg -ss 01:16:25 \
       -i "<year>/download/MovieFolder/source_movie.mkv" \
       -t 00:00:35 \
       -c:v copy \
       -c:a pcm_s16le -ar 48000 \
       "<year>/clips/SourceMovie_01h16m25s_to_01h17m00s.mp4"
```

* `-ss 01:16:25` **before** `-i`: fast seek to nearest keyframe at or before that timestamp.
* `-t 00:00:35`: duration of 35 seconds (ends at 1:17:00).
* `-c:v copy`: stream-copy video without re-encoding.
* `-c:a pcm_s16le -ar 48000`: encode audio to uncompressed PCM at 48kHz for DaVinci Resolve compatibility.
* Always specify an **output filename**; omitting it streams raw output to stdout (huge RAM usage).

### Frame-Accurate Cut (Light Re-encode)

```bash
ffmpeg -ss 01:16:00 \
       -i "<year>/download/MovieFolder/source_movie.mkv" \
       -ss 00:00:25 \
       -t 00:00:35 \
       -c:v libx264 -preset veryfast -crf 18 \
       -c:a pcm_s16le -ar 48000 \
       "<year>/clips/AccurateClip_01h16m25s_to_01h17m00s.mp4"
```

* First `-ss` (before input) jumps close to target.
* Second `-ss` (after input) does precise frame-accurate start—but requires decoding/re-encoding.
* Video: re-encoded with x264; Audio: encoded to uncompressed PCM for DaVinci Resolve compatibility.

### Using `-to` Instead of `-t`

```bash
# Using absolute end time (relative to input start): must follow -i
ffmpeg -i "<year>/download/MovieFolder/source_movie.mkv" \
       -ss 00:30:00 \
       -to 00:31:00 \
       -c:v copy \
       -c:a pcm_s16le -ar 48000 \
       "<year>/clips/Clip_00h30m00s_to_00h31m00s.mp4"
```

* `-ss` before or after `-i`: fast vs accurate seek behavior.
* `-to 00:31:00`: cuts until 31 minutes from the start of input.
* `-c:a pcm_s16le -ar 48000`: ensures DaVinci Resolve compatibility with uncompressed PCM audio.

## Audio Conversion for DaVinci Resolve Compatibility

```bash
# Copy video, convert audio to PCM for DaVinci Resolve (RECOMMENDED)
ffmpeg -i "<year>/clips/input_clip.mkv" \
       -c:v copy \
       -c:a pcm_s16le -ar 48000 \
       "<year>/clips/input_clip_davinci.mp4"
```

**Why PCM Audio?** DaVinci Resolve has significant compatibility issues with AAC audio, especially on Linux and with the free version. PCM (uncompressed) audio ensures maximum compatibility and quality.

## PCM Audio Format Specifications

**Recommended Settings:**
* **Codec**: `pcm_s16le` (16-bit signed little-endian PCM)
* **Sample Rate**: `48000` Hz (48 kHz - DaVinci Resolve's native rate)
* **Channels**: Preserves original channel layout (mono, stereo, 5.1, etc.)

**Benefits:**
* 100% DaVinci Resolve compatibility (all versions, all platforms)
* No compression artifacts or quality loss
* Better editing performance (no decoding overhead)
* No licensing or codec issues

**Trade-offs:**
* Larger file sizes (~10x larger than AAC)
* Suitable for short clips where quality > file size

## Bulk Audio Conversion

Use the existing `convert_all.sh` script in `<year>/download/not_detected/`:

* Converts TrueHD and DTS audio tracks to AC3 or AAC for broad compatibility.
* Preserves video streams with `-c:v copy`.
* Maintains metadata.
* Outputs `_converted.mp4` files in `converted/` subdirectory.

## Video Processing Guidelines

### File Naming Convention

* Use descriptive names: `MovieName_StartTimestamp_to_EndTimestamp[_lang][_fixed].mp4`
* Examples:

  * `IronMan2_00h22m00s_to_00h23m00s_eng.mp4`
  * `DoctorStrange_00h30m45s_to_00h31m15s_fixed.mp4`

### Audio Track Selection

* `0:0` = Video
* `0:1` = Audio track 1 (often French)
* `0:2` = Audio track 2 (often English)
* Run `ffmpeg -i filename.mkv` to inspect streams before processing.

### DaVinci Resolve Compatibility

* **CRITICAL**: DaVinci Resolve has significant issues with AAC audio, especially on Linux and free version.
* **RECOMMENDED**: Use PCM audio (`-c:a pcm_s16le -ar 48000`) for guaranteed compatibility.
* Many editors don't support EAC3, DTS, TrueHD - avoid these formats entirely.
* DaVinci Resolve works natively at 48kHz and resamples other rates to 48kHz.
* PCM audio provides uncompressed quality and eliminates codec compatibility issues.
* File sizes will be larger with PCM audio but editing performance is better.
* Test in VLC and DaVinci Resolve to verify sync and compatibility.

## Common Pitfalls & Troubleshooting

* **Missing output file**: FFmpeg defaults to stdout if no output name is given—buffers raw frames in RAM, causing crashes.
* **High memory usage**: Omit `-c:v copy` or forget output path.
* **Slow seeks**: Placing `-ss` after `-i` decodes all preceding frames—use pre-input `-ss` for speed.
* **Library mismatch warnings**: Install a self-consistent FFmpeg build or match shared libraries via your package manager.
* **Unicode ellipsis**: Use three ASCII dots (`...`) or avoid ellipsis in scripts.

## Processing Workflow

1. Always save clips to `<year>/clips/` (where `<year>` is the current year).
2. Use `-c:v copy` and `-c:a pcm_s16le -ar 48000` for DaVinci Resolve compatibility.
3. For frame-accurate cuts, use two-stage seeking plus minimal re-encode.
4. PCM audio eliminates the need for additional compatibility fixes.
5. Verify clip length and content before finalizing edits.
6. For maximum compatibility: WAV/PCM > AAC > everything else.

## Technical Notes

* Source files are high-resolution (1080p, 4K) with multiple audio streams.
* Use `-map` to select specific video/audio streams when needed.
* Keep repository scripts up-to-date to avoid manual errors.

