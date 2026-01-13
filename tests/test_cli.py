import errno
import time
from decimal import Decimal
from pathlib import Path

import pytest
import toml
from click.testing import CliRunner

from movieclipper import cli


@pytest.fixture(autouse=True)
def reset_config():
    cli.config = None
    yield
    cli.config = None


def make_config(tmp_path: Path) -> cli.Config:
    movies_dir = tmp_path / "movies"
    clips_dir = tmp_path / "clips"
    movies_dir.mkdir()
    clips_dir.mkdir()
    return cli.Config(directories=cli.DirectoryConfig(movies_dir=movies_dir, clips_dir=clips_dir))


def make_cache_data(movies_dir: Path, config: cli.Config, timestamp=None) -> dict:
    if timestamp is None:
        timestamp = time.time()
    return {
        "timestamp": timestamp,
        "movies_dir": str(movies_dir),
        "follow_symlinks": config.settings.follow_symlinks,
        "extensions": list(config.settings.video_extensions),
        "movies": [
            {"path": str(movies_dir / "movie.mkv"), "size": 123, "mtime": 456.0},
        ],
    }


def test_read_config_creates_missing_clips_dir(tmp_path):
    movies_dir = tmp_path / "movies"
    movies_dir.mkdir()
    clips_dir = tmp_path / "clips"
    config_path = tmp_path / "movieclipper.toml"
    config_path.write_text(
        toml.dumps(
            {
                "directories": {
                    "movies_dir": str(movies_dir),
                    "clips_dir": str(clips_dir),
                }
            }
        ),
        encoding="utf-8",
    )

    config = cli.read_config(config_path)

    assert clips_dir.is_dir()
    assert config.directories.clips_dir == clips_dir


def test_validate_movies_dir_rejects_unreadable(tmp_path):
    movies_dir = tmp_path / "movies"
    clips_dir = tmp_path / "clips"
    movies_dir.mkdir()
    clips_dir.mkdir()
    movies_dir.chmod(0o000)
    try:
        with pytest.raises(ValueError, match="not readable"):
            cli.DirectoryConfig(movies_dir=movies_dir, clips_dir=clips_dir)
    finally:
        movies_dir.chmod(0o755)


def test_parse_time_formats():
    assert cli.parse_time("90") == Decimal("90")
    assert cli.parse_time("1:30") == Decimal("90")
    assert cli.parse_time("1:30.5") == Decimal("90.5")
    assert cli.parse_time("01:02:03") == Decimal("3723")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0", Decimal("0")),
        ("00", Decimal("0")),
        ("1:02", Decimal("62")),
        ("01:02", Decimal("62")),
        ("10:00", Decimal("600")),
        ("1:2:3", Decimal("3723")),
        ("00:00:05", Decimal("5")),
        ("1.123456", Decimal("1.123456")),
        ("0:01.999999", Decimal("1.999999")),
    ],
)
def test_parse_time_edge_cases(value, expected):
    assert cli.parse_time(value) == expected


def test_parse_time_invalid():
    with pytest.raises(ValueError):
        cli.parse_time("1:2:3:4")


@pytest.mark.parametrize(
    "value",
    [
        "",
        "1:",
        ":30",
        "abc",
        "1:xx",
        "1:2:xx",
        "-5",
        "-1:30",
    ],
)
def test_parse_time_invalid_edge_cases(value):
    with pytest.raises(ValueError):
        cli.parse_time(value)


def test_format_time():
    assert cli.format_time(3723) == "01:02:03"


def test_format_time_handles_decimal_sum():
    start = cli.parse_time("0.1")
    duration = cli.parse_time("0.2")
    assert cli.format_time(start + duration) == "00:00:00.3"


def test_generate_output_filename():
    movie_file = Path("Iron.Man.2008.BluRay.x264.mkv")
    filename = cli.generate_output_filename(movie_file, 60, 120)
    assert filename == "IronMan_00h01m00s_to_00h02m00s.mp4"


def test_fuzzy_match_movie_no_matches():
    movie_files = [Path("/movies/Alpha.mkv"), Path("/movies/Beta.mkv")]
    assert cli.fuzzy_match_movie("zzzz", movie_files) == []


def test_fuzzy_match_movie_uses_parent_folder():
    movie_files = [
        Path("/movies/Marvel/Iron.Man.mkv"),
        Path("/movies/Other/Random.mkv"),
    ]
    matches = cli.fuzzy_match_movie("Marvel", movie_files)
    assert matches
    assert matches[0][0].name == "Iron.Man.mkv"


def test_is_cache_valid_accepts_fresh_cache(tmp_path):
    config = make_config(tmp_path)
    movies_dir = config.directories.movies_dir
    cache_data = make_cache_data(movies_dir, config)
    assert cli.is_cache_valid(cache_data, movies_dir, config) is True


@pytest.mark.parametrize(
    "mutator",
    [
        lambda data, config: data.pop("movies"),
        lambda data, config: data.__setitem__(
            "movies_dir", str(Path(data["movies_dir"]) / "other")
        ),
        lambda data, config: data.__setitem__("extensions", [".zzz"]),
        lambda data, config: data.__setitem__(
            "follow_symlinks", not config.settings.follow_symlinks
        ),
        lambda data, config: data.__setitem__(
            "timestamp",
            time.time() - (config.settings.cache_ttl_hours + 1) * 3600,
        ),
    ],
)
def test_is_cache_valid_rejects_mismatches(tmp_path, mutator):
    config = make_config(tmp_path)
    movies_dir = config.directories.movies_dir
    cache_data = make_cache_data(movies_dir, config)
    mutator(cache_data, config)
    assert cli.is_cache_valid(cache_data, movies_dir, config) is False


def test_is_cache_valid_rejects_empty(tmp_path):
    config = make_config(tmp_path)
    assert cli.is_cache_valid({}, config.directories.movies_dir, config) is False


def test_iter_movie_files_warns_once_on_permission_error(monkeypatch, tmp_path):
    movies_dir = tmp_path / "movies"
    movies_dir.mkdir()
    (movies_dir / "ok.mkv").write_text("data", encoding="utf-8")
    warnings = []

    def fake_print(*args, **_kwargs):
        warnings.append(" ".join(str(arg) for arg in args))

    def fake_walk(root, followlinks=None, onerror=None):
        if onerror is not None:
            onerror(PermissionError(errno.EACCES, "Permission denied", str(Path(root) / "secret")))
            onerror(PermissionError(errno.EACCES, "Permission denied", str(Path(root) / "secret")))
        yield str(root), [], ["ok.mkv"]

    monkeypatch.setattr(cli.console, "print", fake_print)
    monkeypatch.setattr(cli.os, "walk", fake_walk)

    movie_files = cli.iter_movie_files(movies_dir, [".mkv"], follow_symlinks=True)

    assert movie_files == [movies_dir / "ok.mkv"]
    warning_messages = [message for message in warnings if "Warning" in message]
    assert len(warning_messages) == 1
    assert "Permission denied" in warning_messages[0]
    assert "secret" in warning_messages[0]


def test_iter_movie_files_skips_symlinked_files(tmp_path):
    movies_dir = tmp_path / "movies"
    movies_dir.mkdir()
    real_movie = movies_dir / "movie.mkv"
    real_movie.write_text("data", encoding="utf-8")
    symlinked_movie = movies_dir / "movie-link.mkv"
    try:
        symlinked_movie.symlink_to(real_movie)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Symlinks not supported: {exc}")

    movie_files = cli.iter_movie_files(movies_dir, [".mkv"], follow_symlinks=False)

    assert real_movie in movie_files
    assert symlinked_movie not in movie_files

    movie_files = cli.iter_movie_files(movies_dir, [".mkv"], follow_symlinks=True)

    assert real_movie in movie_files
    assert symlinked_movie in movie_files


def test_select_movie_file_expands_user_path(monkeypatch, tmp_path):
    home = tmp_path / "home"
    movies_dir = tmp_path / "movies"
    clips_dir = tmp_path / "clips"
    home.mkdir()
    movies_dir.mkdir()
    clips_dir.mkdir()
    movie_path = home / "Movies" / "Title.mkv"
    movie_path.parent.mkdir()
    movie_path.write_text("data", encoding="utf-8")

    monkeypatch.setenv("HOME", str(home))
    config = cli.Config(
        directories=cli.DirectoryConfig(
            movies_dir=movies_dir,
            clips_dir=clips_dir,
        )
    )

    def fail_find_movie_files(*_args, **_kwargs):
        raise AssertionError("Unexpected search")

    monkeypatch.setattr(cli, "find_movie_files", fail_find_movie_files)

    assert cli.select_movie_file("~/Movies/Title.mkv", config) == movie_path


def test_main_uses_config_default_for_preserve_audio(monkeypatch, tmp_path):
    movies_dir = tmp_path / "movies"
    clips_dir = tmp_path / "clips"
    movies_dir.mkdir()
    clips_dir.mkdir()
    config = cli.Config(
        directories=cli.DirectoryConfig(
            movies_dir=movies_dir,
            clips_dir=clips_dir,
        ),
        settings=cli.Settings(preserve_all_audio=True),
    )

    def fake_load_config():
        return config

    def fake_check_ffmpeg(*_args, **_kwargs):
        return cli.FfmpegTools(ffmpeg=Path("/usr/bin/ffmpeg"), ffprobe=None)

    def fake_select_movie_file(*_args, **_kwargs):
        return tmp_path / "movie.mkv"

    monkeypatch.setattr(cli, "load_config", fake_load_config)
    monkeypatch.setattr(cli, "check_ffmpeg", fake_check_ffmpeg)
    monkeypatch.setattr(cli, "select_movie_file", fake_select_movie_file)

    captured = {}

    def fake_build_ffmpeg_command(
        movie_file,
        start_seconds,
        duration_seconds,
        output_file,
        ffmpeg_path,
        ffprobe_path,
        preserve_audio,
        audio_lang,
        stereo,
        config_value,
    ):
        captured["preserve_audio"] = preserve_audio
        return ["ffmpeg"]

    monkeypatch.setattr(cli, "build_ffmpeg_command", fake_build_ffmpeg_command)
    monkeypatch.setattr(cli.Confirm, "ask", lambda *_args, **_kwargs: False)

    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        [
            "--start",
            "0",
            "--duration",
            "10",
            "movie.mkv",
        ],
    )

    assert result.exit_code == 0
    assert captured["preserve_audio"] is True


def test_select_audio_stream_prefers_exact_language():
    streams = [{"language": "eng"}, {"language": "spa"}]
    assert cli.select_audio_stream(streams, "spa") is streams[1]


def test_select_audio_stream_falls_back_to_prefix():
    streams = [{"language": "en-US"}, {"language": "fra"}]
    assert cli.select_audio_stream(streams, "eng") is streams[0]


def test_select_audio_stream_falls_back_to_first():
    streams = [{"language": "jpn"}, {"language": "spa"}]
    assert cli.select_audio_stream(streams, "eng") is streams[0]


def test_select_audio_stream_returns_none_for_empty():
    assert cli.select_audio_stream([], "eng") is None


def test_build_ffmpeg_command_audio_selection(monkeypatch, tmp_path):
    config = make_config(tmp_path)
    monkeypatch.setattr(cli, "load_config", lambda: config)
    monkeypatch.setattr(
        cli,
        "detect_audio_streams",
        lambda movie_file, ffprobe_path: [
            {"index": 1, "language": "eng", "channels": 2, "stream_index": 2}
        ],
    )

    command = cli.build_ffmpeg_command(
        movie_file=tmp_path / "movie.mkv",
        start_seconds=0,
        duration_seconds=10,
        output_file=tmp_path / "out.mp4",
        ffmpeg_path=Path("/usr/bin/ffmpeg"),
        ffprobe_path=None,
        preserve_audio=False,
        audio_lang="eng",
        stereo=True,
        config_value=config,
    )

    assert command[0] == "/usr/bin/ffmpeg"
    assert "-map" in command
    assert "0:a:1" in command
    assert "-ac" in command
    assert str(config.settings.default_audio_channels) in command


def test_build_ffmpeg_command_selects_default_language(monkeypatch, tmp_path):
    config = make_config(tmp_path)
    monkeypatch.setattr(cli, "load_config", lambda: config)
    monkeypatch.setattr(
        cli,
        "detect_audio_streams",
        lambda movie_file, ffprobe_path: [
            {"index": 0, "language": "spa", "channels": 2, "stream_index": 0},
            {"index": 1, "language": "eng", "channels": 2, "stream_index": 1},
        ],
    )

    command = cli.build_ffmpeg_command(
        movie_file=tmp_path / "movie.mkv",
        start_seconds=0,
        duration_seconds=10,
        output_file=tmp_path / "out.mp4",
        ffmpeg_path=Path("/usr/bin/ffmpeg"),
        ffprobe_path=Path("/usr/bin/ffprobe"),
        preserve_audio=False,
        audio_lang=None,
        stereo=True,
        config_value=config,
    )

    map_indices = [i for i, item in enumerate(command) if item == "-map"]
    assert command[map_indices[0] + 1] == "0:v:0"
    assert command[map_indices[1] + 1] == "0:a:1"
    assert "-ac" in command


def test_build_ffmpeg_command_preserve_audio_no_stereo(monkeypatch, tmp_path):
    config = make_config(tmp_path)
    monkeypatch.setattr(cli, "load_config", lambda: config)

    command = cli.build_ffmpeg_command(
        movie_file=tmp_path / "movie.mkv",
        start_seconds=0,
        duration_seconds=10,
        output_file=tmp_path / "out.mp4",
        ffmpeg_path=Path("/usr/bin/ffmpeg"),
        ffprobe_path=None,
        preserve_audio=True,
        audio_lang=None,
        stereo=False,
        config_value=config,
    )

    map_indices = [i for i, item in enumerate(command) if item == "-map"]
    mapped_streams = {command[index + 1] for index in map_indices}
    assert mapped_streams == {"0:v:0", "0:a?"}
    assert "-ac" not in command
    assert "-c:a" in command
    assert str(config.settings.default_sample_rate) in command


def test_resolve_ffmpeg_tools_env(monkeypatch, tmp_path):
    ffmpeg_path = tmp_path / "ffmpeg"
    ffprobe_path = tmp_path / "ffprobe"
    ffmpeg_path.write_text("")
    ffprobe_path.write_text("")
    ffmpeg_path.chmod(0o755)
    ffprobe_path.chmod(0o755)

    monkeypatch.setenv("MOVIECLIPPER_FFMPEG", str(ffmpeg_path))
    monkeypatch.setenv("MOVIECLIPPER_FFPROBE", str(ffprobe_path))
    monkeypatch.setattr(cli.shutil, "which", lambda _: None)

    tools = cli.resolve_ffmpeg_tools(None, None)
    assert tools.ffmpeg == ffmpeg_path
    assert tools.ffprobe == ffprobe_path


def test_default_directories_prefers_existing_home(monkeypatch, tmp_path):
    home = tmp_path / "home"
    videos = home / "Videos"
    videos.mkdir(parents=True)

    monkeypatch.setattr(cli.Path, "home", lambda: home)
    monkeypatch.setattr(cli.Path, "cwd", lambda: tmp_path)

    movies_dir, clips_dir = cli.default_directories()
    assert movies_dir == videos
    assert clips_dir == videos / "clips"


def test_default_directories_falls_back_to_cwd(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    monkeypatch.setattr(cli.Path, "home", lambda: home)
    monkeypatch.setattr(cli.Path, "cwd", lambda: tmp_path)

    movies_dir, clips_dir = cli.default_directories()
    assert movies_dir == tmp_path
    assert clips_dir == tmp_path / "clips"
