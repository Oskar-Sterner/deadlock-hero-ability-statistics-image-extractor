import subprocess
import time
import psutil
import os
import threading
import asyncio
import json
import requests
import platform
from pathlib import Path
from typing import Optional, List, Dict
from PIL import Image
import numpy as np
import pyautogui
import pynput.keyboard as keyboard


def fetch_hero_data():
    try:
        print("Fetching hero data from API...")
        response = requests.get('https://assets.deadlock-api.com/v2/heroes?only_active=true', timeout=10)
        response.raise_for_status()
        
        heroes = response.json()
        
        filtered_heroes = [{"id": hero["id"], "name": hero["name"]} for hero in heroes]
        
        sorted_heroes = sorted(filtered_heroes, key=lambda x: x["name"])
        
        print(f"Successfully fetched {len(sorted_heroes)} heroes from API")
        print(f"First 3 heroes: {[h['name'] for h in sorted_heroes[:3]]}")
        
        return sorted_heroes, True
    except Exception as e:
        print(f"Failed to fetch hero data from API: {e}")
        print("Using fallback hero data...")
        
        fallback_heroes = [
            {"id": 6, "name": "Abrams"},
            {"id": 15, "name": "Bebop"},
            {"id": 72, "name": "Billy"},
            {"id": 16, "name": "Calico"},
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
            {"id": 69, "name": "The Doorman"},
            {"id": 66, "name": "Victor"},
            {"id": 3, "name": "Vindicta"},
            {"id": 35, "name": "Viscous"},
            {"id": 58, "name": "Vyper"},
            {"id": 25, "name": "Warden"},
            {"id": 7, "name": "Wraith"},
            {"id": 27, "name": "Yamato"}
        ]
        
        sorted_heroes = sorted(fallback_heroes, key=lambda x: x["name"])
        print(f"Using {len(sorted_heroes)} fallback heroes")
        
        return sorted_heroes, False


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
            
        self.hotkey_listener = keyboard.GlobalHotKeys({
            '<ctrl>+<shift>+q': on_hotkey
        })
        self.hotkey_listener.start()
    
    def should_stop(self):
        return self.stop_flag
    
    def cleanup(self):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
    
    def click(self, x, y, button="left", clicks=1):
        if self.stop_flag:
            return
        try:
            pyautogui.click(x, y, clicks=clicks, button=button)
        except Exception as e:
            print(f"Click failed: {e}")
    
    def move_mouse(self, x, y):
        if self.stop_flag:
            return
        try:
            pyautogui.moveTo(x, y)
        except Exception as e:
            print(f"Mouse move failed: {e}")
    
    def press_key(self, key):
        if self.stop_flag:
            return
        try:
            pyautogui.press(key)
        except Exception as e:
            print(f"Key press failed: {e}")


class DeadlockLauncher:
    def __init__(self, game_path: str, websocket_callback=None):
        self.game_path = Path(game_path)
        self.process: Optional[subprocess.Popen] = None
        self.game_pid: Optional[int] = None
        self.websocket_callback = websocket_callback
        
    async def send_status(self, message):
        if self.websocket_callback:
            await self.websocket_callback({"type": "status", "message": message})
        
    def is_game_running(self) -> bool:
        system = platform.system()
        
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                proc_name = proc.info['name']
                proc_exe = proc.info.get('exe', '')
                
                if system == "Windows":
                    if proc_name.lower() == 'deadlock.exe' and proc_exe and 'deadlock' in proc_exe.lower():
                        return True
                elif system == "Linux":
                    if proc_name == 'deadlock' and proc_exe and 'deadlock' in proc_exe.lower():
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    
    async def wait_for_game_window(self, timeout: int = 60) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_game_running():
                await self.send_status("Game process detected!")
                time.sleep(2)
                return True
            time.sleep(1)
        return False
    
    async def wait_for_main_menu(self, timeout: int = 120) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                screenshot = pyautogui.screenshot()
                screenshot_np = np.array(screenshot)
                
                non_black_pixels = np.sum(screenshot_np > 30)
                total_pixels = screenshot_np.size
                non_black_ratio = non_black_pixels / total_pixels
                
                if non_black_ratio > 0.3:
                    await self.send_status("Main menu detected!")
                    return True
            except Exception as e:
                print(f"Screenshot failed: {e}")
            
            time.sleep(2)
        return False
    
    async def launch_game(self) -> bool:
        if not self.game_path.exists():
            await self.send_status(f"Game executable not found at: {self.game_path}")
            return False
            
        if self.is_game_running():
            await self.send_status("Found existing Deadlock process. Closing it first...")
            self.close_game()
            await asyncio.sleep(3)
            
            if self.is_game_running():
                await self.send_status("Failed to close existing Deadlock process. Please close it manually.")
                return False
            
        try:
            await self.send_status(f"Launching Deadlock from: {self.game_path}")
            
            if platform.system() == "Windows":
                self.process = subprocess.Popen(
                    str(self.game_path),
                    cwd=self.game_path.parent,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                self.process = subprocess.Popen(
                    [str(self.game_path)],
                    cwd=self.game_path.parent,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            await self.send_status("Waiting for game to load...")
            if await self.wait_for_game_window():
                await self.send_status("Game process started, waiting for main menu...")
                if await self.wait_for_main_menu():
                    await self.send_status("Game loaded successfully!")
                    return True
                else:
                    await self.send_status("Timeout waiting for main menu")
                    return False
            else:
                await self.send_status("Timeout waiting for game to load")
                return False
                
        except Exception as e:
            await self.send_status(f"Failed to launch game: {e}")
            return False
    
    def close_game(self):
        system = platform.system()
        
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                proc_name = proc.info['name']
                proc_exe = proc.info.get('exe', '')
                
                should_terminate = False
                
                if system == "Windows":
                    if proc_name.lower() == 'deadlock.exe' and 'deadlock' in proc_exe.lower():
                        should_terminate = True
                elif system == "Linux":
                    if proc_name == 'deadlock' and 'deadlock' in proc_exe.lower():
                        should_terminate = True
                
                if should_terminate:
                    proc.terminate()
                    proc.wait(timeout=10)
                    print("Game closed successfully")
                    return
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired, psutil.ZombieProcess):
                continue


class HeroImageExtractor:
    def __init__(self, websocket_callback=None):
        self.output_dir = Path("extracted_images")
        self.abilities_dir = self.output_dir / "abilities"
        self.stats_dir = self.output_dir / "stats"
        
        self.output_dir.mkdir(exist_ok=True)
        self.abilities_dir.mkdir(exist_ok=True)
        self.stats_dir.mkdir(exist_ok=True)
        
        self.controller = CrossPlatformController(websocket_callback)
        self.websocket_callback = websocket_callback
        
        try:
            hero_data_result = fetch_hero_data()
            if isinstance(hero_data_result, tuple) and len(hero_data_result) == 2:
                self.hero_data = hero_data_result[0]
                self.api_success = hero_data_result[1]
            else:
                raise ValueError("Invalid hero data format")
                
            if not isinstance(self.hero_data, list):
                raise ValueError("Hero data should be a list")
                
            self.hero_ids = [hero["id"] for hero in self.hero_data]
        except Exception as e:
            print(f"Error initializing hero data: {e}")
            fallback_heroes = [
                {"id": 6, "name": "Abrams"},
                {"id": 15, "name": "Bebop"},
                {"id": 72, "name": "Billy"}
            ]
            self.hero_data = sorted(fallback_heroes, key=lambda x: x["name"])
            self.api_success = False
            self.hero_ids = [hero["id"] for hero in self.hero_data]
        
        self.ability_positions = [
            (1417, 983),
            (1517, 983), 
            (1617, 983),
            (1717, 983)
        ]
        
        self.tooltip_bottom_corners = [
            {"left": 1149, "right": 1687, "bottom": 929},
            {"left": 1249, "right": 1787, "bottom": 929},
            {"left": 1349, "right": 1887, "bottom": 929},
            {"left": 1371, "right": 1909, "bottom": 929}
        ]
        
        self.hero_grid_start = (104, 305)
        self.hero_portrait_size = (75, 125)
        self.hero_gap = 8
        self.heroes_per_row = 7
        self.total_rows = 5
        self.last_row_heroes = 4
        
    async def send_status(self, message):
        if self.websocket_callback:
            await self.websocket_callback({"type": "status", "message": message})
    
    async def send_image_update(self, hero_id, ability_index, filename):
        if self.websocket_callback:
            await self.websocket_callback({
                "type": "image_update",
                "hero_id": hero_id,
                "ability_index": ability_index,
                "filename": filename
            })
        
    def is_settings_menu_open(self):
        try:
            screenshot = pyautogui.screenshot()
            screenshot_np = np.array(screenshot)
            
            x, y = 162, 917
            if y < screenshot_np.shape[0] and x < screenshot_np.shape[1]:
                pixel = screenshot_np[y, x]
                red_value = pixel[0]
                return red_value > 100
            return False
        except Exception as e:
            print(f"Settings menu detection failed: {e}")
            return False
    
    async def navigate_to_hero_selection(self):
        if self.controller.should_stop():
            return False
            
        await self.send_status("Waiting 1.5 seconds after loading screen...")
        for _ in range(15):
            if self.controller.should_stop():
                return False
            await asyncio.sleep(0.1)
        
        await self.send_status("Pressing left mouse button...")
        screen_width, screen_height = pyautogui.size()
        self.controller.click(screen_width // 2, screen_height // 2)
        
        await self.send_status("Waiting 2 seconds...")
        for _ in range(20):
            if self.controller.should_stop():
                return False
            await asyncio.sleep(0.1)
        
        await self.send_status("Opening settings menu...")
        max_attempts = 10
        attempts = 0
        
        while attempts < max_attempts:
            if self.controller.should_stop():
                return False
                
            self.controller.press_key("escape")
            
            for _ in range(15):
                if self.controller.should_stop():
                    return False
                await asyncio.sleep(0.1)
            
            if self.is_settings_menu_open():
                await self.send_status("Settings menu detected!")
                break
            
            attempts += 1
            await self.send_status(f"Settings menu not detected, pressing ESC again (attempt {attempts}/{max_attempts})")
        
        if attempts >= max_attempts:
            await self.send_status("Failed to open settings menu after maximum attempts")
            return False
        
        await self.send_status("Clicking SWAP HERO button...")
        self.controller.click(273, 767)
        
        for _ in range(20):
            if self.controller.should_stop():
                return False
            await asyncio.sleep(0.1)
        
        return True
    
    def get_hero_position(self, hero_index):
        row = hero_index // self.heroes_per_row
        col = hero_index % self.heroes_per_row
        
        total_heroes = len(self.hero_ids)
        last_row = (total_heroes - 1) // self.heroes_per_row
        heroes_in_last_row = total_heroes - (last_row * self.heroes_per_row)
        
        if row == last_row and col >= heroes_in_last_row:
            return None
            
        x = self.hero_grid_start[0] + col * (self.hero_portrait_size[0] + self.hero_gap) + self.hero_portrait_size[0] // 2
        y = self.hero_grid_start[1] - self.hero_portrait_size[1] // 2 + row * (self.hero_portrait_size[1] + self.hero_gap)
        
        return (x, y)
    
    def find_tooltip_top(self, x_coord, bottom_y, screenshot_np):
        target_color = [0x12, 0x12, 0x12]
        tolerance = 2
        required_consecutive = 70
        valid_tops = []
        
        for start_y in range(bottom_y, 0, -1):
            try:
                if start_y < screenshot_np.shape[0] and x_coord < screenshot_np.shape[1]:
                    consecutive_count = 0
                    for y in range(start_y, max(0, start_y - required_consecutive), -1):
                        if y < screenshot_np.shape[0]:
                            pixel = screenshot_np[y, x_coord]
                            if all(abs(pixel[i] - target_color[i]) <= tolerance for i in range(3)):
                                consecutive_count += 1
                            else:
                                break
                        else:
                            break
                    
                    if consecutive_count >= required_consecutive:
                        top_y = start_y - consecutive_count + 1
                        valid_tops.append(top_y)
            except IndexError:
                continue
        
        if valid_tops:
            return min(valid_tops)
        
        return max(0, bottom_y - 300)
    
    async def capture_ability_tooltip(self, hero_index, ability_index):
        if self.controller.should_stop():
            return False
            
        hero_id = self.hero_ids[hero_index]
        ability_pos = self.ability_positions[ability_index]
        tooltip_info = self.tooltip_bottom_corners[ability_index]
        
        await self.send_status(f"Hovering over ability {ability_index + 1} for hero ID {hero_id}")
        self.controller.move_mouse(ability_pos[0], ability_pos[1])
        
        for _ in range(7):
            if self.controller.should_stop():
                return False
            await asyncio.sleep(0.1)
        
        try:
            screenshot = pyautogui.screenshot()
            screenshot_np = np.array(screenshot)
            
            left_x = tooltip_info["left"]
            right_x = tooltip_info["right"]
            bottom_y = tooltip_info["bottom"]
            
            top_y = self.find_tooltip_top(left_x, bottom_y, screenshot_np)
            
            screen_width, screen_height = pyautogui.size()
            
            left_x = max(0, min(left_x, screen_width - 1))
            right_x = max(left_x + 1, min(right_x, screen_width))
            top_y = max(0, min(top_y, screen_height - 1))
            bottom_y = max(top_y + 1, min(bottom_y, screen_height))
            
            if right_x <= left_x or bottom_y <= top_y:
                await self.send_status(f"Invalid crop dimensions for hero ID {hero_id} ability {ability_index + 1}")
                return True
            
            tooltip_region = screenshot.crop((left_x, top_y, right_x, bottom_y))
            
            filename = f"hero{hero_id}_ability_{ability_index + 1}.png"
            filepath = self.abilities_dir / filename
            tooltip_region.save(filepath)
            
            await self.send_status(f"Saved {filename}")
            await self.send_image_update(hero_id, ability_index, filename)
        except Exception as e:
            await self.send_status(f"Failed to save image for hero ID {hero_id} ability {ability_index + 1}: {e}")
        
        return True
    
    async def extract_hero_abilities(self):
        await self.send_status("Starting hero ability extraction...")
        await self.send_status("Press Ctrl+Shift+Q to stop the program at any time.")
        
        if not await self.navigate_to_hero_selection():
            return False
        
        total_heroes = len(self.hero_ids)
        
        for hero_index in range(total_heroes):
            if self.controller.should_stop():
                await self.send_status("Stopping extraction due to user request...")
                return False
                
            hero_pos = self.get_hero_position(hero_index)
            if hero_pos is None:
                continue
                
            hero_id = self.hero_ids[hero_index]
            hero_name = self.hero_data[hero_index]["name"]
            await self.send_status(f"Processing {hero_name} (ID: {hero_id}) ({hero_index + 1}/{total_heroes})")
            
            await self.send_status(f"Hovering over hero portrait at {hero_pos}")
            self.controller.move_mouse(hero_pos[0], hero_pos[1])
            
            for _ in range(10):
                if self.controller.should_stop():
                    return False
                await asyncio.sleep(0.1)
            
            for ability_index in range(4):
                if not await self.capture_ability_tooltip(hero_index, ability_index):
                    return False
        
        await self.send_status("Hero ability extraction completed!")
        return True
        
    async def extract_hero_stats(self):
        await self.send_status("Hero stats extraction will be implemented here")
        pass
    
    def cleanup(self):
        self.controller.cleanup()


def get_default_game_paths():
    system = platform.system()
    paths = []
    
    if system == "Windows":
        common_paths = [
            r"C:\Program Files (x86)\Steam\steamapps\common\Deadlock\game\bin\win64\deadlock.exe",
            r"D:\Steam\steamapps\common\Deadlock\game\bin\win64\deadlock.exe",
            r"F:\SteamLibrary\steamapps\common\Deadlock\game\bin\win64\deadlock.exe"
        ]
        paths.extend(common_paths)
    elif system == "Linux":
        home = Path.home()
        common_paths = [
            home / ".steam/steam/steamapps/common/Deadlock/game/bin/linuxsteamrt64/deadlock",
            home / ".local/share/Steam/steamapps/common/Deadlock/game/bin/linuxsteamrt64/deadlock",
            "/usr/games/steam/steamapps/common/Deadlock/game/bin/linuxsteamrt64/deadlock"
        ]
        paths.extend([str(p) for p in common_paths])
    
    for path in paths:
        if Path(path).exists():
            return path
    
    return paths[0] if paths else ""


async def main_cli():
    game_path = get_default_game_paths()
    
    launcher = DeadlockLauncher(game_path)
    extractor = HeroImageExtractor()
    
    try:
        if await launcher.launch_game():
            print("Game is ready for image extraction")
            
            if not await extractor.extract_hero_abilities():
                print("Extraction stopped by user")
                return 0
            await extractor.extract_hero_stats()
            
        else:
            print("Failed to launch game")
            return 1
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        extractor.cleanup()
        launcher.close_game()
    
    return 0


def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "web":
        from .web_app import run_web_app
        run_web_app()
    else:
        asyncio.run(main_cli())


if __name__ == "__main__":
    main()