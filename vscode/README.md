# ChemDraw 2D Studio & Mol* 3D Workbench for VS Code-Family IDEs

Universal Reaxys / SciFinder-style 2D chemical structure, reaction, mechanism, and substructure-query editor plus offline/online 3D Mol* conformer viewer for **VS Code**, **Cursor**, **Windsurf**, **Cline**, **Roo Code**, **Continue**, **Trae**, **Kiro**, **Qoder**, and **Antigravity**.

## Key Features

- **Reaxys / SciFinder 4-Edge Docked 2D Editor (`Ctrl+Alt+M`)**:
  - Dynamic ghost ring fusion & spiro preview across 18 vector ring & chair/bicyclo templates
  - 30-degree angle-snapped bond drawing, steric-aware 120-degree sprouting, linear 180-degree `sp` alkynes, and zigzag alkane chain drawing (`C2`-`C24`)
  - Lasso, rectangle, and whole-molecule selection with free-rotation bounding-box handle
  - Full 118-element IUPAC Periodic Table + isotopes (`D`, `T`, `13C`, `15N`, `18O`, `19F`)
  - Substructure query generics (`A`, `Q`, `X`, `M`, `*`, `R1`-`R3`, atom lists `[N,O,S]`, and open-site/ring locks `s*`, `R0`, `R`) and query bonds (`Any`, `1/2`, `1/a`, `2/a`, `Aromatic`, `Coordination`)
  - Reaction arrows, atom-to-atom mapping `[1]`, 1e-/2e- curved electron-pushing arrows, polymer brackets `[ ]n`, and variable ring-position Markush bonds
  - Clean 2D coordinate optimizer, Kekule / Thiele circle toggle, and superatom abbreviation expansion (`Boc`, `CO2Et`, `CF3`, `Ph`, `CN`, `NO2`, `TMS`)
- **Native Visual Custom Editors**:
  - Click any `.cdxml`, `.mol`, or `.sdf` file in Explorer to edit it directly on the 2D chemical canvas (`Ctrl+S` writes lossless ACS 1996 CDXML or MDL Molfile V2000).
  - Click any `.pdb`, `.cif`, `.mmcif`, or `.xyz` file to inspect it in the 3D Mol* / WebGL ball-and-stick & macromolecule viewer.
- **Universal AI Coding Agent Bridge (`Transfer to Agent`)**:
  - Saves `.chemdraw/studio-live.cdxml`, `.chemdraw/studio-live.mol`, and `.chemdraw/studio-live.json` in your workspace, copies the structured SMILES / SMARTS / file prompt to the clipboard, and focuses/prefills your active IDE AI chat (Copilot Chat, Cursor, Windsurf, Cline, Roo Code, Continue, Trae, Kiro).
  - Live `FileSystemWatcher` automatically syncs structures written by CLI or GUI coding agents onto the canvas.

## Building & Installing the `.vsix`

```bash
python vscode/scripts/build_vsix.py --install-all
```
