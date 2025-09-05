import asyncio
import json
import threading
import requests
from pathlib import Path
from typing import Dict, List

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .main import DeadlockLauncher, HeroImageExtractor


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
            except:
                pass

manager = ConnectionManager()

settings = {
    "game_path": r"F:\SteamLibrary\steamapps\common\Deadlock\game\bin\win64\deadlock.exe"
}

extraction_state = {
    "running": False,
    "launcher": None,
    "extractor": None
}

def fetch_hero_data_web():
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

hero_data, api_success = fetch_hero_data_web()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    abilities_dir = images_dir / "abilities"
    extracted_images = {}
    
    for hero in hero_data:
        hero_id = hero["id"]
        hero_name = hero["name"]
        extracted_images[hero_id] = {
            "name": hero_name,
            "abilities": {}
        }
        
        for ability_index in range(1, 5):
            filename = f"hero{hero_id}_ability_{ability_index}.png"
            filepath = abilities_dir / filename
            
            if filepath.exists():
                extracted_images[hero_id]["abilities"][ability_index] = {
                    "filename": filename,
                    "path": f"/images/abilities/{filename}"
                }
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "hero_data": hero_data,
        "extracted_images": extracted_images,
        "extraction_running": extraction_state["running"],
        "api_success": api_success,
        "hero_count": len(hero_data)
    })

@app.get("/api/hero-data")
async def get_hero_data():
    return {
        "heroes": hero_data,
        "api_success": api_success,
        "count": len(hero_data),
        "source": "API" if api_success else "Fallback"
    }

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "game_path": settings["game_path"]
    })

@app.post("/settings")
async def update_settings(game_path: str = Form(...)):
    settings["game_path"] = game_path
    return RedirectResponse(url="/", status_code=303)

@app.post("/start-extraction")
async def start_extraction():
    if extraction_state["running"]:
        return {"status": "error", "message": "Extraction already running"}
    
    extraction_state["running"] = True
    
    async def websocket_callback(message):
        await manager.send_message(message)
    
    async def run_extraction():
        try:
            launcher = DeadlockLauncher(settings["game_path"], websocket_callback)
            extractor = HeroImageExtractor(websocket_callback)
            
            extraction_state["launcher"] = launcher
            extraction_state["extractor"] = extractor
            
            if await launcher.launch_game():
                await websocket_callback({"type": "status", "message": "Game is ready for image extraction"})
                
                if not await extractor.extract_hero_abilities():
                    await websocket_callback({"type": "status", "message": "Extraction stopped by user"})
                else:
                    await extractor.extract_hero_stats()
                    
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
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

def run_web_app():
    uvicorn.run(app, host="127.0.0.1", port=3000)