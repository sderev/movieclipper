# Advanced Guide

## Performance Optimization

### Movie Index Caching

The Movie Clipper includes a sophisticated caching system that dramatically improves performance for large movie collections.

#### How Caching Works

**First Run:**
```bash
uv run clip_movie.py "Iron Man" -s 15:35 -d 12
# Building movie index cache...
# Found 150 movies in cache
```

**Subsequent Runs:**
```bash
uv run clip_movie.py "Thor" -s 1:23:45 -d 30
# Using cached movie index
```

#### Cache Benefits

- **Faster Startup**: Avoids rescanning directories on every run
- **Reduced I/O**: Caches movie file locations and metadata
- **Large Collections**: Scales efficiently with thousands of movies
- **Smart Invalidation**: Automatically rebuilds when needed

### Cache Management

#### View Cache Information

```bash
uv run clip_movie.py --cache-info
```

**Sample Output:**
```
Cache Information:
  Path: /home/user/.cache/movie_clipper/movie_index.json
  Movies: 1,247
  Age: 3.2 hours
  Size: 142.3 KB
  Movies Directory: /home/user/movies
```

#### Clear Cache

```bash
# Clear cache manually
uv run clip_movie.py --clear-cache
# Movie index cache cleared

# Next run will rebuild cache
uv run clip_movie.py "Movie" -s 1:23:45 -d 30
# Building movie index cache...
```

#### Cache Configuration

```toml
[settings]
cache_enabled = true                     # Enable caching (default: true)
cache_ttl_hours = 24                     # Cache expires after 24 hours
cache_location = null                    # Custom cache location (optional)
```

**Custom Cache Location:**
```toml
[settings]
cache_location = "/custom/cache/path"    # Custom location
```

### Automatic Cache Invalidation

The cache automatically rebuilds when:
- Cache age exceeds TTL (default: 24 hours)
- Movies directory is modified
- Cache file is corrupted or missing
- Movies directory path changes

## Directory Management

### Symlink Support

The Movie Clipper supports directory symlinks for accessing movies stored in multiple locations.

#### Basic Symlink Usage

```bash
# Link to external drive
ln -s /media/external/Movies ~/projects/movie-clipper/2025/download/ExternalMovies

# Link to NAS storage
ln -s /mnt/nas/MovieCollection ~/projects/movie-clipper/2025/download/NASMovies

# Link to different genres
ln -s /storage/Action ~/projects/movie-clipper/2025/download/Action
ln -s /storage/Comedy ~/projects/movie-clipper/2025/download/Comedy
```

#### Symlink Configuration

```toml
[settings]
follow_symlinks = true    # Follow directory symlinks (default)
# follow_symlinks = false # Skip symlinked directories
```

**When to Enable Symlinks:**
- Movies on external drives
- NAS or network storage
- Multiple storage locations
- Backup drives

**When to Disable Symlinks:**
- Only local movies
- Security concerns
- Troubleshooting directory issues
- Performance optimization

### Advanced Directory Patterns

#### Multi-Location Setup

```bash
# Create organized symlink structure
mkdir -p ~/movies/download/{local,external,nas,genres}

# Link different storage types
ln -s /home/user/Videos ~/movies/download/local
ln -s /media/usb/Movies ~/movies/download/external
ln -s /mnt/nas/Films ~/movies/download/nas

# Genre-based organization
ln -s /storage/ssd/Action ~/movies/download/genres/action
ln -s /storage/hdd/Comedy ~/movies/download/genres/comedy
```

#### Performance Considerations

- **Local storage**: Fastest access
- **External drives**: Good for large collections
- **Network storage**: Slower but centralized
- **Mixed setup**: Balance performance and capacity

## Configuration Management

### Advanced Configuration

#### Complete Configuration Reference

```toml
[directories]
movies_dir = "/path/to/movies"
clips_dir = "/path/to/clips"

[settings]
# Audio settings
default_audio_codec = "pcm_s16le"
default_sample_rate = 48000
default_audio_channels = 2
default_audio_language = "eng"
preserve_all_audio = false

# File handling
preview_by_default = false
follow_symlinks = true
video_extensions = [".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm"]

# Cache settings
cache_enabled = true
cache_ttl_hours = 24
cache_location = null
```

#### Environment Variables

The script respects these environment variables:

```bash
# Override cache location
export MOVIE_CLIPPER_CACHE_DIR="/tmp/movie_cache"

# Disable cache temporarily
export MOVIE_CLIPPER_CACHE_ENABLED="false"

# Set default movies directory
export MOVIE_CLIPPER_MOVIES_DIR="/movies"
```

### Configuration Validation

#### Automatic Validation

The script validates configuration on startup:
- Directory existence and permissions
- Audio codec compatibility
- Cache location accessibility
- File extension validity

#### Manual Validation

```bash
# Reconfigure interactively
uv run clip_movie.py --setup

# Test configuration
uv run clip_movie.py --help
```

## FFmpeg Integration

### Command Generation

The script generates optimized FFmpeg commands:

```bash
# Basic command structure
ffmpeg -y -ss 01:15:35 -i input.mkv -t 00:00:12 -c:v copy -map 0:v:0 -map 0:a:1 -ac 2 -c:a pcm_s16le -ar 48000 output.mp4
```

**Command Breakdown:**
- `-y`: Overwrite output files
- `-ss 01:15:35`: Fast seek to start time
- `-i input.mkv`: Input file
- `-t 00:00:12`: Duration
- `-c:v copy`: Stream copy video (no re-encoding)
- `-map 0:v:0`: Map first video stream
- `-map 0:a:1`: Map selected audio stream
- `-ac 2`: Force stereo output
- `-c:a pcm_s16le`: PCM audio codec
- `-ar 48000`: 48kHz sample rate

### Performance Optimizations

#### Fast Seeking

```bash
# Places -ss before -i for keyframe seeking
-ss 01:15:35 -i input.mkv
```

**Benefits:**
- Faster startup time
- Reduced memory usage
- Efficient for large files

#### Stream Copy

```bash
# Copies video without re-encoding
-c:v copy
```

**Benefits:**
- Lightning fast processing
- No quality loss
- Minimal CPU usage

### Error Handling

The script handles various FFmpeg errors:
- **File not found**: Clear error message with suggestions
- **Invalid timestamps**: Time format validation
- **Codec issues**: Fallback to compatible codecs
- **Permissions**: Directory access validation

## Batch Processing

### Multiple Clips from Same Movie

```bash
# Create multiple clips efficiently
uv run clip_movie.py "Iron Man" -s 15:35 -d 12
uv run clip_movie.py "Iron Man" -s 45:20 -d 8
uv run clip_movie.py "Iron Man" -s 1:23:45 -d 25
```

### Scripted Workflows

```bash
#!/bin/bash
# Batch processing script

MOVIE="Iron Man"
CLIPS=(
    "15:35 12"
    "45:20 8"
    "1:23:45 25"
)

for clip in "${CLIPS[@]}"; do
    read -r start duration <<< "$clip"
    uv run clip_movie.py "$MOVIE" -s "$start" -d "$duration"
done
```

### Testing Workflows

```bash
# Test all clips first
for clip in "${CLIPS[@]}"; do
    read -r start duration <<< "$clip"
    uv run clip_movie.py "$MOVIE" --test -s "$start" -d "$duration"
done

# Then create final clips
# (repeat without --test flag)
```

## Debugging and Development

### Verbose Output

```bash
# Enable verbose ffmpeg output
MOVIE_CLIPPER_VERBOSE=1 uv run clip_movie.py "Movie" -s 1:23:45 -d 30
```

### Testing Mode

```bash
# Use testing directory for safe experimentation
uv run clip_movie.py "Movie" --test -s 1:23:45 -d 30
```

**Testing Benefits:**
- Separate output directory
- Safe experimentation
- No impact on main clips
- Easy cleanup

### Development Tools

#### Cache Debugging

```bash
# View cache details
uv run clip_movie.py --cache-info

# Clear cache for fresh start
uv run clip_movie.py --clear-cache

# Disable cache for debugging
# Edit clip_movie.toml: cache_enabled = false
```

#### Configuration Debugging

```bash
# View current configuration
cat clip_movie.toml

# Reset configuration
rm clip_movie.toml
uv run clip_movie.py --setup
```

## Advanced Workflows

### Professional Video Editing

```bash
# Create clips with different audio configurations
uv run clip_movie.py "Movie" --audio-lang eng -s 1:23:45 -d 30  # English
uv run clip_movie.py "Movie" --audio-lang fre -s 1:23:45 -d 30  # French
uv run clip_movie.py "Movie" --preserve-audio -s 1:23:45 -d 30  # All tracks
```

### Multi-Language Projects

```bash
# Create language-specific clips
LANGUAGES=("eng" "fre" "spa" "ger")
for lang in "${LANGUAGES[@]}"; do
    uv run clip_movie.py "Movie" --audio-lang "$lang" -s 1:23:45 -d 30
done
```

### Quality Assurance

```bash
# Create test clips first
uv run clip_movie.py "Movie" --test -s 1:23:45 -d 5

# Verify in DaVinci Resolve
# Then create full clips
uv run clip_movie.py "Movie" -s 1:23:45 -d 30
```

## Security and Permissions

### File Permissions

```bash
# Ensure proper permissions
chmod 755 /path/to/movies
chmod 755 /path/to/clips
```

### Network Storage Security

```bash
# Secure NAS mounting
sudo mount -t cifs //nas.local/Movies /mnt/nas -o username=user,uid=1000,gid=1000
```

### Cache Security

```bash
# Restrict cache directory permissions
chmod 700 ~/.cache/movie_clipper
```

## Troubleshooting Advanced Issues

### Cache Corruption

```bash
# Clear corrupted cache
uv run clip_movie.py --clear-cache

# Disable cache temporarily
# Edit clip_movie.toml: cache_enabled = false
```

### Symlink Issues

```bash
# Check broken symlinks
find ~/movies -xtype l

# Remove broken symlinks
find ~/movies -xtype l -delete
```

### Performance Issues

```bash
# Disable cache for debugging
# Edit clip_movie.toml: cache_enabled = false

# Check disk space
df -h /path/to/clips

# Monitor I/O
iotop -a
```

---

**Previous**: [Audio Guide](AUDIO.md) | **Next**: [Troubleshooting Guide](TROUBLESHOOTING.md)