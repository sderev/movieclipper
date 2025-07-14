# Usage Guide

## Basic Usage

### Quick Start

The most common way to use the Movie Clipper:

```bash
# Find and clip a movie by title
uv run clip_movie.py "Iron Man" -s 15:35 -d 12
```

This command:
- Finds "Iron Man" movie using fuzzy matching
- Starts at 15 minutes 35 seconds
- Creates a 12-second clip
- Outputs to your clips directory

### Interactive Mode

For a guided experience:

```bash
# Just provide the movie title
uv run clip_movie.py "Doctor Strange"
```

The script will prompt you for:
- Start time (default: 0)
- Duration (default: 20 seconds)
- Confirmation before processing

## Finding Movies

### Fuzzy Matching

The script uses intelligent fuzzy matching to find movies:

```bash
# All these find the same movie
uv run clip_movie.py "iron man" -s 15:35 -d 12
uv run clip_movie.py "Iron Man" -s 15:35 -d 12
uv run clip_movie.py "ironman" -s 15:35 -d 12
uv run clip_movie.py "iron" -s 15:35 -d 12
```

### Direct File Paths

You can also use direct file paths:

```bash
# Use full path
uv run clip_movie.py "/path/to/movie.mkv" -s 1:16:25 -d 35

# Use relative path
uv run clip_movie.py "movies/action/movie.mkv" -s 1:16:25 -d 35
```

### Multiple Matches

When multiple movies match your search:

```
Multiple movies found for 'Iron Man':
┏━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ #   ┃ Movie                                         ┃ Location ┃ Score  ┃
┡━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│ 1   │ Iron.Man.2008.Multi.VF.1080p.Bluray.x264-BDHD │ .        │ 88%    │
│ 2   │ Iron.Man.2.2010.1080p.BluRay.x264-SECTOR7     │ .        │ 85%    │
└─────┴───────────────────────────────────────────────┴──────────┴────────┘

Select movie (1-2) [1]:
```

Simply type the number and press Enter.

## Time Formats

### Flexible Time Input

The script accepts multiple time formats:

```bash
# Hours:Minutes:Seconds
uv run clip_movie.py "Thor" -s 1:23:45 -d 0:00:30

# Minutes:Seconds
uv run clip_movie.py "Thor" -s 23:45 -d 30

# Pure seconds
uv run clip_movie.py "Thor" -s 1425 -d 30
```

### Time Examples

```bash
# 5 seconds into the movie, 10 second clip
uv run clip_movie.py "Avengers" -s 5 -d 10

# 1 hour 30 minutes in, 45 second clip
uv run clip_movie.py "Avengers" -s 1:30:00 -d 45

# 2 minutes 15 seconds in, 1 minute 30 second clip
uv run clip_movie.py "Avengers" -s 2:15 -d 1:30
```

## Audio Options

### Default Behavior (Recommended)

By default, the script creates DaVinci Resolve-compatible clips:

```bash
# Creates stereo English audio, PCM format
uv run clip_movie.py "Iron Man" -s 15:35 -d 12
```

This gives you:
- English audio (if available)
- Stereo mix (2 channels)
- PCM format for maximum compatibility

### Language Selection

Choose specific audio languages:

```bash
# French audio
uv run clip_movie.py "Iron Man" --audio-lang fre -s 15:35 -d 12

# Chinese audio
uv run clip_movie.py "Hero" --audio-lang chi -s 1:05:15 -d 20

# Spanish audio
uv run clip_movie.py "Coco" --audio-lang spa -s 45:20 -d 25
```

### Audio Mixing Options

```bash
# Force stereo mix (default)
uv run clip_movie.py "Iron Man" --stereo -s 15:35 -d 12

# Keep original surround sound
uv run clip_movie.py "Iron Man" --no-stereo -s 15:35 -d 12

# Keep all audio tracks (8 tracks in DaVinci Resolve)
uv run clip_movie.py "Iron Man" --preserve-audio -s 15:35 -d 12
```

## Testing Mode

Use testing mode to experiment safely:

```bash
# Creates clip in clips_testing/ directory
uv run clip_movie.py "Avengers" --test -s 18:35 -d 15
```

Benefits of testing mode:
- Separate output directory
- Safe experimentation
- No impact on your main clips

## Common Workflows

### Quick Clip Creation

```bash
# Standard workflow
uv run clip_movie.py "Movie Title" -s 1:23:45 -d 30
```

### Batch Processing Different Languages

```bash
# Create multiple versions
uv run clip_movie.py "Spirited Away" --audio-lang jpn -s 25:30 -d 15  # Japanese
uv run clip_movie.py "Spirited Away" --audio-lang eng -s 25:30 -d 15  # English dub
```

### Advanced Audio Control

```bash
# Keep all tracks but mix to stereo (best of both worlds)
uv run clip_movie.py "Interstellar" --preserve-audio --stereo -s 2:15:30 -d 45

# Original behavior (8 tracks in DaVinci - for advanced users)
uv run clip_movie.py "Dunkirk" --preserve-audio --no-stereo -s 1:30:00 -d 60
```

## Output Files

### File Naming Convention

Generated clips follow this pattern:
```
MovieName_StartTime_to_EndTime.mp4
```

Examples:
- `IronMan_01h15m35s_to_01h15m47s.mp4`
- `DoctorStrange_00h30m45s_to_00h31m15s.mp4`
- `Thor_00h59m40s_to_01h00m00s.mp4`

### File Locations

```bash
# Default clips directory
~/your-project/<year>/clips/

# Testing mode
~/your-project/<year>/clips_testing/
```

## Performance Tips

### Movie Index Caching

The script automatically caches movie locations for faster performance:

```bash
# First run builds cache (may take time)
uv run clip_movie.py "Iron Man" -s 15:35 -d 12
# Building movie index cache...
# Found 150 movies in cache

# Subsequent runs use cache (much faster)
uv run clip_movie.py "Thor" -s 1:23:45 -d 30
# Using cached movie index
```

### Cache Management

```bash
# View cache information
uv run clip_movie.py --cache-info

# Clear cache if needed
uv run clip_movie.py --clear-cache
```

## Tips and Tricks

### Finding Movies Efficiently

```bash
# Use distinctive parts of the title
uv run clip_movie.py "strange" -s 30:45 -d 15  # Finds "Doctor Strange"
uv run clip_movie.py "america" -s 48:40 -d 20  # Finds "Captain America"
```

### Time Navigation

```bash
# Use round numbers for easy navigation
uv run clip_movie.py "Movie" -s 1:30:00 -d 30  # Hour and half mark
uv run clip_movie.py "Movie" -s 45:00 -d 15    # 45 minute mark
```

### Quality Checking

```bash
# Create short test clips first
uv run clip_movie.py "Movie" --test -s 1:23:45 -d 5

# Then create the full clip
uv run clip_movie.py "Movie" -s 1:23:45 -d 30
```

## Error Handling

### Common Issues

**Movie not found:**
```bash
# Be more specific
uv run clip_movie.py "Iron Man 2008" -s 15:35 -d 12

# Or use more of the title
uv run clip_movie.py "Iron Man Multi VF" -s 15:35 -d 12
```

**Time format errors:**
```bash
# Make sure time format is correct
uv run clip_movie.py "Movie" -s 1:23:45 -d 30  # Correct
uv run clip_movie.py "Movie" -s 1.23.45 -d 30  # Wrong (uses dots)
```

### Confirmation Steps

The script always asks for confirmation:

```
Creating clip: IronMan_01h15m35s_to_01h15m47s.mp4
From: 01:15:35 to 01:15:47
Duration: 00:00:12
Proceed with clipping? [Y/n]:
```

Type 'Y' or press Enter to proceed.

## Next Steps

- **Audio Details**: Read the [Audio Guide](AUDIO.md) for DaVinci Resolve compatibility
- **Advanced Features**: Explore [Advanced Guide](ADVANCED.md) for power user features
- **Troubleshooting**: Check [Troubleshooting](TROUBLESHOOTING.md) for common issues
- **Full Reference**: See [Reference Guide](REFERENCE.md) for complete options

---

**Previous**: [Installation Guide](INSTALLATION.md) | **Next**: [Audio Guide](AUDIO.md)