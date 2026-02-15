import pytest

from deadlock_hero_ability_statistics_image_extractor.main import (
    DeadlockLauncher,
    _parse_xdotool_window_geometry,
    _parse_xrandr_primary_resolution,
    validate_input_automation_environment,
)


def test_deadlock_process_detection_ignores_extractor_name():
    proc_info = {
        "name": "deadlock-extractor",
        "exe": "/usr/bin/python3",
        "cmdline": ["deadlock-extractor-web"],
    }

    assert DeadlockLauncher._is_deadlock_process_info(proc_info) is False


def test_deadlock_process_detection_matches_game_executable_in_cmdline():
    proc_info = {
        "name": "python3",
        "exe": "/usr/bin/python3",
        "cmdline": ["python3", "launcher.py", "/games/Deadlock/deadlock.exe"],
    }

    assert DeadlockLauncher._is_deadlock_process_info(proc_info) is True


def test_parse_xrandr_primary_resolution_prefers_primary_monitor():
    output = """
Screen 0: minimum 16 x 16, current 6400 x 2520, maximum 32767 x 32767
DP-1 connected primary 2560x1440+0+0 (normal left inverted right x axis y axis) 597mm x 336mm
HDMI-1 connected 3840x2160+2560+0 (normal left inverted right x axis y axis) 600mm x 340mm
"""

    assert _parse_xrandr_primary_resolution(output) == (2560, 1440)


def test_validate_input_automation_environment_blocks_wayland_by_default():
    with pytest.raises(RuntimeError, match="Wayland session detected"):
        validate_input_automation_environment(
            platform_name="linux",
            session_type="wayland",
            allow_wayland_override=False,
        )


def test_validate_input_automation_environment_allows_x11_or_override():
    validate_input_automation_environment(
        platform_name="linux",
        session_type="x11",
        allow_wayland_override=False,
    )
    validate_input_automation_environment(
        platform_name="linux",
        session_type="wayland",
        allow_wayland_override=True,
    )


def test_parse_xdotool_window_geometry_extracts_region():
    output = """
WINDOW=73400324
X=3840
Y=0
WIDTH=2560
HEIGHT=1440
SCREEN=1
"""

    assert _parse_xdotool_window_geometry(output) == (3840, 0, 2560, 1440)


def test_parse_xdotool_window_geometry_rejects_invalid_input():
    assert _parse_xdotool_window_geometry("X=0\nY=0\nWIDTH=0\nHEIGHT=1440") is None
    assert _parse_xdotool_window_geometry("X=0\nY=0\nWIDTH=1920") is None
