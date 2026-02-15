import asyncio
import json
import requests
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, Form, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .main import (
    DEFAULT_STEAM_APP_ID,
    DeadlockLauncher,
    ExtractionOptions,
    HeroImageExtractor,
    detect_host_platform,
    detect_primary_display_resolution,
    get_candidate_game_paths,
    get_default_game_path,
    parse_display_resolution,
    resolve_platform,
)

app = FastAPI()

package_dir = Path(__file__).parent
static_dir = package_dir / "static"
templates_dir = package_dir / "templates"
images_dir = Path("extracted_images")

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.mount("/images", StaticFiles(directory=str(images_dir)), name="images")
templates = Jinja2Templates(directory=str(templates_dir))

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                pass

manager = ConnectionManager()

settings = {
    "platform_override": "auto",
    "launch_mode": "auto",
    "game_path": get_default_game_path("auto"),
    "steam_app_id": DEFAULT_STEAM_APP_ID,
    "display_width": "",
    "display_height": "",
}

extraction_state = {
    "running": False,
    "launcher": None,
    "extractor": None
}

def get_sort_name(name):
    if name.startswith("The "):
        return name[4:]
    return name

def fetch_hero_data_web():
    try:
        print("Fetching hero data from API...")
        response = requests.get('https://assets.deadlock-api.com/v2/heroes?only_active=true', timeout=10)
        response.raise_for_status()
        
        heroes = response.json()
        
        filtered_heroes = [{"id": hero["id"], "name": hero["name"]} for hero in heroes]
        
        sorted_heroes = sorted(filtered_heroes, key=lambda x: get_sort_name(x["name"]))
        
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
            {"id": 27, "name": "Yamato"}
        ]
        
        sorted_heroes = sorted(fallback_heroes, key=lambda x: get_sort_name(x["name"]))
        print(f"Using {len(sorted_heroes)} fallback heroes")
        
        return sorted_heroes, False

hero_data, api_success = fetch_hero_data_web()

def _parse_optional_int(value: str) -> Optional[int]:
    text = str(value or "").strip()
    if not text:
        return None
    return int(text)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    abilities_dir = images_dir / "abilities"
    stats_dir = images_dir / "stats"
    extracted_images = {}
    
    for hero in hero_data:
        hero_id = hero["id"]
        hero_name = hero["name"]
        extracted_images[hero_id] = {
            "name": hero_name,
            "abilities": {},
            "stats": {}
        }
        
        for ability_index in range(1, 5):
            filename = f"hero{hero_id}_ability_{ability_index}.png"
            filepath = abilities_dir / filename
            
            if filepath.exists():
                extracted_images[hero_id]["abilities"][ability_index] = {
                    "filename": filename,
                    "path": f"/images/abilities/{filename}"
                }

        stat_names = ["weapon", "vitality", "spirit"]
        for stat_index, stat_name in enumerate(stat_names):
            filename = f"hero{hero_id}_{stat_name}_stat.png"
            filepath = stats_dir / filename
            
            if filepath.exists():
                extracted_images[hero_id]["stats"][stat_index] = {
                    "filename": filename,
                    "path": f"/images/stats/{filename}",
                    "name": stat_name
                }
    
    current_platform = detect_host_platform()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "hero_data": hero_data,
        "extracted_images": extracted_images,
        "extraction_running": extraction_state["running"],
        "api_success": api_success,
        "hero_count": len(hero_data),
        "platform": current_platform
    })

@app.get("/api/hero-data")
async def get_hero_data():
    return {
        "heroes": hero_data,
        "api_success": api_success,
        "count": len(hero_data),
        "source": "API" if api_success else "Fallback",
        "platform": detect_host_platform()
    }

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    host_platform = detect_host_platform()
    selected_platform = settings["platform_override"]
    effective_platform = resolve_platform(selected_platform)
    default_paths = [str(path) for path in get_candidate_game_paths(selected_platform)]
    detected_width, detected_height = detect_primary_display_resolution()

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "host_platform": host_platform,
        "selected_platform": selected_platform,
        "effective_platform": effective_platform,
        "selected_launch_mode": settings["launch_mode"],
        "game_path": settings["game_path"],
        "steam_app_id": settings["steam_app_id"],
        "display_width": settings["display_width"],
        "display_height": settings["display_height"],
        "detected_width": detected_width,
        "detected_height": detected_height,
        "default_paths": default_paths,
    })

@app.post("/settings")
async def update_settings(
    platform_override: str = Form("auto"),
    launch_mode: str = Form("auto"),
    game_path: str = Form(""),
    steam_app_id: str = Form(DEFAULT_STEAM_APP_ID),
    display_width: str = Form(""),
    display_height: str = Form(""),
):
    platform_override = (platform_override or "auto").strip().lower()
    launch_mode = (launch_mode or "auto").strip().lower()
    if launch_mode not in {"auto", "direct", "steam"}:
        raise HTTPException(status_code=400, detail="Invalid launch mode.")

    try:
        resolve_platform(platform_override)
        parsed_width = _parse_optional_int(display_width)
        parsed_height = _parse_optional_int(display_height)
        parse_display_resolution(parsed_width, parsed_height)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    game_path_value = (game_path or "").strip() or get_default_game_path(platform_override)
    steam_app_id_value = str(steam_app_id or "").strip() or DEFAULT_STEAM_APP_ID

    settings["platform_override"] = platform_override
    settings["launch_mode"] = launch_mode
    settings["game_path"] = game_path_value
    settings["steam_app_id"] = steam_app_id_value
    settings["display_width"] = "" if parsed_width is None else str(parsed_width)
    settings["display_height"] = "" if parsed_height is None else str(parsed_height)

    return RedirectResponse(url="/", status_code=303)

@app.post("/start-extraction")
async def start_extraction(request: Request):
    if extraction_state["running"]:
        return {"status": "error", "message": "Extraction already running"}
    
    body = await request.json()
    extract_abilities = body.get("extract_abilities", True)
    extract_stats = body.get("extract_stats", False)
    
    options = ExtractionOptions(extract_abilities, extract_stats)

    try:
        display_width = _parse_optional_int(settings["display_width"])
        display_height = _parse_optional_int(settings["display_height"])
        display_resolution = parse_display_resolution(display_width, display_height)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}

    game_path = settings["game_path"].strip() or get_default_game_path(
        settings["platform_override"]
    )
    
    extraction_state["running"] = True
    
    async def websocket_callback(message):
        await manager.send_message(message)
    
    async def run_extraction():
        try:
            launcher = DeadlockLauncher(
                game_path,
                websocket_callback,
                platform_override=settings["platform_override"],
                launch_mode=settings["launch_mode"],
                steam_app_id=settings["steam_app_id"],
            )
            extractor = HeroImageExtractor(
                websocket_callback=websocket_callback,
                debug=True,
                display_resolution=display_resolution,
            )

            await websocket_callback(
                {
                    "type": "status",
                    "message": (
                        "Runtime settings: "
                        f"platform={launcher.platform_name}, "
                        f"launch_mode={launcher.launch_mode}, "
                        f"display={extractor.display_resolution[0]}x{extractor.display_resolution[1]}"
                    ),
                }
            )
            
            extraction_state["launcher"] = launcher
            extraction_state["extractor"] = extractor
            
            if await launcher.launch_game():
                await websocket_callback({"type": "status", "message": "Game is ready for image extraction"})
                
                if not await extractor.extract_hero_data(options):
                    await websocket_callback({"type": "status", "message": "Extraction stopped by user"})
                    
            else:
                await websocket_callback({"type": "status", "message": "Failed to launch game"})
                
        except Exception as e:
            await websocket_callback({"type": "status", "message": f"Error: {str(e)}"})
        finally:
            if extraction_state["extractor"]:
                extraction_state["extractor"].cleanup()
            if extraction_state["launcher"]:
                extraction_state["launcher"].close_game()
            extraction_state["running"] = False
            extraction_state["launcher"] = None
            extraction_state["extractor"] = None
            await websocket_callback({"type": "extraction_finished"})
    
    asyncio.create_task(run_extraction())
    return {"status": "success", "message": "Extraction started"}

@app.post("/stop-extraction")
async def stop_extraction():
    if not extraction_state["running"]:
        return {"status": "error", "message": "No extraction running"}
    
    if extraction_state["extractor"]:
        extraction_state["extractor"].controller.stop_flag = True
    
    return {"status": "success", "message": "Stop signal sent"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

def run_web_app():
    uvicorn.run(app, host="127.0.0.1", port=3000)