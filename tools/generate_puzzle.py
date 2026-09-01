#!/usr/bin/env python3
"""
generate_puzzle.py — build new mini-crossword puzzles for a given theme.

Usage:
    python tools/generate_puzzle.py --theme motorcycling --count 5

Reads:
    tools/wordlists/<theme>.csv   (required) — your curated "word,clue" pairs
                                    for this theme, one per line, e.g.:
                                        DUCATI,Bologna-based bike maker
                                        APEX,Fastest point through a corner

Writes / appends to:
    puzzles/<theme>.json          — in the exact shape index.html expects

Design notes:
  - Grid shape (5x5, black squares at row0col3 and row4col1, same numbering)
    is fixed and matches index.html's TEMPLATE — do not change this unless
    you also update the grid layout in the engine.
  - Theme words are tried first for every slot; general "fill" words (a
    small bundled common-word/clue bank below) complete whatever the theme
    list can't. Most 3–5 letter theme lists are too sparse to fill an
    entire 5x5 grid, so this is expected and normal — the fill words are
    what real newspaper themed crosswords do too.
  - Any fill word without a bundled clue gets a "TODO: write a clue"
    placeholder rather than a fabricated one — grep the output for TODO
    before merging.
  - Existing answers already used in puzzles/<theme>.json are avoided
    where possible, so repeat-generating doesn't reuse the same words.
"""

import argparse
import csv
import json
import random
import re
import sys
import time
from pathlib import Path

SIZE = 5
BLACKS = {(0, 3), (4, 1)}

TEMPLATE = {
    "across": [
        {"num": 1, "row": 0, "col": 0, "len": 3},
        {"num": 5, "row": 1, "col": 0, "len": 5},
        {"num": 7, "row": 2, "col": 0, "len": 5},
        {"num": 8, "row": 3, "col": 0, "len": 5},
        {"num": 9, "row": 4, "col": 2, "len": 3},
    ],
    "down": [
        {"num": 1, "row": 0, "col": 0, "len": 5},
        {"num": 2, "row": 0, "col": 1, "len": 4},
        {"num": 3, "row": 0, "col": 2, "len": 5},
        {"num": 4, "row": 0, "col": 4, "len": 5},
        {"num": 6, "row": 1, "col": 3, "len": 4},
    ],
}

BLOCKLIST = {
    "SLAVE", "ABUSE", "DIES", "DEAD", "DYING", "KILL", "KILLS", "GUNS", "GUN",
    "RAPE", "HATE", "HATES", "DRUNK", "DRUGS", "DRUG", "NAZI", "DAMN", "HELL",
    "CRAP", "CURSE", "WAR", "WARS", "BOMB", "BOMBS", "BLOOD", "FEAR", "CRIES",
    "CRY", "WEEP", "UGLY", "FAT", "DUMB", "EVIL", "SIN", "SINS", "LIAR",
    "LIES", "LIE", "STOLE", "STEAL", "THEFT", "JAIL", "PRISON", "GUILTY",
    "PANIC", "SCARE", "SCARY", "GRIEF", "SUFFER", "PAIN", "HURT", "WOUND",
    "BRA", "RAGE", "BLAME", "SHAME", "ANGRY", "ANGER", "CREEP", "CREEPY",
    "GROSS", "FILTH", "GORE", "GORY", "CRASH", "WRECK", "SMASH",
}

# Small bundled fallback fill bank: common, clean, already-clued short
# words used to complete grids around your theme words. Extend freely —
# it's just a dict of WORD -> clue, lengths 3-5.
FILL_BANK = {
    "ART": "Museum display", "ONE": "First number", "TWO": "Number after one",
    "NEW": "Not used before", "SEE": "Perceive with the eyes", "SKY": "Where clouds float",
    "SEA": "Body of salt water", "TEN": "Perfect score, some say", "OFF": "Not switched on",
    "AMP": "Guitar amplifier, briefly", "FIN": "Shark's steering part", "ERA": "Historical period",
    "MOD": "Trendy, in the '60s", "YET": "Not ___ (still pending)", "NOR": "Neither... ___",
    "CAB": "Taxi", "TOY": "Plaything", "ADD": "Combine numbers", "SAT": "Took a seat",
    "ADS": "Commercials", "ITS": "Belonging to it", "ARM": "Limb with a hand",
    "RENT": "Monthly payment to a landlord", "SOME": "A few, informally", "NINE": "One below ten",
    "NODE": "Junction in a network", "GENE": "Unit of DNA", "WALL": "Surface for hanging art",
    "ORAL": "Spoken rather than written", "IDOL": "Object of fan worship", "REEL": "Fishing rod part",
    "MEAT": "Butcher's product", "FIRE": "Let an employee go", "TIES": "Neckwear, plural",
    "AREA": "Region", "DROP": "Let fall", "MARK": "Grade, or a stain",
    "TRIES": "Makes attempts", "SENSE": "Common ___", "VERSE": "A poem's stanza",
    "ONION": "Vegetable that brings tears", "ITEMS": "Entries on a shopping list",
    "RANGE": "Kitchen appliance with burners", "ALIEN": "Extraterrestrial being",
    "CLONE": "Exact genetic copy", "TRACE": "Follow back to the source",
    "RENEW": "Extend a library book", "ARENA": "Sports venue", "RAPID": "Lightning-fast",
    "MARCH": "Month before April", "DEPOT": "Bus or train station", "LADEN": "Weighed down with cargo",
    "LOVES": "Adores deeply", "IDEAS": "Brainwave results", "OLIVE": "Martini garnish",
    "EVERY": "Each, without exception", "ASSET": "Valuable resource", "EASE": "Freedom from effort",
    "PIANO": "Instrument with 88 keys", "ERROR": "Mistake", "NEEDS": "Requires",
    "OPENS": "Unlocks or begins", "FARES": "Taxi or bus charges", "HORSE": "Animal you might saddle up",
    "LEASE": "Rental contract", "LATER": "See you ___", "OTHER": "Not this one, the ___ one",
    "ALLOW": "Give permission", "PATHS": "Hiking trails", "FERRY": "Boat that shuttles across water",
    "SEEK": "Look for", "ADOBE": "Sun-baked clay brick", "TOTAL": "Grand sum",
    "ALERT": "Watchful and ready", "FATAL": "Ultimately serious", "NOTES": "Study jottings",
    "DELTA": "River's mouth landform", "BARE": "Uncovered, plain", "LEGAL": "Permitted by law",
    "DEALT": "Distributed playing cards", "ELITE": "The very best of a group",
    "ELDER": "Older, more senior person", "AGAIN": "One more time", "ALTER": "Change or modify",
    "ALTO": "Voice type between soprano and tenor", "TRADE": "Buy and sell", "SITES": "Web pages",
    "USAGE": "Manner of use", "STEAM": "Vapor from boiling water", "SEEDS": "What plants grow from",
    "ISSUE": "Topic under discussion", "OASIS": "Desert watering hole", "MASON": "Bricklayer",
    "ADOPT": "Take in as one's own", "PROVE": "Show to be true", "DEALS": "Business agreements",
    "LIVE": "Broadcast in real time", "REAR": "Back part", "NET": "Fishing gear, or a total after deductions",
}


def load_dictwords():
    """A basic real-word check so fallback fill never invents non-words."""
    path = Path("/usr/share/dict/words")
    if not path.exists():
        return None
    words = set()
    for line in path.read_text().splitlines():
        if re.fullmatch(r"[a-z]+", line.strip()):
            words.add(line.strip().upper())
    return words


def load_theme_words(csv_path):
    theme = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row or row[0].strip().startswith("#"):
                continue
            word, clue = row[0].strip().upper(), row[1].strip()
            if not re.fullmatch(r"[A-Z]+", word):
                print(f"  skipping invalid theme entry: {row}", file=sys.stderr)
                continue
            theme[word] = clue
    return theme


def load_existing_bank(out_path):
    if not out_path.exists():
        return [], set()
    data = json.loads(out_path.read_text())
    used = set()
    for entry in data:
        for d in (entry.get("across", {}), entry.get("down", {})):
            for word, _clue in d.values():
                used.add(word.upper())
    return data, used


def load_fill_words(fill_path):
    """Large structural fill list (word only, no clue) for good crossing
    coverage. Falls back to the small embedded FILL_BANK if the bundled
    tools/wordlists/common_fill.txt isn't found."""
    if fill_path and Path(fill_path).exists():
        words = {w.strip().upper() for w in Path(fill_path).read_text().splitlines() if w.strip()}
        return words
    print("  (no common_fill.txt found — using the small embedded fill bank; "
          "theme words may fail to cross. See --fill-words.)", file=sys.stderr)
    return set(FILL_BANK.keys())


def build_pools(theme_words, fill_words, dictwords):
    """word -> clue for both theme and fill, split by length, theme-first order."""
    pools = {3: [], 4: [], 5: []}
    for w, c in theme_words.items():
        if len(w) in pools:
            pools[len(w)].append((w, c, True))  # True = theme word, tried first
    for w in fill_words:
        if len(w) in pools and w not in theme_words and w not in BLOCKLIST:
            if dictwords is None or w in dictwords:
                clue = FILL_BANK.get(w, "")  # may be filled in later, else TODO
                pools[len(w)].append((w, clue, False))
    return pools


def solve_one(pools, avoid_words, seed):
    rng = random.Random(seed)
    ordered = {}
    for length, entries in pools.items():
        lst = list(entries)
        rng.shuffle(lst)
        # theme words first, then fill; both shuffled internally for variety
        lst.sort(key=lambda e: (e[0] in avoid_words, not e[2]))
        ordered[length] = lst

    grid = {}
    sol = {}  # slot_key -> (word, clue, is_theme)

    def key(r, c):
        return (r, c)

    slots = {}
    for cl in TEMPLATE["across"]:
        slots[("A", cl["num"])] = [(cl["row"], cl["col"] + i) for i in range(cl["len"])]
    for cl in TEMPLATE["down"]:
        slots[("D", cl["num"])] = [(cl["row"] + i, cl["col"]) for i in range(cl["len"])]

    def candidates(slot_id):
        cells = slots[slot_id]
        pattern = "".join(grid.get(c, ".") for c in cells)
        rx = re.compile("^" + pattern + "$")
        used_here = {w for (w, _c, _t) in sol.values()}
        return [e for e in ordered[len(cells)] if rx.match(e[0]) and e[0] not in used_here]

    def place(slot_id, entry):
        added = []
        for cell, ch in zip(slots[slot_id], entry[0]):
            if cell not in grid:
                grid[cell] = ch
                added.append(cell)
        return added

    def unplace(added):
        for c in added:
            del grid[c]

    start = time.time()

    def backtrack(remaining):
        if time.time() - start > 15:
            raise TimeoutError
        if not remaining:
            return True
        best = min(remaining, key=lambda s: len(candidates(s)))
        cands = candidates(best)
        if not cands:
            return False
        rest = [s for s in remaining if s != best]
        for entry in cands:
            added = place(best, entry)
            sol[best] = entry
            if backtrack(rest):
                return True
            del sol[best]
            unplace(added)
        return False

    try:
        ok = backtrack(list(slots.keys()))
    except TimeoutError:
        ok = False
    if not ok:
        return None

    across, down = {}, {}
    for (kind, num), entry in sol.items():
        word, clue, is_theme = entry
        if not clue:
            clue = f"TODO: write a clue for {word}"
        target = across if kind == "A" else down
        target[num] = [word, clue]
    return {"across": across, "down": down}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", required=True)
    ap.add_argument("--wordlist", default=None, help="defaults to tools/wordlists/<theme>.csv")
    ap.add_argument("--fill-words", default="tools/wordlists/common_fill.txt",
                     help="large structural fill list, word-per-line (default bundled file)")
    ap.add_argument("--out", default=None, help="defaults to puzzles/<theme>.json")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    wordlist_path = Path(args.wordlist or f"tools/wordlists/{args.theme}.csv")
    out_path = Path(args.out or f"puzzles/{args.theme}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not wordlist_path.exists():
        print(f"Theme word list not found: {wordlist_path}", file=sys.stderr)
        print("Create it as CSV rows of WORD,clue and try again.", file=sys.stderr)
        sys.exit(1)

    theme_words = load_theme_words(wordlist_path)
    dictwords = load_dictwords()
    fill_words = load_fill_words(args.fill_words)
    pools = build_pools(theme_words, fill_words, dictwords)

    existing_bank, used_words = load_existing_bank(out_path)

    made = 0
    seed = args.seed if args.seed is not None else random.randint(0, 1_000_000)
    attempts = 0
    todo_count = 0
    while made < args.count and attempts < args.count * 200:
        attempts += 1
        result = solve_one(pools, used_words, seed)
        seed += 1
        if result is None:
            continue
        new_words = {w for w, _c in result["across"].values()} | {w for w, _c in result["down"].values()}
        if len(new_words & used_words) > 1:
            continue  # too much overlap with prior puzzles, try another seed
        existing_bank.append(result)
        used_words |= new_words
        made += 1
        for d in (result["across"], result["down"]):
            for _w, c in d.values():
                if c.startswith("TODO"):
                    todo_count += 1
        print(f"puzzle {len(existing_bank)}: "
              f"{' / '.join(w for w, _ in result['across'].values())}"
              f" | {' / '.join(w for w, _ in result['down'].values())}")

    if made < args.count:
        print(f"Only generated {made}/{args.count} — your theme word list may be too sparse "
              f"for the remaining slots. Add more short (3-5 letter) theme words and re-run.",
              file=sys.stderr)

    out_path.write_text(json.dumps(existing_bank, indent=2))
    print(f"\nWrote {len(existing_bank)} total puzzles to {out_path}")
    if todo_count:
        print(f"{todo_count} clue(s) marked TODO — grep the file and fill those in before merging.")


if __name__ == "__main__":
    main()
