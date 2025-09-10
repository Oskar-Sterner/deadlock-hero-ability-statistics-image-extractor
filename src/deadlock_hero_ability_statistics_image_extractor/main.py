import subprocess
import time
import psutil
import os
import asyncio
import requests
import platform
import argparse
from pathlib import Path
from typing import Optional
from PIL import Image
import numpy as np
import pyautogui
import pynput.keyboard as keyboard
from .tooltip_detector import TooltipDetector


def get_sort_name(name):
    if name.startswith("The "):
        return name[4:]
    return name


def fetch_hero_data():
    try:
        print("Fetching hero data from API...")
        response = requests.get('https://assets.deadlock-api.com/v2/heroes?only_active=true', timeout=10)
        response.raise_for_status()
        heroes = response.json()
        filtered_heroes = [{"id": hero["id"], "name": hero["name"]} for hero in heroes]
        sorted_heroes = sorted(filtered_heroes, key=lambda x: get_sort_name(x["name"]))
        print(f"Successfully fetched {len(sorted_heroes)} heroes from API")
        return sorted_heroes, True
    except Exception as e:
        print(f"Failed to fetch hero data from API: {e}. Using fallback...")
        fallback_heroes = [
            {"id": 6, "name": "Abrams"}, {"id": 15, "name": "Bebop"}, {"id": 72, "name": "Billy"},
            {"id": 16, "name": "Calico"}, {"id": 69, "name": "The Doorman"}, {"id": 64, "name": "Drifter"},
            {"id": 11, "name": "Dynamo"}, {"id": 17, "name": "Grey Talon"}, {"id": 13, "name": "Haze"},
            {"id": 14, "name": "Holliday"}, {"id": 1, "name": "Infernus"}, {"id": 20, "name": "Ivy"},
            {"id": 12, "name": "Kelvin"}, {"id": 4, "name": "Lady Geist"}, {"id": 31, "name": "Lash"},
            {"id": 8, "name": "McGinnis"}, {"id": 63, "name": "Mina"}, {"id": 52, "name": "Mirage"},
            {"id": 18, "name": "Mo & Krill"}, {"id": 67, "name": "Paige"}, {"id": 10, "name": "Paradox"},
            {"id": 50, "name": "Pocket"}, {"id": 2, "name": "Seven"}, {"id": 19, "name": "Shiv"},
            {"id": 60, "name": "Sinclair"}, {"id": 66, "name": "Victor"}, {"id": 3, "name": "Vindicta"},
            {"id": 35, "name": "Viscous"}, {"id": 58, "name": "Vyper"}, {"id": 25, "name": "Warden"},
            {"id": 7, "name": "Wraith"}, {"id": 27, "name": "Yamato"}
        ]
        return sorted(fallback_heroes, key=lambda x: get_sort_name(x["name"])), False


class ExtractionOptions:
    def __init__(self, extract_abilities=True, extract_stats=False):
        self.extract_abilities = extract_abilities
        self.extract_stats = extract_stats


class CrossPlatformController:
    def __init__(self, websocket_callback=None):
        self.stop_flag = False
        self.hotkey_listener = None
        self.websocket_callback = websocket_callback
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

    def click(self, x, y):
        if self.stop_flag: return
        pyautogui.click(x, y)

    def move_mouse(self, x, y):
        if self.stop_flag: return
        pyautogui.moveTo(x, y)

    def press_key(self, key):
        if self.stop_flag: return
        pyautogui.press(key)


class DeadlockLauncher:
    def __init__(self, game_path: str, websocket_callback=None):
        self.game_path = Path(game_path)
        self.process: Optional[subprocess.Popen] = None
        self.websocket_callback = websocket_callback

    async def send_status(self, message):
        if self.websocket_callback:
            await self.websocket_callback({"type": "status", "message": message})

    def is_game_running(self) -> bool:
        for proc in psutil.process_iter(['name', 'exe']):
            try:
                if 'deadlock' in proc.info.get('name', '').lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    async def wait_for_main_menu(self, timeout: int = 120) -> bool:
        await self.send_status("Waiting for game process to appear...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_game_running():
                break
            await asyncio.sleep(1)
        else:
            return False

        await self.send_status("Game process detected, waiting for main menu...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            non_black_ratio = np.sum(np.array(pyautogui.screenshot()) > 30) / pyautogui.screenshot().size[0] / pyautogui.screenshot().size[1] / 3
            if non_black_ratio > 0.1:
                await self.send_status("Main menu detected!")
                return True
            await asyncio.sleep(2)
        return False

    async def launch_game(self) -> bool:
        if not self.game_path.exists():
            await self.send_status(f"Game executable not found: {self.game_path}")
            return False
        
        if self.is_game_running():
            await self.send_status("Deadlock is already running. Closing it first...")
            self.close_game()
            await asyncio.sleep(3)

        try:
            await self.send_status(f"Launching Deadlock from: {self.game_path.parent}")
            self.process = subprocess.Popen(str(self.game_path), cwd=self.game_path.parent)
            if await self.wait_for_main_menu():
                return True
            else:
                await self.send_status("Timeout waiting for game to load.")
                return False
        except Exception as e:
            await self.send_status(f"Failed to launch game: {e}")
            return False

    def close_game(self):
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                if 'deadlock' in proc.info.get('name', '').lower():
                    proc.terminate()
                    proc.wait(timeout=10)
                    print("Game closed successfully.")
                    return
            except Exception:
                continue


class HeroImageExtractor:
    def __init__(self, websocket_callback=None, debug=False):
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

        self.ability_positions = [(1417, 983), (1517, 983), (1617, 983), (1717, 983)]
        self.stat_positions = [(1900, 470), (1900, 520), (1900, 560)]
        self.stat_names = ["weapon", "vitality", "spirit"]
        self.hero_grid_start = (104, 305)
        self.hero_portrait_size = (75, 125)
        self.hero_gap = 8
        self.heroes_per_row = 7

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
        pixel = pyautogui.pixel(162, 917)
        return pixel[0] > 100

    async def navigate_to_hero_selection(self):
        await self.send_status("Waiting after loading screen...")
        await asyncio.sleep(1.5)
        if self.controller.should_stop(): return False
        
        sw, sh = pyautogui.size()
        self.controller.click(sw // 2, sh // 2)
        await asyncio.sleep(2)
        
        await self.send_status("Opening hero selection...")
        for _ in range(5):
            if self.is_settings_menu_open(): break
            self.controller.press_key("escape")
            await asyncio.sleep(1.5)
        else:
            await self.send_status("Failed to open settings menu.")
            return False
        
        self.controller.click(273, 767) # Click "SWAP HERO"
        await asyncio.sleep(2)
        return True

    def get_hero_position(self, hero_index):
        row = hero_index // self.heroes_per_row
        col = hero_index % self.heroes_per_row
        x = self.hero_grid_start[0] + col * (self.hero_portrait_size[0] + self.hero_gap) + self.hero_portrait_size[0] // 2
        y = self.hero_grid_start[1] + row * (self.hero_portrait_size[1] + self.hero_gap) - self.hero_portrait_size[1] // 2
        return (x, y)

    async def capture_ability_tooltip(self, hero_index, ability_index):
        hero_id = self.hero_ids[hero_index]
        hero_name = self.hero_data[hero_index]["name"]
        ability_pos = self.ability_positions[ability_index]
        await self.send_status(f"Capturing ability {ability_index + 1} for {hero_name}")

        result = await self.detector.capture_ability_tooltip(ability_pos, hero_id, ability_index)
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

        result = await self.detector.capture_stat_tooltip(stat_pos, hero_id, stat_name)
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
            if self.controller.should_stop(): break
            
            hero_pos = self.get_hero_position(hero_index)
            hero_name = self.hero_data[hero_index]["name"]
            await self.send_status(f"Processing {hero_name} ({hero_index + 1}/{total_heroes})")
            self.controller.move_mouse(hero_pos[0], hero_pos[1])
            await asyncio.sleep(1.0)
            
            if options.extract_abilities:
                for ability_index in range(4):
                    if not await self.capture_ability_tooltip(hero_index, ability_index): return False
            
            if options.extract_stats:
                for stat_index in range(3):
                    if not await self.capture_stat_tooltip(hero_index, stat_index): return False
        
        await self.send_status("Extraction loop completed!")
        return True

    async def extract_hero_data(self, options: ExtractionOptions):
        if not await self.navigate_to_hero_selection(): return False
        return await self.run_extraction_loop(options)

    def cleanup(self):
        self.controller.cleanup()


def get_default_game_path():
    if platform.system() == "Windows":
        for drive in "CFDE":
            path = Path(f"{drive}:/SteamLibrary/steamapps/common/Deadlock/game/bin/win64/deadlock.exe")
            if path.exists(): return str(path)
        return r"C:\Program Files (x86)\Steam\steamapps\common\Deadlock\game\bin\win64\deadlock.exe"
    else: # Linux
        home = Path.home()
        paths = [
            home / ".steam/steam/steamapps/common/Deadlock/game/bin/linuxsteamrt64/deadlock",
            home / ".local/share/Steam/steamapps/common/Deadlock/game/bin/linuxsteamrt64/deadlock",
        ]
        for path in paths:
            if path.exists(): return str(path)
        return str(paths[0])


async def main_cli():
    parser = argparse.ArgumentParser(description='Deadlock Hero Image Extractor')
    parser.add_argument('--abilities', action='store_true', help='Extract hero abilities')
    parser.add_argument('--stats', action='store_true', help='Extract hero stats')
    parser.add_argument('--game-path', type=str, help='Path to game executable')
    args = parser.parse_args()
    
    # If no flags are given, default to extracting abilities
    extract_abilities = args.abilities or not (args.abilities or args.stats)
    options = ExtractionOptions(extract_abilities, args.stats)
    
    game_path = args.game_path or get_default_game_path()
    
    launcher = DeadlockLauncher(game_path)
    extractor = HeroImageExtractor()
    
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
    if __name__ == "__main__":
        if len(os.sys.argv) > 1 and os.sys.argv[1] == "web":
            from .web_app import run_web_app
            run_web_app()
        else:
            asyncio.run(main_cli())

main()