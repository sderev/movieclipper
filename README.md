# Movie Clipper

A Python script that automates movie clipping with intelligent fuzzy matching. Find movies by partial titles, extract clips with flexible time formats, and get perfectly compatible output for video editing.

## Quick Start

### Prerequisites

- **[uv](https://docs.astral.sh/uv/)** - Python package manager
- **[ffmpeg](https://ffmpeg.org/)** - Video processing tool

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install ffmpeg
sudo apt install ffmpeg
```

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/movie-clipper.git
cd movie-clipper

# First-time setup
uv run clip_movie.py --setup
```

### Basic Usage

```bash
# Create a clip (English stereo)
uv run clip_movie.py "Mickey 17" -s 15:35 -d 12

# Interactive mode
uv run clip_movie.py "A Complete Unknown"

# Testing mode
uv run clip_movie.py "Bleeder" --test -s 1:23:45 -d 30
```

## Key Features

- **Fuzzy Matching**: `"iron man"` finds `Iron.Man.2008.Multi.1080p.Bluray.x264-BDHD.mkv`
- **Smart Audio**: Automatically selects English stereo
- **Flexible Time Input**: `HH:MM:SS`, `MM:SS`, or pure seconds
- **Fast Processing**: Stream copy for lossless, lightning-fast video processing
- **Movie Index Caching**: Dramatically faster startup for large collections
- **DaVinci Resolve Ready**: PCM audio for maximum compatibility

## Common Commands

```bash
# Standard usage
uv run clip_movie.py "Movie Title" -s 1:23:45 -d 30

# Different language
uv run clip_movie.py "Movie Title" --audio-lang fre -s 1:23:45 -d 30

# Cache management
uv run clip_movie.py --cache-info
uv run clip_movie.py --clear-cache
```

## Documentation

**[Documentation Guide](docs/README.md)** - **Start here!** Learn which docs to read and in what order.

### Quick Access
- **[Installation Guide](docs/INSTALLATION.md)** - Complete setup instructions
- **[Usage Guide](docs/USAGE.md)** - Common usage patterns and examples
- **[Audio Guide](docs/AUDIO.md)** - Audio handling and DaVinci Resolve compatibility
- **[Advanced Guide](docs/ADVANCED.md)** - Performance, caching, and power user features
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Reference](docs/REFERENCE.md)** - Complete CLI and configuration reference

### Recommended Reading Order
1. **New users**: Installation → Usage → Audio
2. **Video editors**: Installation → Usage → Audio
3. **Power users**: Installation → Advanced → Reference

## Quick Examples

### Finding Movies
```bash
# All these work with fuzzy matching
uv run clip_movie.py "iron man" -s 15:35 -d 12
uv run clip_movie.py "Iron Man" -s 15:35 -d 12
uv run clip_movie.py "ironman" -s 15:35 -d 12
```

### Time Formats
```bash
uv run clip_movie.py "Skyfall" -s 1:23:45 -d 30    # HH:MM:SS
uv run clip_movie.py "Skyfall" -s 23:45 -d 30      # MM:SS
uv run clip_movie.py "Skyfall" -s 1425 -d 30       # Seconds
```

### Audio Options
```bash
# Default: English stereo (recommended)
uv run clip_movie.py "Movie" -s 1:23:45 -d 30

# Specific language
uv run clip_movie.py "Movie" --audio-lang fre -s 1:23:45 -d 30

# Keep all audio tracks
uv run clip_movie.py "Movie" --preserve-audio -s 1:23:45 -d 30
```

## Performance

The script includes intelligent caching that makes it extremely fast:
- **First run**: Builds index of your movie collection
- **Subsequent runs**: Instant movie discovery
- **Large collections**: Handles thousands of movies efficiently

## Configuration

Settings are stored in `~/.config/movieclipper/clip_movie.toml`:
```toml
[directories]
movies_dir = "/path/to/your/movies"
clips_dir = "/path/to/your/clips"

[settings]
default_audio_language = "eng"
cache_enabled = true
cache_ttl_hours = 24
```

## Requirements

- **Python 3.9+** (managed by uv)
- **FFmpeg** (video processing)
- **Operating System**: Linux, macOS, or Windows

## Support

- **Issues**: [GitHub Issues](https://github.com/sderev/movie-clipper/issues)
- **Documentation**: Check the [docs/](docs/) directory
- **Troubleshooting**: See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
