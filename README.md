# Mini Crossword

A daily 5×5 crossword, in the spirit of the NYT Mini — English, themeable,
and hosted for free on GitHub Pages.

## Structure

```
index.html                 # the engine — grid, input, timer, checking. Never
                            # needs to change when you add puzzles or themes.
puzzles/
  general.json              # default theme, 8 puzzles
  motorcycling.json          # example theme (sample included)
tools/
  generate_puzzle.py         # dictionary-backed puzzle generator/solver
  wordlists/
    common_fill.txt          # ~2,100 clean, common 3-5 letter words used
                              # to fill grid slots your theme list can't
    motorcycling.csv          # example theme word list — WORD,clue pairs
.github/workflows/deploy.yml # auto-publishes to Pages on every push to main
```

## Hosting

Enable **Settings → Pages → Deploy from a branch → main** (or just let the
included Action handle it — it deploys automatically on every push to
`main`). No build step.

## Adding puzzles to an existing theme

```bash
python tools/generate_puzzle.py --theme general --count 5
```

Generates 5 new solver-verified puzzles and appends them to
`puzzles/general.json`, skipping repeats where possible.

## Adding a new theme

1. Create `tools/wordlists/<theme>.csv` — one `WORD,clue` pair per line,
   words 3–5 letters, e.g.:
   ```
   APEX,Fastest point through a corner
   DUCATI,Bologna-based bike maker
   ```
   30–50 entries is a good starting size. Longer theme words (6+) are
   read but can't be placed in this 5×5 grid shape — keep to 3–5 letters.

2. Generate:
   ```bash
   python tools/generate_puzzle.py --theme motorcycling --count 5
   ```

3. **Grep for `TODO`** in the output file and write real clues for any
   fill words that didn't have one bundled. This is expected — a small
   curated theme list won't cover every slot in every puzzle, so the
   solver borrows from the common fill list to complete the grid, same
   as a real themed newspaper crossword.

4. Add the theme to the dropdown in `index.html` (one line — see the
   `THEMES` list near the top of the script).

## A practical Claude Code workflow

```bash
git checkout -b add-westend-batch1
python tools/generate_puzzle.py --theme west-end --count 5
# review + fill in TODO clues
git add puzzles/west-end.json
git commit -m "Add 5 West End puzzles"
git push -u origin add-westend-batch1
# open a PR, review, merge to main -> auto-deploys
```

## Notes on quality control

- `generate_puzzle.py` only ever places real dictionary words (checked
  against the system word list) or words you've explicitly curated in a
  theme CSV — it can't invent gibberish.
- A small blocklist filters out common-fill words with violent, adult,
  or otherwise unwanted connotations. It does **not** filter your theme
  CSV — that's curated by you, so use your judgement there (e.g. skip
  "CRASH" for a motorcycling list).
- Re-running the generator against an existing `puzzles/<theme>.json`
  avoids reusing answers you've already shipped, so the bank grows
  without getting repetitive.
