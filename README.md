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
git clone https://github.com/sderev/movie-clipper.git
cd movie-clipper

# Add `movieclipper` to your PATH
echo 'export PATH="$PATH:$(pwd)/bin"' >> ~/.bashrc # or ~/.zshrc
source ~/.bashrc # or ~/.zshrc
# Or use your usual method to add to PATH

# First-time setup
movieclipper --setup
```

### Basic Usage

```bash
# Create a clip (English stereo)
movieclipper "Mickey 17" -s 15:35 -d 12

# Interactive mode
movieclipper "A Complete Unknown"

# Testing mode
movieclipper "Bleeder" --test -s 1:23:45 -d 30
```

## Key Features

- **Fuzzy Matching**: `"steve zissou"` finds `The.Life.Aquatic.with.Steve.Zissou.2004.Multi.1080p.Bluray.x264-BDHD.mkv`
- **Smart Audio**: Automatically selects English stereo
- **Flexible Time Input**: `HH:MM:SS`, `MM:SS`, or pure seconds
- **Fast Processing**: Stream copy for lossless, lightning-fast video processing
- **Movie Index Caching**: Dramatically faster startup for large collections
- **DaVinci Resolve Ready**: PCM audio for maximum compatibility

## Common Commands

```bash
# Standard usage
movieclipper "Movie Title" -s 1:23:45 -d 30

# Different language
movieclipper "Movie Title" --audio-lang fre -s 1:23:45 -d 30

# Cache management
movieclipper --cache-info
movieclipper --clear-cache
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
movieclipper "steve zissou" -s 15:35 -d 12
movieclipper "Steve Zissou" -s 15:35 -d 12
movieclipper "stevezissou" -s 15:35 -d 12
```

### Time Formats
```bash
movieclipper "Skyfall" -s 1:23:45 -d 30    # HH:MM:SS
movieclipper "Skyfall" -s 23:45 -d 30      # MM:SS
movieclipper "Skyfall" -s 1425 -d 30       # Seconds
```

### Audio Options
```bash
# Default: English stereo (recommended)
movieclipper "Movie" -s 1:23:45 -d 30

# Specific language
movieclipper "Movie" --audio-lang fre -s 1:23:45 -d 30

# Keep all audio tracks
movieclipper "Movie" --preserve-audio -s 1:23:45 -d 30
```

## Performance

The script includes intelligent caching that makes it extremely fast:
- **First run**: Builds index of your movie collection
- **Subsequent runs**: Instant movie discovery
- **Large collections**: Handles thousands of movies efficiently

## Configuration

Settings are stored in `~/.config/movieclipper/movieclipper.toml`:
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
