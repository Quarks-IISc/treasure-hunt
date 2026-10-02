import os
import requests
import json
import hashlib
from dotenv import load_dotenv

load_dotenv()

AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_ID = os.getenv("AIRTABLE_TABLE_ID")
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
CLUES_FILE = "clues.json"
HASH_SALT = os.getenv("HASH_SALT", "change-me")

def generate_clue_hash(clue_id: str):
    return hashlib.sha256(f"{HASH_SALT}_{clue_id}".encode()).hexdigest()[:12]

def fetch_all_from_airtable():
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_ID}"
    all_records = []
    offset = None
    while True:
        params = {"offset": offset} if offset else {}
        r = requests.get(url, headers=headers, params=params)
        data = r.json()
        all_records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset: break
    return all_records

def sync():
    print("Fetching from Airtable...")
    records = fetch_all_from_airtable()
    
    clues = []
    print(f"Syncing {len(records)} clues to JSON...")
    for rec in records:
        f = rec.get("fields", {})
        rid = rec.get("id")
        short_id = rid[3:] if rid.startswith("rec") else rid
        c_hash = generate_clue_hash(short_id)
        
        # ACTUAL LOCATIONS (For manifest)
        actual_building = f.get("Location", "Unknown Building")
        actual_spot = f.get("Exact room/place inside the Location mentioned above", "Unknown Spot")

        # HINTS (For the game)
        building_hint = f.get("Clue for Location-Building", "")
        place_hint = f.get("Clue for the PLACE/ROOM", "")

        clues.append({
            "id": short_id,
            "clue_hash": c_hash,
            "clue_order": str(f.get("Order", "")),
            "actual_building": actual_building,
            "actual_spot": actual_spot,
            "building_clue": building_hint,
            "place_clue": place_hint,
            "wordle_hint": f.get("Hint for WORDLE", ""),
            "wordle_answer": f.get("WORDLE Answer", "")
        })
    
    with open(CLUES_FILE, "w") as f:
        json.dump(clues, f, indent=4)
        
    print(f"Sync Complete! {CLUES_FILE} is ready.")

if __name__ == "__main__":
    sync()
