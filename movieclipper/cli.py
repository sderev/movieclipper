"""Movie Clipper CLI.

Create clips from movie files using ffmpeg with fuzzy title matching and
configurable audio handling.
"""

from __future__ import annotations

import errno
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click
import toml
from pydantic import BaseModel, ValidationError, field_validator
from rapidfuzz import fuzz
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()


@dataclass(frozen=True)
class FfmpegTools:
    ffmpeg: Path
    ffprobe: Optional[Path]


class DirectoryConfig(BaseModel):
    """Configuration for movie and clip directories."""

    movies_dir: Path
    clips_dir: Path

    @field_validator("movies_dir")
    @classmethod
    def validate_movies_dir(cls, value: Path) -> Path:
        if not value.exists():
            raise ValueError(f"Directory does not exist: {value}")
        if not value.is_dir():
            raise ValueError(f"Path is not a directory: {value}")
        if not os.access(value, os.R_OK):
            raise ValueError(f"Movies directory is not readable: {value}")
        return value

    @field_validator("clips_dir")
    @classmethod
    def validate_clips_dir_writable(cls, value: Path) -> Path:
        if value.exists() and not value.is_dir():
            raise ValueError(f"Path is not a directory: {value}")
        if not value.exists():
            try:
                value.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise ValueError(f"Cannot create clips directory: {exc}")
        return value


class Settings(BaseModel):
    """Application settings."""

    default_audio_codec: str = "pcm_s16le"
    default_sample_rate: int = 48_000
    default_audio_channels: int = 2
    default_audio_language: str = "eng"
    preserve_all_audio: bool = False
    preview_by_default: bool = False
    follow_symlinks: bool = True
    video_extensions: List[str] = [
        ".mkv",
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".m2ts",
    ]
    cache_enabled: bool = True
    cache_ttl_hours: int = 24
    cache_location: Optional[str] = None


class Config(BaseModel):
    """Main configuration model."""

    directories: DirectoryConfig
    settings: Settings = Settings()


config: Optional[Config] = None


def get_config_path() -> Path:
    """Get the path to the configuration file."""
    config_dir = Path.home() / ".config" / "movieclipper"
    return config_dir / "movieclipper.toml"


def read_config(config_path: Path) -> Config:
    with config_path.open("r", encoding="utf-8") as handle:
        config_data = toml.load(handle)
    return Config(**config_data)


def load_config() -> Config:
    """Load configuration from file or create default."""
    global config
    if config is not None:
        return config

    config_path = get_config_path()

    if not config_path.exists():
        config = setup_config()
    else:
        try:
            config = read_config(config_path)
        except (ValidationError, FileNotFoundError, toml.TomlDecodeError) as exc:
            console.print(f"[red]Error loading config: {exc}[/red]")
            console.print("[yellow]Running setup again...[/yellow]")
            config = setup_config()

    return config


def default_directories() -> Tuple[Path, Path]:
    home = Path.home()
    candidates = [home / "Videos", home / "Movies"]
    movies_root = next((path for path in candidates if path.exists()), None)
    if movies_root is None:
        movies_root = Path.cwd()
    clips_root = movies_root / "clips"
    return movies_root, clips_root


def setup_config() -> Config:
    """Interactive configuration setup."""
    console.print(
        Panel.fit(
            "Movie Clipper setup\n\nConfigure your directories for movie clipping.",
            style="blue",
        )
    )

    default_movies, default_clips = default_directories()

    movies_dir_str = Prompt.ask("Where are your movie files located?", default=str(default_movies))
    movies_dir = Path(movies_dir_str).expanduser().resolve()

    if not movies_dir.exists():
        create_movies = Confirm.ask(
            f"Movies directory does not exist. Create {movies_dir}?", default=False
        )
        if create_movies:
            movies_dir.mkdir(parents=True, exist_ok=True)
        else:
            console.print("[red]Movies directory is required. Setup cancelled.[/red]")
            sys.exit(1)

    clips_dir_str = Prompt.ask("Where should clips be saved?", default=str(default_clips))
    clips_dir = Path(clips_dir_str).expanduser().resolve()

    if not clips_dir.exists():
        clips_dir.mkdir(parents=True, exist_ok=True)

    try:
        config_value = Config(
            directories=DirectoryConfig(movies_dir=movies_dir, clips_dir=clips_dir)
        )
        save_config(config_value)
        console.print("[green]Configuration saved.[/green]")
        console.print(f"Movies directory: {movies_dir}")
        console.print(f"Clips directory: {clips_dir}")
        return config_value
    except ValidationError as exc:
        console.print(f"[red]Configuration error: {exc}[/red]")
        sys.exit(1)


def save_config(config_value: Config) -> None:
    """Save configuration to file."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config_data = {
        "directories": {
            "movies_dir": str(config_value.directories.movies_dir),
            "clips_dir": str(config_value.directories.clips_dir),
        },
        "settings": {
            "default_audio_codec": config_value.settings.default_audio_codec,
            "default_sample_rate": config_value.settings.default_sample_rate,
            "default_audio_channels": config_value.settings.default_audio_channels,
            "default_audio_language": config_value.settings.default_audio_language,
            "preserve_all_audio": config_value.settings.preserve_all_audio,
            "preview_by_default": config_value.settings.preview_by_default,
            "follow_symlinks": config_value.settings.follow_symlinks,
            "video_extensions": config_value.settings.video_extensions,
            "cache_enabled": config_value.settings.cache_enabled,
            "cache_ttl_hours": config_value.settings.cache_ttl_hours,
            "cache_location": config_value.settings.cache_location,
        },
    }

    with config_path.open("w", encoding="utf-8") as handle:
        toml.dump(config_data, handle)


def get_cache_path(config_value: Optional[Config] = None) -> Path:
    """Get the path to the movie index cache file."""
    if config_value is None:
        config_value = load_config()

    if config_value.settings.cache_location:
        cache_dir = Path(config_value.settings.cache_location).expanduser()
    else:
        # Migration: use old path if new path doesn't exist but old path does
        new_cache_dir = Path.home() / ".cache" / "movieclipper"
        old_cache_dir = Path.home() / ".cache" / "movie_clipper"
        new_cache_path = new_cache_dir / "movie_index.json"
        old_cache_path = old_cache_dir / "movie_index.json"

        if not new_cache_path.exists() and old_cache_path.exists():
            cache_dir = old_cache_dir
        else:
            cache_dir = new_cache_dir

    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "movie_index.json"


def load_movie_cache() -> Optional[Dict[str, Any]]:
    """Load movie index cache from file."""
    cache_path = get_cache_path()

    if not cache_path.exists():
        return None

    try:
        with cache_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, FileNotFoundError, OSError):
        return None


def save_movie_cache(cache_data: Dict[str, Any], config_value: Optional[Config] = None) -> None:
    """Save movie index cache to file."""
    cache_path = get_cache_path(config_value)

    try:
        with cache_path.open("w", encoding="utf-8") as handle:
            json.dump(cache_data, handle, indent=2)
    except (OSError, IOError) as exc:
        console.print(f"[yellow]Warning: Could not save cache: {exc}[/yellow]")


def is_cache_valid(cache_data: Dict[str, Any], movies_dir: Path, config_value: Config) -> bool:
    """Check if cached movie index is still valid."""
    if not cache_data:
        return False

    required_keys = {"timestamp", "movies_dir", "movies", "extensions", "follow_symlinks"}
    if not required_keys.issubset(cache_data.keys()):
        return False

    if cache_data["movies_dir"] != str(movies_dir):
        return False

    if cache_data.get("extensions") != config_value.settings.video_extensions:
        return False

    if cache_data.get("follow_symlinks") != config_value.settings.follow_symlinks:
        return False

    cache_age_hours = (time.time() - cache_data["timestamp"]) / 3600
    if cache_age_hours > config_value.settings.cache_ttl_hours:
        return False

    return True


def iter_movie_files(movies_dir: Path, extensions: List[str], follow_symlinks: bool) -> List[Path]:
    """Return movie files from a directory tree."""
    extensions_lower = {ext.lower() for ext in extensions}
    movie_files: List[Path] = []
    warned_errors: set[tuple[int | None, str | None]] = set()

    def handle_walk_error(error: OSError) -> None:
        """Handle permission errors gracefully during walk."""
        if error.errno not in (errno.EACCES, errno.EPERM):
            return
        key = (error.errno, error.filename)
        if key in warned_errors:
            return
        warned_errors.add(key)
        location = error.filename or "unknown path"
        console.print(f"[yellow]Warning:[/yellow] Permission denied while scanning {location}")

    for root, _, files in os.walk(
        movies_dir, followlinks=follow_symlinks, onerror=handle_walk_error
    ):
        for name in files:
            path = Path(root) / name
            if path.suffix.lower() in extensions_lower:
                # Skip symlinked files when follow_symlinks is False
                if not follow_symlinks and path.is_symlink():
                    continue
                movie_files.append(path)

    return sorted(movie_files)


def build_movie_cache(
    movies_dir: Path, extensions: List[str], follow_symlinks: bool
) -> Dict[str, Any]:
    """Build movie index cache by scanning directory."""
    console.print("[blue]Building movie index cache...[/blue]")

    movie_files = []
    for path in iter_movie_files(movies_dir, extensions, follow_symlinks):
        try:
            stat = path.stat()
            movie_files.append(
                {
                    "path": str(path),
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                }
            )
        except OSError:
            continue

    cache_data = {
        "timestamp": time.time(),
        "movies_dir": str(movies_dir),
        "follow_symlinks": follow_symlinks,
        "extensions": extensions,
        "movies": movie_files,
    }

    console.print(f"[green]Found {len(movie_files)} movies in cache[/green]")
    return cache_data


def invalidate_movie_cache() -> None:
    """Invalidate the movie index cache."""
    cache_path = get_cache_path()

    if cache_path.exists():
        try:
            cache_path.unlink()
            console.print("[green]Movie index cache cleared[/green]")
        except OSError as exc:
            console.print(f"[yellow]Warning: Could not clear cache: {exc}[/yellow]")
    else:
        console.print("[yellow]No cache file found[/yellow]")


def get_cache_info() -> Dict[str, Any]:
    """Get information about the current cache."""
    cache_path = get_cache_path()

    if not cache_path.exists():
        return {"exists": False}

    try:
        cache_data = load_movie_cache()
        if not cache_data:
            return {"exists": False}

        cache_age_hours = (time.time() - cache_data["timestamp"]) / 3600

        return {
            "exists": True,
            "path": str(cache_path),
            "movies_count": len(cache_data.get("movies", [])),
            "age_hours": cache_age_hours,
            "movies_dir": cache_data.get("movies_dir", "unknown"),
            "size_bytes": cache_path.stat().st_size,
        }
    except Exception:
        return {"exists": False}


def find_movie_files(
    movies_dir: Path,
    extensions: List[str],
    follow_symlinks: bool = True,
    config_value: Optional[Config] = None,
) -> List[Path]:
    """Find all movie files in the directory and subdirectories."""
    if config_value is None:
        config_value = load_config()

    if config_value.settings.cache_enabled:
        cache_data = load_movie_cache()
        if cache_data and is_cache_valid(cache_data, movies_dir, config_value):
            console.print("[blue]Using cached movie index[/blue]")
            movie_paths = [Path(info["path"]) for info in cache_data["movies"]]
            existing_paths = [path for path in movie_paths if path.exists()]
            return sorted(existing_paths)

        cache_data = build_movie_cache(movies_dir, extensions, follow_symlinks)
        save_movie_cache(cache_data, config_value)
        return [Path(info["path"]) for info in cache_data["movies"]]

    return iter_movie_files(movies_dir, extensions, follow_symlinks)


def fuzzy_match_movie(query: str, movie_files: List[Path]) -> List[Tuple[Path, float]]:
    """Find movies matching the query using fuzzy matching."""
    matches = []

    for movie_file in movie_files:
        filename = movie_file.stem
        score = fuzz.partial_ratio(query.lower(), filename.lower())

        if movie_file.parent.name != movie_file.parent.parent.name:
            parent_score = fuzz.partial_ratio(query.lower(), movie_file.parent.name.lower())
            score = max(score, parent_score)

        if score > 60:
            matches.append((movie_file, score))

    matches.sort(key=lambda item: item[1], reverse=True)
    return matches


def select_movie_file(query: str, config_value: Optional[Config] = None) -> Path:
    """Select a movie file based on query (path or title)."""
    if config_value is None:
        config_value = load_config()

    query_path = Path(query).expanduser()
    if query_path.exists() and query_path.is_file():
        return query_path

    movie_files = find_movie_files(
        config_value.directories.movies_dir,
        config_value.settings.video_extensions,
        config_value.settings.follow_symlinks,
        config_value,
    )

    if not movie_files:
        console.print("[red]No movie files found in the movies directory.[/red]")
        sys.exit(1)

    matches = fuzzy_match_movie(query, movie_files)

    if not matches:
        console.print(f"[red]No movies found matching '{query}'[/red]")
        console.print("\nAvailable movies:")
        for movie_file in movie_files[:10]:
            console.print(f"  - {movie_file.stem}")
        sys.exit(1)

    if len(matches) == 1 or matches[0][1] > 90:
        return matches[0][0]

    console.print(f"\n[yellow]Multiple movies found for '{query}':[/yellow]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="cyan", width=3)
    table.add_column("Movie", style="green")
    table.add_column("Location", style="blue")
    table.add_column("Score", style="yellow", width=6)

    for i, (movie_file, score) in enumerate(matches[:10], 1):
        relative_path = movie_file.relative_to(config_value.directories.movies_dir)
        table.add_row(
            str(i),
            movie_file.stem,
            str(relative_path.parent),
            f"{score:.0f}%",
        )

    console.print(table)

    while True:
        try:
            selection = Prompt.ask(f"\nSelect movie (1-{min(len(matches), 10)})", default="1")
            index = int(selection) - 1
            if 0 <= index < len(matches):
                return matches[index][0]
            console.print("[red]Invalid selection. Please try again.[/red]")
        except ValueError:
            console.print("[red]Please enter a number.[/red]")


def parse_time(time_str: str) -> int:
    """Parse time string into seconds."""
    if time_str.isdigit():
        return int(time_str)

    parts = time_str.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + int(seconds)
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds)

    raise ValueError(f"Invalid time format: {time_str}")


def format_time(seconds: int) -> str:
    """Format seconds into HH:MM:SS."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def generate_output_filename(movie_file: Path, start_seconds: int, end_seconds: int) -> str:
    """Generate output filename based on movie and timestamps."""
    movie_name = movie_file.stem

    movie_name = re.sub(r"\.(19|20)\d{2}\..*", "", movie_name)
    movie_name = re.sub(r"\.(BluRay|WEB|HDTV|DVDRip)\..*", "", movie_name, flags=re.IGNORECASE)
    movie_name = re.sub(r"\.x26[45].*", "", movie_name, flags=re.IGNORECASE)
    movie_name = movie_name.replace(".", "")

    start_formatted = format_time(start_seconds).replace(":", "h", 1).replace(":", "m", 1) + "s"
    end_formatted = format_time(end_seconds).replace(":", "h", 1).replace(":", "m", 1) + "s"

    return f"{movie_name}_{start_formatted}_to_{end_formatted}.mp4"


def detect_audio_streams(movie_file: Path, ffprobe_path: Optional[Path]) -> List[Dict[str, Any]]:
    """Detect audio streams in a movie file."""
    if ffprobe_path is None:
        return [{"index": 0, "language": "unknown", "channels": 2, "stream_index": 0}]

    try:
        command = [
            str(ffprobe_path),
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-select_streams",
            "a",
            str(movie_file),
        ]

        result = subprocess.run(command, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        audio_streams = []
        for i, stream in enumerate(data.get("streams", [])):
            audio_streams.append(
                {
                    "index": i,
                    "codec_name": stream.get("codec_name", "unknown"),
                    "channels": stream.get("channels", 0),
                    "sample_rate": stream.get("sample_rate", 0),
                    "language": stream.get("tags", {}).get("language", "unknown"),
                    "title": stream.get("tags", {}).get("title", ""),
                    "stream_index": stream.get("index", i),
                }
            )

        return audio_streams
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as exc:
        console.print(f"[yellow]Warning: Could not detect audio streams: {exc}[/yellow]")
        return [{"index": 0, "language": "unknown", "channels": 2, "stream_index": 0}]


def select_audio_stream(
    audio_streams: List[Dict[str, Any]], preferred_language: str
) -> Optional[Dict[str, Any]]:
    """Select the best audio stream based on language preference."""
    if not audio_streams:
        return None

    for stream in audio_streams:
        if stream["language"] == preferred_language:
            return stream

    for stream in audio_streams:
        if stream["language"].startswith(preferred_language[:2]):
            return stream

    return audio_streams[0]


def build_ffmpeg_command(
    movie_file: Path,
    start_seconds: int,
    duration_seconds: int,
    output_file: Path,
    ffmpeg_path: Path,
    ffprobe_path: Optional[Path],
    preserve_audio: bool = False,
    audio_lang: Optional[str] = None,
    stereo: bool = True,
    config_value: Optional[Config] = None,
) -> List[str]:
    """Build ffmpeg command for clipping."""
    if config_value is None:
        config_value = load_config()

    start_time = format_time(start_seconds)
    duration_time = format_time(duration_seconds)

    command = [
        str(ffmpeg_path),
        "-y",
        "-ss",
        start_time,
        "-i",
        str(movie_file),
        "-t",
        duration_time,
        "-c:v",
        "copy",
    ]

    if preserve_audio:
        command.extend(["-map", "0:v:0", "-map", "0:a?"])
        if stereo:
            command.extend(["-ac", str(config_value.settings.default_audio_channels)])
        command.extend(
            [
                "-c:a",
                config_value.settings.default_audio_codec,
                "-ar",
                str(config_value.settings.default_sample_rate),
            ]
        )
    else:
        if ffprobe_path is None and audio_lang:
            console.print(
                "[yellow]Warning: ffprobe unavailable; audio language selection ignored.[/yellow]"
            )

        audio_streams = detect_audio_streams(movie_file, ffprobe_path)

        if audio_streams:
            target_language = audio_lang or config_value.settings.default_audio_language
            selected_stream = select_audio_stream(audio_streams, target_language)

            if selected_stream:
                command.extend(["-map", "0:v:0"])
                command.extend(["-map", f"0:a:{selected_stream['index']}"])
                lang_info = (
                    selected_stream["language"]
                    if selected_stream["language"] != "unknown"
                    else "unknown language"
                )
                console.print(
                    f"[blue]Selected audio:[/blue] Stream {selected_stream['index']} ({lang_info})"
                )

        if stereo:
            command.extend(["-ac", str(config_value.settings.default_audio_channels)])

        command.extend(
            [
                "-c:a",
                config_value.settings.default_audio_codec,
                "-ar",
                str(config_value.settings.default_sample_rate),
            ]
        )

    command.append(str(output_file))
    return command


def _resolve_executable(
    candidate: Optional[str], env_key: str, default_name: str
) -> Optional[Path]:
    value = candidate or os.getenv(env_key)
    if value:
        path = Path(value).expanduser()
        if not path.is_file():
            raise ValueError(f"{env_key} path does not exist: {path}")
        if not os.access(path, os.X_OK):
            raise ValueError(f"{env_key} path is not executable: {path}")
        return path

    resolved = shutil.which(default_name)
    return Path(resolved) if resolved else None


def _resolve_imageio_ffmpeg() -> Optional[Path]:
    try:
        import imageio_ffmpeg
    except ImportError:
        return None

    try:
        return Path(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        return None


def resolve_ffmpeg_tools(ffmpeg_path: Optional[str], ffprobe_path: Optional[str]) -> FfmpegTools:
    try:
        ffmpeg = _resolve_executable(ffmpeg_path, "MOVIECLIPPER_FFMPEG", "ffmpeg")
    except ValueError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        sys.exit(1)

    if ffmpeg is None:
        ffmpeg = _resolve_imageio_ffmpeg()

    if ffmpeg is None:
        console.print("[red]Error: ffmpeg not found in PATH.[/red]")
        console.print("Install ffmpeg or use movieclipper[ffmpeg].")
        sys.exit(1)

    try:
        ffprobe = _resolve_executable(ffprobe_path, "MOVIECLIPPER_FFPROBE", "ffprobe")
    except ValueError as exc:
        console.print(f"[red]Error: {exc}[/red]")
        sys.exit(1)

    if ffprobe is None:
        candidate = ffmpeg.with_name("ffprobe.exe" if os.name == "nt" else "ffprobe")
        if candidate.exists() and os.access(candidate, os.X_OK):
            ffprobe = candidate

    return FfmpegTools(ffmpeg=ffmpeg, ffprobe=ffprobe)


def _verify_tool(path: Path, label: str) -> None:
    try:
        subprocess.run([str(path), "-version"], check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        console.print(f"[red]Error: {label} failed to run: {exc}[/red]")
        sys.exit(1)


def check_ffmpeg(
    ffmpeg_path: Optional[str], ffprobe_path: Optional[str], require_ffprobe: bool = False
) -> FfmpegTools:
    tools = resolve_ffmpeg_tools(ffmpeg_path, ffprobe_path)

    _verify_tool(tools.ffmpeg, "ffmpeg")

    if tools.ffprobe:
        _verify_tool(tools.ffprobe, "ffprobe")
    elif require_ffprobe:
        console.print("[red]Error: ffprobe not found in PATH.[/red]")
        sys.exit(1)
    else:
        console.print(
            "[yellow]Warning: ffprobe not found; audio stream detection limited.[/yellow]"
        )

    return tools


def check_environment(ffmpeg_path: Optional[str], ffprobe_path: Optional[str]) -> None:
    tools = check_ffmpeg(ffmpeg_path, ffprobe_path, require_ffprobe=False)
    config_path = get_config_path()

    if not config_path.exists():
        console.print("[red]Config file not found.[/red]")
        console.print("Run movieclipper --setup to create it.")
        sys.exit(1)

    try:
        read_config(config_path)
    except (ValidationError, FileNotFoundError, toml.TomlDecodeError) as exc:
        console.print(f"[red]Config file is invalid: {exc}[/red]")
        sys.exit(1)

    console.print("[green]ffmpeg:[/green] " + str(tools.ffmpeg))
    if tools.ffprobe:
        console.print("[green]ffprobe:[/green] " + str(tools.ffprobe))
    else:
        console.print("[yellow]ffprobe:[/yellow] not found")
    console.print("[green]Config file:[/green] " + str(config_path))


def execute_ffmpeg(command: List[str]) -> bool:
    """Execute ffmpeg command with progress feedback."""
    console.print(f"[green]Executing:[/green] {' '.join(command)}")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Processing video...", total=None)

            subprocess.run(command, capture_output=True, text=True, check=True)
            progress.update(task, description="Video processed successfully")

        return True
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]FFmpeg error:[/red] {exc.stderr}")
        return False


@click.command()
@click.argument("movie_input", required=False)
@click.option("--start", "-s", help="Start time (HH:MM:SS, MM:SS, or seconds)")
@click.option("--duration", "-d", help="Duration (HH:MM:SS, MM:SS, or seconds)")
@click.option("--test", is_flag=True, help="Use clips_testing directory for output")
@click.option("--setup", is_flag=True, help="Run configuration setup")
@click.option("--check", is_flag=True, help="Check ffmpeg and configuration")
@click.option("--ffmpeg-path", help="Path to ffmpeg binary")
@click.option("--ffprobe-path", help="Path to ffprobe binary")
@click.option(
    "--preserve-audio",
    is_flag=True,
    help="Keep all audio tracks (re-encodes to PCM for editor compatibility)",
)
@click.option("--audio-lang", help="Select specific audio language (e.g., eng, fre, spa)")
@click.option("--stereo/--no-stereo", default=True, help="Force stereo mix (default: stereo)")
@click.option("--clear-cache", is_flag=True, help="Clear movie index cache")
@click.option("--cache-info", is_flag=True, help="Show cache information")
def main(
    movie_input: Optional[str],
    start: Optional[str],
    duration: Optional[str],
    test: bool,
    setup: bool,
    check: bool,
    ffmpeg_path: Optional[str],
    ffprobe_path: Optional[str],
    preserve_audio: bool,
    audio_lang: Optional[str],
    stereo: bool,
    clear_cache: bool,
    cache_info: bool,
) -> None:
    """Movie clipping tool with fuzzy matching."""
    if check:
        check_environment(ffmpeg_path, ffprobe_path)
        return

    if setup:
        setup_config()
        return

    if clear_cache:
        invalidate_movie_cache()
        return

    if cache_info:
        info = get_cache_info()
        if info["exists"]:
            console.print("[green]Cache Information:[/green]")
            console.print(f"  Path: {info['path']}")
            console.print(f"  Movies: {info['movies_count']}")
            console.print(f"  Age: {info['age_hours']:.1f} hours")
            console.print(f"  Size: {info['size_bytes'] / 1024:.1f} KB")
            console.print(f"  Movies Directory: {info['movies_dir']}")
        else:
            console.print("[yellow]No cache found[/yellow]")
        return

    if not movie_input:
        console.print("[red]Error: Movie input is required (unless using --setup)[/red]")
        console.print("Usage: movieclipper MOVIE_INPUT [OPTIONS]")
        sys.exit(1)

    tools = check_ffmpeg(ffmpeg_path, ffprobe_path, require_ffprobe=False)
    config_value = load_config()

    ctx = click.get_current_context()
    if ctx.get_parameter_source("preserve_audio") == click.core.ParameterSource.DEFAULT:
        preserve_audio = config_value.settings.preserve_all_audio

    movie_file = select_movie_file(movie_input, config_value)
    console.print(f"[green]Selected movie:[/green] {movie_file.name}")

    if not start:
        start = Prompt.ask("Start time (HH:MM:SS, MM:SS, or seconds)", default="0")

    if not duration:
        duration = Prompt.ask("Duration (HH:MM:SS, MM:SS, or seconds)", default="20")

    try:
        start_seconds = parse_time(start)
        duration_seconds = parse_time(duration)
    except ValueError as exc:
        console.print(f"[red]Time parsing error: {exc}[/red]")
        sys.exit(1)

    end_seconds = start_seconds + duration_seconds
    output_filename = generate_output_filename(movie_file, start_seconds, end_seconds)

    if test:
        output_dir = config_value.directories.clips_dir.parent / "clips_testing"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / output_filename
    else:
        output_file = config_value.directories.clips_dir / output_filename

    command = build_ffmpeg_command(
        movie_file,
        start_seconds,
        duration_seconds,
        output_file,
        tools.ffmpeg,
        tools.ffprobe,
        preserve_audio,
        audio_lang,
        stereo,
        config_value,
    )

    console.print(f"[blue]Creating clip:[/blue] {output_filename}")
    console.print(f"[blue]From:[/blue] {format_time(start_seconds)} to {format_time(end_seconds)}")
    console.print(f"[blue]Duration:[/blue] {format_time(duration_seconds)}")

    if not Confirm.ask("Proceed with clipping?", default=True):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    success = execute_ffmpeg(command)

    if success:
        console.print("[green]Clip created successfully.[/green]")
        console.print(f"[green]Output:[/green] {output_file}")
    else:
        console.print("[red]Failed to create clip.[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
