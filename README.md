# Treasure Hunt

A self-hosted QR-code treasure hunt. Teams register, scan QR codes hidden around a venue, solve a Wordle at each stop, and get riddles leading to the next location. A live leaderboard shows how far each team has progressed.

## How it works

- Every clue has an **order** `X.Y`: `X` is the step number, `Y` is the track. `1.1`, `2.1`, `3.1`… is track 1; `1.2`, `2.2`… is track 2, and so on. You can have any number of tracks.
- The home page shows the Wordle hint of every starting clue (`1.Y`).
- Scanning a QR opens `/?clue=<clue_hash>`. The team solves that clue's Wordle (`wordle_answer`) and then sees the **building** and **place** riddles plus the Wordle hint for the next clue in the same track.
- A team is locked to the track of the first clue it solves and can't skip steps.
- Teams and progress are stored in `teams.json`, which is created automatically.

## Setup

```bash
uv sync            # or: pip install -r requirements.txt
cp .env.example .env
cp clues.example.json clues.json
```

Edit `.env` (event name, secret key, public base URL, hash salt), then fill in `clues.json` with your clues.

### Clue fields

| Field | Purpose |
|---|---|
| `clue_hash` | Unique, unguessable ID that goes in the QR link |
| `clue_order` | `step.track`, e.g. `3.2` |
| `wordle_answer` | Word the team must guess at this QR |
| `wordle_hint` | Hint for this clue's Wordle (shown with the previous clue's riddles, or on the home page for step 1) |
| `building_clue` / `place_clue` | Riddles leading to *this* clue's location (shown after solving the previous step) |
| `actual_building` / `actual_spot` | Real location, used only in the organiser manifest |

### Optional: pulling clues from Airtable

Set the `AIRTABLE_*` variables and run `python sync_clues.py`. It expects the columns `Order`, `Location`, `Exact room/place inside the Location mentioned above`, `Clue for Location-Building`, `Clue for the PLACE/ROOM`, `Hint for WORDLE` and `WORDLE Answer`. Clue hashes are derived from the record ID and `HASH_SALT`.

## Running

```bash
python main.py
```

Starts the server on `0.0.0.0:$PORT` and prints the local and network links.

## Organiser tools

- `python get_links.py`: writes a QR code per clue plus a `manifest.txt` with the real locations to `qrcodes_package/`, and zips it.
- `python generate_answers.py`: writes `answers.txt` with every clue's order, link and Wordle answer.

Both use `BASE_URL` from `.env`, so set it to the address teams will actually reach before printing QR codes.

> `clues.json`, `teams.json`, the generated answers and the QR package are gitignored. Never commit them, because they reveal the answers and team passwords.
