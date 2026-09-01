# Vocab Mini

A daily 5×5 crossword, in the spirit of the NYT Mini — English, themeable,
and hosted for free on GitHub Pages. Players can pick any past date from
the archive; future dates are never reachable.

## Structure

```
index.html                 # the engine — grid, input, timer, checking. Never
                            # needs to change when you add puzzles or themes.
puzzles/
  general.json              # default theme, 30 puzzles
  motorcycling.json          # example theme, 30 puzzles
tools/
  generate_puzzle.py         # dictionary-backed puzzle generator/solver
  wordlists/
    common_fill.txt          # ~2,100 clean, common 3-5 letter words used
                              # to fill grid slots your theme list can't
    general.csv               # everyday English words for the default theme
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

Two flags shape the result:

- `--min-theme N` (default 1) rejects grids with fewer than N theme
  answers, so no puzzle in a themed set is themeless. On a 5×5, 2 is
  reachable but yields fewer puzzles and 3 is not achievable.
- `--max-repeat N` (default 1) is how many answers a new puzzle may share
  with all earlier ones. As a bank grows, every new grid inevitably shares
  more common fill with what came before, so raise this if generation
  stalls.
- `--no-theme-first` stops theme words being tried ahead of ordinary fill.
  Trying a large list first funnels the search down the same branches: the
  general bank had only 16 distinct reachable grids with its 623 words
  prioritised, and 73 without. Use it for a set with no theme to express
  (pair with `--min-theme 0`); leave it off for a real theme.
- `--dict-check` validates fill words against `/usr/share/dict/words`. Off
  by default — on macOS that is Webster's 1934, which lists no inflected
  forms and so rejects 373 curated answers (`ACTS`, `ADDS`, `ASKED`). Use
  it only for a fill list you have not vetted yourself.

**If generation stalls, the usual cause is grid variety, not vocabulary.**
Check how many *distinct* grids the solver can actually reach before adding
more words — a bank tops out when the search keeps rediscovering the same
handful of solutions.

## Adding a new theme

1. Create `tools/wordlists/<theme>.csv` — one `WORD,clue` pair per line,
   words 3–5 letters, e.g.:
   ```
   APEX,Fastest point through a corner
   DUCATI,Bologna-based bike maker
   ```
   30–50 entries is a workable minimum, but more is materially better:
   each puzzle needs six 5-letter, two 4-letter and two 3-letter answers,
   so 5-letter words are the scarcest resource. Longer theme words (6+)
   are read but silently dropped — they can't be placed in a 5×5, so
   `DUCATI` and `SILVERSTONE` are wasted entries. Clues must not contain
   commas; the loader reads the second field only and would truncate.

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
