# Installation Guide

## Prerequisites

Before installing the Movie Clipper, ensure you have the following installed:

### Required Software

#### 1. uv (Python Package Manager)
```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 2. FFmpeg (Video Processing)
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
# Or use chocolatey: choco install ffmpeg
```

### System Requirements

- **Python 3.9+** (automatically managed by uv)
- **Operating System**: Linux, macOS, or Windows
- **Storage**: At least 100MB free space for clips directory
- **RAM**: 4GB minimum (8GB recommended for large movie collections)

## Installation

### Option 1: Clone from Repository

```bash
# Clone the repository
git clone https://github.com/yourusername/movie-clipper.git
cd movie-clipper

# Verify installation
uv run clip_movie.py --help
```

### Option 2: Download Script Only

```bash
# Download the main script
curl -O https://raw.githubusercontent.com/yourusername/movie-clipper/main/clip_movie.py

# Make it executable
chmod +x clip_movie.py

# Test installation
uv run clip_movie.py --help
```

## First-Time Setup

### 1. Run Setup Wizard

```bash
# Interactive configuration setup
uv run clip_movie.py --setup
```

The setup wizard will ask you to configure:
- **Movies directory**: Where your movie files are stored
- **Clips directory**: Where generated clips will be saved

### 2. Verify Setup

```bash
# Check your configuration
cat ~/.config/movieclipper/clip_movie.toml

# Test with a sample movie
uv run clip_movie.py "test movie" --help
```

## Directory Structure

After installation, your project should look like this:

```
movie-clipper/
├── clip_movie.py           # Main script
├── docs/                   # Documentation (optional)
└── your-movies/            # Your configured movies directory
    ├── movie1.mkv
    ├── Movie Folder/
    │   └── movie2.mkv
    └── clips/              # Generated clips directory
        └── YourClip.mp4
```

## Configuration

### Basic Configuration

The setup wizard creates a `~/.config/movieclipper/clip_movie.toml` file with your settings:

```toml
[directories]
movies_dir = "/path/to/your/movies"
clips_dir = "/path/to/your/clips"

[settings]
default_audio_codec = "pcm_s16le"
default_sample_rate = 48000
default_audio_channels = 2
default_audio_language = "eng"
preserve_all_audio = false
preview_by_default = false
follow_symlinks = true
video_extensions = [".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm"]
# Cache settings
cache_enabled = true
cache_ttl_hours = 24
cache_location = null
```

### Advanced Configuration

For advanced users, you can manually edit the configuration:

```bash
# Edit configuration file
nano ~/.config/movieclipper/clip_movie.toml

# Reconfigure interactively
uv run clip_movie.py --setup
```

## Verification

### Test Basic Functionality

```bash
# Test with a real movie file
uv run clip_movie.py "your movie title" --test -s 1:00:00 -d 10

# This should create a 10-second clip in clips_testing/
```

### Test Cache System

```bash
# Check cache information
uv run clip_movie.py --cache-info

# Clear cache if needed
uv run clip_movie.py --clear-cache
```

## Common Setup Issues

### FFmpeg Not Found

```bash
# Check if FFmpeg is installed
ffmpeg -version
ffprobe -version

# If not found, install using your package manager
# See "Required Software" section above
```

### Permission Errors

```bash
# Ensure directories are writable
chmod 755 /path/to/your/movies
chmod 755 /path/to/your/clips

# Check directory ownership
ls -la /path/to/your/movies
```

### Movies Not Found

```bash
# Verify movies directory exists
ls -la /path/to/your/movies

# Check configuration
cat ~/.config/movieclipper/clip_movie.toml

# Reconfigure if needed
uv run clip_movie.py --setup
```

## External Storage Setup

If your movies are on external drives or network storage:

### External Drive

```bash
# Create symlink to external drive
ln -s /media/external/Movies ~/clips/download/ExternalMovies

# Verify symlink
ls -la ~/clips/download/ExternalMovies
```

### Network Storage (NAS)

```bash
# Mount NAS
sudo mount -t cifs //nas.local/Movies /mnt/nas -o username=your_username

# Create symlink
ln -s /mnt/nas ~/clips/download/NASMovies
```

## Next Steps

After successful installation:

1. **Read the [Usage Guide](USAGE.md)** for common usage patterns
2. **Review [Audio Guide](AUDIO.md)** for DaVinci Resolve compatibility
3. **Check [Troubleshooting](TROUBLESHOOTING.md)** for common issues
4. **Explore [Advanced Features](ADVANCED.md)** for power user features

## Getting Help

If you encounter issues during installation:

1. Check the [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Verify all prerequisites are installed
3. Run `uv run clip_movie.py --help` for available options
4. Check the [GitHub Issues](https://github.com/yourusername/movie-clipper/issues) for known problems

---

**Next**: [Usage Guide](USAGE.md) - Learn how to use the Movie Clipper effectively