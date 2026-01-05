from pathlib import Path

import pytest

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


def test_parse_time_formats():
    assert cli.parse_time("90") == 90
    assert cli.parse_time("1:30") == 90
    assert cli.parse_time("01:02:03") == 3723


def test_parse_time_invalid():
    with pytest.raises(ValueError):
        cli.parse_time("1:2:3:4")


def test_format_time():
    assert cli.format_time(3723) == "01:02:03"


def test_generate_output_filename():
    movie_file = Path("Iron.Man.2008.BluRay.x264.mkv")
    filename = cli.generate_output_filename(movie_file, 60, 120)
    assert filename == "IronMan_00h01m00s_to_00h02m00s.mp4"


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
    )

    assert command[0] == "/usr/bin/ffmpeg"
    assert "-map" in command
    assert "0:a:1" in command
    assert "-ac" in command
    assert str(config.settings.default_audio_channels) in command


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
