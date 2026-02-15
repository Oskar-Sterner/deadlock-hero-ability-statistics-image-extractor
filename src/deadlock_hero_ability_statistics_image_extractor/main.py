import subprocess
import time
import psutil
import os
import asyncio
import shutil
import requests
import platform
import argparse
import re
from pathlib import Path
from typing import Optional, List, Tuple
import pyautogui
import pynput.keyboard as keyboard
from .tooltip_detector import TooltipDetector


DEFAULT_STEAM_APP_ID = "1422450"
DEFAULT_BASE_RESOLUTION = (1920, 1080)
VALID_PLATFORM_OVERRIDES = {"auto", "windows", "linux"}
VALID_LAUNCH_MODES = {"auto", "direct", "steam"}
GAME_PROCESS_NAMES = {"deadlock", "deadlock.exe"}
GAME_PROCESS_START_TIMEOUT_SECONDS = 30
GAME_MAIN_MENU_TIMEOUT_SECONDS = 180
GAME_INITIALIZATION_DELAY_SECONDS = 30
ALLOW_WAYLAND_OVERRIDE_ENV = "DEADLOCK_ALLOW_WAYLAND"


def get_sort_name(name):
    if name.startswith("The "):
        return name[4:]
    return name


def detect_host_platform() -> str:
    current = platform.system().strip().lower()
    if current.startswith("win"):
        return "windows"
    if current.startswith("linux"):
        return "linux"
    return current


def resolve_platform(platform_override: str = "auto") -> str:
    override = (platform_override or "auto").strip().lower()
    if override not in VALID_PLATFORM_OVERRIDES:
        raise ValueError(
            f"Invalid platform override '{platform_override}'. "
            f"Expected one of: {sorted(VALID_PLATFORM_OVERRIDES)}"
        )

    if override != "auto":
        return override

    detected = detect_host_platform()
    if detected in {"windows", "linux"}:
        return detected

    raise RuntimeError(
        "Unsupported host platform detected. "
        "This tool currently supports only Windows and Linux."
    )


def _collect_steamlibrary_mount_candidates(mount_root: Path) -> List[Path]:
    candidates: List[Path] = []
    if not mount_root.exists() or not mount_root.is_dir():
        return candidates

    try:
        entries = list(mount_root.iterdir())
    except OSError:
        return candidates

    for entry in entries:
        deadlock_bin = (
            entry
            / "SteamLibrary"
            / "steamapps"
            / "common"
            / "Deadlock"
            / "game"
            / "bin"
        )
        candidates.append(deadlock_bin / "linuxsteamrt64" / "deadlock")
        candidates.append(deadlock_bin / "win64" / "deadlock.exe")

    return candidates


def get_candidate_game_paths(platform_override: str = "auto") -> List[Path]:
    platform_name = resolve_platform(platform_override)
    candidates: List[Path] = []

    if platform_name == "windows":
        candidates.extend(
            [
                Path(
                    r"C:/Program Files (x86)/Steam/steamapps/common/Deadlock/game/bin/win64/deadlock.exe"
                ),
                Path(r"D:/Steam/steamapps/common/Deadlock/game/bin/win64/deadlock.exe"),
            ]
        )
        for drive in "CDEFG":
            candidates.append(
                Path(
                    f"{drive}:/SteamLibrary/steamapps/common/Deadlock/game/bin/win64/deadlock.exe"
                )
            )
    else:
        home = Path.home()
        candidates.extend(
            [
                home
                / ".steam"
                / "steam"
                / "steamapps"
                / "common"
                / "Deadlock"
                / "game"
                / "bin"
                / "linuxsteamrt64"
                / "deadlock",
                home
                / ".local"
                / "share"
                / "Steam"
                / "steamapps"
                / "common"
                / "Deadlock"
                / "game"
                / "bin"
                / "linuxsteamrt64"
                / "deadlock",
                home
                / ".steam"
                / "steam"
                / "steamapps"
                / "common"
                / "Deadlock"
                / "game"
                / "bin"
                / "win64"
                / "deadlock.exe",
                home
                / ".local"
                / "share"
                / "Steam"
                / "steamapps"
                / "common"
                / "Deadlock"
                / "game"
                / "bin"
                / "win64"
                / "deadlock.exe",
            ]
        )

        for mount_root in (Path("/mnt"), Path("/media"), Path("/run/media")):
            candidates.extend(_collect_steamlibrary_mount_candidates(mount_root))

    unique_candidates: List[Path] = []
    seen: set = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(path)

    return unique_candidates


def parse_display_resolution(
    width: Optional[int], height: Optional[int]
) -> Optional[Tuple[int, int]]:
    if width is None and height is None:
        return None

    if width is None or height is None:
        raise ValueError(
            "Both display width and display height must be provided together."
        )

    if width <= 0 or height <= 0:
        raise ValueError("Display width and height must be positive integers.")

    return int(width), int(height)


def _parse_xrandr_primary_resolution(output: str) -> Optional[Tuple[int, int]]:
    connected_resolutions: List[Tuple[int, int]] = []

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if " connected" not in line or "disconnected" in line:
            continue

        match = re.search(r"(\d+)x(\d+)\+\d+\+\d+", line)
        if not match:
            continue

        width = int(match.group(1))
        height = int(match.group(2))
        if width <= 0 or height <= 0:
            continue

        if " connected primary " in line:
            return width, height

        connected_resolutions.append((width, height))

    if connected_resolutions:
        return connected_resolutions[0]
    return None


def _parse_xdotool_window_geometry(
    output: str,
) -> Optional[Tuple[int, int, int, int]]:
    parsed_values = {}

    for raw_line in str(output or "").splitlines():
        line = raw_line.strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        normalized_key = key.strip().upper()
        if normalized_key not in {"X", "Y", "WIDTH", "HEIGHT"}:
            continue

        try:
            parsed_values[normalized_key] = int(str(value).strip())
        except ValueError:
            return None

    required = {"X", "Y", "WIDTH", "HEIGHT"}
    if not required.issubset(parsed_values):
        return None

    width = int(parsed_values["WIDTH"])
    height = int(parsed_values["HEIGHT"])
    if width <= 0 or height <= 0:
        return None

    return (
        int(parsed_values["X"]),
        int(parsed_values["Y"]),
        width,
        height,
    )


def _detect_linux_primary_display_resolution() -> Optional[Tuple[int, int]]:
    try:
        result = subprocess.run(
            ["xrandr", "--query"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return None

    if result.returncode != 0:
        return None

    return _parse_xrandr_primary_resolution(result.stdout)


def _detect_windows_primary_display_resolution() -> Optional[Tuple[int, int]]:
    try:
        import ctypes

        user32 = ctypes.windll.user32
        width = int(user32.GetSystemMetrics(0))
        height = int(user32.GetSystemMetrics(1))
        if width > 0 and height > 0:
            return width, height
    except Exception:
        pass

    return None


def detect_primary_display_resolution() -> Tuple[int, int]:
    platform_name = detect_host_platform()

    if platform_name == "linux":
        linux_resolution = _detect_linux_primary_display_resolution()
        if linux_resolution is not None:
            return linux_resolution
    elif platform_name == "windows":
        windows_resolution = _detect_windows_primary_display_resolution()
        if windows_resolution is not None:
            return windows_resolution

    try:
        width, height = pyautogui.size()
        width = int(width)
        height = int(height)
        if width > 0 and height > 0:
            return width, height
    except Exception:
        pass

    return DEFAULT_BASE_RESOLUTION


def validate_input_automation_environment(
    platform_name: Optional[str] = None,
    session_type: Optional[str] = None,
    allow_wayland_override: Optional[bool] = None,
) -> None:
    effective_platform = platform_name or detect_host_platform()
    if effective_platform != "linux":
        return

    if session_type is None:
        raw_session = os.environ.get("XDG_SESSION_TYPE", "")
    else:
        raw_session = session_type

    normalized_session = str(raw_session or "").strip().lower()

    if allow_wayland_override is None:
        allow_wayland = (
            str(os.environ.get(ALLOW_WAYLAND_OVERRIDE_ENV, "")).strip() == "1"
        )
    else:
        allow_wayland = bool(allow_wayland_override)

    if normalized_session == "wayland" and not allow_wayland:
        raise RuntimeError(
            "Wayland session detected. Mouse/keyboard automation with pyautogui/pynput "
            "is unreliable on Wayland and is disabled by default. "
            "Log into an X11 session (Ubuntu on Xorg), or set "
            f"{ALLOW_WAYLAND_OVERRIDE_ENV}=1 to force-enable at your own risk."
        )


def fetch_hero_data():
    try:
        print("Fetching hero data from API...")
        response = requests.get(
            "https://assets.deadlock-api.com/v2/heroes?only_active=true", timeout=10
        )
        response.raise_for_status()
        heroes = response.json()
        filtered_heroes = [{"id": hero["id"], "name": hero["name"]} for hero in heroes]
        sorted_heroes = sorted(filtered_heroes, key=lambda x: get_sort_name(x["name"]))
        print(f"Successfully fetched {len(sorted_heroes)} heroes from API")
        return sorted_heroes, True
    except Exception as e:
        print(f"Failed to fetch hero data from API: {e}. Using fallback...")
        fallback_heroes = [
            {"id": 6, "name": "Abrams"},
            {"id": 15, "name": "Bebop"},
            {"id": 72, "name": "Billy"},
            {"id": 16, "name": "Calico"},
            {"id": 69, "name": "The Doorman"},
            {"id": 64, "name": "Drifter"},
            {"id": 11, "name": "Dynamo"},
            {"id": 17, "name": "Grey Talon"},
            {"id": 13, "name": "Haze"},
            {"id": 14, "name": "Holliday"},
            {"id": 1, "name": "Infernus"},
            {"id": 20, "name": "Ivy"},
            {"id": 12, "name": "Kelvin"},
            {"id": 4, "name": "Lady Geist"},
            {"id": 31, "name": "Lash"},
            {"id": 8, "name": "McGinnis"},
            {"id": 63, "name": "Mina"},
            {"id": 52, "name": "Mirage"},
            {"id": 18, "name": "Mo & Krill"},
            {"id": 67, "name": "Paige"},
            {"id": 10, "name": "Paradox"},
            {"id": 50, "name": "Pocket"},
            {"id": 2, "name": "Seven"},
            {"id": 19, "name": "Shiv"},
            {"id": 60, "name": "Sinclair"},
            {"id": 66, "name": "Victor"},
            {"id": 3, "name": "Vindicta"},
            {"id": 35, "name": "Viscous"},
            {"id": 58, "name": "Vyper"},
            {"id": 25, "name": "Warden"},
            {"id": 7, "name": "Wraith"},
            {"id": 27, "name": "Yamato"},
        ]
        return sorted(fallback_heroes, key=lambda x: get_sort_name(x["name"])), False


class ExtractionOptions:
    def __init__(self, extract_abilities=True, extract_stats=False):
        self.extract_abilities = extract_abilities
        self.extract_stats = extract_stats


class CrossPlatformController:
    def __init__(self, websocket_callback=None):
        validate_input_automation_environment()
        self.stop_flag = False
        self.hotkey_listener = None
        self.websocket_callback = websocket_callback
        self.platform_name = detect_host_platform()
        self.session_type = str(os.environ.get("XDG_SESSION_TYPE", "")).strip().lower()
        self.xdotool_path: Optional[str] = None
        self.active_window_id: Optional[str] = None

        if self.platform_name == "linux" and self.session_type == "x11":
            self.xdotool_path = shutil.which("xdotool")
            if self.xdotool_path:
                print("Linux X11 detected: using xdotool input backend.")
            else:
                print(
                    "Linux X11 detected but xdotool is not installed; "
                    "falling back to pyautogui input backend."
                )

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1
        self.start_hotkey_listener()

    def start_hotkey_listener(self):
        def on_hotkey():
            print("\nCtrl+Shift+Q pressed. Stopping program...")
            self.stop_flag = True
        self.hotkey_listener = keyboard.GlobalHotKeys({'<ctrl>+<shift>+q': on_hotkey})
        self.hotkey_listener.start()

    def should_stop(self):
        return self.stop_flag

    def cleanup(self):
        if self.hotkey_listener:
            self.hotkey_listener.stop()

    def get_input_backend_name(self) -> str:
        if self.xdotool_path:
            return "xdotool"
        return "pyautogui"

    @staticmethod
    def _normalize_key_for_xdotool(key: str) -> str:
        normalized = str(key or "").strip().lower()
        key_map = {
            "esc": "Escape",
            "escape": "Escape",
            "enter": "Return",
            "return": "Return",
            "tab": "Tab",
            "left": "Left",
            "right": "Right",
            "up": "Up",
            "down": "Down",
            "space": "space",
        }
        return key_map.get(normalized, normalized)

    def _run_xdotool(self, *args: str) -> bool:
        if not self.xdotool_path:
            return False

        try:
            result = subprocess.run(
                [self.xdotool_path, *args],
                capture_output=True,
                text=True,
                check=False,
                timeout=2,
            )
        except (OSError, subprocess.SubprocessError):
            return False

        if result.returncode != 0:
            stderr = str(result.stderr or "").strip()
            if stderr:
                print(f"xdotool {' '.join(args)} failed: {stderr}")
            return False

        return True

    def _search_window_ids_by_name(self, *patterns: str) -> List[str]:
        if not self.xdotool_path:
            return []

        for pattern in patterns:
            try:
                search_result = subprocess.run(
                    [
                        self.xdotool_path,
                        "search",
                        "--onlyvisible",
                        "--name",
                        pattern,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=2,
                )
            except (OSError, subprocess.SubprocessError):
                continue

            if search_result.returncode != 0:
                continue

            window_ids = [
                line.strip()
                for line in str(search_result.stdout or "").splitlines()
                if line.strip()
            ]
            if window_ids:
                return window_ids

        return []

    def focus_deadlock_window(self) -> bool:
        if not self.xdotool_path:
            return False

        window_ids = self._search_window_ids_by_name(
            "Deadlock",
            "deadlock",
            "steam_app_1422450",
        )
        if not window_ids:
            return False

        target_window_id = window_ids[-1]
        if not self._run_xdotool("windowactivate", "--sync", target_window_id):
            return False

        self.active_window_id = target_window_id
        time.sleep(0.2)
        return True

    def get_active_window_region(self) -> Optional[Tuple[int, int, int, int]]:
        if not self.xdotool_path:
            return None

        window_id = str(self.active_window_id or "").strip()
        if not window_id:
            return None

        try:
            result = subprocess.run(
                [self.xdotool_path, "getwindowgeometry", "--shell", window_id],
                capture_output=True,
                text=True,
                check=False,
                timeout=2,
            )
        except (OSError, subprocess.SubprocessError):
            return None

        if result.returncode != 0:
            stderr = str(result.stderr or "").strip()
            if stderr:
                print(f"xdotool getwindowgeometry failed: {stderr}")
            return None

        return _parse_xdotool_window_geometry(result.stdout)

    @staticmethod
    def _raise_action_error(action: str, exc: Exception) -> None:
        if isinstance(exc, pyautogui.FailSafeException):
            raise RuntimeError(
                "PyAutoGUI fail-safe triggered while attempting to "
                f"{action}. Move the mouse away from the screen corner "
                "and retry extraction."
            ) from exc
        raise exc

    def click(self, x, y):
        if self.stop_flag:
            return
        target_x = int(round(x))
        target_y = int(round(y))

        window_id = self.active_window_id
        if window_id:
            self._run_xdotool("windowactivate", "--sync", window_id)
            if self._run_xdotool(
                "mousemove", "--window", window_id, str(target_x), str(target_y)
            ):
                if self._run_xdotool("click", "1"):
                    return

        if self._run_xdotool("mousemove", "--sync", str(target_x), str(target_y)):
            if self._run_xdotool("click", "1"):
                return

        try:
            pyautogui.click(target_x, target_y)
        except Exception as exc:
            self._raise_action_error("click", exc)

    def move_mouse(self, x, y):
        if self.stop_flag:
            return
        target_x = int(round(x))
        target_y = int(round(y))

        window_id = self.active_window_id
        if window_id:
            self._run_xdotool("windowactivate", "--sync", window_id)
            if self._run_xdotool(
                "mousemove", "--window", window_id, str(target_x), str(target_y)
            ):
                return

        if self._run_xdotool("mousemove", "--sync", str(target_x), str(target_y)):
            return

        try:
            pyautogui.moveTo(target_x, target_y, duration=0.1)
        except Exception as exc:
            self._raise_action_error("move mouse", exc)

    def press_key(self, key):
        if self.stop_flag:
            return

        xdotool_key = self._normalize_key_for_xdotool(key)
        window_id = self.active_window_id
        if window_id and xdotool_key:
            self._run_xdotool("windowactivate", "--sync", window_id)
            if self._run_xdotool("key", "--window", window_id, xdotool_key):
                return

        if xdotool_key and self._run_xdotool("key", xdotool_key):
            return

        try:
            pyautogui.press(key)
        except Exception as exc:
            self._raise_action_error(f"press key '{key}'", exc)


class DeadlockLauncher:
    def __init__(
        self,
        game_path: str,
        websocket_callback=None,
        platform_override: str = "auto",
        launch_mode: str = "auto",
        steam_app_id: str = DEFAULT_STEAM_APP_ID,
    ):
        self.game_path = Path(game_path)
        self.process: Optional[subprocess.Popen] = None
        self.websocket_callback = websocket_callback

        self.platform_name = resolve_platform(platform_override)

        normalized_launch_mode = (launch_mode or "auto").strip().lower()
        if normalized_launch_mode not in VALID_LAUNCH_MODES:
            raise ValueError(
                f"Invalid launch mode '{launch_mode}'. "
                f"Expected one of: {sorted(VALID_LAUNCH_MODES)}"
            )

        self.launch_mode = normalized_launch_mode
        normalized_steam_app_id = str(steam_app_id or "").strip()
        self.steam_app_id = normalized_steam_app_id or DEFAULT_STEAM_APP_ID

    async def send_status(self, message):
        if self.websocket_callback:
            await self.websocket_callback({"type": "status", "message": message})

    @staticmethod
    def _is_deadlock_process_info(proc_info: dict) -> bool:
        candidates: List[str] = []

        process_name = str(proc_info.get("name") or "").strip()
        if process_name:
            candidates.append(Path(process_name).name.lower())

        process_exe = str(proc_info.get("exe") or "").strip()
        if process_exe:
            candidates.append(Path(process_exe).name.lower())

        cmdline = proc_info.get("cmdline") or []
        for cmd_entry in cmdline:
            cmd_part = str(cmd_entry).strip()
            if cmd_part:
                candidates.append(Path(cmd_part).name.lower())

        return any(candidate in GAME_PROCESS_NAMES for candidate in candidates)

    def _resolve_launch_strategy(self) -> Tuple[List[str], Optional[Path], str]:
        selected_mode = self.launch_mode
        if selected_mode == "auto":
            if self.platform_name == "windows":
                selected_mode = "direct"
            else:
                if self.game_path.suffix.lower() == ".exe":
                    selected_mode = "steam"
                elif self.game_path.exists():
                    selected_mode = "direct"
                else:
                    selected_mode = "steam"

        if selected_mode == "direct":
            if not self.game_path.exists():
                raise FileNotFoundError(f"Game executable not found: {self.game_path}")
            return [str(self.game_path)], self.game_path.parent, "direct"

        return ["steam", "-applaunch", self.steam_app_id], None, "steam"

    def is_game_running(self) -> bool:
        for proc in psutil.process_iter(["name", "exe", "cmdline"]):
            try:
                if self._is_deadlock_process_info(proc.info):
                    print(f"Found matching game process: {proc.info.get('name')}")
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    async def wait_for_main_menu(
        self,
        process_timeout: int = GAME_PROCESS_START_TIMEOUT_SECONDS,
        load_wait_seconds: int = GAME_INITIALIZATION_DELAY_SECONDS,
    ) -> bool:
        await self.send_status(
            "Waiting for game process to appear "
            f"(up to {process_timeout} seconds)..."
        )
        start_time = time.time()
        while time.time() - start_time < process_timeout:
            if self.is_game_running():
                break
            await asyncio.sleep(1)
        else:
            await self.send_status("Game process did not appear in time.")
            return False

        await self.send_status(
            "Game process detected, waiting for game UI to load "
            f"({load_wait_seconds} seconds)..."
        )

        load_deadline = time.time() + max(0, int(load_wait_seconds))
        while time.time() < load_deadline:
            if not self.is_game_running():
                await self.send_status(
                    "Game process exited while waiting for UI to load."
                )
                return False
            await asyncio.sleep(1)

        await self.send_status("Proceeding with hero-selection navigation.")
        return True

    async def launch_game(self) -> bool:
        if self.is_game_running():
            await self.send_status("Deadlock is already running. Closing it first...")
            self.close_game()
            await asyncio.sleep(3)

        try:
            command, command_cwd, strategy = self._resolve_launch_strategy()
            await self.send_status(
                "Launching Deadlock "
                f"(platform={self.platform_name}, mode={strategy})"
            )
            await self.send_status(f"Command: {' '.join(command)}")

            popen_cwd = str(command_cwd) if command_cwd is not None else None
            self.process = subprocess.Popen(command, cwd=popen_cwd)
            await self.send_status(
                "Game launch command started; waiting for process and load stabilization..."
            )
            if await self.wait_for_main_menu(
                process_timeout=GAME_PROCESS_START_TIMEOUT_SECONDS,
                load_wait_seconds=GAME_INITIALIZATION_DELAY_SECONDS,
            ):
                return True
            else:
                await self.send_status("Timeout waiting for game to load.")
                return False
        except FileNotFoundError as e:
            await self.send_status(str(e))
            return False
        except Exception as e:
            await self.send_status(f"Failed to launch game: {e}")
            return False

    def close_game(self):
        terminated_any = False
        for proc in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
            try:
                if not self._is_deadlock_process_info(proc.info):
                    continue
                proc.terminate()
                proc.wait(timeout=10)
                terminated_any = True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                continue

        if terminated_any:
            print("Game closed successfully.")


class HeroImageExtractor:
    BASE_RESOLUTION = DEFAULT_BASE_RESOLUTION
    UI_LAYOUT_REFERENCE_RESOLUTION = (2560, 1440)

    ABILITY_ICON_CENTERS = [
        (1889, 1320),
        (2020, 1320),
        (2154, 1320),
        (2293, 1320),
    ]
    HERO_GRID_TOP_LEFT = (99, 202)
    HERO_PORTRAIT_SIZE = (100, 167)
    HERO_GAP = (10, 10)
    HEROES_PER_ROW = 8

    def __init__(
        self,
        websocket_callback=None,
        debug: bool = False,
        display_resolution: Optional[Tuple[int, int]] = None,
    ):
        self.output_dir = Path("extracted_images")
        self.abilities_dir = self.output_dir / "abilities"
        self.stats_dir = self.output_dir / "stats"

        self.output_dir.mkdir(exist_ok=True)
        self.abilities_dir.mkdir(exist_ok=True)
        self.stats_dir.mkdir(exist_ok=True)

        self.controller = CrossPlatformController(websocket_callback)
        self.websocket_callback = websocket_callback
        self.detector = TooltipDetector()
        
        self.hero_data, self.api_success = fetch_hero_data()
        self.hero_ids = [hero["id"] for hero in self.hero_data]

        auto_resolution = detect_primary_display_resolution()
        if display_resolution is None:
            self.display_resolution = auto_resolution
        else:
            display_width, display_height = display_resolution
            if int(display_width) <= 0 or int(display_height) <= 0:
                raise ValueError("Display resolution override must be positive.")
            self.display_resolution = (int(display_width), int(display_height))

        screen_width, screen_height = self.display_resolution
        if debug:
            print(
                "Display scaling resolution "
                f"{screen_width}x{screen_height} (auto={auto_resolution[0]}x{auto_resolution[1]})"
            )

        scale_x = screen_width / self.BASE_RESOLUTION[0]
        scale_y = screen_height / self.BASE_RESOLUTION[1]

        layout_scale_x = screen_width / self.UI_LAYOUT_REFERENCE_RESOLUTION[0]
        layout_scale_y = screen_height / self.UI_LAYOUT_REFERENCE_RESOLUTION[1]

        self.ability_positions = [
            self.scale_point(pos, layout_scale_x, layout_scale_y)
            for pos in self.ABILITY_ICON_CENTERS
        ]
        self.stat_positions = [
            self.scale_point(pos, scale_x, scale_y)
            for pos in [(1900, 470), (1900, 520), (1900, 560)]
        ]
        self.stat_names = ["weapon", "vitality", "spirit"]
        self.hero_grid_start = self.scale_point(
            self.HERO_GRID_TOP_LEFT, layout_scale_x, layout_scale_y
        )
        self.hero_portrait_size = self.scale_size(
            self.HERO_PORTRAIT_SIZE, layout_scale_x, layout_scale_y
        )
        self.hero_gap = self.scale_size(self.HERO_GAP, layout_scale_x, layout_scale_y)
        self.heroes_per_row = self.HEROES_PER_ROW

        self.settings_menu_probe = self.scale_point((162, 917), scale_x, scale_y)
        self.hero_selection_button = self.scale_point((273, 767), scale_x, scale_y)

    def scale_point(self, point, scale_x, scale_y):
        return (int(round(point[0] * scale_x)), int(round(point[1] * scale_y)))

    def scale_size(self, size, scale_x, scale_y):
        return (int(round(size[0] * scale_x)), int(round(size[1] * scale_y)))

    async def send_status(self, message):
        if self.websocket_callback:
            await self.websocket_callback({"type": "status", "message": message})

    async def send_image_update(self, hero_id, ability_index, filename):
        if self.websocket_callback:
            await self.websocket_callback({"type": "image_update", "hero_id": hero_id, "ability_index": ability_index, "filename": filename})

    async def send_stat_update(self, hero_id, stat_index, filename):
        if self.websocket_callback:
            await self.websocket_callback({"type": "stat_update", "hero_id": hero_id, "stat_index": stat_index, "filename": filename})

    def is_settings_menu_open(self):
        pixel = pyautogui.pixel(self.settings_menu_probe[0], self.settings_menu_probe[1])
        return pixel[0] > 100

    def _capture_game_window_screenshot(self):
        window_region = self.controller.get_active_window_region()
        if window_region is not None:
            left, top, width, height = window_region
            try:
                return pyautogui.screenshot(region=(left, top, width, height))
            except Exception:
                pass

        return pyautogui.screenshot()

    async def navigate_to_hero_selection(self):
        await self.send_status("Waiting after loading screen...")
        await asyncio.sleep(1.5)
        if self.controller.should_stop():
            return False
        
        await self.send_status(
            f"Input backend: {self.controller.get_input_backend_name()}"
        )
        
        if self.controller.focus_deadlock_window():
            await self.send_status("Focused Deadlock window for input automation.")
        else:
            await self.send_status(
                "Could not auto-focus Deadlock window; using global desktop input."
            )
        
        sw, sh = self.display_resolution
        self.controller.move_mouse(sw // 2, sh // 2)
        await asyncio.sleep(0.2)
        self.controller.click(sw // 2, sh // 2)
        await asyncio.sleep(2)
        
        await self.send_status("Opening hero selection...")
        settings_menu_detected = False
        for _ in range(5):
            try:
                settings_menu_detected = self.is_settings_menu_open()
            except Exception:
                settings_menu_detected = False

            if settings_menu_detected:
                break

            self.controller.press_key("escape")
            await asyncio.sleep(1.5)

        if not settings_menu_detected:
            await self.send_status(
                "Settings menu probe did not confirm open; attempting hero selection click anyway."
            )
        
        self.controller.move_mouse(
            self.hero_selection_button[0], self.hero_selection_button[1]
        )
        await asyncio.sleep(0.2)
        self.controller.click(self.hero_selection_button[0], self.hero_selection_button[1])
        await asyncio.sleep(2)
        return True

    def get_hero_position(self, hero_index):
        row = hero_index // self.heroes_per_row
        col = hero_index % self.heroes_per_row
        x = (
            self.hero_grid_start[0]
            + col * (self.hero_portrait_size[0] + self.hero_gap[0])
            + self.hero_portrait_size[0] // 2
        )
        y = (
            self.hero_grid_start[1]
            + row * (self.hero_portrait_size[1] + self.hero_gap[1])
            + self.hero_portrait_size[1] // 2
        )
        return (x, y)

    async def capture_ability_tooltip(self, hero_index, ability_index):
        hero_id = self.hero_ids[hero_index]
        hero_name = self.hero_data[hero_index]["name"]
        ability_pos = self.ability_positions[ability_index]
        await self.send_status(f"Capturing ability {ability_index + 1} for {hero_name}")

        result = await self.detector.capture_ability_tooltip(
            ability_pos,
            hero_id,
            ability_index,
            move_mouse_callback=self.controller.move_mouse,
            screenshot_provider=self._capture_game_window_screenshot,
        )
        if result:
            filename = f"hero{hero_id}_ability_{ability_index + 1}.png"
            result["image"].save(self.abilities_dir / filename)
            await self.send_status(f"Saved {filename}")
            await self.send_image_update(hero_id, ability_index + 1, filename)
        else:
            await self.send_status(f"Failed to detect tooltip for {hero_name} ability {ability_index + 1}")
        return not self.controller.should_stop()

    async def capture_stat_tooltip(self, hero_index, stat_index):
        hero_id = self.hero_ids[hero_index]
        hero_name = self.hero_data[hero_index]["name"]
        stat_name = self.stat_names[stat_index]
        stat_pos = self.stat_positions[stat_index]
        await self.send_status(f"Capturing {stat_name} stat for {hero_name}")

        result = await self.detector.capture_stat_tooltip(
            stat_pos,
            hero_id,
            stat_name,
            move_mouse_callback=self.controller.move_mouse,
            screenshot_provider=self._capture_game_window_screenshot,
        )
        if result:
            filename = f"hero{hero_id}_{stat_name}_stat.png"
            result["image"].save(self.stats_dir / filename)
            await self.send_status(f"Saved {filename}")
            await self.send_stat_update(hero_id, stat_index, filename)
        else:
            await self.send_status(f"Failed to detect tooltip for {hero_name} {stat_name} stat")
        return not self.controller.should_stop()

    async def run_extraction_loop(self, options: ExtractionOptions):
        total_heroes = len(self.hero_ids)
        for hero_index in range(total_heroes):
            if self.controller.should_stop():
                break
            
            hero_pos = self.get_hero_position(hero_index)
            hero_name = self.hero_data[hero_index]["name"]
            await self.send_status(f"Processing {hero_name} ({hero_index + 1}/{total_heroes})")
            self.controller.move_mouse(hero_pos[0], hero_pos[1])
            await asyncio.sleep(1.0)
            
            if options.extract_abilities:
                for ability_index in range(4):
                    if not await self.capture_ability_tooltip(hero_index, ability_index):
                        return False
            
            if options.extract_stats:
                for stat_index in range(3):
                    if not await self.capture_stat_tooltip(hero_index, stat_index):
                        return False
        
        await self.send_status("Extraction loop completed!")
        return True

    async def extract_hero_data(self, options: ExtractionOptions):
        if not await self.navigate_to_hero_selection():
            return False
        return await self.run_extraction_loop(options)

    def cleanup(self):
        self.controller.cleanup()


def get_default_game_path(platform_override: str = "auto"):
    candidate_paths = get_candidate_game_paths(platform_override)
    for path in candidate_paths:
        if path.exists():
            return str(path)

    if candidate_paths:
        return str(candidate_paths[0])

    platform_name = resolve_platform(platform_override)
    if platform_name == "windows":
        return (
            r"C:\Program Files (x86)\Steam\steamapps\common\Deadlock"
            r"\game\bin\win64\deadlock.exe"
        )
    return str(
        Path.home()
        / ".local"
        / "share"
        / "Steam"
        / "steamapps"
        / "common"
        / "Deadlock"
        / "game"
        / "bin"
        / "linuxsteamrt64"
        / "deadlock"
    )


async def main_cli():
    parser = argparse.ArgumentParser(description='Deadlock Hero Image Extractor')
    parser.add_argument('--abilities', action='store_true', help='Extract hero abilities')
    parser.add_argument('--stats', action='store_true', help='Extract hero stats')
    parser.add_argument('--game-path', type=str, help='Path to game executable')
    parser.add_argument(
        '--platform',
        type=str,
        default='auto',
        choices=sorted(VALID_PLATFORM_OVERRIDES),
        help='Platform override used for launch strategy and default paths',
    )
    parser.add_argument(
        '--launch-mode',
        type=str,
        default='auto',
        choices=sorted(VALID_LAUNCH_MODES),
        help='Launch mode: auto, direct executable, or steam app launch',
    )
    parser.add_argument(
        '--display-width',
        type=int,
        help='Manual display width override for coordinate scaling',
    )
    parser.add_argument(
        '--display-height',
        type=int,
        help='Manual display height override for coordinate scaling',
    )
    parser.add_argument(
        '--steam-app-id',
        type=str,
        default=DEFAULT_STEAM_APP_ID,
        help='Steam app id used when launch mode is steam',
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run in CLI/headless mode without the web dashboard (default behavior).',
    )
    args = parser.parse_args()
    
    extract_abilities = args.abilities or not (args.abilities or args.stats)
    options = ExtractionOptions(extract_abilities, args.stats)

    try:
        display_resolution = parse_display_resolution(
            args.display_width,
            args.display_height,
        )
    except ValueError as exc:
        parser.error(str(exc))
    
    game_path = args.game_path or get_default_game_path(args.platform)
    
    launcher = DeadlockLauncher(
        game_path,
        platform_override=args.platform,
        launch_mode=args.launch_mode,
        steam_app_id=args.steam_app_id,
    )
    extractor = HeroImageExtractor(display_resolution=display_resolution)
    
    try:
        if await launcher.launch_game():
            if not await extractor.extract_hero_data(options):
                print("Extraction stopped.")
        else:
            print("Failed to launch game.")
    finally:
        extractor.cleanup()
        launcher.close_game()


def main():
    if len(os.sys.argv) > 1 and os.sys.argv[1] == "web":
        from .web_app import run_web_app

        run_web_app()
    else:
        asyncio.run(main_cli())


if __name__ == "__main__":
    main()