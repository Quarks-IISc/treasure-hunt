import os
import json
import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, List, Tuple, Dict
from fastapi import FastAPI, Request, Form, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
CLUES_FILE = os.getenv("CLUES_FILE", "clues.json")
TEAMS_FILE = os.getenv("TEAMS_FILE", "teams.json")
SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key")
EVENT_NAME = os.getenv("EVENT_NAME", "Treasure Hunt")
PORT = int(os.getenv("PORT", "8010"))

app = FastAPI()
templates = Jinja2Templates(directory="templates")
templates.env.globals["event_name"] = EVENT_NAME

# --- JSON DATA HELPERS ---
def load_json(file_path: str):
    if not os.path.exists(file_path):
        return [] if "teams" in file_path else {}
    with open(file_path, "r") as f:
        return json.load(f)

def save_json(file_path: str, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

def get_current_team_json(request: Request):
    team_id = request.cookies.get("team_id")
    if not team_id:
        return None
    teams = load_json(TEAMS_FILE)
    for team in teams:
        if str(team.get("id")) == team_id:
            return team
    return None

def parse_order(order_str: str) -> Tuple[int, int]:
    if not order_str or order_str == "None":
        return (999, 999)
    if "." in order_str:
        try:
            parts = order_str.split(".")
            return (int(parts[0]), int(parts[1]))
        except:
            return (999, 999)
    return (int(order_str), 0) if order_str.isdigit() else (999, 999)

# --- ROUTES ---
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    team = get_current_team_json(request)
    clue = request.query_params.get("clue")
    
    if clue:
        if not team:
            return RedirectResponse(url=f"/register?clue={clue}")
        return templates.TemplateResponse(request, "hunt.html", {"team": team, "clue": clue})
    
    clues = load_json(CLUES_FILE)
    # One starting card per track, from every clue with order "1.<track>"
    start_hints = sorted(
        (parse_order(c["clue_order"])[1], c["wordle_hint"])
        for c in clues if parse_order(c["clue_order"])[0] == 1
    )
    return templates.TemplateResponse(request, "index.html", {"team": team, "start_hints": start_hints})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    clue = request.query_params.get("clue")
    return templates.TemplateResponse(request, "register.html", {"clue": clue})

@app.post("/register")
async def register(
    request: Request,
    response: Response,
    name: str = Form(...),
    password: str = Form(...),
    clue: Optional[str] = Form(None)
):
    teams = load_json(TEAMS_FILE)
    team = next((t for t in teams if t["name"] == name), None)
    target_url = "/" if not clue else f"/?clue={clue}"
    
    if team:
        if team["password"] == password:
            response = RedirectResponse(url=target_url, status_code=303)
            response.set_cookie(key="team_id", value=str(team["id"]), max_age=31536000)
            return response
        else:
            return templates.TemplateResponse(request, "register.html", {"error": "Invalid password for this team.", "clue": clue})
    
    new_id = len(teams) + 1
    new_team = {
        "id": new_id,
        "name": name,
        "password": password,
        "progress": []
    }
    teams.append(new_team)
    save_json(TEAMS_FILE, teams)
    
    response = RedirectResponse(url=target_url, status_code=303)
    response.set_cookie(key="team_id", value=str(new_id), max_age=31536000)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/register")
    response.delete_cookie("team_id")
    return response

@app.get("/api/clue/{clue_hash}")
async def get_clue(clue_hash: str, request: Request):
    team = get_current_team_json(request)
    if not team:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    clues = load_json(CLUES_FILE)
    clue_map = {c["clue_hash"]: c for c in clues}
    db_clue = clue_map.get(clue_hash)
    
    if not db_clue:
        return JSONResponse(status_code=404, content={"error": "Clue not found"})

    clue_order = str(db_clue["clue_order"])
    clue_num, track_num = parse_order(clue_order)
    progress = team.get("progress", [])

    # 1. Track Locking
    if progress:
        active_tracks = {parse_order(po)[1] for po in progress}
        if active_tracks and track_num not in active_tracks:
            return JSONResponse(status_code=403, content={"error": "You are on a different track! Stick to your path."})

    # 2. Sequence Check
    if clue_num > 1:
        prev_clues = [c for c in clues if parse_order(c["clue_order"])[1] == track_num and parse_order(c["clue_order"])[0] < clue_num]
        if prev_clues:
            prev_clues.sort(key=lambda x: parse_order(x["clue_order"])[0], reverse=True)
            immediate_prev_order = prev_clues[0]["clue_order"]
            if immediate_prev_order not in progress:
                return JSONResponse(status_code=403, content={"error": "You haven't solved the previous one!"})

    # Find NEXT clue in track
    next_clue = None
    all_in_track = [c for c in clues if parse_order(c["clue_order"])[1] == track_num]
    all_in_track.sort(key=lambda x: parse_order(x["clue_order"])[0])
    
    for i, c in enumerate(all_in_track):
        if c["clue_hash"] == clue_hash:
            if i + 1 < len(all_in_track):
                next_clue = all_in_track[i+1]
            break

    is_solved = clue_order in progress

    return {
        "is_solved": is_solved,
        "WORDLE Answer": db_clue["wordle_answer"],
        "Clue for Location-Building": next_clue["building_clue"] if next_clue else "Congratulations! You have completed this track.",
        "Clue for the PLACE": next_clue["place_clue"] if next_clue else "",
        "Hint for WORDLE": next_clue["wordle_hint"] if next_clue else "THE END"
    }

@app.post("/api/solve/{clue_hash}")
async def solve_clue(clue_hash: str, request: Request):
    team = get_current_team_json(request)
    if not team:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    clues = load_json(CLUES_FILE)
    db_clue = next((c for c in clues if c["clue_hash"] == clue_hash), None)
    if not db_clue:
        return JSONResponse(status_code=404, content={"error": "Clue not found"})

    clue_order = str(db_clue["clue_order"])
    
    # Reload teams to get freshest state
    teams = load_json(TEAMS_FILE)
    for t in teams:
        if str(t["id"]) == str(team["id"]):
            if clue_order not in t["progress"]:
                t["progress"].append(clue_order)
                save_json(TEAMS_FILE, teams)
            break
    
    return {"status": "success"}

@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard(request: Request):
    team = get_current_team_json(request)
    teams = load_json(TEAMS_FILE)
    
    # Group teams by number of clues solved
    levels = {}
    for t in teams:
        count = len(t.get("progress", []))
        if count not in levels:
            levels[count] = []
        levels[count].append(t["name"])
    
    # Sort levels descending (Highest count first)
    # Include ALL levels that have teams, including level 0
    sorted_levels = []
    # Using sorted(levels.keys()) ensures we catch 0, 1, 2...
    for count in sorted(levels.keys(), reverse=True):
        sorted_levels.append({
            "count": count,
            "teams": sorted(levels[count]) 
        })
        
    return templates.TemplateResponse(request, "leaderboard.html", {
        "levels": sorted_levels, 
        "team": team,
        "total_teams": len(teams)
    })

@app.get("/treasure-hunt/", response_class=HTMLResponse)
async def treasure_hunt_redirect(request: Request, clue: Optional[str] = None):
    if not clue:
        return RedirectResponse(url="/")
    return RedirectResponse(url=f"/?clue={clue}")

if __name__ == "__main__":
    import uvicorn
    import socket

    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
        if local_ip.startswith("127."):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
    except:
        local_ip = "127.0.0.1"

    print("\n" + "="*50)
    print(f"  {EVENT_NAME.upper()} SERVER STARTING")
    print("="*50)
    print(f"  Local Link:  http://127.0.0.1:{PORT}")
    print(f"  Network Link: http://{local_ip}:{PORT}")
    print("="*50 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=PORT)
