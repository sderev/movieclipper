# Audio Guide

## Overview

The Movie Clipper is specifically designed for DaVinci Resolve compatibility, with smart audio handling that solves common editing workflow problems.

## The 8-Track Problem - Solved

### Before: The Problem

Traditional movie clipping resulted in clips that would import into DaVinci Resolve with 8 confusing audio tracks:
- Track 1-2: English stereo
- Track 3-8: Surround sound channels
- All tracks needed to be played simultaneously
- Complex audio setup required for each clip

### After: The Solution

Movie Clipper's smart audio selection gives you clean, usable audio by default:
- **Single stereo track** (2 channels) 
- **English preference** with automatic fallback
- **PCM format** for maximum compatibility
- **Ready to edit** immediately in DaVinci Resolve

## Default Audio Behavior

### Recommended Settings (Default)

```bash
# This creates optimal DaVinci Resolve audio
uv run clip_movie.py "Iron Man" -s 15:35 -d 12
```

**What happens:**
1. **Language Selection**: Automatically selects English audio if available
2. **Stereo Mixing**: Converts surround sound to 2-channel stereo
3. **PCM Conversion**: Uses uncompressed PCM audio at 48kHz
4. **Result**: Clean 2-track audio that "just works"

### Technical Details

- **Codec**: PCM 16-bit signed little-endian (`pcm_s16le`)
- **Sample Rate**: 48kHz (DaVinci Resolve's native rate)
- **Channels**: 2 (stereo mix)
- **Container**: MP4 for broad compatibility

## Audio Stream Detection

### Automatic Detection

The script automatically detects and analyzes audio streams:

```bash
# When you run the script, you'll see:
uv run clip_movie.py "Iron Man" -s 15:35 -d 12
# Selected audio: Stream 0 (eng)
```

### What's Detected

For each audio stream:
- **Language**: English (eng), French (fre), Spanish (spa), etc.
- **Channels**: Stereo, 5.1, 7.1 surround configurations
- **Codec**: Original format (AC3, DTS, AAC, etc.)
- **Sample Rate**: 48kHz, 44.1kHz, etc.

### Fallback Behavior

When language metadata is missing:
- Uses first available audio stream
- Shows "unknown language" in output
- Still processes correctly

## Language Selection

### Supported Languages

Use these language codes with `--audio-lang`:

```bash
# English (default)
uv run clip_movie.py "Movie" --audio-lang eng -s 1:23:45 -d 30

# French
uv run clip_movie.py "Movie" --audio-lang fre -s 1:23:45 -d 30

# Spanish  
uv run clip_movie.py "Movie" --audio-lang spa -s 1:23:45 -d 30

# Chinese
uv run clip_movie.py "Movie" --audio-lang chi -s 1:23:45 -d 30

# German
uv run clip_movie.py "Movie" --audio-lang ger -s 1:23:45 -d 30

# Italian
uv run clip_movie.py "Movie" --audio-lang ita -s 1:23:45 -d 30

# Japanese
uv run clip_movie.py "Movie" --audio-lang jpn -s 1:23:45 -d 30
```

### Language Matching

The script uses intelligent language matching:
- **Exact match**: `eng` matches `eng`
- **Partial match**: `en` matches `eng`
- **Fallback**: If no match, uses first stream

## Audio Options

### Channel Mixing

```bash
# Stereo mix (default - recommended)
uv run clip_movie.py "Movie" --stereo -s 1:23:45 -d 30

# Preserve original channels (5.1, 7.1, etc.)
uv run clip_movie.py "Movie" --no-stereo -s 1:23:45 -d 30
```

### Audio Preservation

```bash
# Smart selection (default)
uv run clip_movie.py "Movie" -s 1:23:45 -d 30

# Keep all original audio tracks
uv run clip_movie.py "Movie" --preserve-audio -s 1:23:45 -d 30
```

## Common Workflows

### Standard DaVinci Resolve Workflow

```bash
# Clean stereo English audio - perfect for DaVinci Resolve
uv run clip_movie.py "Top Gun" -s 1:23:45 -d 30
# → Creates clip with 2 stereo tracks, ready to edit
```

**Result in DaVinci Resolve:**
- Single audio track
- Stereo channels (Left/Right)
- No additional configuration needed

### Multi-Language Content

```bash
# French dub for international content
uv run clip_movie.py "Amélie" --audio-lang fre -s 45:20 -d 25

# Chinese audio with original surround sound
uv run clip_movie.py "Hero" --audio-lang chi --no-stereo -s 1:05:15 -d 20
```

### Advanced Audio Workflows

```bash
# Keep all tracks but mix to stereo (best of both worlds)
uv run clip_movie.py "Interstellar" --preserve-audio --stereo -s 2:15:30 -d 45

# Original behavior (8 tracks in DaVinci - for advanced users)
uv run clip_movie.py "Dunkirk" --preserve-audio --no-stereo -s 1:30:00 -d 60
```

## DaVinci Resolve Compatibility

### Why PCM Audio?

**Universal Compatibility:**
- Works with free and paid DaVinci Resolve versions
- Compatible with all platforms (Windows, macOS, Linux)
- No codec licensing issues

**Performance Benefits:**
- No decoding overhead during editing
- Faster scrubbing and playback
- Better real-time performance

**Quality Advantages:**
- Uncompressed audio preserves original fidelity
- No generation loss from compression
- Perfect for professional workflows

### Comparison: AAC vs PCM

| Feature | AAC | PCM |
|---------|-----|-----|
| File Size | Smaller | Larger |
| Quality | Good | Perfect |
| Compatibility | Issues on Linux | Universal |
| Performance | Decode overhead | Direct playback |
| DaVinci Resolve | Problems | Perfect |

### Import Experience

**With Movie Clipper (PCM):**
1. Drag clip into DaVinci Resolve
2. Audio appears as clean stereo track
3. Ready to edit immediately

**Without Movie Clipper (Original):**
1. Drag clip into DaVinci Resolve  
2. 8 audio tracks appear
3. Manual audio configuration required
4. Potential compatibility issues

## Troubleshooting Audio

### Common Issues

**"Could not detect audio streams"**
```bash
# The script will use default settings and likely still work
# This warning appears when ffprobe can't analyze the file
# Verify your movie file isn't corrupted
```

**"Selected audio: Stream 0 (unknown language)"**
```bash
# The movie file doesn't have language metadata
# Audio selection still works, just without language info
# Use --audio-lang to force a specific stream if needed
```

**DaVinci Resolve still shows multiple audio tracks**
```bash
# Make sure you're NOT using --preserve-audio flag
# Default behavior should give you 2 stereo tracks
uv run clip_movie.py "Movie" -s 1:23:45 -d 30  # Correct
uv run clip_movie.py "Movie" --preserve-audio -s 1:23:45 -d 30  # Wrong
```

**Audio is in wrong language**
```bash
# Use --audio-lang to specify your preferred language
uv run clip_movie.py "Movie" --audio-lang fre -s 1:23:45 -d 30

# Check available languages with --preserve-audio (then re-run without it)
uv run clip_movie.py "Movie" --preserve-audio --test -s 1:23:45 -d 5
```

### Audio Quality Issues

**Audio sounds compressed or distorted**
```bash
# Default PCM audio should be perfect quality
# If issues persist, try --no-stereo for original channels
uv run clip_movie.py "Movie" --no-stereo -s 1:23:45 -d 30
```

**Audio sync issues**
```bash
# This is rare with stream copy - verify source file
# Test with a different timestamp
uv run clip_movie.py "Movie" -s 1:00:00 -d 30
```

## Advanced Audio Features

### Stream Mapping

The script intelligently maps audio streams:

```bash
# For smart selection, maps specific streams:
# -map 0:v:0    (first video stream)
# -map 0:a:X    (selected audio stream)
```

### Audio Processing Pipeline

1. **Stream Detection**: Analyze all audio streams with ffprobe
2. **Language Selection**: Choose best stream based on preference
3. **Channel Processing**: Mix to stereo if requested
4. **Format Conversion**: Convert to PCM for compatibility
5. **Output**: Generate MP4 with optimized audio

### Custom Audio Configuration

Edit `~/.config/movieclipper/clip_movie.toml` for advanced settings:

```toml
[settings]
default_audio_codec = "pcm_s16le"        # PCM format
default_sample_rate = 48000              # 48kHz sample rate
default_audio_channels = 2               # Stereo mix
default_audio_language = "eng"           # English preference
```

## Best Practices

### For DaVinci Resolve Users

1. **Use default settings** for maximum compatibility
2. **Test with short clips** before creating long sequences
3. **Verify audio in DaVinci** before starting major edits
4. **Use testing mode** for experimentation

### For Multi-Language Projects

1. **Create separate clips** for each language
2. **Use consistent naming** with language codes
3. **Test language detection** with sample clips
4. **Document your workflow** for team consistency

### For Professional Workflows

1. **Use PCM audio** for uncompressed quality
2. **Preserve original channels** when needed with `--no-stereo`
3. **Create backup clips** with `--preserve-audio`
4. **Verify compatibility** with your editing software

---

**Previous**: [Usage Guide](USAGE.md) | **Next**: [Advanced Guide](ADVANCED.md)