# Troubleshooting Guide

## Installation Issues

### FFmpeg Not Found

**Error:** `ffmpeg is not installed or not in PATH`

**Solutions:**
```bash
# Check if FFmpeg is installed
ffmpeg -version
ffprobe -version

# Install FFmpeg
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# Windows (Winget)
winget install FFmpeg

# Windows (Manual)
# Download from https://ffmpeg.org/download.html
# Add to PATH environment variable
```

### Python/UV Issues

**Error:** `uv: command not found`

**Solutions:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Reload shell
source ~/.bashrc  # or ~/.zshrc
```

**Error:** `Python version incompatible`

**Solutions:**
```bash
# Check Python version
python --version

# UV automatically manages Python versions
# Script requires Python 3.9+
uv run clip_movie.py --help
```

## Configuration Issues

### Directory Errors

**Error:** `Directory does not exist`

**Solutions:**
```bash
# Reconfigure directories
uv run clip_movie.py --setup

# Manually check directory
ls -la /path/to/your/movies

# Create missing directory
mkdir -p /path/to/your/movies
```

**Error:** `Permission denied`

**Solutions:**
```bash
# Fix directory permissions
chmod 755 /path/to/your/movies
chmod 755 /path/to/your/clips

# Check ownership
ls -la /path/to/your/movies
chown user:group /path/to/your/movies
```

### Configuration File Issues

**Error:** `Error loading config`

**Solutions:**
```bash
# Reset configuration
rm ~/.config/movieclipper/clip_movie.toml
uv run clip_movie.py --setup

# Check file permissions
ls -la ~/.config/movieclipper/clip_movie.toml
chmod 644 ~/.config/movieclipper/clip_movie.toml
```

## Movie Discovery Issues

### No Movies Found

**Error:** `No movie files found in the movies directory!`

**Solutions:**
```bash
# Check movies directory
ls -la /path/to/your/movies

# Verify file extensions
# Supported: .mkv, .mp4, .avi, .mov, .wmv, .flv, .webm

# Check subdirectories
find /path/to/your/movies -name "*.mkv" -o -name "*.mp4"

# Reconfigure movies directory
uv run clip_movie.py --setup
```

### Movie Not Found

**Error:** `No movies found matching 'query'`

**Solutions:**
```bash
# Use more specific search terms
uv run clip_movie.py "Iron Man 2008" -s 15:35 -d 12

# Use partial matching
uv run clip_movie.py "iron" -s 15:35 -d 12

# Check available movies
ls /path/to/your/movies

# Clear cache if movies were recently added
uv run clip_movie.py --clear-cache
```

### Symlink Issues

**Error:** Movies in symlinked directories not found

**Solutions:**
```bash
# Check symlink configuration
cat ~/.config/movieclipper/clip_movie.toml
# Should show: follow_symlinks = true

# Verify symlinks
ls -la /path/to/your/movies
# Look for -> symbols indicating symlinks

# Test symlink
ls -la /path/to/symlinked/directory

# Fix broken symlinks
find /path/to/your/movies -xtype l -delete
```

## Audio Issues

### Audio Stream Detection

**Warning:** `Could not detect audio streams`

**Solutions:**
```bash
# This is usually not fatal - script will use defaults
# Check if output clip has audio

# Verify source file
ffprobe -i "path/to/movie.mkv"

# Test with different movie
uv run clip_movie.py "different movie" -s 1:00:00 -d 10
```

### Wrong Audio Language

**Issue:** Audio is in wrong language

**Solutions:**
```bash
# Specify language explicitly
uv run clip_movie.py "Movie" --audio-lang eng -s 1:23:45 -d 30

# Common language codes
# eng = English, fre = French, spa = Spanish, ger = German

# Check available languages
ffprobe -i "path/to/movie.mkv" 2>&1 | grep "Audio"

# Use preserve-audio to see all streams
uv run clip_movie.py "Movie" --preserve-audio --test -s 1:23:45 -d 5
```

### DaVinci Resolve Audio Issues

**Issue:** Multiple audio tracks in DaVinci Resolve

**Solutions:**
```bash
# Make sure NOT using --preserve-audio
uv run clip_movie.py "Movie" -s 1:23:45 -d 30  # Correct

# Force stereo explicitly
uv run clip_movie.py "Movie" --stereo -s 1:23:45 -d 30

# Check output file
ffprobe -i "output_clip.mp4" 2>&1 | grep "Audio"
```

**Issue:** Audio sync problems

**Solutions:**
```bash
# Try different timestamp
uv run clip_movie.py "Movie" -s 1:00:00 -d 30

# Use --no-stereo for original channels
uv run clip_movie.py "Movie" --no-stereo -s 1:23:45 -d 30

# Check source file integrity
ffmpeg -v error -i "source.mkv" -f null -
```

## Performance Issues

### Slow Startup

**Issue:** Script takes long time to start

**Solutions:**
```bash
# Check cache status
uv run clip_movie.py --cache-info

# Cache might be building - wait for completion
# First run with large movie collection is slow

# Check disk space
df -h ~/.cache/movie_clipper/

# Clear cache if corrupted
uv run clip_movie.py --clear-cache
```

### Cache Issues

**Issue:** Cache not working properly

**Solutions:**
```bash
# View cache information
uv run clip_movie.py --cache-info

# Clear and rebuild cache
uv run clip_movie.py --clear-cache

# Disable cache temporarily
# Edit ~/.config/movieclipper/clip_movie.toml: cache_enabled = false

# Check cache directory permissions
ls -la ~/.cache/movie_clipper/
chmod 755 ~/.cache/movie_clipper/
```

**Issue:** Movies not found after adding new files

**Solutions:**
```bash
# Cache might be stale
uv run clip_movie.py --clear-cache

# Check cache TTL setting
cat ~/.config/movieclipper/clip_movie.toml
# Default: cache_ttl_hours = 24

# Force cache rebuild
uv run clip_movie.py --clear-cache
uv run clip_movie.py "new movie" -s 1:00:00 -d 10
```

## FFmpeg Issues

### Processing Errors

**Error:** `FFmpeg error: [specific error message]`

**Solutions:**
```bash
# Check input file
ffmpeg -i "path/to/movie.mkv"

# Test with different timestamp
uv run clip_movie.py "Movie" -s 0:30:00 -d 10

# Try testing mode first
uv run clip_movie.py "Movie" --test -s 1:23:45 -d 5

# Check disk space
df -h /path/to/clips/
```

### Time Format Errors

**Error:** `Invalid time format`

**Solutions:**
```bash
# Use correct time formats
uv run clip_movie.py "Movie" -s 1:23:45 -d 30      # HH:MM:SS
uv run clip_movie.py "Movie" -s 23:45 -d 30        # MM:SS
uv run clip_movie.py "Movie" -s 1425 -d 30         # Seconds

# Common mistakes to avoid
# Wrong: 1.23.45 (uses dots)
# Wrong: 1:23:45.5 (includes milliseconds)
# Wrong: 83:45 (minutes > 59)
```

### Output File Issues

**Error:** Output file not created

**Solutions:**
```bash
# Check output directory permissions
ls -la /path/to/clips/
chmod 755 /path/to/clips/

# Check disk space
df -h /path/to/clips/

# Try testing mode
uv run clip_movie.py "Movie" --test -s 1:23:45 -d 30

# Check for existing file
ls -la /path/to/clips/MovieName_*
```

## Network and Storage Issues

### External Drive Issues

**Issue:** Movies on external drive not found

**Solutions:**
```bash
# Check if drive is mounted
df -h
mount | grep /media

# Verify symlink
ls -la /path/to/movies/ExternalMovies
# Should show -> /media/external/Movies

# Remount drive
sudo umount /media/external
sudo mount /dev/sdb1 /media/external

# Recreate symlink
ln -s /media/external/Movies /path/to/movies/ExternalMovies
```

### NAS/Network Storage Issues

**Issue:** Network storage not accessible

**Solutions:**
```bash
# Check NAS mount
mount | grep cifs
df -h /mnt/nas

# Remount NAS
sudo umount /mnt/nas
sudo mount -t cifs //nas.local/Movies /mnt/nas -o username=user

# Check network connectivity
ping nas.local

# Test symlink
ls -la /path/to/movies/NASMovies
```

## Advanced Troubleshooting

### Debug Mode

```bash
# Enable verbose output
export MOVIE_CLIPPER_VERBOSE=1
uv run clip_movie.py "Movie" -s 1:23:45 -d 30

# Check FFmpeg command
# Script shows exact command before execution
```

### Log Analysis

```bash
# Check system logs
journalctl -u mount  # For mount issues
dmesg | grep -i error  # For hardware issues

# Monitor disk usage
watch df -h /path/to/clips/

# Monitor I/O
iotop -a
```

### Test Methodology

```bash
# 1. Test with simple case
uv run clip_movie.py "Movie" --test -s 1:00:00 -d 5

# 2. Check output
ls -la clips_testing/
ffprobe -i clips_testing/output.mp4

# 3. Test in DaVinci Resolve
# Import clip and verify audio/video

# 4. Scale up to full workflow
uv run clip_movie.py "Movie" -s 1:23:45 -d 30
```

## Getting Help

### Before Asking for Help

1. **Check this troubleshooting guide** first
2. **Test with a simple case** (short clip, common movie)
3. **Check logs and error messages** carefully
4. **Try clearing cache** if movie-related issues
5. **Verify FFmpeg installation** and accessibility

### Information to Include

When seeking help, include:
- **Error message** (exact text)
- **Command used** (what you ran)
- **Operating system** and version
- **FFmpeg version** (`ffmpeg -version`)
- **Python version** (`python --version`)
- **File information** (movie file format, size)
- **Configuration** (`cat ~/.config/movieclipper/clip_movie.toml`)

### Community Resources

- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Check other guides for related topics
- **Stack Overflow**: Search for FFmpeg-related issues
- **Reddit**: r/ffmpeg, r/davinci_resolve communities

## Emergency Procedures

### Complete Reset

```bash
# 1. Stop all processes
killall ffmpeg

# 2. Clear cache
uv run clip_movie.py --clear-cache

# 3. Reset configuration
rm ~/.config/movieclipper/clip_movie.toml
uv run clip_movie.py --setup

# 4. Test basic functionality
uv run clip_movie.py "test movie" --test -s 1:00:00 -d 5
```

### Recover from Corruption

```bash
# 1. Check file system
fsck /dev/sda1  # Adjust device as needed

# 2. Clear all caches
rm -rf ~/.cache/movie_clipper/
uv run clip_movie.py --clear-cache

# 3. Verify movie files
find /path/to/movies -name "*.mkv" -exec ffprobe {} \;

# 4. Rebuild from scratch
uv run clip_movie.py --setup
```

---

**Previous**: [Advanced Guide](ADVANCED.md) | **Next**: [Reference Guide](REFERENCE.md)