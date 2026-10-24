# Landing page

The project website lives at <https://zichenwang114514.github.io/chemdraw-skill/> (Chinese) and <https://zichenwang114514.github.io/chemdraw-skill/en/> (English). It is a static site served by GitHub Pages from the `site/` folder; the READMEs remain the authoritative project description, and the website summarises them for people arriving from a search engine.

## Layout

| Path | Purpose |
| --- | --- |
| `site/index.html` | Chinese page, the canonical home. |
| `site/en/index.html` | English page. Same structure and shared stylesheet; the `<html lang>` drives the copy-button labels. |
| `site/styles.css`, `site/app.js` | Shared styles (light and dark) and the behaviours: copy buttons, the before/after slider and its tabs, the hero replay button and the install picker. The page reads completely without the script. |
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
- The hero molecule is an inline SVG of aspirin generated from RDKit coordinates; the `--i` custom property on each path orders the draw-in animation, which runs when `app.js` adds `.play` to the window. Edit it only to replace the molecule, and keep `prefers-reduced-motion` behaviour (no animation, no replay button). The Analysis caption (formula, exact mass, molecular weight) must match the molecule.
- "How it works" is drawn as a vertical reaction scheme: each step is a reaction arrow with the tool written beside it, leading to the file it produces. Keep the four steps in sync with the README.
- The install picker in `app.js` takes each agent's installer flag and Skill folder from the radio buttons in the HTML, which mirror `AGENTS` in `scripts/install.py`; update them together. The static commands show the Claude Code and Windows defaults.
- Do not add analytics or third-party scripts without a note in the footer; the page currently loads nothing from outside the site.

## Search console

Bing Webmaster Tools verification uses a `<meta name="msvalidate.01">` tag in both pages' `<head>`. After verifying, submit `sitemap.xml` once; later changes are picked up through IndexNow.
