import builtins
import errno
import json
import sys
import time
import types
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
import tomli_w
from click.testing import CliRunner

from movieclipper import cli


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


def make_cache_config(tmp_path: Path, **settings_overrides) -> cli.Config:
    base_config = make_config(tmp_path)
    settings_data = cli.Settings().model_dump()
    settings_data["cache_location"] = str(tmp_path / "cache")
    settings_data.update(settings_overrides)
    return cli.Config(
        directories=base_config.directories,
        settings=cli.Settings(**settings_data),
    )


def test_read_config_creates_missing_clips_dir(tmp_path):
    movies_dir = tmp_path / "movies"
    movies_dir.mkdir()
    clips_dir = tmp_path / "clips"
    config_path = tmp_path / "movieclipper.toml"
    config_path.write_bytes(
        tomli_w.dumps(
            {
                "directories": {
                    "movies_dir": str(movies_dir),
                    "clips_dir": str(clips_dir),
                }
            }
        ).encode()
    )

    config = cli.read_config(config_path)

    assert clips_dir.is_dir()
    assert config.directories.clips_dir == clips_dir


def test_load_config_runs_setup_when_config_missing(monkeypatch, tmp_path):
    expected = make_config(tmp_path)
    config_path = tmp_path / "missing.toml"

    monkeypatch.setattr(cli, "get_config_path", lambda: config_path)
    monkeypatch.setattr(cli, "setup_config", lambda: expected)
    monkeypatch.setattr(cli, "read_config", lambda *_args, **_kwargs: None)

    assert cli.load_config() is expected


def test_load_config_runs_setup_when_config_is_invalid(monkeypatch, tmp_path):
    config_path = tmp_path / "movieclipper.toml"
    config_path.write_text("bad = [", encoding="utf-8")
    expected = make_config(tmp_path)
    messages = []

    def fake_read_config(_config_path):
        raise cli.tomllib.TOMLDecodeError("Invalid value", "bad = [", 7)

    def fake_print(*args, **_kwargs):
        messages.append(" ".join(str(arg) for arg in args))

    monkeypatch.setattr(cli, "get_config_path", lambda: config_path)
    monkeypatch.setattr(cli, "read_config", fake_read_config)
    monkeypatch.setattr(cli, "setup_config", lambda: expected)
    monkeypatch.setattr(cli.console, "print", fake_print)

    assert cli.load_config() is expected
    assert any("Running setup again" in message for message in messages)


def test_setup_config_exits_when_movies_dir_missing_and_not_created(monkeypatch, tmp_path):
    movies_dir = tmp_path / "missing-movies"
    clips_dir = tmp_path / "clips"

    monkeypatch.setattr(cli, "default_directories", lambda: (movies_dir, clips_dir))
    monkeypatch.setattr(cli.Prompt, "ask", lambda *_args, **_kwargs: str(movies_dir))
    monkeypatch.setattr(cli.Confirm, "ask", lambda *_args, **_kwargs: False)

    with pytest.raises(SystemExit, match="1"):
        cli.setup_config()


def test_setup_config_creates_missing_movies_dir_when_confirmed(monkeypatch, tmp_path):
    movies_dir = tmp_path / "movies"
    clips_dir = tmp_path / "clips"
    prompts = iter([str(movies_dir), str(clips_dir)])
    saved = {}

    monkeypatch.setattr(cli, "default_directories", lambda: (movies_dir, clips_dir))
    monkeypatch.setattr(cli.Prompt, "ask", lambda *_args, **_kwargs: next(prompts))
    monkeypatch.setattr(cli.Confirm, "ask", lambda *_args, **_kwargs: True)

    def fake_save_config(config_value):
        saved["config"] = config_value

    monkeypatch.setattr(cli, "save_config", fake_save_config)

    config_value = cli.setup_config()

    assert movies_dir.is_dir()
    assert clips_dir.is_dir()
    assert config_value.directories.movies_dir == movies_dir
    assert config_value.directories.clips_dir == clips_dir
    assert saved["config"] == config_value


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


def test_get_cache_path_uses_configured_location(tmp_path):
    config = make_cache_config(tmp_path)

    cache_path = cli.get_cache_path(config)

    assert cache_path == tmp_path / "cache" / "movie_index.json"
    assert cache_path.parent.is_dir()


def test_get_cache_path_uses_legacy_cache_when_new_cache_is_missing(monkeypatch, tmp_path):
    home = tmp_path / "home"
    legacy_cache_path = home / ".cache" / "movie_clipper" / "movie_index.json"
    legacy_cache_path.parent.mkdir(parents=True)
    legacy_cache_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(cli.Path, "home", lambda: home)
    config = make_config(tmp_path)

    cache_path = cli.get_cache_path(config)

    assert cache_path == legacy_cache_path


def test_save_and_load_movie_cache_round_trip(tmp_path):
    config = make_cache_config(tmp_path)
    cache_data = make_cache_data(config.directories.movies_dir, config, timestamp=1234.0)

    cli.save_movie_cache(cache_data, config)

    assert cli.load_movie_cache(config) == cache_data


def test_load_movie_cache_returns_none_when_cache_is_invalid_json(tmp_path):
    config = make_cache_config(tmp_path)
    cache_path = cli.get_cache_path(config)
    cache_path.write_text("{broken-json", encoding="utf-8")

    assert cli.load_movie_cache(config) is None


def test_invalidate_movie_cache_removes_cache_file(tmp_path):
    config = make_cache_config(tmp_path)
    cache_data = make_cache_data(config.directories.movies_dir, config, timestamp=1234.0)
    cli.save_movie_cache(cache_data, config)
    cache_path = cli.get_cache_path(config)

    assert cache_path.exists()

    cli.invalidate_movie_cache(config)

    assert not cache_path.exists()


def test_invalidate_movie_cache_warns_when_file_is_missing(monkeypatch, tmp_path):
    config = make_cache_config(tmp_path)
    messages = []
    monkeypatch.setattr(
        cli.console, "print", lambda *args, **_kwargs: messages.append(" ".join(map(str, args)))
    )

    cli.invalidate_movie_cache(config)

    assert any("No cache file found" in message for message in messages)


def test_get_cache_info_reports_existing_cache_metadata(tmp_path):
    config = make_cache_config(tmp_path)
    cache_data = make_cache_data(
        config.directories.movies_dir,
        config,
        timestamp=time.time() - 3600,
    )
    cli.save_movie_cache(cache_data, config)

    info = cli.get_cache_info(config)

    assert info["exists"] is True
    assert info["path"] == str(cli.get_cache_path(config))
    assert info["movies_count"] == 1
    assert info["movies_dir"] == str(config.directories.movies_dir)
    assert info["size_bytes"] > 0
    assert info["age_hours"] == pytest.approx(1, rel=0.2)


def test_get_cache_info_returns_missing_for_corrupt_cache(tmp_path):
    config = make_cache_config(tmp_path)
    cache_path = cli.get_cache_path(config)
    cache_path.write_text("{broken-json", encoding="utf-8")

    assert cli.get_cache_info(config) == {"exists": False}


def test_find_movie_files_uses_valid_cache_without_rebuild(monkeypatch, tmp_path):
    config = make_cache_config(tmp_path)
    movies_dir = config.directories.movies_dir
    cached_movie = movies_dir / "cached.mkv"
    cached_movie.write_text("data", encoding="utf-8")
    cache_data = make_cache_data(movies_dir, config, timestamp=time.time())
    cache_data["movies"] = [{"path": str(cached_movie), "size": 1, "mtime": 1.0}]
    cli.save_movie_cache(cache_data, config)

    def fail_build(*_args, **_kwargs):
        raise AssertionError("Unexpected cache rebuild")

    monkeypatch.setattr(cli, "build_movie_cache", fail_build)

    movie_files, used_cached_index = cli.find_movie_files(
        movies_dir,
        config.settings.video_extensions,
        config.settings.follow_symlinks,
        config,
        include_cache_source=True,
    )

    assert movie_files == [cached_movie]
    assert used_cached_index is True


def test_find_movie_files_excludes_missing_paths_from_valid_cache(tmp_path):
    config = make_cache_config(tmp_path)
    movies_dir = config.directories.movies_dir
    cached_movie = movies_dir / "cached.mkv"
    cached_movie.write_text("data", encoding="utf-8")
    missing_movie = movies_dir / "missing.mkv"
    cache_data = make_cache_data(movies_dir, config, timestamp=time.time())
    cache_data["movies"] = [
        {"path": str(missing_movie), "size": 1, "mtime": 1.0},
        {"path": str(cached_movie), "size": 1, "mtime": 1.0},
    ]
    cli.save_movie_cache(cache_data, config)

    movie_files, used_cached_index = cli.find_movie_files(
        movies_dir,
        config.settings.video_extensions,
        config.settings.follow_symlinks,
        config,
        include_cache_source=True,
    )

    assert movie_files == [cached_movie]
    assert used_cached_index is True


def test_find_movie_files_rebuilds_when_cache_is_stale(tmp_path):
    config = make_cache_config(tmp_path)
    movies_dir = config.directories.movies_dir
    fresh_movie = movies_dir / "fresh.mkv"
    fresh_movie.write_text("data", encoding="utf-8")
    stale_timestamp = time.time() - (config.settings.cache_ttl_hours + 2) * 3600
    stale_cache_data = make_cache_data(movies_dir, config, timestamp=stale_timestamp)
    stale_cache_data["movies"] = []
    cli.save_movie_cache(stale_cache_data, config)

    movie_files, used_cached_index = cli.find_movie_files(
        movies_dir,
        config.settings.video_extensions,
        config.settings.follow_symlinks,
        config,
        include_cache_source=True,
    )

    refreshed_cache = cli.load_movie_cache(config)

    assert movie_files == [fresh_movie]
    assert used_cached_index is False
    assert refreshed_cache is not None
    assert [Path(item["path"]) for item in refreshed_cache["movies"]] == [fresh_movie]
    assert refreshed_cache["timestamp"] > stale_timestamp


def test_find_movie_files_force_refresh_rebuilds_even_with_valid_cache(tmp_path):
    config = make_cache_config(tmp_path)
    movies_dir = config.directories.movies_dir
    movie_file = movies_dir / "movie.mkv"
    movie_file.write_text("data", encoding="utf-8")
    valid_cache_data = make_cache_data(movies_dir, config, timestamp=time.time())
    valid_cache_data["movies"] = []
    cli.save_movie_cache(valid_cache_data, config)

    movie_files, used_cached_index = cli.find_movie_files(
        movies_dir,
        config.settings.video_extensions,
        config.settings.follow_symlinks,
        config,
        force_refresh=True,
        include_cache_source=True,
    )

    refreshed_cache = cli.load_movie_cache(config)

    assert movie_files == [movie_file]
    assert used_cached_index is False
    assert refreshed_cache is not None
    assert [Path(item["path"]) for item in refreshed_cache["movies"]] == [movie_file]


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


def test_select_movie_file_raises_when_no_movies(monkeypatch, tmp_path):
    config = make_config(tmp_path)

    def fake_find_movie_files(*_args, include_cache_source=False, **_kwargs):
        if include_cache_source:
            return [], False
        return []

    monkeypatch.setattr(cli, "find_movie_files", fake_find_movie_files)

    with pytest.raises(cli.MovieNotFoundError, match="No movie files found"):
        cli.select_movie_file("missing", config)


def test_select_movie_file_refreshes_cache_when_empty(monkeypatch, tmp_path):
    config = make_config(tmp_path)
    match_movie = config.directories.movies_dir / "Match.mkv"
    match_movie.write_text("data", encoding="utf-8")

    calls = []
    messages = []

    def fake_find_movie_files(
        _movies_dir,
        _extensions,
        follow_symlinks=True,
        config_value=None,
        force_refresh=False,
        include_cache_source=False,
    ):
        calls.append(force_refresh)
        if force_refresh:
            return [match_movie]
        if include_cache_source:
            return [], True
        return []

    def fake_print(*args, **_kwargs):
        messages.append(" ".join(str(arg) for arg in args))

    monkeypatch.setattr(cli, "find_movie_files", fake_find_movie_files)
    monkeypatch.setattr(cli.console, "print", fake_print)

    selected = cli.select_movie_file("Match", config)

    assert selected == match_movie
    assert calls == [False, True]
    assert any("No movie files found; refreshing cache" in message for message in messages)


def test_select_movie_file_refreshes_cache_on_miss(monkeypatch, tmp_path):
    config = make_config(tmp_path)
    other_movie = config.directories.movies_dir / "Other.mkv"
    match_movie = config.directories.movies_dir / "Match.mkv"
    other_movie.write_text("data", encoding="utf-8")
    match_movie.write_text("data", encoding="utf-8")

    calls = []
    messages = []

    def fake_find_movie_files(
        _movies_dir,
        _extensions,
        follow_symlinks=True,
        config_value=None,
        force_refresh=False,
        include_cache_source=False,
    ):
        calls.append(force_refresh)
        if force_refresh:
            return [match_movie]
        if include_cache_source:
            return [other_movie], True
        return [other_movie]

    def fake_print(*args, **_kwargs):
        messages.append(" ".join(str(arg) for arg in args))

    monkeypatch.setattr(cli, "find_movie_files", fake_find_movie_files)
    monkeypatch.setattr(cli.console, "print", fake_print)

    selected = cli.select_movie_file("Match", config)

    assert selected == match_movie
    assert calls == [False, True]
    assert any("refreshing cache" in message for message in messages)


def test_select_movie_file_refreshes_once_then_errors(monkeypatch, tmp_path):
    config = make_config(tmp_path)
    other_movie = config.directories.movies_dir / "Other.mkv"
    other_movie.write_text("data", encoding="utf-8")

    calls = []

    def fake_find_movie_files(
        _movies_dir,
        _extensions,
        follow_symlinks=True,
        config_value=None,
        force_refresh=False,
        include_cache_source=False,
    ):
        calls.append(force_refresh)
        if include_cache_source:
            return [other_movie], True
        return [other_movie]

    monkeypatch.setattr(cli, "find_movie_files", fake_find_movie_files)

    with pytest.raises(cli.MovieNotFoundError, match="No movies found matching"):
        cli.select_movie_file("zzzz", config)

    assert calls == [False, True]


def test_select_movie_file_skips_refresh_on_miss_after_fresh_scan(monkeypatch, tmp_path):
    config = make_config(tmp_path)
    other_movie = config.directories.movies_dir / "Other.mkv"
    other_movie.write_text("data", encoding="utf-8")

    calls = []

    def fake_find_movie_files(
        _movies_dir,
        _extensions,
        follow_symlinks=True,
        config_value=None,
        force_refresh=False,
        include_cache_source=False,
    ):
        calls.append(force_refresh)
        if include_cache_source:
            return [other_movie], False
        return [other_movie]

    monkeypatch.setattr(cli, "find_movie_files", fake_find_movie_files)

    with pytest.raises(cli.MovieNotFoundError, match="No movies found matching"):
        cli.select_movie_file("zzzz", config)

    assert calls == [False]


def test_select_movie_file_skips_refresh_when_cache_disabled(monkeypatch, tmp_path):
    movies_dir = tmp_path / "movies"
    clips_dir = tmp_path / "clips"
    movies_dir.mkdir()
    clips_dir.mkdir()
    config = cli.Config(
        directories=cli.DirectoryConfig(movies_dir=movies_dir, clips_dir=clips_dir),
        settings=cli.Settings(cache_enabled=False),
    )
    other_movie = movies_dir / "Other.mkv"
    other_movie.write_text("data", encoding="utf-8")

    calls = []

    def fake_find_movie_files(
        _movies_dir,
        _extensions,
        follow_symlinks=True,
        config_value=None,
        force_refresh=False,
        include_cache_source=False,
    ):
        calls.append(force_refresh)
        if include_cache_source:
            return [other_movie], False
        return [other_movie]

    monkeypatch.setattr(cli, "find_movie_files", fake_find_movie_files)

    with pytest.raises(cli.MovieNotFoundError, match="No movies found matching"):
        cli.select_movie_file("zzzz", config)

    assert calls == [False]


def test_select_movie_file_prompts_until_selection_is_valid(monkeypatch, tmp_path):
    config = make_config(tmp_path)
    movie_a = config.directories.movies_dir / "A" / "alpha.mkv"
    movie_b = config.directories.movies_dir / "B" / "beta.mkv"
    movie_a.parent.mkdir()
    movie_b.parent.mkdir()
    movie_a.write_text("data", encoding="utf-8")
    movie_b.write_text("data", encoding="utf-8")
    prompts = iter(["hello", "3", "2"])
    messages = []

    def fake_find_movie_files(*_args, include_cache_source=False, **_kwargs):
        if include_cache_source:
            return [movie_a, movie_b], False
        return [movie_a, movie_b]

    def fake_print(*args, **_kwargs):
        messages.append(" ".join(str(arg) for arg in args))

    monkeypatch.setattr(cli, "find_movie_files", fake_find_movie_files)
    monkeypatch.setattr(
        cli,
        "fuzzy_match_movie",
        lambda _query, _movie_files: [(movie_a, 80.0), (movie_b, 79.0)],
    )
    monkeypatch.setattr(cli.Prompt, "ask", lambda *_args, **_kwargs: next(prompts))
    monkeypatch.setattr(cli.console, "print", fake_print)

    selected = cli.select_movie_file("movie", config)

    assert selected == movie_b
    assert any("Please enter a number" in message for message in messages)
    assert any("Invalid selection" in message for message in messages)


def test_main_requires_movie_input():
    runner = CliRunner()
    result = runner.invoke(cli.main, [])

    assert result.exit_code == 1
    assert "Movie input is required" in result.output


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


def test_main_exits_on_invalid_time_input(monkeypatch, tmp_path):
    config = make_config(tmp_path)
    movie_file = config.directories.movies_dir / "movie.mkv"
    movie_file.write_text("data", encoding="utf-8")

    monkeypatch.setattr(
        cli,
        "check_ffmpeg",
        lambda *_args, **_kwargs: cli.FfmpegTools(ffmpeg=Path("/usr/bin/ffmpeg"), ffprobe=None),
    )
    monkeypatch.setattr(cli, "load_config", lambda: config)
    monkeypatch.setattr(cli, "select_movie_file", lambda *_args, **_kwargs: movie_file)

    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        [
            "--start",
            "not-a-time",
            "--duration",
            "10",
            "movie.mkv",
        ],
    )

    assert result.exit_code == 1
    assert "Time parsing error" in result.output


def test_main_exits_when_ffmpeg_execution_fails(monkeypatch, tmp_path):
    config = make_config(tmp_path)
    movie_file = config.directories.movies_dir / "movie.mkv"
    movie_file.write_text("data", encoding="utf-8")
    command = ["ffmpeg", "-i", "movie.mkv"]
    captured = {}

    monkeypatch.setattr(
        cli,
        "check_ffmpeg",
        lambda *_args, **_kwargs: cli.FfmpegTools(ffmpeg=Path("/usr/bin/ffmpeg"), ffprobe=None),
    )
    monkeypatch.setattr(cli, "load_config", lambda: config)
    monkeypatch.setattr(cli, "select_movie_file", lambda *_args, **_kwargs: movie_file)
    monkeypatch.setattr(cli, "build_ffmpeg_command", lambda *_args, **_kwargs: command)
    monkeypatch.setattr(cli.Confirm, "ask", lambda *_args, **_kwargs: True)

    def fake_execute_ffmpeg(command_value):
        captured["command"] = command_value
        return False

    monkeypatch.setattr(cli, "execute_ffmpeg", fake_execute_ffmpeg)

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

    assert result.exit_code == 1
    assert "Failed to create clip." in result.output
    assert captured["command"] == command


def test_main_refresh_cache_rebuilds_when_disabled(monkeypatch, tmp_path):
    movies_dir = tmp_path / "movies"
    clips_dir = tmp_path / "clips"
    movies_dir.mkdir()
    clips_dir.mkdir()
    config = cli.Config(
        directories=cli.DirectoryConfig(
            movies_dir=movies_dir,
            clips_dir=clips_dir,
        ),
        settings=cli.Settings(cache_enabled=False),
    )

    monkeypatch.setattr(cli, "load_config", lambda: config)

    captured = {}

    def fake_build_movie_cache(movies_dir_value, extensions, follow_symlinks):
        captured["movies_dir"] = movies_dir_value
        captured["extensions"] = extensions
        captured["follow_symlinks"] = follow_symlinks
        return {
            "timestamp": 0,
            "movies_dir": str(movies_dir_value),
            "follow_symlinks": follow_symlinks,
            "extensions": list(extensions),
            "movies": [],
        }

    def fake_save_movie_cache(cache_data, config_value):
        captured["saved_cache"] = cache_data
        captured["saved_config"] = config_value

    monkeypatch.setattr(cli, "build_movie_cache", fake_build_movie_cache)
    monkeypatch.setattr(cli, "save_movie_cache", fake_save_movie_cache)

    def fail_select_movie_file(*_args, **_kwargs):
        raise AssertionError("Unexpected search")

    monkeypatch.setattr(cli, "select_movie_file", fail_select_movie_file)

    runner = CliRunner()
    result = runner.invoke(cli.main, ["--refresh-cache"])

    assert result.exit_code == 0
    assert captured["movies_dir"] == movies_dir
    assert captured["extensions"] == config.settings.video_extensions
    assert captured["follow_symlinks"] is config.settings.follow_symlinks
    assert captured["saved_cache"]["movies"] == []
    assert captured["saved_config"] is config


def test_main_refresh_cache_rejects_clear_cache():
    runner = CliRunner()
    result = runner.invoke(cli.main, ["--refresh-cache", "--clear-cache"])

    assert result.exit_code == 2
    assert "--refresh-cache cannot be used with --clear-cache." in result.output


def test_main_clear_cache_calls_invalidate_cache(monkeypatch, tmp_path):
    config = make_config(tmp_path)
    captured = {}

    monkeypatch.setattr(cli, "load_config", lambda: config)

    def fake_invalidate_movie_cache(config_value):
        captured["config"] = config_value

    monkeypatch.setattr(cli, "invalidate_movie_cache", fake_invalidate_movie_cache)

    runner = CliRunner()
    result = runner.invoke(cli.main, ["--clear-cache"])

    assert result.exit_code == 0
    assert captured["config"] is config


def test_main_cache_info_prints_cache_details(monkeypatch, tmp_path):
    config = make_config(tmp_path)
    monkeypatch.setattr(cli, "load_config", lambda: config)
    monkeypatch.setattr(
        cli,
        "get_cache_info",
        lambda _config: {
            "exists": True,
            "path": "/tmp/movie_index.json",
            "movies_count": 3,
            "age_hours": 4.5,
            "movies_dir": "/movies",
            "size_bytes": 2048,
        },
    )

    runner = CliRunner()
    result = runner.invoke(cli.main, ["--cache-info"])

    assert result.exit_code == 0
    assert "Cache Information:" in result.output
    assert "Path: /tmp/movie_index.json" in result.output
    assert "Movies: 3" in result.output
    assert "Age: 4.5 hours" in result.output
    assert "Size: 2.0 KB" in result.output
    assert "Movies Directory: /movies" in result.output


def test_main_cache_info_prints_missing_cache_message(monkeypatch, tmp_path):
    config = make_config(tmp_path)
    monkeypatch.setattr(cli, "load_config", lambda: config)
    monkeypatch.setattr(cli, "get_cache_info", lambda _config: {"exists": False})

    runner = CliRunner()
    result = runner.invoke(cli.main, ["--cache-info"])

    assert result.exit_code == 0
    assert "No cache found" in result.output


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


def test_resolve_executable_prefers_explicit_candidate(monkeypatch, tmp_path):
    explicit_path = tmp_path / "explicit-ffmpeg"
    explicit_path.write_text("", encoding="utf-8")
    explicit_path.chmod(0o755)
    env_path = tmp_path / "env-ffmpeg"
    env_path.write_text("", encoding="utf-8")
    env_path.chmod(0o755)

    monkeypatch.setenv("MOVIECLIPPER_FFMPEG", str(env_path))
    monkeypatch.setattr(cli.shutil, "which", lambda _name: None)

    resolved = cli._resolve_executable(
        str(explicit_path),
        "MOVIECLIPPER_FFMPEG",
        "ffmpeg",
    )

    assert resolved == explicit_path


def test_resolve_executable_uses_env_var(monkeypatch, tmp_path):
    env_path = tmp_path / "ffmpeg-from-env"
    env_path.write_text("", encoding="utf-8")
    env_path.chmod(0o755)

    monkeypatch.setenv("MOVIECLIPPER_FFMPEG", str(env_path))
    monkeypatch.setattr(cli.shutil, "which", lambda _name: None)

    resolved = cli._resolve_executable(None, "MOVIECLIPPER_FFMPEG", "ffmpeg")

    assert resolved == env_path


def test_resolve_executable_falls_back_to_path_lookup(monkeypatch):
    monkeypatch.delenv("MOVIECLIPPER_FFMPEG", raising=False)
    monkeypatch.setattr(cli.shutil, "which", lambda _name: "/usr/local/bin/ffmpeg")

    resolved = cli._resolve_executable(None, "MOVIECLIPPER_FFMPEG", "ffmpeg")

    assert resolved == Path("/usr/local/bin/ffmpeg")


def test_resolve_executable_rejects_missing_file(monkeypatch, tmp_path):
    missing_path = tmp_path / "missing-ffmpeg"
    monkeypatch.setenv("MOVIECLIPPER_FFMPEG", str(missing_path))

    with pytest.raises(ValueError, match="does not exist"):
        cli._resolve_executable(None, "MOVIECLIPPER_FFMPEG", "ffmpeg")


def test_resolve_executable_rejects_non_executable(monkeypatch, tmp_path):
    ffmpeg_path = tmp_path / "ffmpeg"
    ffmpeg_path.write_text("", encoding="utf-8")
    ffmpeg_path.chmod(0o644)
    monkeypatch.setenv("MOVIECLIPPER_FFMPEG", str(ffmpeg_path))

    with pytest.raises(ValueError, match="not executable"):
        cli._resolve_executable(None, "MOVIECLIPPER_FFMPEG", "ffmpeg")


def test_resolve_imageio_ffmpeg_returns_none_on_import_error(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "imageio_ffmpeg":
            raise ImportError("missing optional dependency")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert cli._resolve_imageio_ffmpeg() is None


def test_resolve_imageio_ffmpeg_returns_path_from_module(monkeypatch):
    fake_module = types.ModuleType("imageio_ffmpeg")
    fake_module.get_ffmpeg_exe = lambda: "/opt/imageio/ffmpeg"
    monkeypatch.setitem(sys.modules, "imageio_ffmpeg", fake_module)

    assert cli._resolve_imageio_ffmpeg() == Path("/opt/imageio/ffmpeg")


def test_resolve_imageio_ffmpeg_returns_none_on_lookup_error(monkeypatch):
    fake_module = types.ModuleType("imageio_ffmpeg")

    def fake_get_ffmpeg_exe():
        raise RuntimeError("bad state")

    fake_module.get_ffmpeg_exe = fake_get_ffmpeg_exe
    monkeypatch.setitem(sys.modules, "imageio_ffmpeg", fake_module)

    assert cli._resolve_imageio_ffmpeg() is None


def test_resolve_ffmpeg_tools_uses_imageio_ffmpeg_and_sibling_ffprobe(monkeypatch, tmp_path):
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    ffmpeg_path = tools_dir / "ffmpeg"
    ffprobe_path = tools_dir / "ffprobe"
    ffmpeg_path.write_text("", encoding="utf-8")
    ffprobe_path.write_text("", encoding="utf-8")
    ffmpeg_path.chmod(0o755)
    ffprobe_path.chmod(0o755)

    monkeypatch.setattr(cli, "_resolve_executable", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli, "_resolve_imageio_ffmpeg", lambda: ffmpeg_path)

    tools = cli.resolve_ffmpeg_tools(None, None)

    assert tools.ffmpeg == ffmpeg_path
    assert tools.ffprobe == ffprobe_path


def test_resolve_ffmpeg_tools_exits_when_ffmpeg_path_invalid(monkeypatch, capsys):
    def fake_resolve_executable(_candidate, env_key, _default_name):
        if env_key == "MOVIECLIPPER_FFMPEG":
            raise ValueError("invalid ffmpeg")
        return None

    monkeypatch.setattr(cli, "_resolve_executable", fake_resolve_executable)

    with pytest.raises(SystemExit, match="1"):
        cli.resolve_ffmpeg_tools(None, None)

    captured = capsys.readouterr()
    assert "invalid ffmpeg" in captured.out


def test_resolve_ffmpeg_tools_exits_when_ffprobe_path_invalid(monkeypatch, capsys):
    ffmpeg_path = Path("/usr/bin/ffmpeg")

    def fake_resolve_executable(_candidate, env_key, _default_name):
        if env_key == "MOVIECLIPPER_FFMPEG":
            return ffmpeg_path
        raise ValueError("invalid ffprobe")

    monkeypatch.setattr(cli, "_resolve_executable", fake_resolve_executable)

    with pytest.raises(SystemExit, match="1"):
        cli.resolve_ffmpeg_tools(None, None)

    captured = capsys.readouterr()
    assert "invalid ffprobe" in captured.out


def test_check_ffmpeg_warns_when_ffprobe_missing(monkeypatch, tmp_path, capsys):
    ffmpeg_path = tmp_path / "ffmpeg"
    ffmpeg_path.write_text("", encoding="utf-8")
    ffmpeg_path.chmod(0o755)

    monkeypatch.setattr(
        cli,
        "resolve_ffmpeg_tools",
        lambda _ffmpeg_path, _ffprobe_path: cli.FfmpegTools(ffmpeg=ffmpeg_path, ffprobe=None),
    )
    checked = []
    monkeypatch.setattr(cli, "_verify_tool", lambda path, label: checked.append((path, label)))

    tools = cli.check_ffmpeg(None, None, require_ffprobe=False)

    assert tools.ffmpeg == ffmpeg_path
    assert tools.ffprobe is None
    assert checked == [(ffmpeg_path, "ffmpeg")]
    assert "ffprobe not found" in capsys.readouterr().out


def test_check_ffmpeg_requires_ffprobe_when_requested(monkeypatch, tmp_path):
    ffmpeg_path = tmp_path / "ffmpeg"
    ffmpeg_path.write_text("", encoding="utf-8")
    ffmpeg_path.chmod(0o755)

    monkeypatch.setattr(
        cli,
        "resolve_ffmpeg_tools",
        lambda _ffmpeg_path, _ffprobe_path: cli.FfmpegTools(ffmpeg=ffmpeg_path, ffprobe=None),
    )
    checked = []
    monkeypatch.setattr(cli, "_verify_tool", lambda path, label: checked.append((path, label)))

    with pytest.raises(SystemExit, match="1"):
        cli.check_ffmpeg(None, None, require_ffprobe=True)

    assert checked == [(ffmpeg_path, "ffmpeg")]


def test_check_ffmpeg_verifies_ffprobe_when_available(monkeypatch, tmp_path):
    ffmpeg_path = tmp_path / "ffmpeg"
    ffprobe_path = tmp_path / "ffprobe"
    ffmpeg_path.write_text("", encoding="utf-8")
    ffprobe_path.write_text("", encoding="utf-8")
    ffmpeg_path.chmod(0o755)
    ffprobe_path.chmod(0o755)

    monkeypatch.setattr(
        cli,
        "resolve_ffmpeg_tools",
        lambda _ffmpeg_path, _ffprobe_path: cli.FfmpegTools(
            ffmpeg=ffmpeg_path,
            ffprobe=ffprobe_path,
        ),
    )
    checked = []
    monkeypatch.setattr(cli, "_verify_tool", lambda path, label: checked.append((path, label)))

    tools = cli.check_ffmpeg(None, None)

    assert tools.ffprobe == ffprobe_path
    assert checked == [(ffmpeg_path, "ffmpeg"), (ffprobe_path, "ffprobe")]


def test_check_environment_reports_tools_and_config(monkeypatch, tmp_path, capsys):
    ffmpeg_path = tmp_path / "ffmpeg"
    ffprobe_path = tmp_path / "ffprobe"
    ffmpeg_path.write_text("", encoding="utf-8")
    ffprobe_path.write_text("", encoding="utf-8")
    ffmpeg_path.chmod(0o755)
    ffprobe_path.chmod(0o755)
    config_path = tmp_path / "movieclipper.toml"
    config_path.write_text("", encoding="utf-8")

    captured = {}

    def fake_check_ffmpeg(ffmpeg_path_arg, ffprobe_path_arg, require_ffprobe=False):
        captured["ffmpeg_path"] = ffmpeg_path_arg
        captured["ffprobe_path"] = ffprobe_path_arg
        captured["require_ffprobe"] = require_ffprobe
        return cli.FfmpegTools(ffmpeg=ffmpeg_path, ffprobe=ffprobe_path)

    monkeypatch.setattr(cli, "check_ffmpeg", fake_check_ffmpeg)
    monkeypatch.setattr(cli, "get_config_path", lambda: config_path)
    monkeypatch.setattr(cli, "read_config", lambda _path: make_config(tmp_path))

    cli.check_environment("ffmpeg-custom", "ffprobe-custom")

    assert captured == {
        "ffmpeg_path": "ffmpeg-custom",
        "ffprobe_path": "ffprobe-custom",
        "require_ffprobe": False,
    }
    output = capsys.readouterr().out
    normalized_output = output.replace("\n", "")
    assert str(ffmpeg_path) in output
    assert str(ffprobe_path) in output
    assert str(config_path) in normalized_output


def test_check_environment_exits_when_config_missing(monkeypatch, tmp_path):
    ffmpeg_path = tmp_path / "ffmpeg"
    ffmpeg_path.write_text("", encoding="utf-8")
    ffmpeg_path.chmod(0o755)
    config_path = tmp_path / "missing-config.toml"

    monkeypatch.setattr(
        cli,
        "check_ffmpeg",
        lambda _ffmpeg_path, _ffprobe_path, require_ffprobe=False: cli.FfmpegTools(
            ffmpeg=ffmpeg_path, ffprobe=None
        ),
    )
    monkeypatch.setattr(cli, "get_config_path", lambda: config_path)

    with pytest.raises(SystemExit, match="1"):
        cli.check_environment(None, None)


def test_check_environment_exits_when_config_invalid(monkeypatch, tmp_path, capsys):
    ffmpeg_path = tmp_path / "ffmpeg"
    ffmpeg_path.write_text("", encoding="utf-8")
    ffmpeg_path.chmod(0o755)
    config_path = tmp_path / "movieclipper.toml"
    config_path.write_text("invalid", encoding="utf-8")

    monkeypatch.setattr(
        cli,
        "check_ffmpeg",
        lambda _ffmpeg_path, _ffprobe_path, require_ffprobe=False: cli.FfmpegTools(
            ffmpeg=ffmpeg_path, ffprobe=None
        ),
    )
    monkeypatch.setattr(cli, "get_config_path", lambda: config_path)
    monkeypatch.setattr(
        cli,
        "read_config",
        lambda _path: (_ for _ in ()).throw(FileNotFoundError("broken config")),
    )

    with pytest.raises(SystemExit, match="1"):
        cli.check_environment(None, None)

    assert "Config file is invalid" in capsys.readouterr().out


def test_main_check_invokes_check_environment(monkeypatch):
    captured = {}

    def fake_check_environment(ffmpeg_path, ffprobe_path):
        captured["ffmpeg_path"] = ffmpeg_path
        captured["ffprobe_path"] = ffprobe_path

    monkeypatch.setattr(cli, "check_environment", fake_check_environment)

    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--check", "--ffmpeg-path", "/tools/ffmpeg", "--ffprobe-path", "/tools/ffprobe"],
    )

    assert result.exit_code == 0
    assert captured == {
        "ffmpeg_path": "/tools/ffmpeg",
        "ffprobe_path": "/tools/ffprobe",
    }


def test_detect_audio_streams_returns_default_when_ffprobe_missing():
    streams = cli.detect_audio_streams(Path("/movies/title.mkv"), ffprobe_path=None)

    assert streams == [{"index": 0, "language": "unknown", "channels": 2, "stream_index": 0}]


def test_detect_audio_streams_parses_ffprobe_output(monkeypatch, tmp_path):
    movie_file = tmp_path / "movie.mkv"
    ffprobe_path = tmp_path / "ffprobe"
    movie_file.write_text("", encoding="utf-8")
    ffprobe_path.write_text("", encoding="utf-8")
    ffprobe_path.chmod(0o755)
    captured = {}

    def fake_run(command, capture_output, text, check):
        captured["command"] = command
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["check"] = check
        return types.SimpleNamespace(
            stdout=json.dumps(
                {
                    "streams": [
                        {
                            "index": 4,
                            "codec_name": "aac",
                            "channels": 6,
                            "sample_rate": "48000",
                            "tags": {"language": "jpn", "title": "Main"},
                        },
                        {"tags": {"language": "eng"}},
                    ]
                }
            )
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    streams = cli.detect_audio_streams(movie_file, ffprobe_path)

    assert captured == {
        "command": [
            str(ffprobe_path),
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-select_streams",
            "a",
            str(movie_file),
        ],
        "capture_output": True,
        "text": True,
        "check": True,
    }
    assert streams == [
        {
            "index": 0,
            "codec_name": "aac",
            "channels": 6,
            "sample_rate": "48000",
            "language": "jpn",
            "title": "Main",
            "stream_index": 4,
        },
        {
            "index": 1,
            "codec_name": "unknown",
            "channels": 0,
            "sample_rate": 0,
            "language": "eng",
            "title": "",
            "stream_index": 1,
        },
    ]


def test_detect_audio_streams_falls_back_on_ffprobe_error(monkeypatch, tmp_path, capsys):
    movie_file = tmp_path / "movie.mkv"
    ffprobe_path = tmp_path / "ffprobe"
    movie_file.write_text("", encoding="utf-8")
    ffprobe_path.write_text("", encoding="utf-8")
    ffprobe_path.chmod(0o755)

    def fake_run(*_args, **_kwargs):
        raise cli.subprocess.CalledProcessError(1, "ffprobe")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    streams = cli.detect_audio_streams(movie_file, ffprobe_path)

    assert streams == [{"index": 0, "language": "unknown", "channels": 2, "stream_index": 0}]
    assert "Could not detect audio streams" in capsys.readouterr().out


def test_detect_audio_streams_falls_back_on_invalid_json(monkeypatch, tmp_path, capsys):
    movie_file = tmp_path / "movie.mkv"
    ffprobe_path = tmp_path / "ffprobe"
    movie_file.write_text("", encoding="utf-8")
    ffprobe_path.write_text("", encoding="utf-8")
    ffprobe_path.chmod(0o755)

    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *_args, **_kwargs: types.SimpleNamespace(stdout="{invalid-json"),
    )

    streams = cli.detect_audio_streams(movie_file, ffprobe_path)

    assert streams == [{"index": 0, "language": "unknown", "channels": 2, "stream_index": 0}]
    assert "Could not detect audio streams" in capsys.readouterr().out


def test_default_directories_prefers_existing_home(monkeypatch, tmp_path):
    home = tmp_path / "home"
    videos = home / "Videos"
    videos.mkdir(parents=True)

    monkeypatch.setattr(cli.Path, "home", lambda: home)
    monkeypatch.setattr(cli.Path, "cwd", lambda: tmp_path)
    monkeypatch.setattr(cli, "_is_wsl", lambda: False)

    movies_dir, clips_dir = cli.default_directories()
    assert movies_dir == videos
    assert clips_dir == videos / "clips"


def test_default_directories_falls_back_to_cwd(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    monkeypatch.setattr(cli.Path, "home", lambda: home)
    monkeypatch.setattr(cli.Path, "cwd", lambda: tmp_path)
    monkeypatch.setattr(cli, "_is_wsl", lambda: False)

    movies_dir, clips_dir = cli.default_directories()
    assert movies_dir == tmp_path
    assert clips_dir == tmp_path / "clips"


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli.main, ["--version"])
    assert result.exit_code == 0
    assert "movieclipper" in result.output


@patch.object(Path, "read_text", return_value="Linux 5.15.0 microsoft-standard-WSL2")
def test_is_wsl_returns_true(_mock_read):
    assert cli._is_wsl() is True


@patch.object(Path, "read_text", return_value="Linux 6.1.0-generic")
def test_is_wsl_returns_false_when_not_wsl(_mock_read):
    assert cli._is_wsl() is False


@patch.object(Path, "read_text", side_effect=FileNotFoundError)
def test_is_wsl_returns_false_on_missing_file(_mock_read):
    assert cli._is_wsl() is False


def test_get_windows_home_parses_userprofile(monkeypatch):
    def fake_run(cmd, **kwargs):
        class FakeResult:
            stdout = r"C:\Users\TestUser" + "\n"
            returncode = 0

        return FakeResult()

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli._get_windows_home()
    assert result == Path("/mnt/c/Users/TestUser")


def test_get_windows_home_returns_none_on_failure(monkeypatch):
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("cmd.exe not found")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    assert cli._get_windows_home() is None


def test_default_directories_wsl_prefers_windows_videos(monkeypatch, tmp_path):
    home = tmp_path / "linux_home"
    home.mkdir()
    win_home = tmp_path / "mnt" / "c" / "Users" / "Test"
    win_videos = win_home / "Videos"
    win_videos.mkdir(parents=True)

    monkeypatch.setattr(cli.Path, "home", lambda: home)
    monkeypatch.setattr(cli.Path, "cwd", lambda: tmp_path)
    monkeypatch.setattr(cli, "_is_wsl", lambda: True)
    monkeypatch.setattr(cli, "_get_windows_home", lambda: win_home)

    movies_dir, clips_dir = cli.default_directories()
    assert movies_dir == win_videos
    assert clips_dir == win_videos / "clips"


def test_default_directories_wsl_falls_back_to_linux(monkeypatch, tmp_path):
    home = tmp_path / "linux_home"
    linux_videos = home / "Videos"
    linux_videos.mkdir(parents=True)

    monkeypatch.setattr(cli.Path, "home", lambda: home)
    monkeypatch.setattr(cli.Path, "cwd", lambda: tmp_path)
    monkeypatch.setattr(cli, "_is_wsl", lambda: True)
    monkeypatch.setattr(cli, "_get_windows_home", lambda: None)

    movies_dir, clips_dir = cli.default_directories()
    assert movies_dir == linux_videos
    assert clips_dir == linux_videos / "clips"


def test_setup_warns_when_ffmpeg_missing(monkeypatch, tmp_path):
    movies_dir = tmp_path / "movies"
    clips_dir = tmp_path / "clips"
    movies_dir.mkdir()
    clips_dir.mkdir()

    monkeypatch.setattr(
        cli,
        "setup_config",
        lambda: cli.Config(
            directories=cli.DirectoryConfig(movies_dir=movies_dir, clips_dir=clips_dir),
        ),
    )
    monkeypatch.setattr(cli.shutil, "which", lambda _name: None)
    monkeypatch.setattr(cli, "_resolve_imageio_ffmpeg", lambda: None)

    runner = CliRunner()
    result = runner.invoke(cli.main, ["--setup"])

    assert result.exit_code == 0
    assert "ffmpeg not found" in result.output


def test_setup_no_warning_when_ffmpeg_present(monkeypatch, tmp_path):
    movies_dir = tmp_path / "movies"
    clips_dir = tmp_path / "clips"
    movies_dir.mkdir()
    clips_dir.mkdir()

    monkeypatch.setattr(
        cli,
        "setup_config",
        lambda: cli.Config(
            directories=cli.DirectoryConfig(movies_dir=movies_dir, clips_dir=clips_dir),
        ),
    )
    monkeypatch.setattr(cli.shutil, "which", lambda _name: "/usr/bin/ffmpeg")

    runner = CliRunner()
    result = runner.invoke(cli.main, ["--setup"])

    assert result.exit_code == 0
    assert "ffmpeg not found" not in result.output
