# Reference Guide

## Command Line Interface

### Basic Syntax

```bash
uv run clip_movie.py [OPTIONS] [MOVIE_INPUT]
```

### Arguments

#### MOVIE_INPUT
- **Type**: String (optional)
- **Description**: Movie title for fuzzy matching or direct file path
- **Examples**:
  - `"Iron Man"` - Fuzzy match by title
  - `"iron man"` - Case insensitive
  - `"/path/to/movie.mkv"` - Direct file path
  - `"movies/action/movie.mkv"` - Relative path

### Options

#### Time Options

##### --start, -s
- **Type**: String
- **Description**: Start time for clip extraction
- **Formats**:
  - `HH:MM:SS` - Hours:Minutes:Seconds (e.g., `1:23:45`)
  - `MM:SS` - Minutes:Seconds (e.g., `23:45`)
  - `SECONDS` - Pure seconds (e.g., `1425`)
- **Examples**:
  ```bash
  uv run clip_movie.py "Movie" -s 1:23:45 -d 30
  uv run clip_movie.py "Movie" -s 23:45 -d 30
  uv run clip_movie.py "Movie" -s 1425 -d 30
  ```

##### --duration, -d
- **Type**: String
- **Description**: Duration of clip to extract
- **Formats**: Same as `--start`
- **Examples**:
  ```bash
  uv run clip_movie.py "Movie" -s 1:23:45 -d 0:00:30
  uv run clip_movie.py "Movie" -s 1:23:45 -d 30
  ```

#### Audio Options

##### --preserve-audio
- **Type**: Flag
- **Description**: Keep all original audio tracks (lossless mode)
- **Default**: False (smart audio selection)
- **Examples**:
  ```bash
  uv run clip_movie.py "Movie" --preserve-audio -s 1:23:45 -d 30
  ```

##### --audio-lang
- **Type**: String
- **Description**: Select specific audio language
- **Common Values**:
  - `eng` - English
  - `fre` - French
  - `spa` - Spanish
  - `chi` - Chinese
  - `ger` - German
  - `ita` - Italian
  - `jpn` - Japanese
  - `kor` - Korean
  - `rus` - Russian
- **Examples**:
  ```bash
  uv run clip_movie.py "Movie" --audio-lang fre -s 1:23:45 -d 30
  uv run clip_movie.py "Movie" --audio-lang chi -s 1:23:45 -d 30
  ```

##### --stereo/--no-stereo
- **Type**: Boolean flag
- **Description**: Force stereo mix or preserve original channels
- **Default**: `--stereo` (mix to stereo)
- **Examples**:
  ```bash
  uv run clip_movie.py "Movie" --stereo -s 1:23:45 -d 30      # Force stereo
  uv run clip_movie.py "Movie" --no-stereo -s 1:23:45 -d 30   # Keep original channels
  ```

#### Operational Options

##### --test
- **Type**: Flag
- **Description**: Use clips_testing directory for output
- **Default**: False (use clips directory)
- **Examples**:
  ```bash
  uv run clip_movie.py "Movie" --test -s 1:23:45 -d 30
  ```

##### --setup
- **Type**: Flag
- **Description**: Run interactive configuration setup
- **Examples**:
  ```bash
  uv run clip_movie.py --setup
  ```

#### Cache Options

##### --clear-cache
- **Type**: Flag
- **Description**: Clear movie index cache
- **Examples**:
  ```bash
  uv run clip_movie.py --clear-cache
  ```

##### --cache-info
- **Type**: Flag
- **Description**: Show cache information
- **Examples**:
  ```bash
  uv run clip_movie.py --cache-info
  ```

#### Help Option

##### --help
- **Type**: Flag
- **Description**: Show help message and exit
- **Examples**:
  ```bash
  uv run clip_movie.py --help
  ```

## Configuration File Reference

### File Location

- **Default**: `clip_movie.toml` in script directory
- **Format**: TOML (Tom's Obvious, Minimal Language)

### Configuration Structure

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

# General settings
preview_by_default = false
follow_symlinks = true
video_extensions = [".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm"]

# Cache settings
cache_enabled = true
cache_ttl_hours = 24
cache_location = null
```

### Configuration Options

#### [directories]

##### movies_dir
- **Type**: String (path)
- **Description**: Directory containing movie files
- **Required**: Yes
- **Example**: `"/home/user/movies"`

##### clips_dir
- **Type**: String (path)
- **Description**: Directory for output clips
- **Required**: Yes
- **Example**: `"/home/user/clips"`

#### [settings]

##### default_audio_codec
- **Type**: String
- **Description**: Default audio codec for output
- **Default**: `"pcm_s16le"`
- **Options**: `"pcm_s16le"`, `"aac"`, `"mp3"`
- **Recommended**: `"pcm_s16le"` for DaVinci Resolve

##### default_sample_rate
- **Type**: Integer
- **Description**: Audio sample rate in Hz
- **Default**: `48000`
- **Options**: `44100`, `48000`, `96000`
- **Recommended**: `48000` for DaVinci Resolve

##### default_audio_channels
- **Type**: Integer
- **Description**: Number of audio channels for stereo mix
- **Default**: `2`
- **Options**: `1` (mono), `2` (stereo)

##### default_audio_language
- **Type**: String
- **Description**: Preferred audio language
- **Default**: `"eng"`
- **Examples**: `"eng"`, `"fre"`, `"spa"`, `"chi"`

##### preserve_all_audio
- **Type**: Boolean
- **Description**: Keep all audio tracks by default
- **Default**: `false`
- **Options**: `true`, `false`

##### preview_by_default
- **Type**: Boolean
- **Description**: Enable preview mode by default
- **Default**: `false`
- **Options**: `true`, `false`

##### follow_symlinks
- **Type**: Boolean
- **Description**: Follow directory symlinks when searching
- **Default**: `true`
- **Options**: `true`, `false`

##### video_extensions
- **Type**: Array of strings
- **Description**: Supported video file extensions
- **Default**: `[".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm"]`
- **Customizable**: Yes

##### cache_enabled
- **Type**: Boolean
- **Description**: Enable movie index caching
- **Default**: `true`
- **Options**: `true`, `false`

##### cache_ttl_hours
- **Type**: Integer
- **Description**: Cache time-to-live in hours
- **Default**: `24`
- **Range**: `1` to `8760` (1 year)

##### cache_location
- **Type**: String (path) or null
- **Description**: Custom cache directory
- **Default**: `null` (uses `~/.cache/movie_clipper/`)
- **Example**: `"/tmp/movie_cache"`

## Output File Reference

### File Naming Convention

Generated clips follow this pattern:
```
{MovieName}_{StartTime}_to_{EndTime}.mp4
```

#### Components

- **MovieName**: Cleaned movie title (quality indicators removed)
- **StartTime**: Formatted as `HHhMMmSSs` (e.g., `01h23m45s`)
- **EndTime**: Formatted as `HHhMMmSSs` (e.g., `01h24m15s`)
- **Extension**: Always `.mp4`

#### Examples

```
IronMan_01h15m35s_to_01h15m47s.mp4
DoctorStrange_00h30m45s_to_00h31m15s.mp4
Thor_00h59m40s_to_01h00m00s.mp4
CaptainAmerica_00h48m40s_to_00h49m00s.mp4
```

### Output Directories

#### Default Directory
```
{clips_dir}/filename.mp4
```

#### Testing Directory
```
{clips_dir}_testing/filename.mp4
```

### File Properties

#### Video
- **Codec**: Same as source (stream copy)
- **Resolution**: Same as source
- **Frame Rate**: Same as source
- **Quality**: Lossless (no re-encoding)

#### Audio
- **Codec**: PCM 16-bit signed little-endian (`pcm_s16le`)
- **Sample Rate**: 48kHz
- **Channels**: 2 (stereo) by default
- **Quality**: Uncompressed

#### Container
- **Format**: MP4
- **Compatibility**: Universal playback support

## Environment Variables

### Cache Control

##### MOVIE_CLIPPER_CACHE_DIR
- **Description**: Override cache directory location
- **Example**: `export MOVIE_CLIPPER_CACHE_DIR="/tmp/movie_cache"`

##### MOVIE_CLIPPER_CACHE_ENABLED
- **Description**: Enable/disable cache temporarily
- **Values**: `"true"`, `"false"`
- **Example**: `export MOVIE_CLIPPER_CACHE_ENABLED="false"`

### Directory Overrides

##### MOVIE_CLIPPER_MOVIES_DIR
- **Description**: Override movies directory
- **Example**: `export MOVIE_CLIPPER_MOVIES_DIR="/movies"`

##### MOVIE_CLIPPER_CLIPS_DIR
- **Description**: Override clips directory
- **Example**: `export MOVIE_CLIPPER_CLIPS_DIR="/clips"`

### Debug Options

##### MOVIE_CLIPPER_VERBOSE
- **Description**: Enable verbose output
- **Values**: `"1"`, `"true"`
- **Example**: `export MOVIE_CLIPPER_VERBOSE=1`

## Cache System Reference

### Cache Structure

#### Cache File Location
```
~/.cache/movie_clipper/movie_index.json
```

#### Cache Data Structure
```json
{
  "timestamp": 1640995200.0,
  "movies_dir": "/path/to/movies",
  "follow_symlinks": true,
  "extensions": [".mkv", ".mp4", ".avi"],
  "movies": [
    {
      "path": "/path/to/movie.mkv",
      "size": 1073741824,
      "mtime": 1640995200.0
    }
  ]
}
```

### Cache Operations

#### Automatic Cache Building
- Triggered on first run
- Triggered when cache is invalid
- Triggered when cache is expired

#### Cache Validation
- Checks movies directory modification time
- Checks cache age against TTL
- Validates cache file structure

#### Cache Invalidation
- Movies directory changed
- Cache age exceeds TTL
- Cache file corrupted
- Configuration changed

## FFmpeg Integration Reference

### Command Template

```bash
ffmpeg -y -ss {start_time} -i {input_file} -t {duration} -c:v copy {audio_options} {output_file}
```

### Audio Options by Mode

#### Default Mode (Smart Selection)
```bash
-map 0:v:0 -map 0:a:{selected_stream} -ac 2 -c:a pcm_s16le -ar 48000
```

#### Preserve Audio Mode
```bash
-c:a pcm_s16le -ar 48000
```

#### No Stereo Mode
```bash
-map 0:v:0 -map 0:a:{selected_stream} -c:a pcm_s16le -ar 48000
```

### Performance Optimizations

#### Fast Seeking
- Places `-ss` before `-i` for keyframe seeking
- Reduces processing time significantly

#### Stream Copy
- Uses `-c:v copy` for lossless video processing
- No re-encoding required

#### Selective Stream Mapping
- Maps only required video and audio streams
- Reduces output file size

## Exit Codes

### Success Codes
- `0` - Success
- `0` - Help displayed
- `0` - Setup completed
- `0` - Cache cleared
- `0` - Cache info displayed

### Error Codes
- `1` - General error
- `1` - Configuration error
- `1` - Movie not found
- `1` - FFmpeg error
- `1` - File system error
- `1` - Time parsing error

## Version Information

### Script Version
Check script header for version information:
```bash
head -20 clip_movie.py | grep -i version
```

### Dependencies
- **Python**: 3.9+
- **click**: >=8.0.0
- **fuzzywuzzy**: >=0.18.0
- **python-Levenshtein**: >=0.12.0
- **rich**: >=13.0.0
- **pydantic**: >=1.10.0
- **toml**: >=0.10.0

### System Requirements
- **FFmpeg**: Any recent version
- **Storage**: 100MB+ for clips
- **Memory**: 4GB+ recommended

---

**Previous**: [Troubleshooting Guide](TROUBLESHOOTING.md) | **Back to**: [Main Documentation](../README.md)