import os
from dotenv import load_dotenv
import json
import qrcode
import shutil

# --- CONFIGURATION ---
load_dotenv()

CLUES_FILE = "clues.json"
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8010/treasure-hunt/")
OUTPUT_DIR = "qrcodes_package"

def get_sort_val(clue_order: str):
    if not clue_order or clue_order == "None": return [999, 999]
    if "." in clue_order:
        try: return [int(p) for p in clue_order.split(".")]
        except: return [999, 999]
    return [int(clue_order), 0] if clue_order.isdigit() else [999, 999]

def generate_package():
    if not os.path.exists(CLUES_FILE):
        print(f"Error: {CLUES_FILE} not found. Run sync_clues.py first!")
        return

    with open(CLUES_FILE, "r") as f:
        clues = json.load(f)

    clues.sort(key=lambda x: get_sort_val(x["clue_order"]))
    
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    manifest_lines = []
    manifest_lines.append("TREASURE HUNT QR MANIFEST")
    manifest_lines.append("="*50)
    manifest_lines.append(f"Generated on: {os.popen('date').read().strip()}")
    manifest_lines.append("="*50 + "\n")

    print(f"Generating package for {len(clues)} clues...")
    
    for c in clues:
        order = str(c["clue_order"])
        link = f"{BASE_URL}?clue={c['clue_hash']}"
        
        # USE THE NEW FIELDS FROM SYNC_CLUES.PY
        # actual_building maps to "Location" in Airtable
        # actual_spot maps to "Exact room/place inside the Location mentioned above" in Airtable
        building = c.get("actual_building", "Unknown")
        spot = c.get("actual_spot", "Unknown")
        
        manifest_lines.append(f"ORDER: {order}")
        manifest_lines.append(f"BUILDING: {building}")
        manifest_lines.append(f"EXACT SPOT: {spot}")
        manifest_lines.append(f"LINK: {link}")
        manifest_lines.append("-" * 30)

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(link)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Filename should use the actual building name
        safe_loc = "".join(x for x in building if x.isalnum())
        filename = f"{order.replace('.', '_')}_{safe_loc}.png"
        img_path = os.path.join(OUTPUT_DIR, filename)
        img.save(img_path)
        
    with open(os.path.join(OUTPUT_DIR, "manifest.txt"), "w") as f:
        f.write("\n".join(manifest_lines))
    
    zip_name = "treasure_hunt_package"
    shutil.make_archive(zip_name, 'zip', OUTPUT_DIR)
    
    print(f"\nSUCCESS!")
    print(f"1. Individual QRs and manifest.txt are in '{OUTPUT_DIR}/'")
    print(f"2. Final zip created: '{zip_name}.zip'")

if __name__ == "__main__":
    generate_package()
