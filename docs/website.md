# Landing page

The project website lives at <https://zichenwang114514.github.io/chemdraw-skill/> (Chinese) and <https://zichenwang114514.github.io/chemdraw-skill/en/> (English). It is a static site served by GitHub Pages from the `site/` folder; the READMEs remain the authoritative project description, and the website summarises them for people arriving from a search engine.

## Layout

| Path | Purpose |
| --- | --- |
| `site/index.html` | Chinese page, the canonical home. |
| `site/en/index.html` | English page. Same structure and shared stylesheet; the `<html lang>` drives the copy-button labels. |
| `site/styles.css`, `site/app.js` | Shared styles (light and dark) and the page behaviours: copy buttons, the before/after slider (it swings once when first seen) and its tabs, the theme switch, the scroll-in of the reaction arrows and the install picker. The page reads completely without the script. |
| `site/editor.js` | The hero structure editor: five molecules you can bond, rename, grow, move and erase, with the Analysis caption and the readback line recomputed from the canvas. Its words come from the `<script type="application/json" id="i18n">` block in each page, so the two languages share one script. |
| `site/fonts/` | Self-hosted Latin display face (Schibsted Grotesk, SIL OFL, licence beside it). Chinese text uses system fonts. Google Fonts is not used because it is unreliable from mainland China. |
| `site/og.png`, `site/favicon.svg`, `site/apple-touch-icon.png` | Social preview image (1200×630) and icons. |
| `site/sitemap.xml`, `site/robots.txt` | Search engine files. `lastmod` is refreshed on every deploy. |
| `site/<32 hex chars>.txt` | IndexNow key file. The deploy workflow reads the key from this filename; do not rename it without updating Bing Webmaster Tools. |
| `site/404.html` | Served by GitHub Pages for unknown paths. |
| `assets/readme/gallery/` | Gallery images shared with the READMEs. The deploy copies them to `/gallery/`. |

Both pages carry `canonical` and `hreflang` links to each other, Open Graph tags and JSON-LD (`SoftwareSourceCode`, `HowTo` for the three-step install, `FAQPage`). Keep the FAQ answers in sync with the README FAQ; the JSON-LD copies must match the visible text.

## Deployment

`.github/workflows/pages.yml` runs on every push to `main` that touches `site/`, the gallery images or the workflow itself, and can be started by hand from the Actions tab. It assembles `_site/`, deploys it with `actions/deploy-pages`, then pings IndexNow so Bing recrawls both pages. The repository's Pages source is set to "GitHub Actions"; no `gh-pages` branch exists.

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

## Editing rules

- Change both language pages together, as for the READMEs.
- Keep the `<title>` and `meta description` short: the title under 60 characters, the description under about 160.
- The hero window starts as a static SVG of aspirin, which is what readers see without scripts. With scripts, `editor.js` redraws the canvas from its molecule table. Every molecule in the table, the formula it declares and the caption it produces are checked by `tests/test_site.py`; the caption masses use the same atomic weights as `resolve_name`, so they agree with the numbers in the "How it works" command panels.
- The draw-in animation runs when `editor.js` adds `.play` to the window (on load, on a tab switch and on Replay) and ends at the first edit, so redrawing the canvas never restarts it. The `--i` property on each bond orders it. Keep `prefers-reduced-motion` behaviour: no animation and no Replay button.
- Add a molecule by adding a `data-mol` tab to both pages, a name in both `i18n` tables and an entry in `MOLS`. The entry is a name, the SMILES that `cdx.py call resolve_name` returns for it, its formula, atoms `[symbol, x, y]` and bonds `[from, to, order]` in Kekule form, on a 323 by 262 canvas. Coordinates came from RDKit (`Compute2DCoords` with CoordGen, principal axis horizontal, bond length 62 shrunk to fit with a margin); aspirin keeps ChemDraw's own layout. Only C, N, O, S, F, Cl and Br are supported.
- The command panels in "How it works" hold output that was produced by running the bundled runtime on aspirin. Paths are shortened with an ellipsis and `resolve_name` is abridged; rerun the commands and update both pages if a tool's output changes.
- The calculator section shows `assets/readme/gallery/calculator-light.png` and `calculator-dark.png`, which the READMEs use too (a `<picture>` there, a CSS swap on the site that follows the theme switch). They are 1300 by 1500 screenshots of the page that `reaction_calculator` writes for benzyl alcohol, acetyl chloride, triethylamine and dichloromethane with 120 mg isolated product and `reagent_safety` on (the example in the README). Retake both when the calculator layout changes: set `data-theme="light"` or `"dark"` on the page's `<html>` element and capture each with a headless browser at 1300 by 1500. Keep the numbers in the page text and the FAQ consistent with them.
- "How it works" is drawn as a vertical reaction scheme: each step is a reaction arrow with the tool written beside it, leading to the file it produces. Keep the four steps in sync with the README.
- The install picker in `app.js` takes each agent's installer flag and Skill folder from the radio buttons in the HTML, which mirror `AGENTS` in `scripts/install.py`; update them together. The static commands show the Claude Code and Windows defaults.
- The theme switch follows the system until it is used, then keeps the visitor's choice in `localStorage`; a one-line script in each page's `<head>` applies it before first paint. Dark colours are defined twice in `styles.css` (system preference and explicit choice); change both.
- Do not add analytics or third-party scripts without a note in the footer; the page currently loads nothing from outside the site.

## Search console

Bing Webmaster Tools verification uses a `<meta name="msvalidate.01">` tag in both pages' `<head>`. After verifying, submit `sitemap.xml` once; later changes are picked up through IndexNow.
