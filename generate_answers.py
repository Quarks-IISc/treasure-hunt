import json
import os
from dotenv import load_dotenv

load_dotenv()

CLUES_FILE = "clues.json"
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8010/treasure-hunt/")
OUTPUT_FILE = "answers.txt"

def generate_answers():
    if not os.path.exists(CLUES_FILE):
        print(f"Error: {CLUES_FILE} not found.")
        return

    with open(CLUES_FILE, "r") as f:
        clues = json.load(f)

    # Sort by clue order
    def get_sort_val(clue_order):
        if not clue_order or clue_order == "None": return [999, 999]
        if "." in clue_order:
            try: return [int(p) for p in clue_order.split(".")]
            except: return [999, 999]
        return [int(clue_order), 0] if clue_order.isdigit() else [999, 999]

    clues.sort(key=lambda x: get_sort_val(x["clue_order"]))

    lines = []
    for c in clues:
        url = f"{BASE_URL}?clue={c['clue_hash']}"
        answer = c.get("wordle_answer", "N/A")
        order = c.get("clue_order", "?")
        lines.append(f"{order} | {url} | {answer}")

    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(lines))
    
    print(f"Success! {OUTPUT_FILE} generated with {len(clues)} entries.")

if __name__ == "__main__":
    generate_answers()
