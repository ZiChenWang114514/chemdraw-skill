# Landing page

The project website lives at <https://zichenwang114514.github.io/chemdraw-skill/> (Chinese) and <https://zichenwang114514.github.io/chemdraw-skill/en/> (English), with the Molecule Lab at `lab/` under each. It is a static site served by GitHub Pages from the `site/` folder; the READMEs remain the authoritative project description, and the website summarises them for people arriving from a search engine.

## Layout

| Path | Purpose |
| --- | --- |
| `site/index.html` | Chinese page, the canonical home. |
| `site/en/index.html` | English page. Same structure and shared stylesheet; the `<html lang>` drives the copy-button labels. |
| `site/styles.css`, `site/app.js` | Shared styles (light and dark) and the page behaviours: copy buttons, the before/after slider (it swings once when first seen) and its tabs, the theme switch, the scroll-in of the reaction arrows, the "Run it" replay of the four steps, the install picker, the chapter progress bar with the current section in the nav, `glide` for jumps inside a page, the FAQ search and deep links, the grid that lights up around the pointer, the capability filter with its copyable example requests, and the figure viewer. `flashDone` is the one confirmation of a copy. The page reads completely without the script. |
| `site/chem.js` | The chemistry with no page in it, shared by the browser and Node: the molecule table (`MOLS`) and the starting skeletons (`STARTERS`), `analyse`, the exporters, `cleanUp`, `applyTool` and `previewMarkup`, `formulaDelta`, drawing to an SVG string, the levels, the daily-only molecules (`DAILIES`), `graphKey`, the daily pick and streak, the error hunt, the isomer sets, share links and the progress store. |
| `site/editor.js` | The structure editor as `ChemEditor.mount`, which both the hero and the Lab use: five molecules you can bond, rename, grow, move, erase and clean up, by mouse, touch or keyboard, with undo and redo, the Analysis caption and the readback line recomputed from the canvas, and the rule that decides a win. It copies the drawing as SMILES, saves it as ACS Document 1996 CDXML and copies a share link. The end of the file is the hero, including today's molecule. |
| `site/lab/index.html`, `site/en/lab/index.html`, `site/lab.js` | The Molecule Lab: daily molecule, route map, error hunt, isomer hunt, collection, sketchpad and badges. The hash names the mode (`#daily`, `#levels`, `#level-<id>`, `#hunt`, `#isomers-<formula>`, `#dex`, `#free`, `#s=<drawing>`), so every mode can be linked and the Back button works. |
| `site/words.zh.js`, `site/words.en.js` | Every word the scripts show, as one JSON object behind `globalThis.ChemWords`, loaded before them. The two files must have the same keys. |
| `site/daily.zh.js`, `site/daily.en.js` | The names, tasks, hints and facts of the `DAILIES`, and the names of the `STARTERS`, as one JSON object (`names`, `tasks`) that the file merges into `ChemWords.names` and `ChemWords.challenge.tasks`. Each is loaded right after its `words.<lang>.js` on all four pages. The two files must have the same keys. |
| `tests/daily_sources.json` | Where every starter and daily molecule came from: PubChem CID and published SMILES, the OPSIN reading of its name (`opsin: null` with an `opsinNote` when OPSIN could not confirm it), and for each daily the page behind its fact. `tests/test_site.py` drives the answers from it. |
| `site/cursors/` | The four tool cursors, 32 by 32 with the crosshair at 8,8 and a white halo so they read on both themes. |
| `site/fonts/` | Self-hosted Latin display face (Schibsted Grotesk, SIL OFL, licence beside it). Chinese text uses system fonts. Google Fonts is not used because it is unreliable from mainland China. |
| `site/og.png`, `site/favicon.svg`, `site/apple-touch-icon.png` | Social preview image (1200×630) and icons. |
| `site/sitemap.xml`, `site/robots.txt` | Search engine files. `lastmod` is refreshed on every deploy. |
| `site/<32 hex chars>.txt` | IndexNow key file. The deploy workflow reads the key from this filename; do not rename it without updating Bing Webmaster Tools. |
| `site/404.html` | Served by GitHub Pages for unknown paths. |
| `assets/readme/gallery/` | Gallery images shared with the READMEs. The deploy copies them to `/gallery/`. |

The home pages and the Lab pages all carry `canonical` and `hreflang` links to each other and Open Graph tags; the home pages also carry JSON-LD (`SoftwareSourceCode`, `HowTo` for the three-step install, `FAQPage`). The FAQ on the two home pages must stay in step with each other and, where the README answers the same question, with the README. Each answer opens with a `<p class="lead">` that answers the question, then short paragraphs or a list inside `.answer`. Each entry has a stable `id` (`faq-…`) that deep links use. The JSON-LD answer is the visible text word for word, with blocks joined by one space; `FaqTests` checks this and the length of each paragraph.

## Design system

The tokens at the top of `styles.css` are the whole vocabulary, and `DesignSystemTests` in `tests/test_site.py` holds the file to them.

| Kind | Tokens | Use |
| --- | --- | --- |
| Radius | `--r-xs` 4, `--r-sm` 8, `--r-md` 12, `--r-pill` | Inline code and tool buttons; inputs, thumbnails, code blocks and tips; windows and panels; buttons, chips and toasts. `50%` is for round icons and dots only. |
| Type | `--display`, `--sans`, `--mono`, `--chem` | Headings and large numbers; everything else; commands and code only; labels inside the mock ChemDraw window, which keep fixed px. Numbers use tabular figures, not the mono face. |
| Size | `--fs-xs` .78, `--fs-sm` .875, `--fs-md` 1, `--fs-lg` 1.125, `--fs-xl` 1.375, `--fs-2xl` 1.75 rem, `--fs-code` | Plus the three heading clamps. Weights are 400, 500, 600 and 700. |
| Motion | `--t-fast` 120, `--t-med` 220, `--t-slow` 360 ms, `--ease` | Hover; opening and switching; scrolling. |
| Space | 4, 8, 12, 16, 24, 32, 48, 64 px | Every margin. |
| Shadow | `--shadow-window`, `--shadow-float` | The hero window; viewers, toasts and tips. |

- `.btn` is the one button: 40 px, or 32 with `.sm`; outlined, `.primary` or `.ghost`. With a coarse pointer every button is at least 40 px.
- Toolbar tips are drawn from `data-tip`, not `title`, so they also show on keyboard focus.
- Each drawing tool has a cursor in `site/cursors/` and every rule ends in a keyword fallback. The rest of the site keeps the system pointer.
- Page moves use view transitions, and hash jumps use `glide`. All of it falls back to an immediate change, and neither runs under `prefers-reduced-motion`.
- `@media (scripting: enabled)` reserves the room the hero's export row, palette and theme switch will take, so the page does not jump as `editor.js` loads. Keep it in step with those parts.

## Deployment

`.github/workflows/pages.yml` runs on every push to `main` that touches `site/`, the gallery images or the workflow itself, and can be started by hand from the Actions tab. It assembles `_site/`, deploys it with `actions/deploy-pages`, then pings IndexNow so Bing recrawls the four pages. The repository's Pages source is set to "GitHub Actions"; no `gh-pages` branch exists.

## Preview locally

The pages reference `gallery/…` and `styles.css` relative to the site root, so mirror the deploy layout:

```bash
mkdir -p /tmp/site/chemdraw-skill
cp -r site/. /tmp/site/chemdraw-skill/
cp -r assets/readme/gallery /tmp/site/chemdraw-skill/gallery
python -m http.server 8642 --directory /tmp/site
# open http://localhost:8642/chemdraw-skill/
```

Check both colour schemes and a 390 px viewport before pushing; the hero and the agent log are the parts most likely to overflow on narrow screens.

## Tests

`python -m unittest tests.test_site` checks the chemistry in Node and, when RDKit is installed, reads every exported structure back. With `SITE_BROWSER=1` it also serves the deploy layout and runs `tests/site_smoke.mjs`, which plays the site in headless Chrome with trusted mouse, keyboard and touch input: every level to three stars, one daily-only molecule on a starter in the hero and in the Lab (with a faked date), one level by keyboard alone, bond drags, clipboard, a real download, share links, the hunts, broken and refused storage, viewer gestures and 390 px at both colour schemes. It needs Node 22 or later and Chrome (`CHROME` names the browser). The `site` job in `validate.yml` runs all of this.

## Editing rules

- Change both language pages together, as for the READMEs.
- Keep the `<title>` and `meta description` short: the title under 60 characters, the description under about 160.
- The hero window starts as a static SVG of aspirin, which is what readers see without scripts. With scripts, `editor.js` redraws the canvas from its molecule table. Every molecule in the table, the formula it declares and the caption it produces are checked by `tests/test_site.py`; the caption masses use the same atomic weights as `resolve_name`, so they agree with the numbers in the "How it works" command panels.
- The draw-in animation runs when `editor.js` adds `.play` to the window (on load, on a tab switch and on Replay) and ends at the first edit, so redrawing the canvas never restarts it. The `--i` property on each bond orders it. Keep `prefers-reduced-motion` behaviour: no animation and no Replay button.
- Add a molecule by adding a `data-mol` tab to both home pages, a name in both word files and an entry in `MOLS`. The entry is a name, the SMILES that `cdx.py call resolve_name` returns for it, its formula, atoms `[symbol, x, y]` and bonds `[from, to, order]` in Kekule form, on a 323 by 262 canvas. Coordinates came from RDKit (`Compute2DCoords` with CoordGen, principal axis horizontal, bond length 62 shrunk to fit with a margin); aspirin keeps ChemDraw's own layout. Only C, N, O, S, F, Cl and Br are supported.
- The editor's exporters are plain functions (`toSmiles`, `toCdxml`, `cleanUp`) in `chem.js` that `tests/test_site.py` runs in Node. The SMILES of every table molecule and the CDXML read back through RDKit must match the molecule's `smiles`. `toCdxml` follows `cdxml_builder`: same ACS style values, `NeedsClean` on labelled atoms so ChemDraw lays the labels out itself. Check a native render when it changes.
- `applyTool` is the only place a tool's result is decided. The click carries out its plan and `previewMarkup` draws the same plan, so a preview cannot disagree with a click. Do not edit a graph for a tool anywhere else. A plan with `g: null` is a refusal and shows `not-allowed`. Previews, atom tips and the grid need `hover: hover` with `pointer: fine`, and the error hunt has none of them because they would give the answer away.
- Hotkeys follow ChemDraw: with the pointer or the keyboard cursor on an atom, C, N, O, S, F or L (Cl); on a bond, 1, 2 or 3; Delete on either. Tool keys (V, B, A, R, E) stay inside the window. Do not give a tool a key that is also an element key. The canvas takes focus: the arrows walk between atoms and bonds, Enter or Space applies the tool and Shift with an arrow nudges an atom. Anything added to the editor must work this way too, and goes in `shortcuts.rows` in both word files, which `?` lists.
- Touch on an atom with the bond tool draws a bond; touch anywhere else scrolls the page. Browsers ignore `touch-action` on shapes inside an SVG, so `editor.js` stops the scroll in `touchmove`.
- A level is an entry in `CHALLENGES` (chapter, start molecule and the moves that solve it) plus a `name`, `task`, `hint` and `fact` under `challenge.tasks` in both word files, and its compound's published SMILES in `CHALLENGE_ANSWERS` in `tests/test_site.py`. The target is defined by the moves, never by a hand-written SMILES in the page; the test proves the moves reach the named compound and that its CDXML reads back as that compound. Answers are compared with `graphKey`, which ignores layout and Kekule form but separates isomers and keeps over-valent atoms apart. A hint must work with a finger, so it names tools rather than hover-plus-key.
- A `fact` is a claim shown as true on a public page. Keep it to one or two plain sentences about the compound itself, no dosing or medical advice, and check it against a reference before adding it.
- Scoring: only chemical edits count as moves; Clean Up and moving atoms do not, Undo takes one back and Restart clears the count. A run of element or bond-order changes to one atom or bond is one move, so three stars need no hover keys. A win needs the right structure and no over-valent atom. Three stars is the level's own number of moves or fewer without the hint, two is more moves without the hint, one is any win with the hint.
- The daily molecule is picked by `dailyPick` from the visitor's local date, counted from `FIRST_DAY`, out of `[...CHALLENGES, ...DAILIES]`: the 20 levels, then 100 molecules that are only ever dailies, so the cycle is 120 days. Both lists must only ever grow at their ends, and `CHALLENGES` stays at 20 so the route map, the "x / 60" stars, the collection and the "all 20 levels" badge do not change. The stride of 7 must stay coprime with the length of the pool (120 = 2³·3·5, so it is); `tests/test_site.py` checks this, that 2026-10-31 still gives xanthine and that 120 consecutive days give 120 different molecules. Whoever grows the pool changes the cycle length: check the stride again.
- A daily-only molecule is not a level. `solveDaily` calls `record` only when `isLevel(id)`, so it saves `store.daily.solved` and the streak but never `store.levels`, stars, the collection or the badges that count levels. Anything new that looks a daily up by id must use `isLevel` or handle both kinds.
- Add a daily by appending `{ id, mol, solve }` to `DAILIES` (no chapter), an entry under `tasks` in both `daily.<lang>.js`, and its record in `tests/daily_sources.json`. Take the compound from PubChem by CID, never from memory, and run its name (or, if OPSIN cannot parse that, its IUPAC name) through OPSIN: the two must give the same non-isomeric SMILES. The moves must start from a molecule in `MOLS` or `STARTERS`, number 1 to 6, never run out of room when replayed with `applyTool`, and reach exactly that SMILES; only C, N, O, S, F, Cl and Br, neutral, one fragment, at most about 22 heavy atoms. Keep out explosives, chemical weapons and their precursors, recreational or controlled drugs and notable poisons. The `fact` must come from a page recorded as `factUrl` (Wikipedia or PubChem) that was read, in one or two plain sentences with no dosing or medical advice, in both languages saying the same thing. Mix easy and hard ones through the list so five- and six-move molecules do not cluster; the tests check runs in list order and in the order the days visit them.
- `STARTERS` (at most 20) are skeletons such as benzene, pyridine, indole or acetic acid for the dailies; they have the shape of a `MOLS` entry, are read by `load`, and appear neither on the hero's tabs nor among the Sketchpad's chips. Coordinates come from RDKit as for `MOLS`, with the bond length shrunk to 40 px so there is room to grow. Their names go in `names` of both `daily.<lang>.js`. `editor.restart` works with any of them; with no matching tab, the first hero tab stays reachable by keyboard.
- The error hunt's structures are wrong on purpose and the page says so. `makeHunt(seed)` must always yield rounds whose drawn structure differs from the truth and whose accepted spot is the changed atom or bond.
- The isomer hunt counts constitutional isomers only, and the page says so. `ISOMER_COUNTS` in the tests is checked by exhaustive construction.
- A share link carries the drawing in `#s=`. `decodeDrawing` is the only way in: symbols reach `innerHTML`, so it accepts listed elements only, whole bond orders, valid indices, numeric coordinates on the canvas and a size limit. Do not loosen it.
- Progress stays in `localStorage` under `chemdraw-skill-lab`, versioned, in this browser only, and the Lab says so. `parseStore` checks every field, and a broken or refused store must never stop a page.
- Each row of the capability list has a `data-kind` (the same sequence on both pages, one chip per kind in `.filters`) and an example request in `details.try`. The `.try-note` line above the list names what the requests need and links to the quick start, so the prerequisites still come before the first request. Keep the requests to things the Skill does, in the voice of someone asking an agent; a condition in a request is something the asker supplied.
- Images with `data-zoom` open in the figure viewer, which takes its caption from the `figcaption` of the surrounding figure.
- "Run it" types out whatever is in the four command panels, so it needs no separate script when those panels change. Without motion it opens all four at once.
- The command panels in "How it works" hold output that was produced by running the bundled runtime on aspirin. Paths are shortened with an ellipsis and `resolve_name` is abridged; rerun the commands and update both pages if a tool's output changes.
- The calculator section shows `assets/readme/gallery/stoichiometry-grid.png`, which the READMEs use too. It is ChemDraw's own stoichiometry grid in `toolkit/tests/runtime/data/stoichiometry-grid.cdxml` (benzyl alcohol, acetyl chloride, triethylamine and dichloromethane, 1.08 g of benzyl alcohol typed in), rendered natively with `render_cdxml_files` at 200 dpi. The page sets it on a white plate in both themes. Re-render it when that file changes, and keep the numbers in the page text and the FAQ consistent with it.
- "How it works" is drawn as a vertical reaction scheme: each step is a reaction arrow with the tool written beside it, leading to the file it produces. Keep the four steps in sync with the README.
- The install picker in `app.js` takes each agent's installer flag and Skill folder from the radio buttons in the HTML, which mirror `AGENTS` in `scripts/install.py`; update them together. The static commands show the Claude Code and Windows defaults.
- The theme switch follows the system until it is used, then keeps the visitor's choice in `localStorage`; a one-line script in each page's `<head>` applies it before first paint. Dark colours are defined twice in `styles.css` (system preference and explicit choice); change both.
- Do not add analytics or third-party scripts without a note in the footer; the page currently loads nothing from outside the site.

## Search console

Bing Webmaster Tools verification can use a `<meta name="msvalidate.01">` tag in both pages' `<head>`; no such tag is committed yet, so add it when Bing issues the code. After verifying, submit `sitemap.xml` once; later changes are picked up through IndexNow.
