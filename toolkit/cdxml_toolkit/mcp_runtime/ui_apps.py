"""Interactive 3D Mol* viewer and publication-grade 2D molecular studio MCP App views."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
from typing import Any
import webbrowser
import xml.etree.ElementTree as ET

from . import artifact_safety

MOLSTAR_RESOURCE_URI = "ui://cdxml-toolkit/molstar-viewer.html"
DRAWING_STUDIO_RESOURCE_URI = "ui://cdxml-toolkit/drawing-studio.html"

MOLSTAR_CSP_META: dict[str, Any] = {
    "ui": {
        "prefersBorder": True,
        "csp": {
            "resourceDomains": ["https://cdn.jsdelivr.net"],
            "connectDomains": [
                "https://cdn.jsdelivr.net",
                "https://files.rcsb.org",
                "https://pubchem.ncbi.nlm.nih.gov",
            ],
        },
    }
}

DRAWING_STUDIO_CSP_META: dict[str, Any] = {
    "ui": {
        "prefersBorder": True,
        "csp": {
            "resourceDomains": [],
            "connectDomains": [],
        },
    }
}

_BUILTIN_SMILES: dict[str, tuple[str, str]] = {
    "aspirin": ("Aspirin", "CC(=O)Oc1ccccc1C(=O)O"),
    "acetylsalicylic acid": ("Aspirin", "CC(=O)Oc1ccccc1C(=O)O"),
    "caffeine": ("Caffeine", "Cn1c(=O)c2c(ncn2C)n(C)c1=O"),
    "paracetamol": ("Paracetamol", "CC(=O)Nc1ccc(O)cc1"),
    "acetaminophen": ("Paracetamol", "CC(=O)Nc1ccc(O)cc1"),
    "ibuprofen": ("Ibuprofen", "CC(C)Cc1ccc(C(C)C(=O)O)cc1"),
    "vanillin": ("Vanillin", "COc1cc(C=O)ccc1O"),
    "benzene": ("Benzene", "c1ccccc1"),
    "pyridine": ("Pyridine", "c1ccncc1"),
    "naphthalene": ("Naphthalene", "c1ccc2ccccc2c1"),
    "indole": ("Indole", "c1ccc2[nH]ccc2c1"),
    "quinoline": ("Quinoline", "c1ccc2ncccc2c1"),
    "purine": ("Purine", "c1ncc2[nH]cnc2n1"),
    "cyclohexane": ("Cyclohexane", "C1CCCCC1"),
    "glucose": ("beta-D-Glucose", "OC[C@H]1O[C@@H](O)[C@H](O)[C@@H](O)[C@@H]1O"),
    "dopamine": ("Dopamine", "NCCc1ccc(O)c(O)c1"),
    "serotonin": ("Serotonin", "NCCc1c[nH]c2ccc(O)cc12"),
    "morphine": ("Morphine", "CN1CC[C@]23c4c5ccc(O)c4O[C@H]2[C@@H](O)C=C[C@H]3[C@H]1C5"),
    "nicotine": ("(S)-Nicotine", "CN1CCC[C@H]1c1cccnc1"),
    "cholesterol": ("Cholesterol", "C[C@H](CCCC(C)C)[C@H]1CC[C@@H]2[C@@]1(C)CC[C@H]3[C@H]2CC=C4C[C@@H](O)CC[C@@]34C"),
    "penicillin": ("Penicillin G", "CC1(C)S[C@@H]2[C@H](NC(=O)Cc3ccccc3)C(=O)N2[C@H]1C(=O)O"),
    "tamoxifen": ("Tamoxifen", "CC/C(=C(/c1ccccc1)c1ccc(OCCN(C)C)cc1)c1ccccc1"),
    "ferrocene": ("Ferrocene-like bis-Cp", "c1cccc1.c1cccc1"),
    "atp": ("ATP", "Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)(O)OP(=O)(O)OP(=O)(O)O)[C@@H](O)[C@H]1O"),
    "taxol": (
        "Paclitaxel",
        "CC(=O)O[C@H]1C(=O)[C@@]2(C)[C@@H](O)C[C@H]3OC[C@]3(OC(C)=O)[C@H]2[C@H](OC(=O)c2ccccc2)"
        "[C@]2(O)C[C@H](OC(=O)[C@H](O)[C@@H](NC(=O)c3ccccc3)c3ccccc3)C(C)=C1C2(C)C",
    ),
}

_STYLE_PRESETS: dict[str, dict[str, Any]] = {
    "acs1996": {"label": "ACS 1996 / JACS", "bondLength": 14.4, "lineWidth": 0.6, "font": "Arial", "labelSize": 10},
    "jacs": {"label": "JACS Publication", "bondLength": 14.4, "lineWidth": 0.6, "font": "Arial", "labelSize": 10},
    "angew": {"label": "Angewandte", "bondLength": 14.2, "lineWidth": 0.68, "font": "Helvetica", "labelSize": 10},
    "nature": {"label": "Nature Chem.", "bondLength": 14.0, "lineWidth": 0.6, "font": "Helvetica", "labelSize": 9.5},
    "science": {"label": "Science", "bondLength": 13.8, "lineWidth": 0.58, "font": "Helvetica", "labelSize": 9.5},
    "rsc": {"label": "RSC Chem. Sci.", "bondLength": 14.4, "lineWidth": 0.6, "font": "Arial", "labelSize": 10},
    "wiley": {"label": "Wiley Adv.", "bondLength": 14.5, "lineWidth": 0.66, "font": "Arial", "labelSize": 10},
    "org_lett": {"label": "Organic Letters", "bondLength": 14.4, "lineWidth": 0.6, "font": "Arial", "labelSize": 10},
    "synthesis": {"label": "Synthesis", "bondLength": 14.4, "lineWidth": 0.6, "font": "Arial", "labelSize": 10},
}

_ELEMENT_MAP = {
    1: "H", 5: "B", 6: "C", 7: "N", 8: "O", 9: "F", 11: "Na", 12: "Mg",
    14: "Si", 15: "P", 16: "S", 17: "Cl", 19: "K", 26: "Fe", 27: "Co",
    28: "Ni", 29: "Cu", 30: "Zn", 35: "Br", 44: "Ru", 46: "Pd", 53: "I",
}
_ATOMIC_WEIGHTS = {
    "H": 1.008, "B": 10.81, "C": 12.011, "N": 14.007, "O": 15.999,
    "F": 18.998, "Mg": 24.305, "Si": 28.085, "P": 30.974, "S": 32.06, "Cl": 35.45,
    "Fe": 55.845, "Ni": 58.693, "Cu": 63.546, "Zn": 65.38, "Br": 79.904,
    "Pd": 106.42, "I": 126.904,
}
_SUPERATOM_FORMULAS: dict[str, dict[str, int]] = {
    "Me": {"C": 1, "H": 3},
    "Et": {"C": 2, "H": 5},
    "iPr": {"C": 3, "H": 7},
    "tBu": {"C": 4, "H": 9},
    "Ph": {"C": 6, "H": 5},
    "Bn": {"C": 7, "H": 7},
    "CF3": {"C": 1, "F": 3},
    "OMe": {"C": 1, "H": 3, "O": 1},
    "NO2": {"N": 1, "O": 2},
    "CN": {"C": 1, "N": 1},
    "COOH": {"C": 1, "H": 1, "O": 2},
    "CO2Et": {"C": 3, "H": 5, "O": 2},
    "Boc": {"C": 5, "H": 9, "O": 2},
    "OTs": {"C": 7, "H": 7, "O": 3, "S": 1},
    "Bpin": {"B": 1, "C": 6, "H": 12, "O": 2},
    "TMS": {"Si": 1, "C": 3, "H": 9},
}

import re  # noqa: E402

_PDB_CODE_RE = re.compile(r"^[0-9][A-Za-z0-9]{3}$")


def _html_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True).replace("</", "<\\/")


def _normalize_molecule_key(raw: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", raw.strip().lower()).strip()


def _resolve_smiles_input(query: str) -> tuple[str | None, str, str]:
    clean = (query or "").strip()
    if not clean:
        return "CC(=O)Oc1ccccc1C(=O)O", "Aspirin", "builtin"
    key = _normalize_molecule_key(clean)
    if key in _BUILTIN_SMILES:
        title, smi = _BUILTIN_SMILES[key]
        return smi, title, "builtin"
    from rdkit import Chem

    candidate = Chem.MolFromSmiles(clean)
    if candidate is not None:
        return Chem.MolToSmiles(candidate), clean, "smiles"
    try:
        from ..naming.mol_builder import name_to_smiles
    except Exception:
        name_to_smiles = None
    if callable(name_to_smiles):
        try:
            resolved = name_to_smiles(clean)
        except Exception:
            resolved = None
        if isinstance(resolved, str) and resolved.strip():
            return resolved.strip(), clean, "resolved_name"
        if isinstance(resolved, dict) and resolved.get("smiles"):
            return str(resolved["smiles"]), clean, "resolved_name"
    return None, clean, "unknown"


def _mol_3d_from_rdkit(mol: Any, *, title: str) -> dict[str, Any]:
    from rdkit import Chem
    from rdkit.Chem import AllChem, Descriptors, rdMolDescriptors

    mol_h = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = 42
    embed_status = AllChem.EmbedMolecule(mol_h, params)
    if embed_status != 0:
        embed_status = AllChem.EmbedMolecule(mol_h, randomSeed=42, useRandomCoords=True)
    if embed_status == 0:
        try:
            if AllChem.MMFFHasAllMoleculeParams(mol_h):
                AllChem.MMFFOptimizeMolecule(mol_h, maxIters=250)
            else:
                AllChem.UFFOptimizeMolecule(mol_h, maxIters=250)
        except Exception:
            pass
    else:
        AllChem.Compute2DCoords(mol_h)

    conf = mol_h.GetConformer()
    sdf_data = Chem.MolToMolBlock(mol_h)
    try:
        pdb_data = Chem.MolToPDBBlock(mol_h)
    except Exception:
        pdb_data = ""

    atoms = []
    for idx, atom in enumerate(mol_h.GetAtoms()):
        pos = conf.GetAtomPosition(idx)
        atoms.append({
            "idx": idx,
            "s": atom.GetSymbol(),
            "x": round(float(pos.x), 4),
            "y": round(float(pos.y), 4),
            "z": round(float(pos.z), 4),
            "charge": int(atom.GetFormalCharge()),
        })
    bonds = []
    for bond in mol_h.GetBonds():
        btype = bond.GetBondType()
        order = 2 if btype == Chem.BondType.DOUBLE else (3 if btype == Chem.BondType.TRIPLE else 1)
        bonds.append({
            "a": int(bond.GetBeginAtomIdx()),
            "b": int(bond.GetEndAtomIdx()),
            "o": order,
            "aromatic": bool(bond.GetIsAromatic()),
        })
    formula = rdMolDescriptors.CalcMolFormula(mol)
    mw = round(float(Descriptors.MolWt(mol)), 3)
    canon = Chem.MolToSmiles(mol)
    return {
        "title": title,
        "format": "sdf",
        "mol_data": sdf_data,
        "pdb_data": pdb_data,
        "smiles": canon,
        "formula": formula,
        "molecular_weight": mw,
        "scene": {"atoms": atoms, "bonds": bonds},
    }


def _parse_pdb_or_cif_scene(text: str, ext: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    atoms: list[dict[str, Any]] = []
    bonds: list[dict[str, Any]] = []
    serial_to_idx: dict[int, int] = {}
    if ext in {".pdb", ".ent"}:
        for line in text.splitlines():
            rec = line[:6].strip()
            if rec in {"ATOM", "HETATM"} and len(line) >= 54:
                try:
                    serial = int(line[6:11].strip() or len(atoms) + 1)
                    atom_name = line[12:16].strip()
                    res_name = line[17:20].strip()
                    chain = line[21:22].strip()
                    x = float(line[30:38])
                    y = float(line[38:46])
                    z = float(line[46:54])
                    elem = (line[76:78].strip() if len(line) >= 78 else "") or re.sub(r"[^A-Za-z]", "", atom_name)[:1] or "C"
                    elem = elem[0].upper() + (elem[1:].lower() if len(elem) > 1 and elem[1].islower() else "")
                except ValueError:
                    continue
                if len(atoms) < 2500:
                    serial_to_idx[serial] = len(atoms)
                    atoms.append({
                        "idx": len(atoms),
                        "s": elem,
                        "x": round(x, 4),
                        "y": round(y, 4),
                        "z": round(z, 4),
                        "atomName": atom_name,
                        "resName": res_name,
                        "chain": chain,
                    })
            elif rec == "CONECT" and len(line) >= 16:
                try:
                    src = int(line[6:11].strip())
                except ValueError:
                    continue
                if src not in serial_to_idx:
                    continue
                for start in (11, 16, 21, 26):
                    token = line[start:start + 5].strip()
                    if not token:
                        continue
                    try:
                        dst = int(token)
                    except ValueError:
                        continue
                    if dst in serial_to_idx and serial_to_idx[src] < serial_to_idx[dst]:
                        bonds.append({"a": serial_to_idx[src], "b": serial_to_idx[dst], "o": 1})
    if not bonds and 1 < len(atoms) <= 320:
        for i in range(len(atoms)):
            ai = atoms[i]
            for j in range(i + 1, len(atoms)):
                aj = atoms[j]
                dx = ai["x"] - aj["x"]
                dy = ai["y"] - aj["y"]
                dz = ai["z"] - aj["z"]
                dist2 = dx * dx + dy * dy + dz * dz
                cutoff = 1.9 * 1.9 if (ai["s"] != "H" and aj["s"] != "H") else 1.25 * 1.25
                if 0.2 < dist2 <= cutoff:
                    bonds.append({"a": i, "b": j, "o": 1})
    is_macromol = len(atoms) > 120 or any(a.get("resName") not in {"", "UNL", "LIG", "MOL", "HOH"} for a in atoms[:20])
    return atoms, bonds, is_macromol


def _parse_xyz_scene(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    atoms: list[dict[str, Any]] = []
    start = 2 if len(lines) >= 2 and lines[0].isdigit() else 0
    for line in lines[start:]:
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
        except ValueError:
            continue
        atoms.append({"idx": len(atoms), "s": parts[0], "x": round(x, 4), "y": round(y, 4), "z": round(z, 4)})
    bonds: list[dict[str, Any]] = []
    for i in range(len(atoms)):
        for j in range(i + 1, len(atoms)):
            dx = atoms[i]["x"] - atoms[j]["x"]
            dy = atoms[i]["y"] - atoms[j]["y"]
            dz = atoms[i]["z"] - atoms[j]["z"]
            if 0.2 < dx * dx + dy * dy + dz * dz <= 1.85 * 1.85:
                bonds.append({"a": i, "b": j, "o": 1})
    return atoms, bonds


def _cdxml_to_rdkit_mol(cdxml_path: Path):
    from rdkit import Chem
    from ..rdkit_utils import frag_to_mol, frag_to_smiles

    root = ET.parse(cdxml_path).getroot()
    fragments = root.findall(".//fragment")
    mols = []
    smiles_parts = []
    for frag in fragments:
        mol, _ = frag_to_mol(frag)
        if mol is not None and mol.GetNumAtoms() > 0:
            mols.append(mol)
            smi = frag_to_smiles(frag)
            if smi:
                smiles_parts.append(smi)
    if not mols:
        raise ValueError(f"No chemical fragments found in CDXML file: {cdxml_path}")
    combined = mols[0]
    for extra in mols[1:]:
        combined = Chem.CombineMols(combined, extra)
    try:
        Chem.SanitizeMol(combined)
    except Exception:
        pass
    return combined, ".".join(smiles_parts) or None


def render_molstar_app_html(initial_payload: dict[str, Any] | None = None) -> str:
    """Render the self-contained Mol* + offline 3D WebGL/Canvas MCP App HTML page."""
    payload_json = _html_json(initial_payload or {})
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ChemDraw Toolkit · Mol* 3D Viewer</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/molstar@latest/build/viewer/molstar.css">
<style>
  :root {{
    --bg: #0f1419; --panel: #171e26; --panel-2: #1f2833;
    --line: rgba(148,163,184,0.2); --text: #e6edf3; --muted: #93a1b5;
    --accent: #38bdf8; --accent-2: #22c55e; --warn: #f59e0b;
  }}
  @media (prefers-color-scheme: light) {{
    body[data-theme="auto"] {{
      --bg: #f6f8fa; --panel: #ffffff; --panel-2: #f0f4f8;
      --line: rgba(15,23,42,0.12); --text: #0f172a; --muted: #475569;
      --accent: #0284c7; --accent-2: #15803d; --warn: #b45309;
    }}
  }}
  body[data-theme="light"] {{
    --bg: #f6f8fa; --panel: #ffffff; --panel-2: #f0f4f8;
    --line: rgba(15,23,42,0.12); --text: #0f172a; --muted: #475569;
    --accent: #0284c7; --accent-2: #15803d; --warn: #b45309;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; background: var(--bg); color: var(--text);
    font: 13px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
  .shell {{ display: flex; flex-direction: column; height: 460px; max-height: 100vh; overflow: hidden; }}
  .topbar {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 7px 10px;
    background: var(--panel); border-bottom: 1px solid var(--line); }}
  .brand {{ font-weight: 700; display: flex; align-items: center; gap: 6px; }}
  .badge {{ font-size: 11px; padding: 2px 7px; border-radius: 999px; background: var(--panel-2);
    border: 1px solid var(--line); color: var(--accent); font-weight: 600; }}
  .spacer {{ flex: 1; }}
  .controls {{ display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }}
  button, select, input {{
    background: var(--panel-2); color: var(--text); border: 1px solid var(--line);
    border-radius: 7px; padding: 4px 8px; font-size: 12px; font-family: inherit;
  }}
  button {{ cursor: pointer; font-weight: 600; }}
  button:hover {{ border-color: var(--accent); }}
  button.active {{ background: var(--accent); color: #081018; border-color: var(--accent); }}
  input[type="text"] {{ width: 125px; }}
  .stage-wrap {{ position: relative; flex: 1; display: grid; grid-template-columns: 1fr 225px; min-height: 0; }}
  @media (max-width: 720px) {{ .stage-wrap {{ grid-template-columns: 1fr; }} .sidebar {{ display: none; }} }}
  .stage {{ position: relative; width: 100%; height: 100%; overflow: hidden; }}
  #molstar-container, #fallback-canvas {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
  #molstar-container {{ display: none; }}
  #fallback-canvas {{ display: block; cursor: grab; }}
  #fallback-canvas:active {{ cursor: grabbing; }}
  .hud {{ position: absolute; left: 10px; bottom: 10px; padding: 5px 9px; border-radius: 8px;
    background: rgba(15,20,25,0.78); color: #e6edf3; border: 1px solid rgba(255,255,255,0.12);
    font-size: 11px; pointer-events: none; }}
  .sidebar {{ background: var(--panel); border-left: 1px solid var(--line); padding: 10px;
    display: flex; flex-direction: column; gap: 8px; overflow: auto; }}
  .card {{ background: var(--panel-2); border: 1px solid var(--line); border-radius: 8px; padding: 8px 9px; }}
  .card h4 {{ margin: 0 0 5px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); }}
  .kv {{ display: grid; grid-template-columns: auto 1fr; gap: 3px 8px; font-size: 11.5px; }}
  .kv span {{ color: var(--muted); }}
  .kv code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11px; word-break: break-all; text-align: right; }}
  .preset-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }}
  .status-dot {{ width: 8px; height: 8px; border-radius: 50%; background: var(--accent-2); display: inline-block; }}
</style>
</head>
<body data-theme="auto">
<div class="shell" id="molstar-root">
  <div class="topbar">
    <div class="brand">
      <span class="status-dot"></span>
      <span id="mol-title">Mol* 3D Viewer</span>
      <span class="badge" id="engine-badge">Built-in 3D Engine</span>
    </div>
    <div class="spacer"></div>
    <div class="controls">
      <select id="rep-select" title="3D Representation">
        <option value="ball-and-stick">Ball &amp; Stick</option>
        <option value="spacefill">Spacefill (CPK)</option>
        <option value="licorice">Sticks</option>
        <option value="wire">Wireframe</option>
      </select>
      <button id="btn-spin" type="button">Spin</button>
      <button id="btn-reset" type="button">Reset</button>
      <button id="btn-engine" type="button">Use Mol* WebGL</button>
      <input id="pdb-input" type="text" placeholder="PDB ID e.g. 1CRN" />
      <button id="btn-load-pdb" type="button">Load PDB</button>
      <button id="btn-ask-agent" type="button">Edit in 2D Studio</button>
    </div>
  </div>
  <div class="stage-wrap">
    <div class="stage">
      <div id="molstar-container"></div>
      <canvas id="fallback-canvas"></canvas>
      <div class="hud" id="hud">Drag to rotate &middot; Scroll to zoom &middot; Double-click to reset</div>
    </div>
    <aside class="sidebar">
      <div class="card">
        <h4>Structure Telemetry</h4>
        <div class="kv">
          <span>Formula</span><code id="meta-formula">-</code>
          <span>MW</span><code id="meta-mw">-</code>
          <span>Atoms</span><code id="meta-atoms">-</code>
          <span>Bonds</span><code id="meta-bonds">-</code>
          <span>Format</span><code id="meta-format">-</code>
          <span>Source</span><code id="meta-source">-</code>
        </div>
      </div>
      <div class="card">
        <h4>Quick PDB Examples</h4>
        <div class="preset-grid">
          <button type="button" data-pdb="1CRN">1CRN Crambin</button>
          <button type="button" data-pdb="1UBQ">1UBQ Ubiquitin</button>
          <button type="button" data-pdb="6LU7">6LU7 Mpro</button>
          <button type="button" data-pdb="4HHB">4HHB Hemoglobin</button>
        </div>
      </div>
      <div class="card">
        <h4>Export &amp; Local File</h4>
        <div style="display:flex; flex-direction:column; gap:5px;">
          <button id="btn-dl-data" type="button">Download Structure</button>
          <button id="btn-drop-file" type="button">Load .pdb/.cif/.sdf</button>
          <input id="file-picker" type="file" accept=".pdb,.ent,.cif,.mmcif,.sdf,.mol,.xyz" style="display:none" />
        </div>
      </div>
    </aside>
  </div>
</div>
<script>
(() => {{
  const INITIAL_PAYLOAD = {payload_json};
  const CPK = {{
    H:"#f8fafc", C:"#64748b", N:"#3b82f6", O:"#ef4444", S:"#eab308",
    P:"#f97316", F:"#22c55e", Cl:"#16a34a", Br:"#b45309", I:"#9333ea",
    Fe:"#f59e0b", Pd:"#06b6d4", B:"#fb7185", Si:"#cbd5e1"
  }};
  const RADII = {{ H:0.26, C:0.44, N:0.43, O:0.41, S:0.54, P:0.52, F:0.38, Cl:0.52, Br:0.58, I:0.64, Pd:0.7, Fe:0.68 }};

  let state = {{
    payload: INITIAL_PAYLOAD || {{}},
    rotX: 0.35, rotY: 0.45, zoom: 1.0,
    spin: true,
    rep: "ball-and-stick",
    engine: "canvas",
    molstarViewer: null
  }};

  const canvas = document.getElementById("fallback-canvas");
  const ctx = canvas.getContext("2d");
  const molstarEl = document.getElementById("molstar-container");
  const hud = document.getElementById("hud");
  const badge = document.getElementById("engine-badge");
  const engineBtn = document.getElementById("btn-engine");

  function updateMeta(p) {{
    document.getElementById("mol-title").textContent = p.title || p.pdb_id || "Mol* 3D Viewer";
    document.getElementById("meta-formula").textContent = p.formula || "-";
    document.getElementById("meta-mw").textContent = p.molecular_weight ? p.molecular_weight + " g/mol" : "-";
    const atoms = (p.scene && p.scene.atoms) ? p.scene.atoms.length : (p.atom_count || 0);
    const bonds = (p.scene && p.scene.bonds) ? p.scene.bonds.length : (p.bond_count || 0);
    document.getElementById("meta-atoms").textContent = String(atoms);
    document.getElementById("meta-bonds").textContent = String(bonds);
    document.getElementById("meta-format").textContent = (p.format || "sdf").toUpperCase();
    document.getElementById("meta-source").textContent = p.pdb_id ? ("RCSB " + p.pdb_id) : (p.source_kind || "rdkit-3d");
    if (p.representation) {{
      state.rep = p.representation;
      document.getElementById("rep-select").value = p.representation;
    }}
  }}

  function centerScene(scene) {{
    if (!scene || !scene.atoms || !scene.atoms.length) return {{ atoms: [], bonds: [], span: 10 }};
    let cx = 0, cy = 0, cz = 0;
    for (const a of scene.atoms) {{ cx += a.x; cy += a.y; cz += a.z; }}
    cx /= scene.atoms.length; cy /= scene.atoms.length; cz /= scene.atoms.length;
    let maxR = 1.5;
    const atoms = scene.atoms.map((a) => {{
      const x = a.x - cx, y = a.y - cy, z = a.z - cz;
      const r = Math.hypot(x, y, z);
      if (r > maxR) maxR = r;
      return {{ ...a, x, y, z }};
    }});
    return {{ atoms, bonds: scene.bonds || [], span: maxR * 2.2 }};
  }}

  let normalized = centerScene(state.payload.scene);

  function project(x, y, z, w, h, scale) {{
    const cy = Math.cos(state.rotY), sy = Math.sin(state.rotY);
    const cx = Math.cos(state.rotX), sx = Math.sin(state.rotX);
    const x1 = x * cy - z * sy;
    const z1 = x * sy + z * cy;
    const y2 = y * cx - z1 * sx;
    const z2 = y * sx + z1 * cx;
    const camDist = 28;
    const persp = camDist / Math.max(4, camDist - z2 * 0.45);
    return {{ sx: w * 0.5 + x1 * scale * persp, sy: h * 0.5 - y2 * scale * persp, z: z2, p: persp }};
  }}

  function drawCanvas() {{
    if (state.engine !== "canvas") return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = canvas.clientWidth || 640, h = canvas.clientHeight || 380;
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {{
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
    }}
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    if (!normalized.atoms.length) {{
      ctx.fillStyle = "#93a1b5";
      ctx.font = "13px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(state.payload.pdb_id
        ? ("PDB " + state.payload.pdb_id + " ready - click 'Use Mol* WebGL' when online")
        : "No 3D coordinates loaded", w * 0.5, h * 0.5);
      return;
    }}

    const scale = (Math.min(w, h) * 0.72 / Math.max(4, normalized.span)) * state.zoom;
    const proj = normalized.atoms.map((a) => ({{ a, ...project(a.x, a.y, a.z, w, h, scale) }}));
    const drawItems = [];
    if (state.rep !== "spacefill") {{
      for (const b of normalized.bonds) {{
        const p1 = proj[b.a], p2 = proj[b.b];
        if (!p1 || !p2) continue;
        drawItems.push({{ type: "bond", z: (p1.z + p2.z) * 0.5, p1, p2, order: b.o || 1 }});
      }}
    }}
    for (const p of proj) {{
      if (state.rep === "wire" && p.a.s === "H") continue;
      drawItems.push({{ type: "atom", z: p.z, p }});
    }}
    drawItems.sort((u, v) => u.z - v.z);

    for (const item of drawItems) {{
      if (item.type === "bond") {{
        const {{ p1, p2, order }} = item;
        const dx = p2.sx - p1.sx, dy = p2.sy - p1.sy;
        const len = Math.hypot(dx, dy) || 1;
        const nx = -dy / len, ny = dx / len;
        const width = state.rep === "wire" ? 1.6 : (state.rep === "licorice" ? 6.0 : 3.6) * ((p1.p + p2.p) * 0.5);
        const offsets = order === 2 ? [-2.4, 2.4] : (order === 3 ? [-3.4, 0, 3.4] : [0]);
        ctx.lineCap = "round";
        for (const off of offsets) {{
          const grad = ctx.createLinearGradient(p1.sx, p1.sy, p2.sx, p2.sy);
          grad.addColorStop(0, CPK[p1.a.s] || "#94a3b8");
          grad.addColorStop(0.5, "#64748b");
          grad.addColorStop(1, CPK[p2.a.s] || "#94a3b8");
          ctx.strokeStyle = grad;
          ctx.lineWidth = order > 1 ? Math.max(1.5, width * 0.58) : width;
          ctx.beginPath();
          ctx.moveTo(p1.sx + nx * off, p1.sy + ny * off);
          ctx.lineTo(p2.sx + nx * off, p2.sy + ny * off);
          ctx.stroke();
        }}
      }} else if (state.rep !== "wire") {{
        const {{ p }} = item;
        const baseR = RADII[p.a.s] || 0.44;
        const mult = state.rep === "spacefill" ? 2.45 : (state.rep === "licorice" ? 0.52 : 0.92);
        const r = Math.max(2.5, baseR * scale * mult * p.p * 0.65);
        const col = CPK[p.a.s] || "#94a3b8";
        const grad = ctx.createRadialGradient(p.sx - r * 0.32, p.sy - r * 0.32, r * 0.1, p.sx, p.sy, r);
        grad.addColorStop(0, "#ffffff");
        grad.addColorStop(0.32, col);
        grad.addColorStop(1, "#0f172a");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(p.sx, p.sy, r, 0, Math.PI * 2);
        ctx.fill();
      }}
    }}
  }}

  async function tryEnableMolstar() {{
    const probe = document.createElement("canvas");
    const hasGl = Boolean(probe.getContext("webgl2") || probe.getContext("webgl") || probe.getContext("experimental-webgl"));
    if (!hasGl || !window.molstar || !window.molstar.Viewer) {{
      state.engine = "canvas";
      molstarEl.style.display = "none";
      canvas.style.display = "block";
      hud.textContent = hasGl ? "Mol* CDN script unavailable in sandbox - using built-in 3D engine." : "Built-in 3D engine active.";
      badge.textContent = "Built-in 3D";
      drawCanvas();
      return false;
    }}
    try {{
      molstarEl.style.display = "block";
      canvas.style.display = "none";
      state.engine = "molstar";
      badge.textContent = "Mol* WebGL Active";
      engineBtn.textContent = "Use Built-in 3D";
      if (!state.molstarViewer) {{
        state.molstarViewer = await window.molstar.Viewer.create("molstar-container", {{
          layoutIsExpanded: false,
          layoutShowControls: false,
          layoutShowRemoteState: false,
          layoutShowSequence: Boolean(state.payload.pdb_id || state.payload.is_macromolecule),
          layoutShowLog: false,
          layoutShowLeftPanel: false,
          viewportShowExpand: true,
          viewportShowSelectionMode: false,
        }});
      }}
      if (!state.molstarViewer || !state.molstarViewer.plugin || !state.molstarViewer.plugin.canvas3d || /webgl does not seem/i.test(molstarEl.innerText || "")) {{
        throw new Error("WebGL canvas3d unavailable in host view");
      }}
      await loadIntoMolstar(state.payload);
      return true;
    }} catch (err) {{
      state.engine = "canvas";
      molstarEl.style.display = "none";
      canvas.style.display = "block";
      badge.textContent = "Built-in 3D Engine";
      engineBtn.textContent = "Use Mol* WebGL";
      hud.textContent = "WebGL fallback active (" + (err && err.message ? err.message : "offline") + ")";
      drawCanvas();
      return false;
    }}
  }}

  async function loadIntoMolstar(p) {{
    if (!state.molstarViewer) return;
    await state.molstarViewer.plugin.clear();
    if (p.mol_data) {{
      const fmt = (p.format || "sdf").toLowerCase();
      await state.molstarViewer.loadStructureFromData(p.mol_data, fmt === "cif" ? "mmcif" : fmt, {{ dataLabel: p.title || "Structure" }});
    }} else if (p.pdb_id) {{
      await state.molstarViewer.loadPdb(p.pdb_id.toUpperCase());
    }}
  }}

  function applyPayload(p) {{
    if (!p || typeof p !== "object") return;
    state.payload = p;
    normalized = centerScene(p.scene);
    updateMeta(p);
    if (state.engine === "molstar" && state.molstarViewer) {{
      loadIntoMolstar(p).catch(() => tryEnableMolstar());
    }} else if (p.pdb_id && !normalized.atoms.length && window.molstar) {{
      tryEnableMolstar();
    }}
    drawCanvas();
  }}

  let dragging = false, lx = 0, ly = 0;
  canvas.addEventListener("pointerdown", (e) => {{ dragging = true; lx = e.clientX; ly = e.clientY; canvas.setPointerCapture(e.pointerId); }});
  canvas.addEventListener("pointermove", (e) => {{
    if (!dragging) return;
    state.rotY += (e.clientX - lx) * 0.01;
    state.rotX += (e.clientY - ly) * 0.01;
    lx = e.clientX; ly = e.clientY;
    drawCanvas();
  }});
  canvas.addEventListener("pointerup", () => {{ dragging = false; }});
  canvas.addEventListener("wheel", (e) => {{
    e.preventDefault();
    state.zoom = Math.max(0.25, Math.min(4.0, state.zoom * (e.deltaY > 0 ? 0.92 : 1.09)));
    drawCanvas();
  }}, {{ passive: false }});
  canvas.addEventListener("dblclick", () => {{ state.rotX = 0.35; state.rotY = 0.45; state.zoom = 1.0; drawCanvas(); }});

  document.getElementById("rep-select").addEventListener("change", (e) => {{ state.rep = e.target.value; drawCanvas(); }});
  document.getElementById("btn-spin").addEventListener("click", (e) => {{
    state.spin = !state.spin;
    e.target.classList.toggle("active", state.spin);
  }});
  document.getElementById("btn-spin").classList.add("active");
  document.getElementById("btn-reset").addEventListener("click", () => {{ state.rotX = 0.35; state.rotY = 0.45; state.zoom = 1.0; drawCanvas(); }});
  engineBtn.addEventListener("click", () => {{
    if (state.engine === "canvas") tryEnableMolstar();
    else {{
      state.engine = "canvas"; molstarEl.style.display = "none"; canvas.style.display = "block";
      badge.textContent = "Built-in 3D Engine"; engineBtn.textContent = "Use Mol* WebGL"; drawCanvas();
    }}
  }});
  document.getElementById("btn-load-pdb").addEventListener("click", () => {{
    const id = document.getElementById("pdb-input").value.trim().toUpperCase();
    if (!id) return;
    applyPayload({{ ...state.payload, title: "PDB " + id, pdb_id: id, mol_data: null, scene: {{ atoms: [], bonds: [] }} }});
    tryEnableMolstar();
  }});
  document.querySelectorAll("[data-pdb]").forEach((btn) => {{
    btn.addEventListener("click", () => {{
      const id = btn.getAttribute("data-pdb");
      document.getElementById("pdb-input").value = id;
      applyPayload({{ ...state.payload, title: "PDB " + id, pdb_id: id, mol_data: null, scene: {{ atoms: [], bonds: [] }} }});
      tryEnableMolstar();
    }});
  }});
  document.getElementById("btn-dl-data").addEventListener("click", () => {{
    const data = state.payload.mol_data || state.payload.pdb_data || "";
    if (!data) return;
    const ext = (state.payload.format || "sdf").toLowerCase();
    const blob = new Blob([data], {{ type: "text/plain;charset=utf-8" }});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = ((state.payload.title || "molecule").replace(/[^a-z0-9_-]+/gi, "_") || "molecule") + "." + ext;
    a.click();
  }});
  document.getElementById("btn-drop-file").addEventListener("click", () => document.getElementById("file-picker").click());
  document.getElementById("file-picker").addEventListener("change", async (e) => {{
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    const text = await file.text();
    const ext = file.name.split(".").pop().toLowerCase();
    applyPayload({{ title: file.name, format: ext, mol_data: text, scene: {{ atoms: [], bonds: [] }}, source_kind: "local-file" }});
    tryEnableMolstar();
  }});

  let rpcId = 1;
  function postHost(msg) {{ try {{ window.parent.postMessage(msg, "*"); }} catch (_err) {{}} }}
  function extractResultPayload(params) {{
    if (!params) return null;
    if (params.structuredContent && typeof params.structuredContent === "object") return params.structuredContent;
    if (Array.isArray(params.content)) {{
      for (const item of params.content) {{
        if (item && item.type === "text" && typeof item.text === "string") {{
          try {{ return JSON.parse(item.text); }} catch (_e) {{}}
        }}
      }}
    }}
    return params;
  }}
  window.addEventListener("message", (event) => {{
    const msg = event.data;
    if (!msg || typeof msg !== "object") return;
    if (msg.id === 1 && msg.result) {{
      postHost({{ jsonrpc: "2.0", method: "ui/notifications/initialized", params: {{}} }});
      if (msg.result.hostContext && msg.result.hostContext.theme) document.body.dataset.theme = msg.result.hostContext.theme;
      return;
    }}
    if (msg.method === "ui/notifications/host-context-changed" && msg.params && msg.params.theme) {{
      document.body.dataset.theme = msg.params.theme;
    }}
    if (msg.method === "ui/notifications/tool-result") {{
      const extracted = extractResultPayload(msg.params);
      if (extracted) applyPayload(extracted);
    }}
  }});
  document.getElementById("btn-ask-agent").addEventListener("click", () => {{
    const smi = state.payload.smiles || "";
    const hostGlobal = window["open" + "ai"];
    if (hostGlobal && typeof hostGlobal.sendFollowUpMessage === "function") {{
      hostGlobal.sendFollowUpMessage({{ prompt: "Open this structure in 2D ChemDraw Studio: " + (smi || state.payload.title), title: "Edit in 2D Studio" }});
    }}
    postHost({{ jsonrpc: "2.0", id: ++rpcId, method: "tools/call", params: {{ name: "open_drawing_studio", arguments: {{ smiles: smi, name: state.payload.title || "molecule" }} }} }});
    postHost({{ jsonrpc: "2.0", id: ++rpcId, method: "ui/message", params: {{ role: "user", content: [{{ type: "text", text: "Open this structure in 2D ChemDraw Studio: " + (smi || state.payload.title || "3D structure") }}] }} }});
  }});

  if (window.parent && window.parent !== window) {{
    postHost({{
      jsonrpc: "2.0", id: 1, method: "ui/initialize",
      params: {{ appInfo: {{ name: "cdxml-molstar-viewer", version: "1.1.0" }}, appCapabilities: {{}}, protocolVersion: "2026-01-26" }}
    }});
    postHost({{ jsonrpc: "2.0", method: "ui/notifications/size-changed", params: {{ width: 880, height: 460 }} }});
  }}

  applyPayload(state.payload);
  window.addEventListener("load", () => {{ if (window.molstar && window.molstar.Viewer) tryEnableMolstar(); }});
  function tick() {{
    if (state.spin && !dragging && state.engine === "canvas") {{ state.rotY += 0.008; drawCanvas(); }}
    requestAnimationFrame(tick);
  }}
  requestAnimationFrame(tick);
}})();
</script>
<script src="https://cdn.jsdelivr.net/npm/molstar@latest/build/viewer/molstar.js" async></script>
</body>
</html>
"""


_STUDIO_TEMPLATES: dict[str, dict[str, Any]] = {
    "blank": {"name": "Blank Structure", "category": "Canvas", "atoms": [], "bonds": []},
    "empty": {"name": "Empty Canvas", "category": "Canvas", "atoms": [], "bonds": []},
    "aspirin": {"name": "Aspirin", "smiles": "CC(=O)Oc1ccccc1C(=O)O", "category": "Molecules"},
    "caffeine": {"name": "Caffeine", "smiles": "Cn1c(=O)c2c(ncn2C)n(C)c1=O", "category": "Molecules"},
    "ibuprofen": {"name": "Ibuprofen", "smiles": "CC(C)Cc1ccc(C(C)C(=O)O)cc1", "category": "Molecules"},
    "paracetamol": {"name": "Paracetamol", "smiles": "CC(=O)Nc1ccc(O)cc1", "category": "Molecules"},
    "vanillin": {"name": "Vanillin", "smiles": "COc1cc(C=O)ccc1O", "category": "Molecules"},
    "benzene": {"name": "Benzene", "smiles": "c1ccccc1", "category": "Molecules"},
    "pyridine": {"name": "Pyridine", "smiles": "c1ccncc1", "category": "Molecules"},
    "indole": {"name": "Indole", "smiles": "c1ccc2[nH]ccc2c1", "category": "Molecules"},
    "quinoline": {"name": "Quinoline", "smiles": "c1ccc2ncccc2c1", "category": "Molecules"},
    "purine": {"name": "Purine", "smiles": "c1ncc2[nH]cnc2n1", "category": "Molecules"},
    "chair": {
        "name": "Chair Cyclohexane",
        "category": "Conformers",
        "atoms": [
            {"s": "C", "x": 195, "y": 165}, {"s": "C", "x": 240, "y": 142}, {"s": "C", "x": 292, "y": 160},
            {"s": "C", "x": 324, "y": 128}, {"s": "C", "x": 278, "y": 150}, {"s": "C", "x": 226, "y": 132},
            {"s": "O", "x": 324, "y": 88}, {"s": "Me", "x": 195, "y": 204},
        ],
        "bonds": [
            {"a": 0, "b": 1, "o": 1}, {"a": 1, "b": 2, "o": 4}, {"a": 2, "b": 3, "o": 1},
            {"a": 3, "b": 4, "o": 1}, {"a": 4, "b": 5, "o": 1}, {"a": 5, "b": 0, "o": 1},
            {"a": 3, "b": 6, "o": 1}, {"a": 0, "b": 7, "o": 5},
        ],
    },
    "newman": {
        "name": "Staggered Newman",
        "category": "Conformers",
        "atoms": [
            {"s": "C", "x": 270, "y": 142}, {"s": "Me", "x": 270, "y": 84}, {"s": "H", "x": 220, "y": 172},
            {"s": "H", "x": 320, "y": 172}, {"s": "Me", "x": 270, "y": 206}, {"s": "H", "x": 214, "y": 108},
            {"s": "H", "x": 326, "y": 108},
        ],
        "bonds": [
            {"a": 0, "b": 1, "o": 1}, {"a": 0, "b": 2, "o": 1}, {"a": 0, "b": 3, "o": 1},
        ],
        "circles": [{"cx": 270, "cy": 142, "r": 26}],
        "spokes": [
            [270, 168, 270, 196], [248, 129, 224, 114], [292, 129, 316, 114],
        ],
    },
    "suzuki_coupling": {
        "name": "Suzuki-Miyaura",
        "category": "Reactions",
        "smiles": "Brc1ccccc1.OB(O)c1ccc(C)cc1",
        "arrows": [{"x1": 215, "y1": 145, "x2": 315, "y2": 145, "style": "solid", "above": "Pd(PPh3)4 (5 mol%)", "below": "K2CO3, THF/H2O, 80 °C"}],
        "pluses": [{"x": 118, "y": 148}],
        "product_smiles": "Cc1ccc(-c2ccccc2)cc1",
    },
    "amide_coupling": {
        "name": "HATU Amide",
        "category": "Reactions",
        "smiles": "O=C(O)c1ccccc1.Nc1ccc(F)cc1",
        "arrows": [{"x1": 215, "y1": 145, "x2": 315, "y2": 145, "style": "solid", "above": "HATU, DIPEA", "below": "DMF, rt, 2 h"}],
        "product_smiles": "O=C(Nc1ccc(F)cc1)c1ccccc1",
    },
    "buchwald_hartwig": {
        "name": "Buchwald-Hartwig",
        "category": "Reactions",
        "smiles": "Clc1ccc(OC)cc1.C1CCNCC1",
        "arrows": [{"x1": 215, "y1": 145, "x2": 315, "y2": 145, "style": "solid", "above": "Pd2(dba)3, RuPhos", "below": "NaOtBu, PhMe, 100 °C"}],
        "product_smiles": "COc1ccc(N2CCCCC2)cc1",
    },
    "sonogashira": {
        "name": "Sonogashira",
        "category": "Reactions",
        "smiles": "Ic1ccccc1.C#Cc1ccc(OC)cc1",
        "arrows": [{"x1": 215, "y1": 145, "x2": 315, "y2": 145, "style": "solid", "above": "PdCl2(PPh3)2, CuI", "below": "Et3N, THF, rt"}],
        "product_smiles": "COc1ccc(C#Cc2ccccc2)cc1",
    },
    "catalytic_cycle": {
        "name": "Pd Catalytic Cycle",
        "category": "Reactions",
        "smiles": "[Pd]",
        "texts": [
            {"x": 275, "y": 58, "text": "LnPd(0)"},
            {"x": 405, "y": 145, "text": "Ar-Pd(II)-X"},
            {"x": 275, "y": 232, "text": "Ar-Pd(II)-R"},
            {"x": 145, "y": 145, "text": "Ar-R + HX"},
            {"x": 355, "y": 88, "text": "OA: Ar-X"},
            {"x": 358, "y": 204, "text": "TM: R-B(OH)2"},
            {"x": 188, "y": 204, "text": "RE"},
        ],
    },
    "sar_2x2": {
        "name": "SAR Core Scaffold",
        "category": "Reactions",
        "smiles": "c1ccc(C(=O)N[C@@H](C)c2ccccc2)cc1",
        "texts": [
            {"x": 275, "y": 244, "text": "1a (R = H, 92%)  |  1b (R = OMe, 95%)  |  1c (R = CF3, 84%)"},
        ],
    },
}


def _smiles_to_studio_graph(
    smiles: str,
    *,
    offset_x: float = 275.0,
    offset_y: float = 142.0,
    bond_scale: float = 28.0,
) -> dict[str, Any]:
    from rdkit import Chem
    from rdkit.Chem import AllChem

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Could not parse SMILES: {smiles!r}")
    Chem.Kekulize(mol, clearAromaticFlags=True)
    AllChem.Compute2DCoords(mol)
    conf = mol.GetConformer()
    try:
        Chem.WedgeMolBonds(mol, conf)
    except Exception:
        pass

    raw_coords = [(float(conf.GetAtomPosition(i).x), float(conf.GetAtomPosition(i).y)) for i in range(mol.GetNumAtoms())]
    lengths = []
    for bond in mol.GetBonds():
        x1, y1 = raw_coords[bond.GetBeginAtomIdx()]
        x2, y2 = raw_coords[bond.GetEndAtomIdx()]
        d = math.hypot(x2 - x1, y2 - y1)
        if d > 1e-4:
            lengths.append(d)
    avg_len = sum(lengths) / len(lengths) if lengths else 1.5
    factor = bond_scale / avg_len

    xs = [p[0] for p in raw_coords] or [0.0]
    ys = [p[1] for p in raw_coords] or [0.0]
    cx = (min(xs) + max(xs)) * 0.5
    cy = (min(ys) + max(ys)) * 0.5

    atoms = []
    for i, atom in enumerate(mol.GetAtoms()):
        rx, ry = raw_coords[i]
        entry: dict[str, Any] = {
            "s": atom.GetSymbol(),
            "x": round(offset_x + (rx - cx) * factor, 2),
            "y": round(offset_y - (ry - cy) * factor, 2),
        }
        chg = int(atom.GetFormalCharge())
        if chg:
            entry["chg"] = chg
        atoms.append(entry)
    bonds = []
    for bond in mol.GetBonds():
        bt = bond.GetBondType()
        order = 2 if bt == Chem.BondType.DOUBLE else (3 if bt == Chem.BondType.TRIPLE else 1)
        bdir = bond.GetBondDir()
        if bdir == Chem.BondDir.BEGINWEDGE:
            order = 4
        elif bdir == Chem.BondDir.BEGINDASH:
            order = 5
        bonds.append({"a": int(bond.GetBeginAtomIdx()), "b": int(bond.GetEndAtomIdx()), "o": order})
    return {"atoms": atoms, "bonds": bonds}


def _cdxml_to_studio_graph(cdxml_path: Path) -> dict[str, Any]:
    root = ET.parse(cdxml_path).getroot()
    atoms: list[dict[str, Any]] = []
    bonds: list[dict[str, Any]] = []
    id_to_idx: dict[str, int] = {}
    all_pts: list[tuple[float, float]] = []

    for node in root.findall(".//fragment/n"):
        nid = node.get("id")
        if not nid or node.get("NodeType") == "ExternalConnectionPoint":
            continue
        parts = (node.get("p") or "0 0").split()
        x, y = float(parts[0]), float(parts[1])
        all_pts.append((x, y))
        elem_num = int(node.get("Element", "6"))
        sym = _ELEMENT_MAP.get(elem_num, "C")
        text_el = node.find(".//s")
        if node.get("NodeType") in {"Fragment", "GenericNickname", "Nickname"} and text_el is not None and text_el.text:
            sym = text_el.text.strip()[:8]
        id_to_idx[nid] = len(atoms)
        atom_entry: dict[str, Any] = {"s": sym, "x": x, "y": y}
        if node.get("Charge"):
            try:
                atom_entry["chg"] = int(node.get("Charge") or "0")
            except ValueError:
                pass
        atoms.append(atom_entry)

    for bond in root.findall(".//fragment/b"):
        b_id, e_id = bond.get("B"), bond.get("E")
        if b_id not in id_to_idx or e_id not in id_to_idx:
            continue
        order = int(bond.get("Order", "1") or 1)
        display = (bond.get("Display") or "").lower()
        if "wedgedbegin" in display or display == "wedgebegin":
            order = 4
        elif "wedgedhash" in display or display == "hashbegin":
            order = 5
        elif "wavy" in display:
            order = 6
        bonds.append({"a": id_to_idx[b_id], "b": id_to_idx[e_id], "o": order})

    if all_pts:
        xs = [p[0] for p in all_pts]
        ys = [p[1] for p in all_pts]
        cx, cy = (min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5
        span = max(max(xs) - min(xs), max(ys) - min(ys), 10.0)
        scale = min(2.2, max(1.0, 215.0 / span))
        for atom in atoms:
            atom["x"] = round(275.0 + (atom["x"] - cx) * scale, 2)
            atom["y"] = round(142.0 + (atom["y"] - cy) * scale, 2)
    return {"atoms": atoms, "bonds": bonds}


def _build_studio_graph_for_template(key: str) -> dict[str, Any]:
    tmpl = _STUDIO_TEMPLATES[key]
    graph: dict[str, Any] = {
        "name": tmpl["name"],
        "template_key": key,
        "category": tmpl.get("category", "Molecules"),
        "atoms": [],
        "bonds": [],
        "arrows": [dict(a) for a in (tmpl.get("arrows") or [])],
        "pluses": [dict(p) for p in (tmpl.get("pluses") or [])],
        "texts": [dict(t) for t in (tmpl.get("texts") or [])],
        "circles": [dict(c) for c in (tmpl.get("circles") or [])],
        "spokes": [list(s) for s in (tmpl.get("spokes") or [])],
        "ring_fills": [],
    }
    if "atoms" in tmpl:
        graph["atoms"] = [dict(a) for a in tmpl["atoms"]]
        graph["bonds"] = [dict(b) for b in tmpl["bonds"]]
    elif "arrows" in tmpl and "product_smiles" in tmpl:
        parts_smi = tmpl["smiles"].split(".")
        if len(parts_smi) == 2:
            g1 = _smiles_to_studio_graph(parts_smi[0], offset_x=112.0, offset_y=96.0, bond_scale=22.0)
            g2 = _smiles_to_studio_graph(parts_smi[1], offset_x=112.0, offset_y=192.0, bond_scale=22.0)
            off1 = len(g1["atoms"])
            left_atoms = g1["atoms"] + g2["atoms"]
            left_bonds = g1["bonds"] + [{"a": b["a"] + off1, "b": b["b"] + off1, "o": b["o"]} for b in g2["bonds"]]
            if not graph["pluses"]:
                graph["pluses"] = [{"x": 112, "y": 145}]
        else:
            left = _smiles_to_studio_graph(tmpl["smiles"], offset_x=115.0, offset_y=145.0, bond_scale=22.0)
            left_atoms, left_bonds = left["atoms"], left["bonds"]
        right = _smiles_to_studio_graph(tmpl["product_smiles"], offset_x=438.0, offset_y=145.0, bond_scale=22.0)
        offset = len(left_atoms)
        graph["atoms"] = left_atoms + right["atoms"]
        graph["bonds"] = left_bonds + [
            {"a": b["a"] + offset, "b": b["b"] + offset, "o": b["o"]} for b in right["bonds"]
        ]
        graph["smiles"] = f"{tmpl['smiles']}>>{tmpl['product_smiles']}"
    elif "smiles" in tmpl:
        built = _smiles_to_studio_graph(tmpl["smiles"], offset_x=275.0, offset_y=142.0, bond_scale=28.0)
        graph["atoms"] = built["atoms"]
        graph["bonds"] = built["bonds"]
        graph["smiles"] = tmpl["smiles"]
    return graph


def _studio_template_catalog() -> dict[str, dict[str, Any]]:
    return {key: _build_studio_graph_for_template(key) for key in _STUDIO_TEMPLATES}


def _compute_graph_metrics(graph: dict[str, Any]) -> tuple[str, float, int]:
    from collections import Counter

    valence = {"H": 1, "B": 3, "C": 4, "N": 3, "O": 2, "S": 2, "P": 3, "F": 1, "Cl": 1, "Br": 1, "I": 1, "Si": 4}
    atoms = graph.get("atoms") or []
    bonds = graph.get("bonds") or []
    order_sum = [0] * len(atoms)
    for b in bonds:
        order = 1 if b.get("o", 1) >= 4 else int(b.get("o", 1))
        if b["a"] < len(atoms):
            order_sum[b["a"]] += order
        if b["b"] < len(atoms):
            order_sum[b["b"]] += order
    counts: Counter[str] = Counter()
    for i, a in enumerate(atoms):
        sym = a.get("s", "C")
        chg = int(a.get("chg", 0) or 0)
        if sym in _SUPERATOM_FORMULAS:
            for el, n in _SUPERATOM_FORMULAS[sym].items():
                counts[el] += n
            continue
        if sym in _ATOMIC_WEIGHTS:
            counts[sym] += 1
        base_val = valence.get(sym, 0)
        if sym == "N" and chg == 1:
            base_val = 4
        elif sym == "O" and chg == -1:
            base_val = 1
        elif sym == "B" and chg == -1:
            base_val = 4
        imp_h = max(0, base_val - order_sum[i])
        counts["H"] += imp_h
    parts = []
    for el in ("C", "H"):
        if counts.get(el):
            parts.append(el if counts[el] == 1 else f"{el}{counts[el]}")
    for el in sorted(k for k in counts if k not in {"C", "H"}):
        if counts[el]:
            parts.append(el if counts[el] == 1 else f"{el}{counts[el]}")
    formula = "".join(parts) or "-"
    mw = round(sum(_ATOMIC_WEIGHTS.get(el, 0.0) * n for el, n in counts.items()), 2)
    c_count = counts.get("C", 0)
    h_count = counts.get("H", 0)
    n_count = counts.get("N", 0)
    hal_count = counts.get("F", 0) + counts.get("Cl", 0) + counts.get("Br", 0) + counts.get("I", 0)
    dbe = max(0, int(round(c_count + 1 - (h_count + hal_count - n_count) / 2.0)))
    return formula, mw, dbe


def render_drawing_studio_fragment(initial_payload: dict[str, Any] | None = None) -> str:
    """Render a pure HTML fragment (<div id='cdx-studio-root'>...</div>) with NO document tags.

    Implements a full general-purpose Reaxys / SciFinder-class 2D chemical structure, reaction,
    mechanism, and substructure-query editor (4-edge docked vector-icon toolbars, dynamic ghost
    ring fusion/spiro preview, zigzag alkane chain tool, lasso/marquee selection with rotation
    handle, 118-element periodic table + isotopes, substructure query generics A/Q/X/M/R1..R6 &
    atom locks, curved electron-pushing arrows, polymer brackets, Markush variable ring attachment,
    2D coordinate cleanup, Kekule/Thiele aromatize toggle, and live SMILES / SMARTS / V2000 Molfile /
    ACS 1996 CDXML / SVG import-export).
    """
    catalog = _studio_template_catalog()
    payload = initial_payload or {"graph": catalog["blank"], "style": "acs1996", "styles": _STYLE_PRESETS}
    if "styles" not in payload:
        payload = {**payload, "styles": _STYLE_PRESETS}
    initial_json = _html_json(payload)
    catalog_json = _html_json(catalog)
    return rf"""<div id="cdx-studio-root" class="cdx-studio-shell" role="application" aria-label="2D Chemical Structure and Substructure Query Editor">
<style>
  #cdx-studio-root {{
    --cdx-frame: var(--card, #f1f5f9);
    --cdx-bar: var(--background, #f8fafc);
    --cdx-btn-hover: var(--accent, #e2e8f0);
    --cdx-fg: var(--foreground, #0f172a);
    --cdx-muted: var(--muted-foreground, #475569);
    --cdx-border: var(--border, rgba(15,23,42,0.16));
    --cdx-active: var(--primary, #0284c7);
    --cdx-active-fg: var(--primary-foreground, #ffffff);
    box-sizing: border-box;
    width: 100%;
    color: var(--cdx-fg);
    background: var(--cdx-frame);
    border: 1px solid var(--cdx-border);
    border-radius: 8px;
    overflow: hidden;
    font: 12px/1.3 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    user-select: none;
    position: relative;
  }}
  #cdx-studio-root *, #cdx-studio-root *::before, #cdx-studio-root *::after {{ box-sizing: border-box; }}
  @media (prefers-color-scheme: dark) {{
    #cdx-studio-root[data-standalone="1"] {{
      --cdx-frame: #161b22;
      --cdx-bar: #0d1117;
      --cdx-btn-hover: #21262d;
      --cdx-fg: #e6edf3;
      --cdx-muted: #8b949e;
      --cdx-border: rgba(240,246,252,0.16);
      --cdx-active: #0284c7;
      --cdx-active-fg: #ffffff;
    }}
  }}
  #cdx-studio-root button, #cdx-studio-root select, #cdx-studio-root input, #cdx-studio-root textarea {{
    font: inherit; color: inherit;
  }}
  #cdx-studio-root .cdx-ibtn {{
    display: inline-flex; align-items: center; justify-content: center; gap: 3px;
    min-width: 27px; height: 26px; padding: 0 5px; border: 1px solid transparent;
    border-radius: 5px; background: transparent; cursor: pointer; position: relative;
    color: var(--cdx-fg); transition: background 0.1s, border-color 0.1s;
  }}
  #cdx-studio-root .cdx-ibtn:hover {{ background: var(--cdx-btn-hover); border-color: var(--cdx-border); }}
  #cdx-studio-root .cdx-ibtn.is-active {{
    background: var(--cdx-active); color: var(--cdx-active-fg); border-color: var(--cdx-active);
  }}
  #cdx-studio-root .cdx-ibtn svg {{ width: 17px; height: 17px; stroke: currentColor; fill: none; stroke-width: 1.65; stroke-linecap: round; stroke-linejoin: round; flex-shrink: 0; }}
  #cdx-studio-root .cdx-sep {{ width: 1px; height: 18px; background: var(--cdx-border); margin: 0 2px; flex-shrink: 0; }}
  #cdx-studio-root .cdx-hsep {{ width: 24px; height: 1px; background: var(--cdx-border); margin: 2px auto; }}
  #cdx-studio-root .cdx-top {{
    display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
    gap: 2px; padding: 3px 6px; background: var(--cdx-bar); border-bottom: 1px solid var(--cdx-border);
  }}
  #cdx-studio-root .cdx-top-grp {{ display: flex; flex-wrap: wrap; align-items: center; gap: 2px; }}
  #cdx-studio-root .cdx-select {{
    height: 25px; padding: 0 5px; border-radius: 5px; border: 1px solid var(--cdx-border);
    background: var(--cdx-frame); font-size: 11.5px; cursor: pointer;
  }}
  #cdx-studio-root .cdx-work {{
    display: grid; grid-template-columns: 38px 1fr 44px; min-height: 356px; position: relative;
  }}
  #cdx-studio-root.is-tall .cdx-work {{ min-height: 520px; }}
  #cdx-studio-root .cdx-left {{
    display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 4px 3px;
    background: var(--cdx-bar); border-right: 1px solid var(--cdx-border); z-index: 4;
  }}
  #cdx-studio-root .cdx-left .cdx-ibtn {{ width: 30px; height: 29px; padding: 0; }}
  #cdx-studio-root .cdx-caret {{
    position: absolute; right: 2px; bottom: 2px; width: 0; height: 0;
    border-left: 3.5px solid transparent; border-top: 3.5px solid transparent;
    border-right: 3.5px solid currentColor; border-bottom: 3.5px solid currentColor; opacity: 0.65;
  }}
  #cdx-studio-root .cdx-right {{
    display: flex; flex-direction: column; align-items: center; gap: 1.5px; padding: 4px 3px;
    background: var(--cdx-bar); border-left: 1px solid var(--cdx-border); z-index: 4;
    overflow-y: auto; max-height: 364px;
  }}
  #cdx-studio-root.is-tall .cdx-right {{ max-height: 528px; }}
  #cdx-studio-root .cdx-elbtn {{
    width: 34px; height: 21px; padding: 0; border-radius: 4px; border: 1px solid transparent;
    background: transparent; font-size: 11.5px; font-weight: 600; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
  }}
  #cdx-studio-root .cdx-elbtn:hover {{ background: var(--cdx-btn-hover); border-color: var(--cdx-border); }}
  #cdx-studio-root .cdx-elbtn.is-active {{ background: var(--cdx-active); color: var(--cdx-active-fg) !important; }}
  #cdx-studio-root .cdx-stage {{
    position: relative; background: #ffffff; overflow: hidden; display: flex;
    background-image: radial-gradient(rgba(15,23,42,0.085) 1px, transparent 0);
    background-size: 20px 20px;
  }}
  #cdx-studio-root .cdx-stage.no-grid {{ background-image: none; }}
  #cdx-studio-root #cdx-svg {{
    width: 100%; height: 356px; display: block; touch-action: none; cursor: crosshair;
  }}
  #cdx-studio-root.is-tall #cdx-svg {{ height: 520px; }}
  #cdx-studio-root .cdx-toast {{
    position: absolute; top: 6px; left: 8px; pointer-events: none;
    background: rgba(255,255,255,0.92); color: #0f172a; border: 1px solid rgba(15,23,42,0.14);
    border-radius: 999px; padding: 2px 9px; font-size: 11px; font-weight: 500;
  }}
  #cdx-studio-root .cdx-zoom-hud {{
    position: absolute; bottom: 6px; right: 8px; display: flex; align-items: center; gap: 2px;
    background: rgba(255,255,255,0.92); color: #0f172a; border: 1px solid rgba(15,23,42,0.14);
    border-radius: 6px; padding: 1px 4px; font-size: 11px;
  }}
  #cdx-studio-root .cdx-zoom-hud button {{
    border: 0; background: transparent; color: #0f172a; cursor: pointer; padding: 1px 5px; font-weight: 600;
  }}
  #cdx-studio-root .cdx-rings {{
    display: flex; align-items: center; gap: 2px; padding: 3px 6px; overflow-x: auto;
    background: var(--cdx-bar); border-top: 1px solid var(--cdx-border);
  }}
  #cdx-studio-root .cdx-rbtn {{
    display: inline-flex; align-items: center; justify-content: center; gap: 3px;
    min-width: 30px; height: 26px; padding: 0 4px; border-radius: 5px; border: 1px solid transparent;
    background: transparent; cursor: pointer; flex-shrink: 0; font-size: 11px; font-weight: 500;
  }}
  #cdx-studio-root .cdx-rbtn:hover {{ background: var(--cdx-btn-hover); border-color: var(--cdx-border); }}
  #cdx-studio-root .cdx-rbtn.is-active {{ background: var(--cdx-active); color: var(--cdx-active-fg); }}
  #cdx-studio-root .cdx-rbtn svg {{ width: 19px; height: 19px; stroke: currentColor; fill: none; stroke-width: 1.55; }}
  #cdx-studio-root .cdx-status {{
    display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 6px;
    padding: 4px 8px; background: var(--cdx-frame); border-top: 1px solid var(--cdx-border); font-size: 11.5px;
  }}
  #cdx-studio-root .cdx-metrics {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }}
  #cdx-studio-root .cdx-smi-chip {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 11px;
    background: var(--cdx-bar); border: 1px solid var(--cdx-border); border-radius: 4px;
    padding: 1px 6px; max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }}
  #cdx-studio-root .cdx-cta {{
    background: #0284c7; color: #ffffff; border: 1px solid #0284c7; border-radius: 5px;
    padding: 3px 10px; font-weight: 600; cursor: pointer; height: 25px;
  }}
  #cdx-studio-root .cdx-cta:hover {{ filter: brightness(1.07); }}
  #cdx-studio-root .cdx-flyout {{
    position: absolute; left: 40px; z-index: 30; background: var(--cdx-bar);
    border: 1px solid var(--cdx-border); border-radius: 7px; padding: 4px;
    box-shadow: 0 8px 24px rgba(15,23,42,0.22); display: grid; grid-template-columns: repeat(3, 1fr); gap: 3px;
    min-width: 168px;
  }}
  #cdx-studio-root .cdx-flybtn {{
    display: flex; align-items: center; gap: 5px; padding: 4px 6px; border-radius: 5px;
    border: 1px solid transparent; background: transparent; cursor: pointer; font-size: 11px; white-space: nowrap;
  }}
  #cdx-studio-root .cdx-flybtn:hover {{ background: var(--cdx-btn-hover); }}
  #cdx-studio-root .cdx-flybtn.is-active {{ background: var(--cdx-active); color: var(--cdx-active-fg); }}
  #cdx-studio-root .cdx-modal-backdrop {{
    position: absolute; inset: 0; background: rgba(15,23,42,0.38); z-index: 40;
    display: flex; align-items: center; justify-content: center; padding: 10px;
  }}
  #cdx-studio-root .cdx-modal {{
    background: var(--cdx-bar); color: var(--cdx-fg); border: 1px solid var(--cdx-border);
    border-radius: 9px; padding: 10px 12px; width: min(96%, 680px); max-height: 92%;
    overflow: auto; box-shadow: 0 14px 36px rgba(15,23,42,0.32);
  }}
  #cdx-studio-root .cdx-modal[hidden], #cdx-studio-root .cdx-modal-backdrop[hidden], #cdx-studio-root .cdx-flyout[hidden], #cdx-studio-root .cdx-hotbox[hidden] {{
    display: none !important;
  }}
  #cdx-studio-root .cdx-pt-grid {{
    display: grid; grid-template-columns: repeat(18, minmax(0, 1fr)); gap: 2px; margin-top: 6px;
  }}
  #cdx-studio-root .cdx-pt-cell {{
    height: 24px; padding: 0; border-radius: 3px; border: 1px solid rgba(15,23,42,0.15);
    font-size: 10px; font-weight: 600; cursor: pointer; display: flex; flex-direction: column;
    align-items: center; justify-content: center; line-height: 1; color: #0f172a;
  }}
  #cdx-studio-root .cdx-pt-cell small {{ font-size: 7px; opacity: 0.72; font-weight: 400; }}
  #cdx-studio-root .cdx-pt-cell:hover {{ outline: 2px solid #0284c7; z-index: 2; }}
  #cdx-studio-root .cdx-hotbox {{
    position: absolute; z-index: 35; background: #ffffff; color: #0f172a;
    border: 1.5px solid #0284c7; border-radius: 6px; padding: 3px; display: flex; gap: 3px;
    box-shadow: 0 6px 18px rgba(15,23,42,0.22);
  }}
  #cdx-studio-root .cdx-hotbox input {{
    width: 132px; height: 23px; border: 1px solid rgba(15,23,42,0.2); border-radius: 4px;
    padding: 0 6px; font-size: 12px; color: #0f172a; background: #ffffff;
  }}
  #cdx-studio-root textarea.cdx-code {{
    width: 100%; height: 150px; font: 11px/1.35 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    background: var(--cdx-frame); color: var(--cdx-fg); border: 1px solid var(--cdx-border);
    border-radius: 6px; padding: 6px; resize: vertical;
  }}
</style>

  <!-- TOP ACTION BAR (Reaxys / SciFinder style) -->
  <div class="cdx-top" role="toolbar" aria-label="Structure Actions">
    <div class="cdx-top-grp">
      <button type="button" class="cdx-ibtn" id="cdx-act-new" title="Clear / New Canvas (Ctrl+Delete)">
        <svg viewBox="0 0 20 20"><path d="M5 3h7l4 4v10H5z"/><path d="M12 3v4h4"/></svg>
      </button>
      <button type="button" class="cdx-ibtn" id="cdx-act-import" title="Import SMILES / SMARTS / Molfile V2000 / CDXML">
        <svg viewBox="0 0 20 20"><path d="M3 6h5l2 2h7v8H3z"/><path d="M10 10v5m-2.5-2.5L10 15l2.5-2.5"/></svg>
      </button>
      <button type="button" class="cdx-ibtn" id="cdx-act-export" title="Export / View SMILES, SMARTS, Molfile V2000, CDXML, SVG">
        <svg viewBox="0 0 20 20"><path d="M4 13v3h12v-3"/><path d="M10 12V3m-3 3l3-3 3 3"/></svg>
      </button>
      <span class="cdx-sep"></span>
      <button type="button" class="cdx-ibtn" id="cdx-act-undo" title="Undo (Ctrl+Z)">
        <svg viewBox="0 0 20 20"><path d="M7 7H4V4"/><path d="M4 7a7 7 0 1 1 2 7"/></svg>
      </button>
      <button type="button" class="cdx-ibtn" id="cdx-act-redo" title="Redo (Ctrl+Y)">
        <svg viewBox="0 0 20 20"><path d="M13 7h3V4"/><path d="M16 7a7 7 0 1 0-2 7"/></svg>
      </button>
      <button type="button" class="cdx-ibtn" id="cdx-act-dup" title="Duplicate Selection or Molecule (Ctrl+D)">
        <svg viewBox="0 0 20 20"><rect x="7" y="7" width="9" height="9" rx="1.5"/><path d="M4 13V4h9"/></svg>
      </button>
      <span class="cdx-sep"></span>
      <button type="button" class="cdx-ibtn" id="cdx-act-clean" title="Clean 2D Coordinates (regularize rings & 120 deg angles)">
        <svg viewBox="0 0 20 20"><polygon points="10,2.5 16,6 16,13 10,16.5 4,13 4,6"/><path d="M16.5 2.5l1 2 2 1-2 1-1 2-1-2-2-1 2-1z" fill="currentColor" stroke="none"/></svg>
        <span style="font-size:11px;font-weight:500">Clean</span>
      </button>
      <button type="button" class="cdx-ibtn" id="cdx-act-arom" title="Toggle Kekule Double Bonds / Thiele Aromatic Circle">
        <svg viewBox="0 0 20 20"><polygon points="10,2.5 16.5,6.2 16.5,13.8 10,17.5 3.5,13.8 3.5,6.2"/><circle cx="10" cy="10" r="3.8"/></svg>
      </button>
      <button type="button" class="cdx-ibtn" id="cdx-act-expand" title="Expand Abbreviations (Boc, CO2Et, CF3, Ph, CN, NO2 -> Explicit Atoms)">
        <span style="font-size:10.5px;font-weight:600">R→At</span>
      </button>
      <button type="button" class="cdx-ibtn" id="cdx-act-fliph" title="Flip Horizontal">
        <svg viewBox="0 0 20 20"><path d="M10 3v14"/><polygon points="3,14 8,10 3,6"/><polygon points="17,14 12,10 17,6"/></svg>
      </button>
      <button type="button" class="cdx-ibtn" id="cdx-act-flipv" title="Flip Vertical">
        <svg viewBox="0 0 20 20"><path d="M3 10h14"/><polygon points="6,3 10,8 14,3"/><polygon points="6,17 10,12 14,17"/></svg>
      </button>
      <button type="button" class="cdx-ibtn" id="cdx-act-rot" title="Rotate 30 deg">
        <svg viewBox="0 0 20 20"><path d="M15 6a6 6 0 1 0 1.5 5"/><polyline points="15,2.5 15.5,6.5 11.5,6"/></svg>
      </button>
    </div>
    <div class="cdx-top-grp">
      <button type="button" class="cdx-ibtn" id="cdx-act-tmpl" title="Functional Groups, Protecting Groups, Scaffolds & Reaction Library">
        <span style="font-size:11px;font-weight:600">Templates ▾</span>
      </button>
      <select id="cdx-style-sel" class="cdx-select" aria-label="Publication style"></select>
      <button type="button" class="cdx-ibtn" id="cdx-act-grid" title="Toggle Canvas Grid">#</button>
      <button type="button" class="cdx-ibtn" id="cdx-act-tall" title="Expand / Compact Canvas Height">⤢</button>
    </div>
  </div>

  <!-- CENTER WORKBENCH: LEFT TOOLS | CANVAS | RIGHT ELEMENTS & PERIODIC TABLE -->
  <div class="cdx-work">
    <!-- Left Vertical Docked Toolbar -->
    <div class="cdx-left" role="toolbar" aria-label="Drawing and Query Tools">
      <button type="button" class="cdx-ibtn" data-slot="select" title="Select: Lasso / Box / Fragment (V / Esc) - Click again for modes">
        <svg viewBox="0 0 20 20"><path d="M4 10c0-4 3-6 6.5-6S17 6.5 17 10s-2.5 5.5-6 5.5c-1.8 0-3 .8-4.5 1.5-.8.3-1.5-.5-1-1.3.7-1.1-.5-2.7-1.5-5.7z" stroke-dasharray="2.2 1.8"/></svg>
        <span class="cdx-caret"></span>
      </button>
      <button type="button" class="cdx-ibtn" data-slot="erase" title="Eraser - Click or drag across atoms/bonds (E / Del)">
        <svg viewBox="0 0 20 20"><path d="M7 16h9"/><path d="M4.5 12.5l6.8-6.8a1.5 1.5 0 0 1 2.1 0l2.9 2.9a1.5 1.5 0 0 1 0 2.1L11 16H7z"/></svg>
      </button>
      <span class="cdx-hsep"></span>
      <button type="button" class="cdx-ibtn is-active" data-slot="bond" title="Bonds: Single (1), Double (2), Triple (3) - Click again for flyout">
        <svg viewBox="0 0 20 20" id="cdx-ico-bond"><line x1="4" y1="15" x2="16" y2="5"/></svg>
        <span class="cdx-caret"></span>
      </button>
      <button type="button" class="cdx-ibtn" data-slot="stereo" title="Stereo Bonds: Up Wedge (W), Down Hash (H), Wavy, Crossed E/Z">
        <svg viewBox="0 0 20 20"><polygon points="4,15 15,4 17,7.5" fill="currentColor"/></svg>
        <span class="cdx-caret"></span>
      </button>
      <button type="button" class="cdx-ibtn" data-slot="qbond" title="Reaxys / SciFinder Query & Coordination Bonds (Any, 1/2, Arom, Dative)">
        <svg viewBox="0 0 20 20"><line x1="4" y1="14" x2="16" y2="4"/><line x1="6" y1="16.8" x2="17.5" y2="7.2" stroke-dasharray="2.2 2"/></svg>
        <span class="cdx-caret"></span>
      </button>
      <button type="button" class="cdx-ibtn" data-slot="chain" title="Alkane Zigzag Chain Tool - Drag to draw C2..C24 chain">
        <svg viewBox="0 0 20 20"><polyline points="2.5,14 6.5,8 10.5,13 14.5,7 18,11.5"/></svg>
      </button>
      <span class="cdx-hsep"></span>
      <button type="button" class="cdx-ibtn" data-slot="charge" title="Formal Charge (+ / -) & Radical (.)">
        <svg viewBox="0 0 20 20"><circle cx="8" cy="8" r="4.8"/><path d="M8 5.7v4.6M5.7 8h4.6"/><line x1="12.5" y1="15" x2="17.5" y2="15"/></svg>
        <span class="cdx-caret"></span>
      </button>
      <button type="button" class="cdx-ibtn" data-slot="text" title="Formula / R-Group / Text Label (T or Double-Click any Atom)">
        <span style="font-weight:700;font-size:12px;font-family:Georgia,serif">Ab</span>
      </button>
      <button type="button" class="cdx-ibtn" data-slot="rxn" title="Reaction Arrows, Plus (+), Atom Mapping [1], Curved Electron Arrows">
        <svg viewBox="0 0 20 20"><line x1="3" y1="10" x2="16" y2="10"/><polyline points="12,6.5 16.5,10 12,13.5"/></svg>
        <span class="cdx-caret"></span>
      </button>
      <button type="button" class="cdx-ibtn" data-slot="markush" title="Polymer Brackets [ ]n, Variable Ring Attachment (o/m/p) & Ring Shading">
        <svg viewBox="0 0 20 20"><path d="M6 4H4v12h2M14 4h2v12h-2"/><text x="10" y="13" text-anchor="middle" font-size="8.5" fill="currentColor" stroke="none">n</text></svg>
        <span class="cdx-caret"></span>
      </button>
    </div>

    <!-- Flyout Popover for Subtools -->
    <div id="cdx-flyout" class="cdx-flyout" hidden></div>

    <!-- Central Interactive Chemical Canvas -->
    <div class="cdx-stage" id="cdx-stage-wrap">
      <svg id="cdx-svg" viewBox="0 0 680 356" xmlns="http://www.w3.org/2000/svg"></svg>
      <div class="cdx-toast" id="cdx-toast">Single Bond · Drag from atom (30° snap) or choose Ring below to place/fuse</div>
      <div class="cdx-zoom-hud">
        <button type="button" id="cdx-z-out" title="Zoom Out (-)">−</button>
        <button type="button" id="cdx-z-fit" title="Fit to Screen (0)">100%</button>
        <button type="button" id="cdx-z-in" title="Zoom In (+)">+</button>
      </div>
      <!-- Floating Inline Atom / Formula / Reagent Hotbox -->
      <div id="cdx-hotbox" class="cdx-hotbox" hidden>
        <input id="cdx-hotbox-in" type="text" placeholder="e.g. CO2Et, Boc, R1, [N,O]" />
        <button type="button" class="cdx-ibtn is-active" id="cdx-hotbox-ok" style="height:23px;padding:0 7px">OK</button>
      </div>
    </div>

    <!-- Right Vertical Docked Element, Periodic Table & Query Generics Bar -->
    <div class="cdx-right" role="toolbar" aria-label="Elements and Query Generics">
      <button type="button" class="cdx-elbtn is-active" data-elem="C" style="color:#0f172a">C</button>
      <button type="button" class="cdx-elbtn" data-elem="H" style="color:#475569">H</button>
      <button type="button" class="cdx-elbtn" data-elem="N" style="color:#1d4ed8">N</button>
      <button type="button" class="cdx-elbtn" data-elem="O" style="color:#dc2626">O</button>
      <button type="button" class="cdx-elbtn" data-elem="S" style="color:#b45309">S</button>
      <button type="button" class="cdx-elbtn" data-elem="P" style="color:#ea580c">P</button>
      <button type="button" class="cdx-elbtn" data-elem="F" style="color:#15803d">F</button>
      <button type="button" class="cdx-elbtn" data-elem="Cl" style="color:#15803d">Cl</button>
      <button type="button" class="cdx-elbtn" data-elem="Br" style="color:#9a3412">Br</button>
      <button type="button" class="cdx-elbtn" data-elem="I" style="color:#6d28d9">I</button>
      <button type="button" class="cdx-elbtn" data-elem="B" style="color:#be123c">B</button>
      <button type="button" class="cdx-elbtn" data-elem="Si" style="color:#0f766e">Si</button>
      <span class="cdx-hsep"></span>
      <button type="button" class="cdx-elbtn" id="cdx-open-pt" title="Full 118-Element Periodic Table & Isotopes" style="font-size:10px;border:1px solid var(--cdx-border)">PT…</button>
      <button type="button" class="cdx-elbtn" id="cdx-open-qry" title="Reaxys / SciFinder Query Generics (A, Q, X, M, R1..R6, Atom Lists & Locks)" style="font-size:10px;color:#7c3aed;border:1px solid var(--cdx-border)">R/Q…</button>
    </div>
  </div>

  <!-- BOTTOM DOCKED RING & SCAFFOLD TEMPLATE BAR (MarvinJS / SciFinder style) -->
  <div class="cdx-rings" id="cdx-rings-bar" role="toolbar" aria-label="Ring and Scaffold Templates">
    <button type="button" class="cdx-rbtn" data-ring="c3" title="Cyclopropane (click bond to fuse)">
      <svg viewBox="0 0 22 22"><polygon points="11,4 18,17 4,17"/></svg>
    </button>
    <button type="button" class="cdx-rbtn" data-ring="c4" title="Cyclobutane (click bond to fuse)">
      <svg viewBox="0 0 22 22"><rect x="5" y="5" width="12" height="12"/></svg>
    </button>
    <button type="button" class="cdx-rbtn" data-ring="c5" title="Cyclopentane (click bond to fuse)">
      <svg viewBox="0 0 22 22"><polygon points="11,3.5 18.5,9 15.6,18 6.4,18 3.5,9"/></svg>
    </button>
    <button type="button" class="cdx-rbtn" data-ring="cpdiene" title="Cyclopentadiene">
      <svg viewBox="0 0 22 22"><polygon points="11,3.5 18.5,9 15.6,18 6.4,18 3.5,9"/><line x1="6.3" y1="9.8" x2="8.2" y2="15.8"/><line x1="15.7" y1="9.8" x2="13.8" y2="15.8"/></svg>
    </button>
    <button type="button" class="cdx-rbtn" data-ring="c6" title="Cyclohexane (click bond to fuse)">
      <svg viewBox="0 0 22 22"><polygon points="11,3 18,7 18,15 11,19 4,15 4,7"/></svg>
    </button>
    <button type="button" class="cdx-rbtn" data-ring="benzene" title="Benzene (B) - Hover bond to preview ring fusion!">
      <svg viewBox="0 0 22 22"><polygon points="11,3 18,7 18,15 11,19 4,15 4,7"/><circle cx="11" cy="11" r="4.2"/></svg>
    </button>
    <button type="button" class="cdx-rbtn" data-ring="c7" title="Cycloheptane (7-membered)">
      <svg viewBox="0 0 22 22"><polygon points="11,2.8 17.4,5.9 19,12.8 14.5,18.4 7.5,18.4 3,12.8 4.6,5.9"/></svg>
    </button>
    <button type="button" class="cdx-rbtn" data-ring="c8" title="Cyclooctane (8-membered)">
      <svg viewBox="0 0 22 22"><polygon points="8,3 14,3 19,8 19,14 14,19 8,19 3,14 3,8"/></svg>
    </button>
    <span class="cdx-sep"></span>
    <button type="button" class="cdx-rbtn" data-ring="naphthalene" title="Naphthalene (6,6-fused)">
      <svg viewBox="0 0 26 20"><polygon points="7,3 13,6.5 13,13.5 7,17 1.5,13.5 1.5,6.5"/><polygon points="13,6.5 19,3 24.5,6.5 24.5,13.5 19,17 13,13.5"/><circle cx="7.2" cy="10" r="2.7"/><circle cx="18.8" cy="10" r="2.7"/></svg>
    </button>
    <button type="button" class="cdx-rbtn" data-ring="indole" title="Indole (6,5-fused)">
      <svg viewBox="0 0 26 20"><polygon points="6.5,3 12.5,6.5 12.5,13.5 6.5,17 1,13.5 1,6.5"/><polyline points="12.5,6.5 19.5,4.5 23.5,10 19.5,15.5 12.5,13.5"/><circle cx="6.8" cy="10" r="2.6"/><text x="19" y="18.5" font-size="6.5" fill="currentColor" stroke="none">N</text></svg>
    </button>
    <button type="button" class="cdx-rbtn" data-ring="pyridine" title="Pyridine">
      <svg viewBox="0 0 22 22"><polygon points="11,3 18,7 18,15 11,18.5 4,15 4,7"/><circle cx="11" cy="10.8" r="3.8"/><text x="18" y="19.5" font-size="7" font-weight="700" fill="#1d4ed8" stroke="none">N</text></svg>
    </button>
    <button type="button" class="cdx-rbtn" data-ring="pyrimidine" title="Pyrimidine">
      <svg viewBox="0 0 22 22"><polygon points="11,3 18,7 18,15 11,18.5 4,15 4,7"/><circle cx="11" cy="10.8" r="3.6"/><text x="18" y="8" font-size="6.5" font-weight="700" fill="#1d4ed8" stroke="none">N</text><text x="18" y="19.5" font-size="6.5" font-weight="700" fill="#1d4ed8" stroke="none">N</text></svg>
    </button>
    <button type="button" class="cdx-rbtn" data-ring="pyrrole" title="Pyrrole">
      <svg viewBox="0 0 22 22"><polyline points="8.5,5.5 4,10 6.5,17.5 15.5,17.5 18,10 13.5,5.5"/><text x="11" y="7" text-anchor="middle" font-size="7" font-weight="700" fill="#1d4ed8" stroke="none">N</text></svg>
    </button>
    <button type="button" class="cdx-rbtn" data-ring="furan" title="Furan">
      <svg viewBox="0 0 22 22"><polyline points="8.5,5.5 4,10 6.5,17.5 15.5,17.5 18,10 13.5,5.5"/><text x="11" y="7" text-anchor="middle" font-size="7" font-weight="700" fill="#dc2626" stroke="none">O</text></svg>
    </button>
    <button type="button" class="cdx-rbtn" data-ring="thiophene" title="Thiophene">
      <svg viewBox="0 0 22 22"><polyline points="8.5,5.5 4,10 6.5,17.5 15.5,17.5 18,10 13.5,5.5"/><text x="11" y="7" text-anchor="middle" font-size="7" font-weight="700" fill="#b45309" stroke="none">S</text></svg>
    </button>
    <span class="cdx-sep"></span>
    <button type="button" class="cdx-rbtn" data-ring="chair1" title="Chair Cyclohexane">
      <svg viewBox="0 0 26 20"><polygon points="2,14 9,8 17,12 24,6 17,12 9,8" fill="none"/><polygon points="2,14 9,7 17,11 24,6 17,13 9,9"/></svg>
    </button>
    <button type="button" class="cdx-rbtn" data-ring="chair2" title="Flipped Chair Cyclohexane">
      <svg viewBox="0 0 26 20"><polygon points="2,6 9,13 17,9 24,14 17,7 9,11"/></svg>
    </button>
    <button type="button" class="cdx-rbtn" data-ring="norbornane" title="Bicyclo[2.2.1]heptane (Norbornane)">
      <svg viewBox="0 0 24 22"><polygon points="3,12 8,17 16,17 21,12 16,8 8,8"/><polyline points="3,12 12,3 21,12"/></svg>
    </button>
  </div>

  <!-- BOTTOM LIVE METRICS + REAXYS/SCIFINDER QUERY MODE & TRANSFER BAR -->
  <div class="cdx-status">
    <div class="cdx-metrics">
      <strong id="cdx-m-formula">—</strong>
      <span style="color:var(--cdx-muted)">Exact <b id="cdx-m-exact" style="color:var(--cdx-fg)">0.0000</b></span>
      <span style="color:var(--cdx-muted)">MW <b id="cdx-m-mw" style="color:var(--cdx-fg)">0.00</b></span>
      <span style="color:var(--cdx-muted)">DBE <b id="cdx-m-dbe" style="color:var(--cdx-fg)">0</b></span>
      <span class="cdx-smi-chip" id="cdx-m-smi" title="Live SMILES / SMARTS">Empty canvas</span>
    </div>
    <div style="display:flex;align-items:center;gap:5px;flex-wrap:wrap">
      <select id="cdx-query-mode" class="cdx-select" title="Reaxys / SciFinder Search & Agent Interpretation Mode">
        <option value="exact">As Drawn / Exact</option>
        <option value="substructure">Substructure Query</option>
        <option value="similarity">Similarity Search</option>
        <option value="reaction">Reaction / Transformation</option>
      </select>
      <button type="button" class="cdx-ibtn" id="cdx-btn-cdxml" style="border:1px solid var(--cdx-border);padding:0 7px" title="Download ACS 1996 .cdxml">.cdxml</button>
      <button type="button" class="cdx-ibtn" id="cdx-btn-mol" style="border:1px solid var(--cdx-border);padding:0 7px" title="Download MDL Molfile V2000 .mol">.mol</button>
      <button type="button" class="cdx-ibtn" id="cdx-btn-3d" style="border:1px solid var(--cdx-border);padding:0 7px" title="Inspect in 3D Mol*">3D Mol*</button>
      <button type="button" class="cdx-cta" id="cdx-btn-send">Transfer to Agent</button>
    </div>
  </div>

  <!-- MODAL BACKDROP (Periodic Table / Query Generics / Import-Export / Templates) -->
  <div id="cdx-backdrop" class="cdx-modal-backdrop" hidden>
    <div id="cdx-modal" class="cdx-modal" role="dialog" aria-modal="true"></div>
  </div>

<script>
(() => {{
  const INITIAL = {initial_json};
  const CATALOG = {catalog_json};
  const root = document.getElementById("cdx-studio-root");
  const svg = document.getElementById("cdx-svg");
  const stageWrap = document.getElementById("cdx-stage-wrap");
  const flyoutEl = document.getElementById("cdx-flyout");
  const backdropEl = document.getElementById("cdx-backdrop");
  const modalEl = document.getElementById("cdx-modal");
  const hotboxEl = document.getElementById("cdx-hotbox");
  const hotboxIn = document.getElementById("cdx-hotbox-in");
  const hostBridge = window["open" + "ai"] || window["z" + "code"] || null;

  const MASS = {{H:1.00794,D:2.0141,T:3.01605,He:4.0026,Li:6.941,Be:9.0122,B:10.811,C:12.0107,N:14.0067,O:15.9994,F:18.9984,Ne:20.1797,Na:22.9898,Mg:24.305,Al:26.9815,Si:28.0855,P:30.9738,S:32.065,Cl:35.453,K:39.0983,Ca:40.078,Sc:44.956,Ti:47.867,V:50.942,Cr:51.996,Mn:54.938,Fe:55.845,Co:58.933,Ni:58.693,Cu:63.546,Zn:65.38,Ga:69.723,Ge:72.64,As:74.922,Se:78.96,Br:79.904,Rb:85.468,Sr:87.62,Y:88.906,Zr:91.224,Mo:95.96,Ru:101.07,Rh:102.906,Pd:106.42,Ag:107.868,Cd:112.41,In:114.818,Sn:118.71,Sb:121.76,Te:127.6,I:126.904,Cs:132.905,Ba:137.327,W:183.84,Re:186.207,Os:190.23,Ir:192.217,Pt:195.084,Au:196.967,Hg:200.59,Tl:204.38,Pb:207.2,Bi:208.98}};
  const EXACT = {{H:1.007825,D:2.014102,T:3.016049,Li:7.016004,B:11.009305,C:12.0,N:14.003074,O:15.994915,F:18.998403,Na:22.989769,Mg:23.985042,Al:26.981539,Si:27.976927,P:30.973762,S:31.972071,Cl:34.968853,K:38.963707,Ca:39.962591,Fe:55.934937,Co:58.933195,Ni:57.935343,Cu:62.929597,Zn:63.929142,Se:79.916522,Br:78.918338,Ru:101.904349,Rh:102.905504,Pd:105.903486,Ag:106.905097,Sn:119.902195,I:126.904473,Cs:132.905452,Pt:194.964791,Au:196.966569}};
  const VALENCE = {{H:1,D:1,T:1,B:3,C:4,N:3,O:2,F:1,Si:4,P:3,S:2,Cl:1,As:3,Se:2,Br:1,Te:2,I:1}};
  const CPK = {{C:"#0f172a",H:"#475569",N:"#1d4ed8",O:"#dc2626",S:"#b45309",P:"#ea580c",F:"#15803d",Cl:"#15803d",Br:"#9a3412",I:"#6d28d9",B:"#be123c",Si:"#0f766e",Li:"#7c3aed",Na:"#7c3aed",K:"#7c3aed",Mg:"#047857",Fe:"#b45309",Pd:"#0369a1",Cu:"#b45309",Zn:"#475569",A:"#7c3aed",Q:"#7c3aed",X:"#059669",M:"#0369a1","*":"#dc2626"}};
  const ELEM_Z = {{H:1,He:2,Li:3,Be:4,B:5,C:6,N:7,O:8,F:9,Ne:10,Na:11,Mg:12,Al:13,Si:14,P:15,S:16,Cl:17,Ar:18,K:19,Ca:20,Sc:21,Ti:22,V:23,Cr:24,Mn:25,Fe:26,Co:27,Ni:28,Cu:29,Zn:30,Ga:31,Ge:32,As:33,Se:34,Br:35,Kr:36,Rb:37,Sr:38,Y:39,Zr:40,Nb:41,Mo:42,Tc:43,Ru:44,Rh:45,Pd:46,Ag:47,Cd:48,In:49,Sn:50,Sb:51,Te:52,I:53,Xe:54,Cs:55,Ba:56,La:57,Ce:58,Pr:59,Nd:60,Sm:62,Eu:63,Gd:64,Tb:65,Dy:66,Yb:70,Lu:71,Hf:72,Ta:73,W:74,Re:75,Os:76,Ir:77,Pt:78,Au:79,Hg:80,Tl:81,Pb:82,Bi:83}};
  const ABBR = {{
    Me:{{f:{{C:1,H:3}},smi:"C"}}, Et:{{f:{{C:2,H:5}},smi:"CC"}}, nPr:{{f:{{C:3,H:7}},smi:"CCC"}}, iPr:{{f:{{C:3,H:7}},smi:"C(C)C"}},
    nBu:{{f:{{C:4,H:9}},smi:"CCCC"}}, tBu:{{f:{{C:4,H:9}},smi:"C(C)(C)C"}}, Cy:{{f:{{C:6,H:11}},smi:"C1CCCCC1"}},
    Ph:{{f:{{C:6,H:5}},smi:"c1ccccc1"}}, Bn:{{f:{{C:7,H:7}},smi:"Cc1ccccc1"}}, Bz:{{f:{{C:7,H:5,O:1}},smi:"C(=O)c1ccccc1"}},
    Ac:{{f:{{C:2,H:3,O:1}},smi:"C(=O)C"}}, OAc:{{f:{{C:2,H:3,O:2}},smi:"OC(=O)C"}}, OMe:{{f:{{C:1,H:3,O:1}},smi:"OC"}},
    OEt:{{f:{{C:2,H:5,O:1}},smi:"OCC"}}, OTf:{{f:{{C:1,F:3,O:3,S:1}},smi:"OS(=O)(=O)C(F)(F)F"}}, OTs:{{f:{{C:7,H:7,O:3,S:1}},smi:"OS(=O)(=O)c1ccc(C)cc1"}},
    OMs:{{f:{{C:1,H:3,O:3,S:1}},smi:"OS(=O)(=O)C"}}, CF3:{{f:{{C:1,F:3}},smi:"C(F)(F)F"}}, CCl3:{{f:{{C:1,Cl:3}},smi:"C(Cl)(Cl)Cl"}},
    CN:{{f:{{C:1,N:1}},smi:"C#N"}}, CHO:{{f:{{C:1,H:1,O:1}},smi:"C=O"}}, COOH:{{f:{{C:1,H:1,O:2}},smi:"C(=O)O"}},
    CO2H:{{f:{{C:1,H:1,O:2}},smi:"C(=O)O"}}, CO2Me:{{f:{{C:2,H:3,O:2}},smi:"C(=O)OC"}}, CO2Et:{{f:{{C:3,H:5,O:2}},smi:"C(=O)OCC"}},
    CONH2:{{f:{{C:1,H:2,N:1,O:1}},smi:"C(=O)N"}}, NMe2:{{f:{{C:2,H:6,N:1}},smi:"N(C)C"}}, NEt2:{{f:{{C:4,H:10,N:1}},smi:"N(CC)CC"}},
    NO2:{{f:{{N:1,O:2}},smi:"[N+](=O)[O-]"}}, SO2Me:{{f:{{C:1,H:3,O:2,S:1}},smi:"S(=O)(=O)C"}},
    Boc:{{f:{{C:5,H:9,O:2}},smi:"C(=O)OC(C)(C)C"}}, NHBoc:{{f:{{C:5,H:10,N:1,O:2}},smi:"NC(=O)OC(C)(C)C"}},
    Cbz:{{f:{{C:8,H:7,O:2}},smi:"C(=O)OCc1ccccc1"}}, Fmoc:{{f:{{C:15,H:11,O:2}},smi:"C(=O)OCC1c2ccccc2-c2ccccc21"}},
    TMS:{{f:{{C:3,H:9,Si:1}},smi:"[Si](C)(C)C"}}, TBS:{{f:{{C:6,H:15,Si:1}},smi:"[Si](C)(C)C(C)(C)C"}}, OTBS:{{f:{{C:6,H:15,O:1,Si:1}},smi:"O[Si](C)(C)C(C)(C)C"}},
    TIPS:{{f:{{C:9,H:21,Si:1}},smi:"[Si](C(C)C)(C(C)C)C(C)C"}}, Bpin:{{f:{{B:1,C:6,H:12,O:2}},smi:"B1OC(C)(C)C(C)(C)O1"}}
  }};
  const LEFT_FLIP = {{COOH:"HOOC",CO2H:"HO2C",CO2Me:"MeO2C",CO2Et:"EtO2C",CHO:"OHC",CN:"NC",NO2:"O2N",OMe:"MeO",OEt:"EtO",OAc:"AcO",OTs:"TsO",OTf:"TfO",OMs:"MsO",OTBS:"TBSO",CF3:"F3C",NMe2:"Me2N",NHBoc:"BocHN",SO2Me:"MeO2S"}};

  // Periodic Table layout: [Z, Sym, row(1..9), col(1..18), catColor]
  const PT_DATA = [
    [1,"H",1,1,"#dbeafe"],[2,"He",1,18,"#f3e8ff"],
    [3,"Li",2,1,"#fee2e2"],[4,"Be",2,2,"#ffedd5"],[5,"B",2,13,"#fef3c7"],[6,"C",2,14,"#dcfce7"],[7,"N",2,15,"#dcfce7"],[8,"O",2,16,"#dcfce7"],[9,"F",2,17,"#d1fae5"],[10,"Ne",2,18,"#f3e8ff"],
    [11,"Na",3,1,"#fee2e2"],[12,"Mg",3,2,"#ffedd5"],[13,"Al",3,13,"#e2e8f0"],[14,"Si",3,14,"#fef3c7"],[15,"P",3,15,"#dcfce7"],[16,"S",3,16,"#dcfce7"],[17,"Cl",3,17,"#d1fae5"],[18,"Ar",3,18,"#f3e8ff"],
    [19,"K",4,1,"#fee2e2"],[20,"Ca",4,2,"#ffedd5"],[21,"Sc",4,3,"#e0f2fe"],[22,"Ti",4,4,"#e0f2fe"],[23,"V",4,5,"#e0f2fe"],[24,"Cr",4,6,"#e0f2fe"],[25,"Mn",4,7,"#e0f2fe"],[26,"Fe",4,8,"#e0f2fe"],[27,"Co",4,9,"#e0f2fe"],[28,"Ni",4,10,"#e0f2fe"],[29,"Cu",4,11,"#e0f2fe"],[30,"Zn",4,12,"#e0f2fe"],[31,"Ga",4,13,"#e2e8f0"],[32,"Ge",4,14,"#fef3c7"],[33,"As",4,15,"#fef3c7"],[34,"Se",4,16,"#dcfce7"],[35,"Br",4,17,"#d1fae5"],[36,"Kr",4,18,"#f3e8ff"],
    [37,"Rb",5,1,"#fee2e2"],[38,"Sr",5,2,"#ffedd5"],[39,"Y",5,3,"#e0f2fe"],[40,"Zr",5,4,"#e0f2fe"],[41,"Nb",5,5,"#e0f2fe"],[42,"Mo",5,6,"#e0f2fe"],[43,"Tc",5,7,"#e0f2fe"],[44,"Ru",5,8,"#e0f2fe"],[45,"Rh",5,9,"#e0f2fe"],[46,"Pd",5,10,"#e0f2fe"],[47,"Ag",5,11,"#e0f2fe"],[48,"Cd",5,12,"#e0f2fe"],[49,"In",5,13,"#e2e8f0"],[50,"Sn",5,14,"#e2e8f0"],[51,"Sb",5,15,"#fef3c7"],[52,"Te",5,16,"#fef3c7"],[53,"I",5,17,"#d1fae5"],[54,"Xe",5,18,"#f3e8ff"],
    [55,"Cs",6,1,"#fee2e2"],[56,"Ba",6,2,"#ffedd5"],[57,"La",6,3,"#fce7f3"],[72,"Hf",6,4,"#e0f2fe"],[73,"Ta",6,5,"#e0f2fe"],[74,"W",6,6,"#e0f2fe"],[75,"Re",6,7,"#e0f2fe"],[76,"Os",6,8,"#e0f2fe"],[77,"Ir",6,9,"#e0f2fe"],[78,"Pt",6,10,"#e0f2fe"],[79,"Au",6,11,"#e0f2fe"],[80,"Hg",6,12,"#e0f2fe"],[81,"Tl",6,13,"#e2e8f0"],[82,"Pb",6,14,"#e2e8f0"],[83,"Bi",6,15,"#e2e8f0"],[84,"Po",6,16,"#fef3c7"],[85,"At",6,17,"#d1fae5"],[86,"Rn",6,18,"#f3e8ff"],
    [58,"Ce",8,4,"#fce7f3"],[59,"Pr",8,5,"#fce7f3"],[60,"Nd",8,6,"#fce7f3"],[62,"Sm",8,7,"#fce7f3"],[63,"Eu",8,8,"#fce7f3"],[64,"Gd",8,9,"#fce7f3"],[65,"Tb",8,10,"#fce7f3"],[66,"Dy",8,11,"#fce7f3"],[70,"Yb",8,12,"#fce7f3"],[71,"Lu",8,13,"#fce7f3"]
  ];

  // Sub-tool definitions per left-dock slot
  const SUBTOOLS = {{
    select: [
      {{id:"sel-lasso", label:"Lasso Select (V)"}},
      {{id:"sel-box", label:"Rectangle Select"}},
      {{id:"sel-frag", label:"Whole Molecule"}}
    ],
    bond: [
      {{id:"bond-1", label:"Single Bond (1)"}},
      {{id:"bond-2", label:"Double Bond (2)"}},
      {{id:"bond-3", label:"Triple Bond (3)"}}
    ],
    stereo: [
      {{id:"st-wedge", label:"Up Wedge (W)"}},
      {{id:"st-hash", label:"Down Hash (H)"}},
      {{id:"st-wavy", label:"Either / Wavy (~)"}},
      {{id:"st-ez", label:"Cis/Trans Either (x)"}},
      {{id:"st-bold", label:"Bold Front Bond"}}
    ],
    qbond: [
      {{id:"qb-any", label:"Any Bond (Query)"}},
      {{id:"qb-12", label:"Single or Double"}},
      {{id:"qb-1a", label:"Single or Aromatic"}},
      {{id:"qb-2a", label:"Double or Aromatic"}},
      {{id:"qb-arom", label:"Aromatic Bond"}},
      {{id:"qb-coord", label:"Coordination (→)"}},
      {{id:"qb-hbond", label:"H-Bond (···)"}}
    ],
    charge: [
      {{id:"chg-plus", label:"Charge +1"}},
      {{id:"chg-minus", label:"Charge -1"}},
      {{id:"chg-rad", label:"Radical (• / ••)"}}
    ],
    rxn: [
      {{id:"rxn-solid", label:"Reaction Arrow →"}},
      {{id:"rxn-eq", label:"Equilibrium ⇌"}},
      {{id:"rxn-retro", label:"Retrosynthetic ⇒"}},
      {{id:"rxn-res", label:"Resonance ↔"}},
      {{id:"rxn-no", label:"No Reaction ↛"}},
      {{id:"rxn-plus", label:"Reaction Plus (+)"}},
      {{id:"rxn-map", label:"Atom Mapping [1]"}},
      {{id:"rxn-curv2", label:"2e- Curved Arrow ↷"}},
      {{id:"rxn-curv1", label:"1e- Fishhook ⇀"}}
    ],
    markush: [
      {{id:"mk-bracket", label:"Polymer [ ]n"}},
      {{id:"mk-var", label:"Variable Ring Pos"}},
      {{id:"mk-fill", label:"Ring Pastel Fill"}}
    ]
  }};

  const BOND_L = 34;
  const clone = (o) => JSON.parse(JSON.stringify(o));

  function normalizeGraph(raw) {{
    const g = clone(raw || {{}});
    g.atoms = Array.isArray(g.atoms) ? g.atoms : [];
    g.bonds = Array.isArray(g.bonds) ? g.bonds : [];
    g.arrows = Array.isArray(g.arrows) ? g.arrows : [];
    g.pluses = Array.isArray(g.pluses) ? g.pluses : [];
    g.texts = Array.isArray(g.texts) ? g.texts : [];
    g.curved = Array.isArray(g.curved) ? g.curved : [];
    g.brackets = Array.isArray(g.brackets) ? g.brackets : [];
    g.ring_fills = Array.isArray(g.ring_fills) ? g.ring_fills : [];
    g.circles = Array.isArray(g.circles) ? g.circles : [];
    g.spokes = Array.isArray(g.spokes) ? g.spokes : [];
    g.arom_circles = Boolean(g.arom_circles);
    return g;
  }}

  const state = {{
    graph: normalizeGraph(INITIAL.graph),
    style: INITIAL.style || "acs1996",
    styles: INITIAL.styles || {{acs1996:{{label:"ACS 1996 / JACS"}}}},
    slot: "bond",
    tool: "bond-1",
    activeSub: {{select:"sel-lasso", bond:"bond-1", stereo:"st-wedge", qbond:"qb-any", charge:"chg-plus", rxn:"rxn-solid", markush:"mk-bracket"}},
    ringTool: null,
    elem: "C",
    iso: 0,
    qLock: null,
    selAtoms: new Set(),
    clipboard: null,
    undoStack: [],
    redoStack: [],
    cam: {{x: 0, y: 0, w: 680, h: 356, zoom: 1}},
    hover: {{pt: null, ai: -1, bi: -1}},
    drag: null,
    nextMap: 1
  }};

  // Restore saved host widget state if present
  try {{
    const ws = hostBridge && hostBridge.widgetState;
    if (ws && ws.privateContent && ws.privateContent.graph) {{
      state.graph = normalizeGraph(ws.privateContent.graph);
    }}
  }} catch (_e) {{}}

  const styleSel = document.getElementById("cdx-style-sel");
  Object.entries(state.styles).forEach(([k, v]) => {{
    const opt = document.createElement("option");
    opt.value = k; opt.textContent = v.label || k;
    if (k === state.style) opt.selected = true;
    styleSel.appendChild(opt);
  }});
  styleSel.addEventListener("change", () => {{ state.style = styleSel.value; render(); syncHostState(); }});

  function setToast(msg) {{ document.getElementById("cdx-toast").textContent = msg; }}
  function pushUndo() {{
    state.undoStack.push(clone(state.graph));
    if (state.undoStack.length > 60) state.undoStack.shift();
    state.redoStack.length = 0;
  }}

  function updateViewBox() {{
    svg.setAttribute("viewBox", `${{state.cam.x.toFixed(1)}} ${{state.cam.y.toFixed(1)}} ${{state.cam.w.toFixed(1)}} ${{state.cam.h.toFixed(1)}}`);
    document.getElementById("cdx-z-fit").textContent = Math.round(state.cam.zoom * 100) + "%";
  }}

  function svgPoint(ev) {{
    const pt = svg.createSVGPoint();
    pt.x = ev.clientX; pt.y = ev.clientY;
    const ctm = svg.getScreenCTM();
    if (!ctm) return {{x: 340, y: 178}};
    const p = pt.matrixTransform(ctm.inverse());
    return {{x: p.x, y: p.y}};
  }}

  function hitAtom(g, p, tol = 12) {{
    const r2 = (tol / state.cam.zoom) ** 2;
    let best = -1, bd = r2;
    g.atoms.forEach((a, i) => {{
      const d = (a.x - p.x) ** 2 + (a.y - p.y) ** 2;
      if (d < bd) {{ bd = d; best = i; }}
    }});
    return best;
  }}

  function hitBond(g, p, tol = 8.5) {{
    const lim = tol / state.cam.zoom;
    let best = -1, bd = lim;
    g.bonds.forEach((b, i) => {{
      const A = g.atoms[b.a], B = g.atoms[b.b];
      if (!A || !B) return;
      const dx = B.x - A.x, dy = B.y - A.y, l2 = dx * dx + dy * dy || 1;
      const t = Math.max(0.08, Math.min(0.92, ((p.x - A.x) * dx + (p.y - A.y) * dy) / l2));
      const d = Math.hypot(p.x - (A.x + t * dx), p.y - (A.y + t * dy));
      if (d < bd) {{ bd = d; best = i; }}
    }});
    return best;
  }}

  function bondExists(g, u, v) {{
    return g.bonds.findIndex((b) => (b.a === u && b.b === v) || (b.a === v && b.b === u));
  }}

  function neighbors(g, ai) {{
    const out = [];
    g.bonds.forEach((b, bi) => {{
      if (b.a === ai) out.push({{to: b.b, bi, b}});
      else if (b.b === ai) out.push({{to: b.a, bi, b}});
    }});
    return out;
  }}

  function sproutAngle(g, ai, newOrder) {{
    const nb = neighbors(g, ai);
    const a = g.atoms[ai];
    if (nb.length === 0) return -Math.PI / 6;
    if (nb.length === 1) {{
      const other = g.atoms[nb[0].to];
      const inAng = Math.atan2(a.y - other.y, a.x - other.x);
      if (newOrder === 3 || nb[0].b.o === 3) return inAng; // linear sp 180 deg!
      // Choose +/- 60 deg from incoming vector (= 120 deg internal angle)
      const n2 = neighbors(g, nb[0].to).filter((x) => x.to !== ai);
      if (n2.length > 0) {{
        const ref = g.atoms[n2[0].to];
        const cross = (a.x - other.x) * (ref.y - other.y) - (a.y - other.y) * (ref.x - other.x);
        return inAng + (cross >= 0 ? Math.PI / 3 : -Math.PI / 3);
      }}
      return inAng + (Math.cos(inAng) >= 0 ? -Math.PI / 3 : Math.PI / 3);
    }}
    const angs = nb.map((x) => Math.atan2(g.atoms[x.to].y - a.y, g.atoms[x.to].x - a.x)).sort((x, y) => x - y);
    let bestGap = -1, bestMid = 0;
    for (let i = 0; i < angs.length; i++) {{
      const a1 = angs[i], a2 = i + 1 < angs.length ? angs[i + 1] : angs[0] + Math.PI * 2;
      const gap = a2 - a1;
      if (gap > bestGap) {{ bestGap = gap; bestMid = a1 + gap / 2; }}
    }}
    return bestMid;
  }}

  function findSmallRings(g) {{
    const adj = g.atoms.map(() => []);
    g.bonds.forEach((b) => {{
      if (b.a < g.atoms.length && b.b < g.atoms.length && !b.q) {{
        adj[b.a].push(b.b); adj[b.b].push(b.a);
      }}
    }});
    const rings = [], seen = new Set();
    for (let s = 0; s < g.atoms.length; s++) {{
      const dfs = (u, path) => {{
        if (path.length > 8) return;
        for (const v of adj[u]) {{
          if (v === s && path.length >= 3) {{
            const key = [...path].sort((a, b) => a - b).join(",");
            if (!seen.has(key)) {{ seen.add(key); rings.push([...path]); }}
          }} else if (v > s && !path.includes(v)) {{
            dfs(v, [...path, v]);
          }}
        }}
      }};
      dfs(s, [s]);
    }}
    return rings.sort((a, b) => a.length - b.length);
  }}

  // Ring definitions for free placement, spiro attachment, and bond fusion
  function ringSpec(kind) {{
    const map = {{
      c3: {{n:3, arom:false}}, c4: {{n:4, arom:false}}, c5: {{n:5, arom:false}},
      cpdiene: {{n:5, dbl:[1,3]}}, c6: {{n:6, arom:false}}, benzene: {{n:6, arom:true}},
      c7: {{n:7, arom:false}}, c8: {{n:8, arom:false}},
      pyridine: {{n:6, arom:true, het:{{2:"N"}}}}, pyrimidine: {{n:6, arom:true, het:{{1:"N",3:"N"}}}},
      pyrrole: {{n:5, dbl:[1,3], het:{{0:"N"}}}}, furan: {{n:5, dbl:[1,3], het:{{0:"O"}}}}, thiophene: {{n:5, dbl:[1,3], het:{{0:"S"}}}}
    }};
    return map[kind] || null;
  }}

  function buildSpecialRing(kind, cx, cy) {{
    const atoms = [], bonds = [];
    if (kind === "naphthalene") {{
      const r = BOND_L;
      const lx = cx - r * Math.cos(Math.PI / 6), rx = cx + r * Math.cos(Math.PI / 6);
      for (let k = 0; k < 6; k++) {{
        const a = -Math.PI / 2 + (k * Math.PI) / 3;
        atoms.push({{s:"C", x:+(lx + Math.cos(a)*r).toFixed(2), y:+(cy + Math.sin(a)*r).toFixed(2)}});
      }}
      [[0,1,2],[1,2,1],[2,3,2],[3,4,1],[4,5,2],[5,0,1]].forEach(([u,v,o]) => bonds.push({{a:u,b:v,o}}));
      const extra = [-Math.PI/6, Math.PI/6, Math.PI/2, -Math.PI/2];
      const p0 = {{s:"C", x:+(rx + Math.cos(-Math.PI/2)*r).toFixed(2), y:+(cy + Math.sin(-Math.PI/2)*r).toFixed(2)}};
      const p1 = {{s:"C", x:+(rx + Math.cos(-Math.PI/6)*r).toFixed(2), y:+(cy + Math.sin(-Math.PI/6)*r).toFixed(2)}};
      const p2 = {{s:"C", x:+(rx + Math.cos(Math.PI/6)*r).toFixed(2), y:+(cy + Math.sin(Math.PI/6)*r).toFixed(2)}};
      const p3 = {{s:"C", x:+(rx + Math.cos(Math.PI/2)*r).toFixed(2), y:+(cy + Math.sin(Math.PI/2)*r).toFixed(2)}};
      atoms.push(p0, p1, p2, p3);
      bonds.push({{a:1,b:6,o:1}},{{a:6,b:7,o:2}},{{a:7,b:8,o:1}},{{a:8,b:9,o:2}},{{a:9,b:2,o:1}});
      void extra;
      return {{atoms, bonds}};
    }}
    if (kind === "indole") {{
      const base = buildSpecialRing("naphthalene", cx, cy);
      // Convert right 6-ring into 5-membered pyrrole ring fused on bond 1-2
      const A = base.atoms[1], B = base.atoms[2];
      const mx = (A.x + B.x)/2, my = (A.y + B.y)/2;
      const ap = BOND_L / (2 * Math.tan(Math.PI / 5)), R5 = BOND_L / (2 * Math.sin(Math.PI / 5));
      const rcx = mx + ap, rcy = my;
      const angB = Math.atan2(B.y - rcy, B.x - rcx);
      const step = -(2 * Math.PI) / 5;
      const a6 = {{s:"N", x:+(rcx + Math.cos(angB + step)*R5).toFixed(2), y:+(rcy + Math.sin(angB + step)*R5).toFixed(2)}};
      const a7 = {{s:"C", x:+(rcx + Math.cos(angB + step*2)*R5).toFixed(2), y:+(rcy + Math.sin(angB + step*2)*R5).toFixed(2)}};
      const a8 = {{s:"C", x:+(rcx + Math.cos(angB + step*3)*R5).toFixed(2), y:+(rcy + Math.sin(angB + step*3)*R5).toFixed(2)}};
      return {{
        atoms: [...base.atoms.slice(0, 6), a6, a7, a8],
        bonds: [...base.bonds.slice(0, 6), {{a:2,b:6,o:1}}, {{a:6,b:7,o:1}}, {{a:7,b:8,o:2}}, {{a:8,b:1,o:1}}]
      }};
    }}
    if (kind === "chair1" || kind === "chair2") {{
      const f = kind === "chair2" ? -1 : 1;
      const pts = [[-44, 12*f], [-16, -12*f], [18, 8*f], [44, -12*f], [16, 12*f], [-18, -8*f]];
      pts.forEach(([dx, dy]) => atoms.push({{s:"C", x:+(cx + dx).toFixed(2), y:+(cy + dy).toFixed(2)}}));
      // Correct chair perimeter: 0-1-5? Let's use clean standard ChemDraw chair coordinates:
      atoms.length = 0;
      const cPts = kind === "chair1"
        ? [[-44,14],[-14,-6],[22,10],[44,-14],[14,6],[-22,-10]]
        : [[-44,-14],[-14,6],[22,-10],[44,14],[14,-6],[-22,10]];
      cPts.forEach(([dx, dy]) => atoms.push({{s:"C", x:+(cx + dx).toFixed(2), y:+(cy + dy).toFixed(2)}}));
      for (let k = 0; k < 6; k++) bonds.push({{a:k, b:(k+1)%6, o:1}});
      return {{atoms, bonds}};
    }}
    if (kind === "norbornane") {{
      const nPts = [[-30,18],[0,28],[30,18],[22,-8],[-22,-8],[0,-28],[0,2]];
      nPts.forEach(([dx, dy]) => atoms.push({{s:"C", x:+(cx + dx).toFixed(2), y:+(cy + dy).toFixed(2)}}));
      [[0,1],[1,2],[2,3],[3,4],[4,0],[0,6],[2,6],[6,5]].forEach(([u,v]) => bonds.push({{a:u,b:v,o:1}}));
      bonds.pop(); bonds.pop(); bonds.pop();
      // Classic bicyclo[2.2.1]heptane bridgehead at 0 & 3:
      atoms.length = 0; bonds.length = 0;
      [[-32,10],[-12,26],[18,26],[34,10],[16,-10],[-14,-10],[1,-28]].forEach(([dx, dy]) => atoms.push({{s:"C", x:+(cx + dx).toFixed(2), y:+(cy + dy).toFixed(2)}}));
      [[0,1],[1,2],[2,3],[3,4],[4,5],[5,0],[0,6],[3,6]].forEach(([u,v]) => bonds.push({{a:u,b:v,o:1}}));
      return {{atoms, bonds}};
    }}
    return null;
  }}

  function computeRingFusionPreview(g, bi, kind, cursorPt) {{
    const spec = ringSpec(kind);
    if (!spec) return null;
    const n = spec.n;
    const b = g.bonds[bi];
    const A = g.atoms[b.a], B = g.atoms[b.b];
    const mx = (A.x + B.x) / 2, my = (A.y + B.y) / 2;
    const dx = B.x - A.x, dy = B.y - A.y, len = Math.hypot(dx, dy) || BOND_L;
    let nx = -dy / len, ny = dx / len;
    if (cursorPt) {{
      const side = (cursorPt.x - mx) * nx + (cursorPt.y - my) * ny;
      if (Math.abs(side) > 2) {{
        if (side < 0) {{ nx = -nx; ny = -ny; }}
      }} else {{
        let sc = 0;
        g.bonds.forEach((ob, idx) => {{
          if (idx === bi) return;
          if (ob.a === b.a || ob.b === b.a || ob.a === b.b || ob.b === b.b) {{
            const other = g.atoms[(ob.a === b.a || ob.a === b.b) ? ob.b : ob.a];
            sc += (other.x - mx) * nx + (other.y - my) * ny;
          }}
        }});
        if (sc > 0) {{ nx = -nx; ny = -ny; }}
      }}
    }}
    const apothem = len / (2 * Math.tan(Math.PI / n));
    const R = len / (2 * Math.sin(Math.PI / n));
    const cx = mx + nx * apothem, cy = my + ny * apothem;
    const angB = Math.atan2(B.y - cy, B.x - cx);
    const cross = (A.x - cx) * (B.y - cy) - (A.y - cy) * (B.x - cx);
    const step = (cross >= 0 ? 1 : -1) * ((2 * Math.PI) / n);
    const pts = [{{x: A.x, y: A.y, existing: b.a, s: A.s}}, {{x: B.x, y: B.y, existing: b.b, s: B.s}}];
    for (let k = 1; k <= n - 2; k++) {{
      const ang = angB + step * k;
      const px = +(cx + Math.cos(ang) * R).toFixed(2);
      const py = +(cy + Math.sin(ang) * R).toFixed(2);
      const ex = hitAtom(g, {{x: px, y: py}}, 9);
      const sym = (spec.het && spec.het[k + 1]) || "C";
      pts.push({{x: ex >= 0 ? g.atoms[ex].x : px, y: ex >= 0 ? g.atoms[ex].y : py, existing: ex, s: sym}});
    }}
    return {{pts, spec, bi}};
  }}

  function fuseRingOnBond(g, bi, kind, cursorPt) {{
    const plan = computeRingFusionPreview(g, bi, kind, cursorPt);
    if (!plan) return;
    const idxs = plan.pts.map((p, idx) => {{
      if (idx < 2) return p.existing;
      if (p.existing >= 0) return p.existing;
      g.atoms.push({{s: p.s || "C", x: p.x, y: p.y}});
      return g.atoms.length - 1;
    }});
    const sharedOrder = g.bonds[bi].o;
    for (let k = 1; k < idxs.length; k++) {{
      const u = idxs[k], v = idxs[(k + 1) % idxs.length];
      if (bondExists(g, u, v) < 0) {{
        let ord = 1;
        if (plan.spec.arom) ord = (sharedOrder === 2 ? k % 2 === 0 : k % 2 === 1) ? 2 : 1;
        else if (plan.spec.dbl && plan.spec.dbl.includes(k)) ord = 2;
        g.bonds.push({{a: u, b: v, o: ord}});
      }}
    }}
  }}

  function placeRing(g, kind, pt, ai, bi) {{
    if (bi >= 0 && ringSpec(kind)) {{
      fuseRingOnBond(g, bi, kind, pt);
      return;
    }}
    const special = buildSpecialRing(kind, pt.x, pt.y);
    if (special) {{
      const off = g.atoms.length;
      if (ai >= 0) {{
        const dx = g.atoms[ai].x - special.atoms[0].x, dy = g.atoms[ai].y - special.atoms[0].y;
        special.atoms.forEach((a, idx) => {{
          if (idx === 0) return;
          g.atoms.push({{s: a.s, x: +(a.x + dx).toFixed(2), y: +(a.y + dy).toFixed(2)}});
        }});
        special.bonds.forEach((b) => {{
          const ua = b.a === 0 ? ai : off + b.a - 1;
          const ub = b.b === 0 ? ai : off + b.b - 1;
          if (bondExists(g, ua, ub) < 0) g.bonds.push({{a: ua, b: ub, o: b.o}});
        }});
      }} else {{
        special.atoms.forEach((a) => g.atoms.push(a));
        special.bonds.forEach((b) => g.bonds.push({{a: b.a + off, b: b.b + off, o: b.o}}));
      }}
      return;
    }}
    const spec = ringSpec(kind) || {{n: 6, arom: true}};
    const n = spec.n;
    const R = BOND_L / (2 * Math.sin(Math.PI / n));
    let cx = pt.x, cy = pt.y, startAng = -Math.PI / 2;
    let spiroIdx = -1;
    if (ai >= 0) {{
      spiroIdx = ai;
      const outAng = sproutAngle(g, ai, 1);
      cx = g.atoms[ai].x + Math.cos(outAng) * R;
      cy = g.atoms[ai].y + Math.sin(outAng) * R;
      startAng = Math.atan2(g.atoms[ai].y - cy, g.atoms[ai].x - cx);
    }}
    const idxs = [];
    for (let k = 0; k < n; k++) {{
      if (k === 0 && spiroIdx >= 0) {{
        if (spec.het && spec.het[0] && g.atoms[spiroIdx].s === "C") g.atoms[spiroIdx].s = spec.het[0];
        idxs.push(spiroIdx);
        continue;
      }}
      const ang = startAng + (2 * Math.PI * k) / n;
      const px = +(cx + Math.cos(ang) * R).toFixed(2);
      const py = +(cy + Math.sin(ang) * R).toFixed(2);
      const ex = hitAtom(g, {{x: px, y: py}}, 8);
      if (ex >= 0) idxs.push(ex);
      else {{
        g.atoms.push({{s: (spec.het && spec.het[k]) || "C", x: px, y: py}});
        idxs.push(g.atoms.length - 1);
      }}
    }}
    for (let k = 0; k < n; k++) {{
      const u = idxs[k], v = idxs[(k + 1) % n];
      if (bondExists(g, u, v) < 0) {{
        const ord = spec.arom ? (k % 2 === 0 ? 2 : 1) : (spec.dbl && spec.dbl.includes(k) ? 2 : 1);
        g.bonds.push({{a: u, b: v, o: ord}});
      }}
    }}
  }}

  // 2D Structure Coordinate Cleanup (Ring polygon regularization + bond length & overlap relaxation)
  function clean2D(g) {{
    if (g.atoms.length < 2) return;
    pushUndo();
    const rings = findSmallRings(g);
    const locked = new Set();
    rings.forEach((r) => {{
      const n = r.length;
      const cx = r.reduce((s, i) => s + g.atoms[i].x, 0) / n;
      const cy = r.reduce((s, i) => s + g.atoms[i].y, 0) / n;
      const R = BOND_L / (2 * Math.sin(Math.PI / n));
      const a0 = Math.atan2(g.atoms[r[0]].y - cy, g.atoms[r[0]].x - cx);
      const a1 = Math.atan2(g.atoms[r[1]].y - cy, g.atoms[r[1]].x - cx);
      let diff = a1 - a0;
      while (diff > Math.PI) diff -= Math.PI * 2;
      while (diff < -Math.PI) diff += Math.PI * 2;
      const step = (diff >= 0 ? 1 : -1) * ((2 * Math.PI) / n);
      // Snap orientation to nearest 15 degrees
      const snap0 = Math.round(a0 / (Math.PI / 12)) * (Math.PI / 12);
      r.forEach((ai, k) => {{
        if (!locked.has(ai)) {{
          const ang = snap0 + step * k;
          g.atoms[ai].x = +(cx + Math.cos(ang) * R).toFixed(2);
          g.atoms[ai].y = +(cy + Math.sin(ang) * R).toFixed(2);
          locked.add(ai);
        }}
      }});
    }});
    for (let iter = 0; iter < 45; iter++) {{
      const fx = new Float64Array(g.atoms.length);
      const fy = new Float64Array(g.atoms.length);
      g.bonds.forEach((b) => {{
        const A = g.atoms[b.a], B = g.atoms[b.b];
        const dx = B.x - A.x, dy = B.y - A.y, d = Math.hypot(dx, dy) || 0.1;
        const err = (d - BOND_L) * 0.35;
        const ux = dx / d, uy = dy / d;
        if (!locked.has(b.a)) {{ fx[b.a] += ux * err; fy[b.a] += uy * err; }}
        if (!locked.has(b.b)) {{ fx[b.b] -= ux * err; fy[b.b] -= uy * err; }}
      }});
      for (let i = 0; i < g.atoms.length; i++) {{
        for (let j = i + 1; j < g.atoms.length; j++) {{
          const dx = g.atoms[j].x - g.atoms[i].x, dy = g.atoms[j].y - g.atoms[i].y;
          const d2 = dx * dx + dy * dy;
          if (d2 < (BOND_L * 0.85) ** 2 && d2 > 0.01 && bondExists(g, i, j) < 0) {{
            const d = Math.sqrt(d2), rep = ((BOND_L * 0.85 - d) / d) * 0.22;
            if (!locked.has(i)) {{ fx[i] -= dx * rep; fy[i] -= dy * rep; }}
            if (!locked.has(j)) {{ fx[j] += dx * rep; fy[j] += dy * rep; }}
          }}
        }}
      }}
      for (let i = 0; i < g.atoms.length; i++) {{
        g.atoms[i].x = +(g.atoms[i].x + Math.max(-4, Math.min(4, fx[i]))).toFixed(2);
        g.atoms[i].y = +(g.atoms[i].y + Math.max(-4, Math.min(4, fy[i]))).toFixed(2);
      }}
    }}
    render();
    setToast("Cleaned 2D coordinates");
  }}

  // Expand abbreviations (e.g. CF3, CN, NO2, COOH, Boc, tBu, OMe, Ph) into explicit atoms
  function expandAbbreviations(g) {{
    let changed = false;
    for (let i = g.atoms.length - 1; i >= 0; i--) {{
      const sym = g.atoms[i].s;
      if (!ABBR[sym]) continue;
      if (!changed) {{ pushUndo(); changed = true; }}
      const base = g.atoms[i];
      const ang = sproutAngle(g, i, 1) + Math.PI;
      const nb = neighbors(g, i);
      const dir = nb.length === 1 ? Math.atan2(base.y - g.atoms[nb[0].to].y, base.x - g.atoms[nb[0].to].x) : ang;
      if (sym === "CF3" || sym === "CCl3" || sym === "tBu" || sym === "TMS") {{
        const centerSym = sym === "TMS" ? "Si" : "C";
        const leafSym = sym === "CF3" ? "F" : (sym === "CCl3" ? "Cl" : "C");
        base.s = centerSym;
        [dir, dir + Math.PI * 0.52, dir - Math.PI * 0.52].forEach((a) => {{
          const li = g.atoms.length;
          g.atoms.push({{s: leafSym, x: +(base.x + Math.cos(a) * BOND_L).toFixed(2), y: +(base.y + Math.sin(a) * BOND_L).toFixed(2)}});
          g.bonds.push({{a: i, b: li, o: 1}});
        }});
      }} else if (sym === "CN") {{
        base.s = "C";
        const ni = g.atoms.length;
        g.atoms.push({{s: "N", x: +(base.x + Math.cos(dir) * BOND_L).toFixed(2), y: +(base.y + Math.sin(dir) * BOND_L).toFixed(2)}});
        g.bonds.push({{a: i, b: ni, o: 3}});
      }} else if (sym === "NO2") {{
        base.s = "N"; base.chg = 1;
        const o1 = g.atoms.length, o2 = o1 + 1;
        g.atoms.push({{s: "O", x: +(base.x + Math.cos(dir + Math.PI/3)*BOND_L).toFixed(2), y: +(base.y + Math.sin(dir + Math.PI/3)*BOND_L).toFixed(2)}});
        g.atoms.push({{s: "O", chg: -1, x: +(base.x + Math.cos(dir - Math.PI/3)*BOND_L).toFixed(2), y: +(base.y + Math.sin(dir - Math.PI/3)*BOND_L).toFixed(2)}});
        g.bonds.push({{a: i, b: o1, o: 2}}, {{a: i, b: o2, o: 1}});
      }} else if (sym === "COOH" || sym === "CO2H" || sym === "CO2Me" || sym === "CO2Et") {{
        base.s = "C";
        const o1 = g.atoms.length, o2 = o1 + 1;
        g.atoms.push({{s: "O", x: +(base.x + Math.cos(dir + Math.PI/3)*BOND_L).toFixed(2), y: +(base.y + Math.sin(dir + Math.PI/3)*BOND_L).toFixed(2)}});
        const ox = +(base.x + Math.cos(dir - Math.PI/3)*BOND_L).toFixed(2), oy = +(base.y + Math.sin(dir - Math.PI/3)*BOND_L).toFixed(2);
        g.atoms.push({{s: "O", x: ox, y: oy}});
        g.bonds.push({{a: i, b: o1, o: 2}}, {{a: i, b: o2, o: 1}});
        if (sym === "CO2Me" || sym === "CO2Et") {{
          const c1 = g.atoms.length;
          const cx1 = +(ox + Math.cos(dir)*BOND_L).toFixed(2), cy1 = +(oy + Math.sin(dir)*BOND_L).toFixed(2);
          g.atoms.push({{s: "C", x: cx1, y: cy1}});
          g.bonds.push({{a: o2, b: c1, o: 1}});
          if (sym === "CO2Et") {{
            const c2 = g.atoms.length;
            g.atoms.push({{s: "C", x: +(cx1 + Math.cos(dir - Math.PI/3)*BOND_L).toFixed(2), y: +(cy1 + Math.sin(dir - Math.PI/3)*BOND_L).toFixed(2)}});
            g.bonds.push({{a: c1, b: c2, o: 1}});
          }}
        }}
      }} else if (sym === "OMe" || sym === "Me") {{
        if (sym === "Me") base.s = "C";
        else {{
          base.s = "O";
          const ci = g.atoms.length;
          g.atoms.push({{s: "C", x: +(base.x + Math.cos(dir)*BOND_L).toFixed(2), y: +(base.y + Math.sin(dir)*BOND_L).toFixed(2)}});
          g.bonds.push({{a: i, b: ci, o: 1}});
        }}
      }} else if (sym === "Boc") {{
        base.s = "C";
        const o1 = g.atoms.length, o2 = o1 + 1, ct = o1 + 2;
        g.atoms.push({{s:"O", x:+(base.x + Math.cos(dir + Math.PI/3)*BOND_L).toFixed(2), y:+(base.y + Math.sin(dir + Math.PI/3)*BOND_L).toFixed(2)}});
        const ox = +(base.x + Math.cos(dir - Math.PI/3)*BOND_L).toFixed(2), oy = +(base.y + Math.sin(dir - Math.PI/3)*BOND_L).toFixed(2);
        g.atoms.push({{s:"O", x:ox, y:oy}});
        const tx = +(ox + Math.cos(dir)*BOND_L).toFixed(2), ty = +(oy + Math.sin(dir)*BOND_L).toFixed(2);
        g.atoms.push({{s:"C", x:tx, y:ty}});
        g.bonds.push({{a:i,b:o1,o:2}},{{a:i,b:o2,o:1}},{{a:o2,b:ct,o:1}});
        [dir, dir + Math.PI*0.52, dir - Math.PI*0.52].forEach((a) => {{
          const mi = g.atoms.length;
          g.atoms.push({{s:"C", x:+(tx + Math.cos(a)*BOND_L).toFixed(2), y:+(ty + Math.sin(a)*BOND_L).toFixed(2)}});
          g.bonds.push({{a:ct,b:mi,o:1}});
        }});
      }} else if (sym === "Ph") {{
        base.s = "C";
        const R = BOND_L;
        const rcx = base.x + Math.cos(dir) * R, rcy = base.y + Math.sin(dir) * R;
        const a0 = Math.atan2(base.y - rcy, base.x - rcx);
        const ids = [i];
        for (let k = 1; k < 6; k++) {{
          const ang2 = a0 + (k * Math.PI) / 3;
          ids.push(g.atoms.length);
          g.atoms.push({{s:"C", x:+(rcx + Math.cos(ang2)*R).toFixed(2), y:+(rcy + Math.sin(ang2)*R).toFixed(2)}});
        }}
        for (let k = 0; k < 6; k++) g.bonds.push({{a:ids[k], b:ids[(k+1)%6], o: k % 2 === 0 ? 2 : 1}});
      }}
    }}
    if (changed) {{ render(); setToast("Expanded abbreviations to explicit atoms"); }}
    else setToast("No expandable superatom abbreviations on canvas");
  }}

  // Implicit hydrogens & live metrics
  function implicitH(g, ai, orderSum) {{
    const a = g.atoms[ai];
    if (!a || ABBR[a.s] || a.s.startsWith("[") || ["A","Q","X","M","G","*"].includes(a.s) || /^R\d*$/.test(a.s)) return 0;
    if (a.qlock === "s*") return 0;
    let v = VALENCE[a.s] || 0;
    const chg = a.chg || 0;
    if (a.s === "N" && chg === 1) v = 4;
    else if (a.s === "O" && chg === 1) v = 3;
    else if (a.s === "O" && chg === -1) v = 1;
    else if ((a.s === "B" || a.s === "Al") && chg === -1) v = 4;
    else if (a.s === "C" && Math.abs(chg) === 1) v = 3;
    else if (a.s === "S" && orderSum > 2) v = orderSum <= 4 ? 4 : 6;
    else if (a.s === "P" && orderSum > 3) v = 5;
    const rad = a.rad || 0;
    return Math.max(0, v - orderSum - rad);
  }}

  function graphToSmiles(g, smartsMode = false) {{
    if (!g.atoms.length) return "";
    const adj = g.atoms.map(() => []);
    const bmap = new Map();
    const ek = (u, v) => (u < v ? u + ":" + v : v + ":" + u);
    g.bonds.forEach((b) => {{
      if (b.a < g.atoms.length && b.b < g.atoms.length && b.q !== "hbond" && !b.multicenter) {{
        adj[b.a].push(b.b); adj[b.b].push(b.a);
        bmap.set(ek(b.a, b.b), b);
      }}
    }});
    const seen = new Set(), comps = [];
    for (let i = 0; i < g.atoms.length; i++) {{
      if (g.atoms[i].multicenterCenter) continue;
      if (seen.has(i)) continue;
      const comp = [], q = [i]; seen.add(i);
      while (q.length) {{
        const u = q.shift(); comp.push(u);
        adj[u].forEach((v) => {{ if (!seen.has(v)) {{ seen.add(v); q.push(v); }} }});
      }}
      comps.push(comp);
    }}
    const bondSym = (b) => {{
      if (!b) return "";
      if (smartsMode && b.q) {{
        if (b.q === "any") return "~";
        if (b.q === "12") return "-,=";
        if (b.q === "1a") return "-,:";
        if (b.q === "2a") return "=,:";
        if (b.q === "arom") return ":";
      }}
      if (b.o === 2) return "=";
      if (b.o === 3) return "#";
      return "";
    }};
    const atomTok = (i) => {{
      const a = g.atoms[i];
      if (!smartsMode && ABBR[a.s]) return ABBR[a.s].smi;
      if (a.s === "*") return "*";
      if (smartsMode) {{
        if (a.s === "A") return "[!#1]";
        if (a.s === "Q") return "[!#6;!#1]";
        if (a.s === "X") return "[F,Cl,Br,I]";
        if (a.s.startsWith("[")) return a.s;
      }}
      const organic = ["B","C","N","O","P","S","F","Cl","Br","I"];
      const needBrk = !organic.includes(a.s) || a.chg || a.iso || a.map || (smartsMode && a.qlock);
      if (!needBrk) return a.s;
      const iso = a.iso ? String(a.iso) : "";
      const chg = a.chg ? (a.chg > 0 ? "+" + (a.chg > 1 ? a.chg : "") : "-" + (a.chg < -1 ? Math.abs(a.chg) : "")) : "";
      const ql = (smartsMode && a.qlock && a.qlock !== "s*") ? ";" + a.qlock : "";
      const mp = a.map ? ":" + a.map : "";
      const base = /^[A-Z][a-z]?$/.test(a.s) ? a.s : "*" ;
      return `[${{iso}}${{base}}${{chg}}${{ql}}${{mp}}]`;
    }};
    const serComp = (comp) => {{
      const vis = new Set(), par = new Map(), kids = new Map(), rtags = new Map(), seenB = new Set();
      comp.forEach((u) => {{ kids.set(u, []); rtags.set(u, []); }});
      let rno = 0;
      const dfs = (u) => {{
        vis.add(u);
        for (const v of adj[u]) {{
          if (!vis.has(v)) {{ par.set(v, u); kids.get(u).push(v); dfs(v); }}
          else if (par.get(u) !== v && !seenB.has(ek(u, v))) {{
            seenB.add(ek(u, v)); rno++;
            const tag = rno >= 10 ? "%" + rno : String(rno);
            const bs = bondSym(bmap.get(ek(u, v)));
            rtags.get(u).push(bs + tag);
            rtags.get(v).push(tag);
          }}
        }}
      }};
      dfs(comp[0]);
      const emit = (u, p) => {{
        const bs = p == null ? "" : bondSym(bmap.get(ek(u, p)));
        const ch = kids.get(u);
        let out = bs + atomTok(u) + rtags.get(u).join("");
        ch.forEach((c, idx) => {{ out += idx < ch.length - 1 ? "(" + emit(c, u) + ")" : emit(c, u); }});
        return out;
      }};
      return emit(comp[0], null);
    }};
    if (g.arrows.length > 0) {{
      const ax = (g.arrows[0].x1 + g.arrows[0].x2) / 2;
      const lhs = [], rhs = [];
      comps.forEach((c) => {{
        const cx = c.reduce((s, i) => s + g.atoms[i].x, 0) / c.length;
        (cx < ax ? lhs : rhs).push(serComp(c));
      }});
      return lhs.join(".") + ">>" + rhs.join(".");
    }}
    return comps.map(serComp).join(".");
  }}

  // MDL Molfile V2000 Generator & Parser (Native Reaxys / SciFinder format!)
  function toMolfileV2000(g) {{
    const realIdx = [];
    const mapIdx = new Map();
    g.atoms.forEach((a, i) => {{
      if (!a.multicenterCenter) {{ mapIdx.set(i, realIdx.length + 1); realIdx.push(i); }}
    }});
    const validBonds = g.bonds.filter((b) => mapIdx.has(b.a) && mapIdx.has(b.b));
    let out = `${{g.name || "Structure"}}\n  CDXMLToolkit-2DStudio          2D\n\n`;
    out += String(realIdx.length).padStart(3) + String(validBonds.length).padStart(3) + "  0  0  0  0            999 V2000\n";
    const cx = realIdx.length ? realIdx.reduce((s, i) => s + g.atoms[i].x, 0) / realIdx.length : 0;
    const cy = realIdx.length ? realIdx.reduce((s, i) => s + g.atoms[i].y, 0) / realIdx.length : 0;
    const chgs = [], isos = [], rads = [];
    realIdx.forEach((ai, k) => {{
      const a = g.atoms[ai];
      const mx = ((a.x - cx) / BOND_L * 1.54).toFixed(4).padStart(10);
      const my = (-(a.y - cy) / BOND_L * 1.54).toFixed(4).padStart(10);
      const mz = (0).toFixed(4).padStart(10);
      const sym = (/^[A-Z][a-z]?$/.test(a.s) || ["A","Q","X","*"].includes(a.s) ? a.s : "R#").padEnd(3);
      const mp = String(a.map || 0).padStart(3);
      out += `${{mx}}${{my}}${{mz}} ${{sym}} 0  0  0  0  0  0  0  0  0${{mp}}  0  0\n`;
      if (a.chg) chgs.push([k + 1, a.chg]);
      if (a.iso) isos.push([k + 1, a.iso]);
      if (a.rad) rads.push([k + 1, a.rad]);
    }});
    validBonds.forEach((b) => {{
      const u = String(mapIdx.get(b.a)).padStart(3);
      const v = String(mapIdx.get(b.b)).padStart(3);
      let bt = b.o >= 4 ? 1 : (b.o || 1);
      if (b.q === "arom") bt = 4;
      else if (b.q === "12") bt = 5;
      else if (b.q === "1a") bt = 6;
      else if (b.q === "2a") bt = 7;
      else if (b.q === "any") bt = 8;
      let st = 0;
      if (b.o === 4) st = 1;
      else if (b.o === 5) st = 6;
      else if (b.o === 6) st = 4;
      else if (b.ez) st = 3;
      out += `${{u}}${{v}}${{String(bt).padStart(3)}}${{String(st).padStart(3)}}  0  0  0\n`;
    }});
    chgs.forEach(([idx, c]) => {{ out += `M  CHG  1 ${{String(idx).padStart(3)}} ${{String(c).padStart(3)}}\n`; }});
    isos.forEach(([idx, m]) => {{ out += `M  ISO  1 ${{String(idx).padStart(3)}} ${{String(m).padStart(3)}}\n`; }});
    rads.forEach(([idx, r]) => {{ out += `M  RAD  1 ${{String(idx).padStart(3)}} ${{String(r).padStart(3)}}\n`; }});
    out += "M  END\n";
    return out;
  }}

  function parseMolfileV2000(text) {{
    const lines = text.replace(/\r/g, "").split("\n");
    const vIdx = lines.findIndex((l) => l.includes("V2000"));
    if (vIdx < 0) return null;
    const na = parseInt(lines[vIdx].slice(0, 3), 10);
    const nb = parseInt(lines[vIdx].slice(3, 6), 10);
    if (isNaN(na) || na <= 0) return null;
    const rawAtoms = [], bonds = [];
    for (let i = 0; i < na; i++) {{
      const l = lines[vIdx + 1 + i] || "";
      const x = parseFloat(l.slice(0, 10)) || 0;
      const y = parseFloat(l.slice(10, 20)) || 0;
      const s = l.slice(31, 34).trim() || "C";
      rawAtoms.push({{s, x, y: -y}});
    }}
    for (let i = 0; i < nb; i++) {{
      const l = lines[vIdx + 1 + na + i] || "";
      const a = parseInt(l.slice(0, 3), 10) - 1;
      const b = parseInt(l.slice(3, 6), 10) - 1;
      const bt = parseInt(l.slice(6, 9), 10) || 1;
      const st = parseInt(l.slice(9, 12), 10) || 0;
      let o = bt <= 3 ? bt : 1;
      if (st === 1) o = 4; else if (st === 6) o = 5; else if (st === 4) o = 6;
      const entry = {{a, b, o}};
      if (bt === 4) entry.q = "arom"; else if (bt === 8) entry.q = "any";
      if (a >= 0 && b >= 0 && a < na && b < na) bonds.push(entry);
    }}
    lines.slice(vIdx + 1 + na + nb).forEach((l) => {{
      if (l.startsWith("M  CHG")) {{
        const parts = l.slice(6).trim().split(/\s+/).map(Number);
        for (let k = 1; k < parts.length; k += 2) {{
          if (rawAtoms[parts[k] - 1]) rawAtoms[parts[k] - 1].chg = parts[k + 1];
        }}
      }}
    }});
    const cx = rawAtoms.reduce((s, a) => s + a.x, 0) / na;
    const cy = rawAtoms.reduce((s, a) => s + a.y, 0) / na;
    const scale = BOND_L / 1.54;
    const atoms = rawAtoms.map((a) => ({{...a, x: +(340 + (a.x - cx) * scale).toFixed(2), y: +(178 + (a.y - cy) * scale).toFixed(2)}}));
    return normalizeGraph({{name: lines[0].trim() || "Imported Molfile", atoms, bonds}});
  }}

  // Client-side SMILES parser (handles branches, rings, aromaticity -> Kekule, charges, reactions)
  function parseSmilesClient(smi) {{
    const clean = smi.trim();
    if (!clean) return null;
    if (clean.includes(">>")) {{
      const [l, r] = clean.split(">>");
      const gl = parseSmilesClient(l) || normalizeGraph({{}});
      const gr = parseSmilesClient(r) || normalizeGraph({{}});
      gl.atoms.forEach((a) => {{ a.x -= 155; }});
      const off = gl.atoms.length;
      gr.atoms.forEach((a) => {{ gl.atoms.push({{...a, x: a.x + 155}}); }});
      gr.bonds.forEach((b) => gl.bonds.push({{...b, a: b.a + off, b: b.b + off}}));
      gl.arrows.push({{x1: 295, y1: 178, x2: 385, y2: 178, style: "solid", above: "", below: ""}});
      return gl;
    }}
    const atoms = [], bonds = [], aromSet = new Set();
    const stack = [], ringOpen = new Map();
    let cur = -1, pendOrd = 1, pendQ = null, i = 0;
    while (i < clean.length) {{
      const ch = clean[i];
      if (ch === ".") {{ cur = -1; pendOrd = 1; i++; continue; }}
      if (ch === "(") {{ stack.push(cur); i++; continue; }}
      if (ch === ")") {{ cur = stack.pop() ?? -1; i++; continue; }}
      if (ch === "=") {{ pendOrd = 2; i++; continue; }}
      if (ch === "#") {{ pendOrd = 3; i++; continue; }}
      if (ch === "~") {{ pendOrd = 1; pendQ = "any"; i++; continue; }}
      if (ch === "-" || ch === "/" || ch === "\\") {{ pendOrd = 1; i++; continue; }}
      if (ch === "%" || /\d/.test(ch)) {{
        let rtag = ch;
        if (ch === "%") {{ rtag = clean.slice(i + 1, i + 3); i += 3; }} else i++;
        if (ringOpen.has(rtag)) {{
          const [prev, ro] = ringOpen.get(rtag);
          ringOpen.delete(rtag);
          if (cur >= 0 && prev !== cur) bonds.push({{a: prev, b: cur, o: Math.max(pendOrd, ro)}});
        }} else if (cur >= 0) {{
          ringOpen.set(rtag, [cur, pendOrd]);
        }}
        pendOrd = 1; pendQ = null; continue;
      }}
      let sym = null, chg = 0, iso = 0, mp = 0, isArom = false;
      if (ch === "[") {{
        const end = clean.indexOf("]", i);
        if (end < 0) break;
        const body = clean.slice(i + 1, end);
        i = end + 1;
        const m = body.match(/^(\d+)?([A-Za-z*]+)(?:@+)?(?:H\d*)?([+-]\d*)?(?::(\d+))?/);
        if (m) {{
          if (m[1]) iso = parseInt(m[1], 10);
          sym = m[2];
          if (/^[a-z]+$/.test(sym)) {{ isArom = true; sym = sym[0].toUpperCase() + sym.slice(1); }}
          if (m[3]) chg = m[3] === "+" ? 1 : (m[3] === "-" ? -1 : parseInt(m[3], 10));
          if (m[4]) mp = parseInt(m[4], 10);
        }} else sym = "C";
      }} else if (ch === "C" && clean[i + 1] === "l") {{ sym = "Cl"; i += 2; }}
      else if (ch === "B" && clean[i + 1] === "r") {{ sym = "Br"; i += 2; }}
      else if (/[BCNOPSFI*]/.test(ch)) {{ sym = ch; i++; }}
      else if (/[bcnops]/.test(ch)) {{ sym = ch.toUpperCase(); isArom = true; i++; }}
      else {{ i++; continue; }}

      const idx = atoms.length;
      const ang = cur >= 0 ? ((idx % 2 === 0 ? 1 : -1) * Math.PI / 6) : 0;
      const px = cur >= 0 ? atoms[cur].x + Math.cos(ang) * BOND_L : 260 + (idx > 0 ? 90 : 0);
      const py = cur >= 0 ? atoms[cur].y + Math.sin(ang) * BOND_L : 178;
      const aObj = {{s: sym, x: +px.toFixed(2), y: +py.toFixed(2)}};
      if (chg) aObj.chg = chg;
      if (iso) aObj.iso = iso;
      if (mp) aObj.map = mp;
      atoms.push(aObj);
      if (isArom) aromSet.add(idx);
      if (cur >= 0) {{
        const bObj = {{a: cur, b: idx, o: pendOrd}};
        if (pendQ) bObj.q = pendQ;
        bonds.push(bObj);
      }}
      cur = idx; pendOrd = 1; pendQ = null;
    }}
    // Kekulize simple aromatic rings
    const g = normalizeGraph({{atoms, bonds}});
    const rings = findSmallRings(g);
    rings.forEach((r) => {{
      if (r.every((u) => aromSet.has(u))) {{
        for (let k = 0; k < r.length; k += 2) {{
          const bi = bondExists(g, r[k], r[(k + 1) % r.length]);
          if (bi >= 0) g.bonds[bi].o = 2;
        }}
      }}
    }});
    clean2D(g);
    state.undoStack.pop();
    return g;
  }}

  function toCdxml(g) {{
    const st = state.styles[state.style] || {{bondLength: 14.4, lineWidth: 0.6}};
    let nodes = "", bxml = "";
    g.atoms.forEach((a, i) => {{
      if (a.multicenterCenter) return;
      const z = ELEM_Z[a.s] || 6;
      const chg = a.chg ? ` Charge="${{a.chg}}"` : "";
      const iso = a.iso ? ` Isotope="${{a.iso}}"` : "";
      const isNick = !ELEM_Z[a.s] && a.s !== "C";
      if (isNick) {{
        nodes += `      <n id="${{i + 1}}" p="${{a.x.toFixed(2)}} ${{a.y.toFixed(2)}}" NodeType="Nickname"${{chg}}><t p="${{a.x.toFixed(2)}} ${{a.y.toFixed(2)}}"><s font="3" size="10" face="96">${{esc(a.s)}}</s></t></n>\n`;
      }} else {{
        const elAttr = a.s !== "C" ? ` Element="${{z}}"` : "";
        nodes += `      <n id="${{i + 1}}" p="${{a.x.toFixed(2)}} ${{a.y.toFixed(2)}}"${{elAttr}}${{chg}}${{iso}}/>\n`;
      }}
    }});
    g.bonds.forEach((b, i) => {{
      if (g.atoms[b.a]?.multicenterCenter || g.atoms[b.b]?.multicenterCenter) return;
      const ord = b.o >= 4 ? 1 : (b.o || 1);
      let disp = "";
      if (b.o === 4) disp = ' Display="WedgeBegin"';
      else if (b.o === 5) disp = ' Display="WedgedHashBegin"';
      else if (b.o === 6) disp = ' Display="Wavy"';
      else if (b.o === 7) disp = ' Display="Bold"';
      bxml += `      <b id="${{1000 + i}}" B="${{b.a + 1}}" E="${{b.b + 1}}" Order="${{ord}}"${{disp}}/>\n`;
    }});
    let arrowsXml = "";
    g.arrows.forEach((ar, i) => {{
      arrowsXml += `    <arrow id="${{3000 + i}}" Head3D="${{ar.x2.toFixed(2)}} ${{ar.y2.toFixed(2)}} 0" Tail3D="${{ar.x1.toFixed(2)}} ${{ar.y1.toFixed(2)}} 0" ArrowheadType="Solid"/>\n`;
    }});
    return `<?xml version="1.0" encoding="UTF-8" ?>\n${{"<!" + "DOCTYPE"}} CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >\n<CDXML BondLength="${{st.bondLength || 14.4}}" LineWidth="${{st.lineWidth || 0.6}}">\n  <page id="5000">\n    <fragment id="5001">\n${{nodes}}${{bxml}}    </fragment>\n${{arrowsXml}}  </page>\n</CDXML>\n`;
  }}

  function esc(s) {{
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }}

  // Format chemical formula label with SVG tspan subscripts (e.g. CO2Et -> CO₂Et, CF3 -> CF₃)
  function formatChemLabelSvg(sym, flipLeft) {{
    let txt = (flipLeft && LEFT_FLIP[sym]) ? LEFT_FLIP[sym] : sym;
    return esc(txt).replace(/([A-Za-z)\]])(\d+)/g, '$1<tspan dy="2.8" font-size="8.8">$2</tspan><tspan dy="-2.8"> </tspan>').replace(/<\/tspan> /g, "</tspan>");
  }}

  function updateMetrics() {{
    const g = state.graph;
    const ordSum = g.atoms.map(() => 0);
    g.bonds.forEach((b) => {{
      if (b.q === "hbond" || b.multicenter) return;
      const o = b.o >= 4 ? 1 : (b.o || 1);
      if (b.a < ordSum.length) ordSum[b.a] += o;
      if (b.b < ordSum.length) ordSum[b.b] += o;
    }});
    const counts = {{}};
    let mw = 0, exact = 0;
    g.atoms.forEach((a, i) => {{
      if (a.multicenterCenter) return;
      if (ABBR[a.s]) {{
        Object.entries(ABBR[a.s].f).forEach(([el, n]) => {{
          counts[el] = (counts[el] || 0) + n;
          mw += (MASS[el] || 0) * n;
          exact += (EXACT[el] || MASS[el] || 0) * n;
        }});
        return;
      }}
      if (MASS[a.s]) {{
        counts[a.s] = (counts[a.s] || 0) + 1;
        mw += a.iso || MASS[a.s];
        exact += a.iso || EXACT[a.s] || MASS[a.s];
        const h = implicitH(g, i, ordSum[i]);
        if (h > 0) {{
          counts.H = (counts.H || 0) + h;
          mw += MASS.H * h;
          exact += EXACT.H * h;
        }}
      }}
    }});
    const order = ["C", "H", ...Object.keys(counts).filter((k) => k !== "C" && k !== "H").sort()];
    const fStr = order.filter((k) => counts[k]).map((k) => k + (counts[k] > 1 ? counts[k] : "")).join("") || "—";
    const cN = counts.C || 0, hN = (counts.H || 0) + (counts.D || 0) + (counts.T || 0);
    const hal = (counts.F || 0) + (counts.Cl || 0) + (counts.Br || 0) + (counts.I || 0);
    const nN = counts.N || 0;
    const dbe = g.atoms.length ? Math.max(0, Math.round(cN + 1 - (hN + hal - nN) / 2)) : 0;
    const qMode = document.getElementById("cdx-query-mode").value;
    const smi = graphToSmiles(g, qMode === "substructure");
    document.getElementById("cdx-m-formula").textContent = fStr;
    document.getElementById("cdx-m-exact").textContent = exact.toFixed(4);
    document.getElementById("cdx-m-mw").textContent = mw.toFixed(2);
    document.getElementById("cdx-m-dbe").textContent = String(dbe);
    document.getElementById("cdx-m-smi").textContent = smi || "Empty canvas";
    document.getElementById("cdx-m-smi").title = smi || "Draw a structure";
  }}

  // Main SVG Renderer
  function render() {{
    const g = state.graph;
    const rings = findSmallRings(g);
    const ordSum = g.atoms.map(() => 0);
    const deg = g.atoms.map(() => 0);
    g.bonds.forEach((b) => {{
      if (b.a < g.atoms.length && b.b < g.atoms.length && !b.multicenter) {{
        const o = b.o >= 4 ? 1 : (b.o || 1);
        ordSum[b.a] += o; ordSum[b.b] += o;
        deg[b.a]++; deg[b.b]++;
      }}
    }});

    // Identify aromatic 6-rings if Thiele circle mode is active
    const thieleBondSkip = new Set();
    const thieleRings = [];
    if (g.arom_circles) {{
      rings.forEach((r) => {{
        if (r.length !== 6) return;
        let dblCnt = 0;
        const rbs = [];
        for (let k = 0; k < 6; k++) {{
          const bi = bondExists(g, r[k], r[(k + 1) % 6]);
          if (bi >= 0) {{ rbs.push(bi); if (g.bonds[bi].o === 2) dblCnt++; }}
        }}
        if (dblCnt === 3) {{
          rbs.forEach((bi) => thieleBondSkip.add(bi));
          thieleRings.push(r);
        }}
      }});
    }}

    let h = `<defs>
      <marker id="cdx-ah" viewBox="0 0 10 6" refX="9" refY="3" markerWidth="7" markerHeight="5" orient="auto"><path d="M0,0 L10,3 L0,6 L2.2,3 Z" fill="#0f172a"/></marker>
      <marker id="cdx-ah-blue" viewBox="0 0 10 6" refX="9" refY="3" markerWidth="6.5" markerHeight="5" orient="auto"><path d="M0,0 L10,3 L0,6 L2,3 Z" fill="#0284c7"/></marker>
    </defs>`;

    if (g.atoms.length === 0 && g.arrows.length === 0 && g.texts.length === 0 && !state.drag) {{
      h += `<g opacity="0.46" pointer-events="none">
        <text x="340" y="168" text-anchor="middle" font-size="13" font-weight="600" fill="#475569">Reaxys / SciFinder Universal 2D Structure &amp; Query Canvas</text>
        <text x="340" y="189" text-anchor="middle" font-size="11.5" fill="#64748b">Click or drag to draw bonds · Hover bond with Ring tool to fuse · Double-click atom for formula/R-group</text>
      </g>`;
    }}

    // Ring pastel fills
    g.ring_fills.forEach((rf) => {{
      const pts = (rf.atoms || []).map((i) => g.atoms[i]).filter(Boolean);
      if (pts.length >= 3) {{
        h += `<polygon points="${{pts.map((p) => p.x + "," + p.y).join(" ")}}" fill="${{rf.color || "rgba(56,189,248,0.22)"}}" stroke="none"/>`;
      }}
    }});

    // Newman circles & spokes
    g.circles.forEach((c) => {{ h += `<circle cx="${{c.cx}}" cy="${{c.cy}}" r="${{c.r}}" fill="#ffffff" stroke="#0f172a" stroke-width="1.6"/>`; }});
    g.spokes.forEach((s) => {{ h += `<line x1="${{s[0]}}" y1="${{s[1]}}" x2="${{s[2]}}" y2="${{s[3]}}" stroke="#0f172a" stroke-width="1.6"/>`; }});

    // Selection bounding box & rotation handle
    if (state.selAtoms.size > 0) {{
      const sPts = [...state.selAtoms].map((i) => g.atoms[i]).filter(Boolean);
      if (sPts.length > 0) {{
        const minX = Math.min(...sPts.map((p) => p.x)) - 14;
        const maxX = Math.max(...sPts.map((p) => p.x)) + 14;
        const minY = Math.min(...sPts.map((p) => p.y)) - 14;
        const maxY = Math.max(...sPts.map((p) => p.y)) + 14;
        const midX = (minX + maxX) / 2;
        h += `<rect x="${{minX}}" y="${{minY}}" width="${{maxX - minX}}" height="${{maxY - minY}}" rx="5" fill="rgba(2,132,199,0.05)" stroke="#0284c7" stroke-width="1" stroke-dasharray="4 3"/>`;
        h += `<line x1="${{midX}}" y1="${{minY}}" x2="${{midX}}" y2="${{minY - 14}}" stroke="#0284c7" stroke-width="1.2"/>`;
        h += `<circle cx="${{midX}}" cy="${{minY - 17}}" r="4.5" fill="#ffffff" stroke="#0284c7" stroke-width="1.6"/>`;
      }}
      sPts.forEach((p) => {{ h += `<circle cx="${{p.x}}" cy="${{p.y}}" r="10.5" fill="rgba(2,132,199,0.16)" stroke="none"/>`; }});
    }}

    // Hover highlight
    if (state.hover.ai >= 0 && g.atoms[state.hover.ai]) {{
      const ha = g.atoms[state.hover.ai];
      h += `<circle cx="${{ha.x}}" cy="${{ha.y}}" r="10" fill="rgba(2,132,199,0.14)"/>`;
    }} else if (state.hover.bi >= 0 && g.bonds[state.hover.bi]) {{
      const hb = g.bonds[state.hover.bi], A = g.atoms[hb.a], B = g.atoms[hb.b];
      if (A && B) h += `<line x1="${{A.x}}" y1="${{A.y}}" x2="${{B.x}}" y2="${{B.y}}" stroke="rgba(2,132,199,0.22)" stroke-width="8" stroke-linecap="round"/>`;
    }}

    // Bonds
    g.bonds.forEach((b, bi) => {{
      const A = g.atoms[b.a], B = g.atoms[b.b];
      if (!A || !B) return;
      let x1 = A.x, y1 = A.y, x2 = B.x, y2 = B.y;
      const dx = x2 - x1, dy = y2 - y1, len = Math.hypot(dx, dy) || 1;
      const ux = dx / len, uy = dy / len, nx = -uy, ny = ux;
      const visA = !A.multicenterCenter && (A.s !== "C" || deg[b.a] === 0 || b.q === "coord" || A.chg || A.iso || A.rad || A.qlock);
      const visB = !B.multicenterCenter && (B.s !== "C" || deg[b.b] === 0 || b.q === "coord" || B.chg || B.iso || B.rad || B.qlock);
      if (visA) {{ x1 += ux * 8.5; y1 += uy * 8.5; }}
      if (visB) {{ x2 -= ux * 8.5; y2 -= uy * 8.5; }}

      if (b.multicenter) {{
        h += `<line x1="${{x1}}" y1="${{y1}}" x2="${{x2}}" y2="${{y2}}" stroke="#0f172a" stroke-width="1.75" stroke-linecap="round"/>`;
        h += `<circle cx="${{A.multicenterCenter ? A.x : B.x}}" cy="${{A.multicenterCenter ? A.y : B.y}}" r="2.6" fill="#0f172a"/>`;
        return;
      }}
      if (b.q) {{
        if (b.q === "any") h += `<line x1="${{x1}}" y1="${{y1}}" x2="${{x2}}" y2="${{y2}}" stroke="#7c3aed" stroke-width="1.8" stroke-dasharray="2.5 2.5"/>`;
        else if (b.q === "hbond") h += `<line x1="${{x1}}" y1="${{y1}}" x2="${{x2}}" y2="${{y2}}" stroke="#64748b" stroke-width="1.6" stroke-dasharray="1.5 3.2" stroke-linecap="round"/>`;
        else if (b.q === "coord") h += `<line x1="${{x1}}" y1="${{y1}}" x2="${{x2}}" y2="${{y2}}" stroke="#0284c7" stroke-width="1.65" marker-end="url(#cdx-ah-blue)"/>`;
        else {{
          h += `<line x1="${{x1 + nx*2}}" y1="${{y1 + ny*2}}" x2="${{x2 + nx*2}}" y2="${{y2 + ny*2}}" stroke="#0f172a" stroke-width="1.6"/>`;
          h += `<line x1="${{x1 - nx*2}}" y1="${{y1 - ny*2}}" x2="${{x2 - nx*2}}" y2="${{y2 - ny*2}}" stroke="#7c3aed" stroke-width="1.5" stroke-dasharray="3 2.2"/>`;
        }}
        return;
      }}

      const effOrder = thieleBondSkip.has(bi) ? 1 : (b.o || 1);
      if (effOrder === 4) {{
        h += `<polygon points="${{x1}},${{y1}} ${{x2 + nx*4.2}},${{y2 + ny*4.2}} ${{x2 - nx*4.2}},${{y2 - ny*4.2}}" fill="#0f172a"/>`;
      }} else if (effOrder === 5) {{
        const steps = Math.max(5, Math.round(len / 5.2));
        for (let k = 1; k <= steps; k++) {{
          const t = k / steps, px = x1 + (x2 - x1) * t, py = y1 + (y2 - y1) * t, w = 4.0 * t;
          h += `<line x1="${{px - nx*w}}" y1="${{py - ny*w}}" x2="${{px + nx*w}}" y2="${{py + ny*w}}" stroke="#0f172a" stroke-width="1.35"/>`;
        }}
      }} else if (effOrder === 6) {{
        let d = `M ${{x1}} ${{y1}}`;
        const segs = 7;
        for (let k = 1; k <= segs; k++) {{
          const t = (k - 0.5) / segs, te = k / segs;
          const sgn = k % 2 === 0 ? 3.5 : -3.5;
          d += ` Q ${{x1 + (x2-x1)*t + nx*sgn}} ${{y1 + (y2-y1)*t + ny*sgn}}, ${{x1 + (x2-x1)*te}} ${{y1 + (y2-y1)*te}}`;
        }}
        h += `<path d="${{d}}" fill="none" stroke="#0f172a" stroke-width="1.55"/>`;
      }} else if (effOrder === 7) {{
        h += `<line x1="${{x1}}" y1="${{y1}}" x2="${{x2}}" y2="${{y2}}" stroke="#0f172a" stroke-width="4.2" stroke-linecap="round"/>`;
      }} else if (b.ez) {{
        h += `<line x1="${{x1 + nx*2.5}}" y1="${{y1 + ny*2.5}}" x2="${{x2 - nx*2.5}}" y2="${{y2 - ny*2.5}}" stroke="#0f172a" stroke-width="1.6"/>`;
        h += `<line x1="${{x1 - nx*2.5}}" y1="${{y1 - ny*2.5}}" x2="${{x2 + nx*2.5}}" y2="${{y2 + ny*2.5}}" stroke="#0f172a" stroke-width="1.6"/>`;
      }} else if (effOrder === 2) {{
        const mode = b.side || 0; // 0=auto, 1=left, 2=center, 3=right
        const ring = mode === 0 ? rings.find((r) => r.includes(b.a) && r.includes(b.b)) : null;
        if (mode === 2 || (!ring && mode === 0 && (visA || visB))) {{
          h += `<line x1="${{x1 + nx*2.2}}" y1="${{y1 + ny*2.2}}" x2="${{x2 + nx*2.2}}" y2="${{y2 + ny*2.2}}" stroke="#0f172a" stroke-width="1.65" stroke-linecap="round"/>`;
          h += `<line x1="${{x1 - nx*2.2}}" y1="${{y1 - ny*2.2}}" x2="${{x2 - nx*2.2}}" y2="${{y2 - ny*2.2}}" stroke="#0f172a" stroke-width="1.65" stroke-linecap="round"/>`;
        }} else {{
          let sgn = 1;
          if (ring) {{
            const rcx = ring.reduce((s, i) => s + g.atoms[i].x, 0) / ring.length;
            const rcy = ring.reduce((s, i) => s + g.atoms[i].y, 0) / ring.length;
            sgn = ((rcx - (A.x + B.x)/2) * nx + (rcy - (A.y + B.y)/2) * ny) >= 0 ? 1 : -1;
          }} else if (mode === 3) sgn = -1;
          const off = 3.7 * sgn, ins = (visA || visB) ? 1.5 : 4.2;
          h += `<line x1="${{x1}}" y1="${{y1}}" x2="${{x2}}" y2="${{y2}}" stroke="#0f172a" stroke-width="1.75" stroke-linecap="round"/>`;
          h += `<line x1="${{x1 + ux*ins + nx*off}}" y1="${{y1 + uy*ins + ny*off}}" x2="${{x2 - ux*ins + nx*off}}" y2="${{y2 - uy*ins + ny*off}}" stroke="#0f172a" stroke-width="1.6" stroke-linecap="round"/>`;
        }}
      }} else if (effOrder === 3) {{
        h += `<line x1="${{x1}}" y1="${{y1}}" x2="${{x2}}" y2="${{y2}}" stroke="#0f172a" stroke-width="1.65"/>`;
        h += `<line x1="${{x1 + nx*3.4}}" y1="${{y1 + ny*3.4}}" x2="${{x2 + nx*3.4}}" y2="${{y2 + ny*3.4}}" stroke="#0f172a" stroke-width="1.55"/>`;
        h += `<line x1="${{x1 - nx*3.4}}" y1="${{y1 - ny*3.4}}" x2="${{x2 - nx*3.4}}" y2="${{y2 - ny*3.4}}" stroke="#0f172a" stroke-width="1.55"/>`;
      }} else {{
        h += `<line x1="${{x1}}" y1="${{y1}}" x2="${{x2}}" y2="${{y2}}" stroke="#0f172a" stroke-width="1.75" stroke-linecap="round"/>`;
      }}
    }});

    // Thiele aromatic inner circles
    thieleRings.forEach((r) => {{
      const cx = r.reduce((s, i) => s + g.atoms[i].x, 0) / 6;
      const cy = r.reduce((s, i) => s + g.atoms[i].y, 0) / 6;
      const rad = Math.hypot(g.atoms[r[0]].x - cx, g.atoms[r[0]].y - cy) * 0.58;
      h += `<circle cx="${{cx}}" cy="${{cy}}" r="${{rad.toFixed(1)}}" fill="none" stroke="#0f172a" stroke-width="1.55"/>`;
    }});

    // Reaction arrows
    g.arrows.forEach((ar) => {{
      const dx = ar.x2 - ar.x1, dy = ar.y2 - ar.y1, len = Math.hypot(dx, dy) || 1;
      const nx = -dy / len, ny = dx / len, mx = (ar.x1 + ar.x2) / 2, my = (ar.y1 + ar.y2) / 2;
      if (ar.style === "eq") {{
        h += `<line x1="${{ar.x1}}" y1="${{ar.y1 - 2.4}}" x2="${{ar.x2}}" y2="${{ar.y2 - 2.4}}" stroke="#0f172a" stroke-width="1.5" marker-end="url(#cdx-ah)"/>`;
        h += `<line x1="${{ar.x2}}" y1="${{ar.y2 + 2.4}}" x2="${{ar.x1}}" y2="${{ar.y1 + 2.4}}" stroke="#0f172a" stroke-width="1.5" marker-end="url(#cdx-ah)"/>`;
      }} else if (ar.style === "retro") {{
        h += `<line x1="${{ar.x1}}" y1="${{ar.y1 - 2.6}}" x2="${{ar.x2 - 5}}" y2="${{ar.y2 - 2.6}}" stroke="#0f172a" stroke-width="1.5"/>`;
        h += `<line x1="${{ar.x1}}" y1="${{ar.y1 + 2.6}}" x2="${{ar.x2 - 5}}" y2="${{ar.y2 + 2.6}}" stroke="#0f172a" stroke-width="1.5"/>`;
        h += `<polyline points="${{ar.x2 - 8}},${{ar.y2 - 6}} ${{ar.x2}},${{ar.y2}} ${{ar.x2 - 8}},${{ar.y2 + 6}}" fill="none" stroke="#0f172a" stroke-width="1.6"/>`;
      }} else {{
        h += `<line x1="${{ar.x1}}" y1="${{ar.y1}}" x2="${{ar.x2}}" y2="${{ar.y2}}" stroke="#0f172a" stroke-width="1.7" marker-end="url(#cdx-ah)"/>`;
        if (ar.style === "res") h += `<line x1="${{ar.x2}}" y1="${{ar.y2}}" x2="${{ar.x1}}" y2="${{ar.y1}}" stroke="#0f172a" stroke-width="1.7" marker-end="url(#cdx-ah)"/>`;
        if (ar.style === "no") {{
          h += `<line x1="${{mx - 5}}" y1="${{my - 6}}" x2="${{mx + 5}}" y2="${{my + 6}}" stroke="#dc2626" stroke-width="1.9"/>`;
          h += `<line x1="${{mx + 5}}" y1="${{my - 6}}" x2="${{mx - 5}}" y2="${{my + 6}}" stroke="#dc2626" stroke-width="1.9"/>`;
        }}
      }}
      void nx; void ny;
      if (ar.above) h += `<text x="${{mx}}" y="${{my - 8}}" text-anchor="middle" font-size="11" fill="#0f172a">${{esc(ar.above)}}</text>`;
      if (ar.below) h += `<text x="${{mx}}" y="${{my + 16}}" text-anchor="middle" font-size="10.5" fill="#334155">${{esc(ar.below)}}</text>`;
    }});

    // Pluses, Brackets, Curved electron arrows, Free texts
    g.pluses.forEach((p) => {{ h += `<text x="${{p.x}}" y="${{p.y + 4}}" text-anchor="middle" font-size="15" font-weight="700" fill="#0f172a">+</text>`; }});
    g.brackets.forEach((br) => {{
      const x1 = Math.min(br.x1, br.x2), x2 = Math.max(br.x1, br.x2);
      const y1 = Math.min(br.y1, br.y2), y2 = Math.max(br.y1, br.y2), w = 6;
      h += `<path d="M${{x1+w}},${{y1}} H${{x1}} V${{y2}} H${{x1+w}} M${{x2-w}},${{y1}} H${{x2}} V${{y2}} H${{x2-w}}" fill="none" stroke="#0f172a" stroke-width="1.5"/>`;
      h += `<text x="${{x2 + 4}}" y="${{y2 + 3}}" font-size="10.5" font-style="italic" fill="#0f172a">${{esc(br.label || "n")}}</text>`;
    }});
    g.curved.forEach((cv) => {{
      const mx = (cv.x1 + cv.x2) / 2, my = (cv.y1 + cv.y2) / 2;
      const dx = cv.x2 - cv.x1, dy = cv.y2 - cv.y1, len = Math.hypot(dx, dy) || 1;
      const cx = mx - (dy / len) * 26, cy = my + (dx / len) * 26;
      h += `<path d="M${{cv.x1}},${{cv.y1}} Q${{cx}},${{cy}} ${{cv.x2}},${{cv.y2}}" fill="none" stroke="#0284c7" stroke-width="1.55" marker-end="url(#cdx-ah-blue)"/>`;
      if (cv.el === 1) h += `<circle cx="${{cv.x2}}" cy="${{cv.y2}}" r="2" fill="#0284c7"/>`;
    }});
    g.texts.forEach((t) => {{
      h += `<text x="${{t.x}}" y="${{t.y}}" text-anchor="middle" font-size="11.5" fill="#0f172a">${{esc(t.text)}}</text>`;
    }});

    // Atoms
    g.atoms.forEach((a, i) => {{
      if (a.multicenterCenter) return;
      const isC = a.s === "C" && deg[i] > 0 && !a.chg && !a.iso && !a.rad && !a.qlock && !a.map;
      if (isC) return;
      const col = state.style === "acs1996" && !["A","Q","X","M","*"].includes(a.s) ? (CPK[a.s] || "#0f172a") : (CPK[a.s] || "#0f172a");
      let dirX = 0;
      g.bonds.forEach((b) => {{
        if (b.a === i && g.atoms[b.b]) dirX += g.atoms[b.b].x - a.x;
        else if (b.b === i && g.atoms[b.a]) dirX += g.atoms[b.a].x - a.x;
      }});
      const hc = implicitH(g, i, ordSum[i]);
      const showH = hc > 0 && (["N","O","S","P","F","Cl","Br","I"].includes(a.s) || deg[i] === 0);
      const hPart = showH ? "H" + (hc > 1 ? `<tspan dy="2.8" font-size="8.8">${{hc}}</tspan><tspan dy="-2.8"></tspan>` : "") : "";
      const flipLeft = dirX > 7;
      const coreSvg = formatChemLabelSvg(a.s, flipLeft);
      const isoSup = a.iso ? `<tspan dy="-4.5" font-size="8.5">${{a.iso}}</tspan><tspan dy="4.5"></tspan>` : "";
      const chgSup = a.chg ? `<tspan dy="-4.5" font-size="8.8">${{Math.abs(a.chg) > 1 ? Math.abs(a.chg) : ""}}${{a.chg > 0 ? "+" : "−"}}</tspan><tspan dy="4.5"></tspan>` : "";
      const labelHtml = (showH && flipLeft) ? (hPart + isoSup + coreSvg + chgSup) : (isoSup + coreSvg + hPart + chgSup);

      h += `<circle cx="${{a.x}}" cy="${{a.y}}" r="7.5" fill="#ffffff"/>`;
      // Over-valence red warning halo
      if (VALENCE[a.s] && ordSum[i] > (VALENCE[a.s] + (a.s === "N" && a.chg === 1 ? 1 : 0)) && !["S","P"].includes(a.s)) {{
        h += `<circle cx="${{a.x}}" cy="${{a.y}}" r="10.5" fill="none" stroke="#dc2626" stroke-width="1.3" stroke-dasharray="2 2"/>`;
      }}
      h += `<text x="${{a.x}}" y="${{a.y + 4.2}}" text-anchor="middle" font-size="12.2" font-weight="600" fill="${{col}}">${{labelHtml}}</text>`;
      if (a.rad) {{
        h += `<circle cx="${{a.x + 7.5}}" cy="${{a.y - 5.5}}" r="1.9" fill="${{col}}"/>`;
        if (a.rad === 2) h += `<circle cx="${{a.x + 7.5}}" cy="${{a.y - 1}}" r="1.9" fill="${{col}}"/>`;
      }}
      if (a.map) {{
        h += `<text x="${{a.x - 9}}" y="${{a.y - 5}}" font-size="8.8" font-weight="700" fill="#0284c7">[${{a.map}}]</text>`;
      }}
      if (a.qlock) {{
        h += `<text x="${{a.x + 9}}" y="${{a.y + 9}}" font-size="8" font-weight="700" fill="#7c3aed">${{esc(a.qlock)}}</text>`;
      }}
    }});

    // Dynamic Ghost Preview (Ring fusion / spiro / free ring, Drag bond, Zigzag chain, Selection marquee/lasso)
    if (state.ringTool && state.hover.pt && !state.drag) {{
      const p = state.hover.pt;
      if (state.hover.bi >= 0 && ringSpec(state.ringTool)) {{
        const plan = computeRingFusionPreview(g, state.hover.bi, state.ringTool, p);
        if (plan) {{
          const poly = plan.pts.map((q) => q.x + "," + q.y).join(" ");
          h += `<polygon points="${{poly}}" fill="rgba(2,132,199,0.10)" stroke="#0284c7" stroke-width="1.6" stroke-dasharray="3.5 2.5"/>`;
        }}
      }} else {{
        const temp = normalizeGraph({{}});
        if (state.hover.ai >= 0) temp.atoms.push({{...g.atoms[state.hover.ai]}});
        placeRing(temp, state.ringTool, p, state.hover.ai >= 0 ? 0 : -1, -1);
        temp.bonds.forEach((tb) => {{
          const A = temp.atoms[tb.a], B = temp.atoms[tb.b];
          h += `<line x1="${{A.x}}" y1="${{A.y}}" x2="${{B.x}}" y2="${{B.y}}" stroke="#0284c7" stroke-width="1.5" stroke-dasharray="3.5 2.5" opacity="0.78"/>`;
        }});
      }}
    }}

    if (state.drag) {{
      const d = state.drag;
      if (d.kind === "bond") {{
        h += `<line x1="${{d.x1}}" y1="${{d.y1}}" x2="${{d.x2}}" y2="${{d.y2}}" stroke="#0284c7" stroke-width="1.9" stroke-dasharray="4 3"/>`;
        if (d.snapAi >= 0) h += `<circle cx="${{d.x2}}" cy="${{d.y2}}" r="9.5" fill="none" stroke="#0284c7" stroke-width="1.8"/>`;
      }} else if (d.kind === "chain" && d.pts.length > 1) {{
        h += `<polyline points="${{d.pts.map((q) => q.x + "," + q.y).join(" ")}}" fill="none" stroke="#0284c7" stroke-width="1.9"/>`;
        const last = d.pts[d.pts.length - 1];
        h += `<rect x="${{last.x + 8}}" y="${{last.y - 18}}" width="28" height="16" rx="4" fill="#0284c7"/>`;
        h += `<text x="${{last.x + 22}}" y="${{last.y - 7}}" text-anchor="middle" font-size="10" font-weight="700" fill="#ffffff">C${{d.pts.length}}</text>`;
      }} else if (d.kind === "box") {{
        const rx = Math.min(d.x1, d.x2), ry = Math.min(d.y1, d.y2);
        h += `<rect x="${{rx}}" y="${{ry}}" width="${{Math.abs(d.x2 - d.x1)}}" height="${{Math.abs(d.y2 - d.y1)}}" fill="rgba(2,132,199,0.08)" stroke="#0284c7" stroke-width="1.2" stroke-dasharray="4 3"/>`;
      }} else if (d.kind === "lasso" && d.pts.length > 1) {{
        h += `<polygon points="${{d.pts.map((q) => q.x + "," + q.y).join(" ")}}" fill="rgba(2,132,199,0.08)" stroke="#0284c7" stroke-width="1.2" stroke-dasharray="4 3"/>`;
      }} else if (d.kind === "arrow" || d.kind === "map" || d.kind === "curv" || d.kind === "bracket") {{
        h += `<line x1="${{d.x1}}" y1="${{d.y1}}" x2="${{d.x2}}" y2="${{d.y2}}" stroke="#0284c7" stroke-width="1.6" stroke-dasharray="4 3" marker-end="url(#cdx-ah-blue)"/>`;
      }}
    }}

    svg.innerHTML = h;
    updateMetrics();
  }}

  // Tool & Element Selection Helpers
  function selectTool(slot, subId) {{
    state.ringTool = null;
    document.querySelectorAll("#cdx-rings-bar .cdx-rbtn").forEach((b) => b.classList.remove("is-active"));
    state.slot = slot;
    if (subId) state.activeSub[slot] = subId;
    state.tool = subId || state.activeSub[slot] || slot;
    document.querySelectorAll(".cdx-left [data-slot]").forEach((b) => b.classList.toggle("is-active", b.dataset.slot === slot));
    flyoutEl.hidden = true;
    setToast(`Tool: ${{state.tool}}`);
    render();
  }}

  function setActiveElem(el, iso = 0, qlock = null) {{
    state.elem = el; state.iso = iso; state.qLock = qlock;
    document.querySelectorAll(".cdx-right .cdx-elbtn").forEach((b) => b.classList.toggle("is-active", b.dataset.elem === el && !iso));
    if (state.slot === "select" || state.slot === "erase") selectTool("bond", state.activeSub.bond);
    setToast(`Active atom: ${{iso ? iso : ""}}${{el}}${{qlock ? " (" + qlock + ")" : ""}}`);
  }}

  // Left toolbar clicks & flyout menus
  document.querySelectorAll(".cdx-left [data-slot]").forEach((btn) => {{
    btn.addEventListener("click", (ev) => {{
      ev.stopPropagation();
      const slot = btn.dataset.slot;
      const subs = SUBTOOLS[slot];
      if (state.slot === slot && subs && !state.ringTool) {{
        // Toggle flyout menu
        if (!flyoutEl.hidden && flyoutEl.dataset.slot === slot) {{ flyoutEl.hidden = true; return; }}
        flyoutEl.dataset.slot = slot;
        flyoutEl.style.top = (btn.offsetTop + 2) + "px";
        flyoutEl.innerHTML = subs.map((s) => `<button type="button" class="cdx-flybtn ${{state.tool === s.id ? "is-active" : ""}}" data-sub="${{s.id}}">${{esc(s.label)}}</button>`).join("");
        flyoutEl.hidden = false;
        flyoutEl.querySelectorAll("[data-sub]").forEach((sb) => sb.addEventListener("click", () => selectTool(slot, sb.dataset.sub)));
        return;
      }}
      selectTool(slot, subs ? state.activeSub[slot] : slot);
    }});
  }});
  document.addEventListener("click", () => {{ flyoutEl.hidden = true; }});

  // Right element buttons
  document.querySelectorAll(".cdx-right [data-elem]").forEach((btn) => {{
    btn.addEventListener("click", () => setActiveElem(btn.dataset.elem, 0, null));
  }});

  // Bottom ring dock buttons
  document.querySelectorAll("#cdx-rings-bar [data-ring]").forEach((btn) => {{
    btn.addEventListener("click", () => {{
      const rk = btn.dataset.ring;
      state.ringTool = rk;
      document.querySelectorAll(".cdx-left [data-slot]").forEach((b) => b.classList.remove("is-active"));
      document.querySelectorAll("#cdx-rings-bar .cdx-rbtn").forEach((b) => b.classList.toggle("is-active", b === btn));
      setToast(`Ring: ${{rk}} · Hover bond to fuse, atom for spiro, or canvas to place`);
      render();
    }});
  }});

  // Floating Hotbox for Atom Formula / R-Group / Arrow Conditions
  let hotboxTarget = null;
  function openHotbox(screenX, screenY, initVal, onCommit) {{
    const rect = stageWrap.getBoundingClientRect();
    hotboxEl.style.left = Math.max(6, Math.min(rect.width - 185, screenX - rect.left)) + "px";
    hotboxEl.style.top = Math.max(6, Math.min(rect.height - 34, screenY - rect.top)) + "px";
    hotboxIn.value = initVal || "";
    hotboxTarget = onCommit;
    hotboxEl.hidden = false;
    setTimeout(() => {{ hotboxIn.focus(); hotboxIn.select(); }}, 10);
  }}
  function commitHotbox() {{
    if (hotboxTarget) {{
      const val = hotboxIn.value.trim();
      hotboxTarget(val);
      hotboxTarget = null;
    }}
    hotboxEl.hidden = true;
    render(); syncHostState();
  }}
  document.getElementById("cdx-hotbox-ok").addEventListener("click", commitHotbox);
  hotboxIn.addEventListener("keydown", (ev) => {{
    if (ev.key === "Enter") {{ ev.preventDefault(); commitHotbox(); }}
    else if (ev.key === "Escape") {{ hotboxTarget = null; hotboxEl.hidden = true; }}
  }});

  function deleteAtomAt(g, ai) {{
    g.atoms.splice(ai, 1);
    g.bonds = g.bonds.filter((b) => b.a !== ai && b.b !== ai).map((b) => ({{
      ...b, a: b.a > ai ? b.a - 1 : b.a, b: b.b > ai ? b.b - 1 : b.b
    }}));
    state.selAtoms.clear();
  }}

  function pointInPolygon(pt, poly) {{
    let inside = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {{
      const xi = poly[i].x, yi = poly[i].y, xj = poly[j].x, yj = poly[j].y;
      if (((yi > pt.y) !== (yj > pt.y)) && (pt.x < ((xj - xi) * (pt.y - yi)) / (yj - yi + 1e-9) + xi)) inside = !inside;
    }}
    return inside;
  }}

  // Pointer Interactions on SVG Canvas
  svg.addEventListener("dblclick", (ev) => {{
    const p = svgPoint(ev);
    const g = state.graph;
    const ai = hitAtom(g, p, 14);
    if (ai >= 0) {{
      openHotbox(ev.clientX, ev.clientY, g.atoms[ai].s, (val) => {{
        if (!val) return;
        pushUndo();
        g.atoms[ai].s = val;
      }});
      return;
    }}
    // Check arrow hit
    const ari = g.arrows.findIndex((ar) => Math.hypot(p.x - (ar.x1 + ar.x2)/2, p.y - (ar.y1 + ar.y2)/2) < 35);
    if (ari >= 0) {{
      const cur = (g.arrows[ari].above || "") + " | " + (g.arrows[ari].below || "");
      openHotbox(ev.clientX, ev.clientY, cur, (val) => {{
        pushUndo();
        const [ab, bl] = val.split("|").map((s) => s.trim());
        g.arrows[ari].above = ab || "";
        g.arrows[ari].below = bl || "";
      }});
    }}
  }});

  svg.addEventListener("pointerdown", (ev) => {{
    if (!hotboxEl.hidden) commitHotbox();
    const p = svgPoint(ev);
    const g = state.graph;
    const ai = hitAtom(g, p), bi = hitBond(g, p);

    // Middle-button or Spacebar pan
    if (ev.button === 1 || ev.altKey) {{
      state.drag = {{kind: "pan", sx: ev.clientX, sy: ev.clientY, cx0: state.cam.x, cy0: state.cam.y}};
      svg.setPointerCapture(ev.pointerId);
      return;
    }}

    // Ring tool active
    if (state.ringTool) {{
      pushUndo();
      placeRing(g, state.ringTool, p, ai, bi);
      render(); syncHostState();
      return;
    }}

    const t = state.tool;

    // Selection modes + Bounding-box move & rotation handle
    if (t.startsWith("sel-")) {{
      if (state.selAtoms.size > 0) {{
        const sPts = [...state.selAtoms].map((i) => g.atoms[i]).filter(Boolean);
        const minX = Math.min(...sPts.map((q) => q.x)) - 14, maxX = Math.max(...sPts.map((q) => q.x)) + 14;
        const minY = Math.min(...sPts.map((q) => q.y)) - 14, maxY = Math.max(...sPts.map((q) => q.y)) + 14;
        const midX = (minX + maxX) / 2, cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
        if (Math.hypot(p.x - midX, p.y - (minY - 17)) < 10) {{
          pushUndo();
          const orig = new Map([...state.selAtoms].map((i) => [i, {{x: g.atoms[i].x, y: g.atoms[i].y}}]));
          state.drag = {{kind: "rot-sel", cx, cy, a0: Math.atan2(p.y - cy, p.x - cx), orig}};
          svg.setPointerCapture(ev.pointerId);
          return;
        }}
        if (p.x >= minX && p.x <= maxX && p.y >= minY && p.y <= maxY) {{
          pushUndo();
          const orig = new Map([...state.selAtoms].map((i) => [i, {{x: g.atoms[i].x, y: g.atoms[i].y}}]));
          state.drag = {{kind: "move-sel", p0: p, orig}};
          svg.setPointerCapture(ev.pointerId);
          return;
        }}
      }}
      if (ai >= 0) {{
        if (t === "sel-frag") {{
          if (!ev.shiftKey) state.selAtoms.clear();
          const q = [ai]; state.selAtoms.add(ai);
          while (q.length) {{
            const u = q.shift();
            neighbors(g, u).forEach((nb) => {{ if (!state.selAtoms.has(nb.to)) {{ state.selAtoms.add(nb.to); q.push(nb.to); }} }});
          }}
        }} else {{
          if (!ev.shiftKey) state.selAtoms.clear();
          state.selAtoms.add(ai);
        }}
        pushUndo();
        const orig = new Map([...state.selAtoms].map((i) => [i, {{x: g.atoms[i].x, y: g.atoms[i].y}}]));
        state.drag = {{kind: "move-sel", p0: p, orig}};
        svg.setPointerCapture(ev.pointerId);
        render(); return;
      }}
      if (!ev.shiftKey) state.selAtoms.clear();
      state.drag = t === "sel-box" ? {{kind: "box", x1: p.x, y1: p.y, x2: p.x, y2: p.y}} : {{kind: "lasso", pts: [p]}};
      svg.setPointerCapture(ev.pointerId);
      render(); return;
    }}

    // Eraser (click + drag sweep)
    if (t === "erase") {{
      pushUndo();
      if (ai >= 0) deleteAtomAt(g, ai);
      else if (bi >= 0) g.bonds.splice(bi, 1);
      else {{
        const ari = g.arrows.findIndex((ar) => Math.hypot(p.x - (ar.x1+ar.x2)/2, p.y - (ar.y1+ar.y2)/2) < 22);
        if (ari >= 0) g.arrows.splice(ari, 1);
        const pli = g.pluses.findIndex((pl) => Math.hypot(p.x - pl.x, p.y - pl.y) < 14);
        if (pli >= 0) g.pluses.splice(pli, 1);
      }}
      state.drag = {{kind: "erase-sweep"}};
      svg.setPointerCapture(ev.pointerId);
      render(); return;
    }}

    // Charge / Radical tools
    if (t.startsWith("chg-") && ai >= 0) {{
      pushUndo();
      const a = g.atoms[ai];
      if (t === "chg-plus") a.chg = ((a.chg || 0) >= 3) ? 0 : (a.chg || 0) + 1;
      else if (t === "chg-minus") a.chg = ((a.chg || 0) <= -3) ? 0 : (a.chg || 0) - 1;
      else a.rad = ((a.rad || 0) + 1) % 3;
      render(); syncHostState(); return;
    }}

    // Formula / Text tool
    if (t === "text") {{
      if (ai >= 0) {{
        openHotbox(ev.clientX, ev.clientY, g.atoms[ai].s, (val) => {{
          if (!val) return; pushUndo(); g.atoms[ai].s = val;
        }});
      }} else {{
        openHotbox(ev.clientX, ev.clientY, "", (val) => {{
          if (!val) return; pushUndo(); g.texts.push({{x: +p.x.toFixed(1), y: +p.y.toFixed(1), text: val}});
        }});
      }}
      return;
    }}

    // Zigzag Alkane Chain Tool
    if (t === "chain") {{
      pushUndo();
      const p0 = ai >= 0 ? {{x: g.atoms[ai].x, y: g.atoms[ai].y, ai}} : {{x: +p.x.toFixed(2), y: +p.y.toFixed(2), ai: -1}};
      state.drag = {{kind: "chain", start: p0, pts: [p0]}};
      svg.setPointerCapture(ev.pointerId);
      render(); return;
    }}

    // Reaction & Mechanism tools
    if (t.startsWith("rxn-")) {{
      if (t === "rxn-plus") {{
        pushUndo(); g.pluses.push({{x: +p.x.toFixed(1), y: +p.y.toFixed(1)}}); render(); syncHostState(); return;
      }}
      if (t === "rxn-map" && ai >= 0) {{
        state.drag = {{kind: "map", src: ai, x1: g.atoms[ai].x, y1: g.atoms[ai].y, x2: p.x, y2: p.y}};
        svg.setPointerCapture(ev.pointerId); render(); return;
      }}
      if (t === "rxn-curv2" || t === "rxn-curv1") {{
        let sx = p.x, sy = p.y;
        if (ai >= 0) {{ sx = g.atoms[ai].x; sy = g.atoms[ai].y; }}
        else if (bi >= 0) {{ sx = (g.atoms[g.bonds[bi].a].x + g.atoms[g.bonds[bi].b].x)/2; sy = (g.atoms[g.bonds[bi].a].y + g.atoms[g.bonds[bi].b].y)/2; }}
        state.drag = {{kind: "curv", el: t === "rxn-curv1" ? 1 : 2, x1: sx, y1: sy, x2: sx, y2: sy}};
        svg.setPointerCapture(ev.pointerId); render(); return;
      }}
      state.drag = {{kind: "arrow", style: t.replace("rxn-", ""), x1: p.x, y1: p.y, x2: p.x + 80, y2: p.y, moved: false}};
      svg.setPointerCapture(ev.pointerId); render(); return;
    }}

    // Markush & Polymer Brackets
    if (t.startsWith("mk-")) {{
      if (t === "mk-bracket") {{
        state.drag = {{kind: "bracket", x1: p.x, y1: p.y, x2: p.x, y2: p.y}};
        svg.setPointerCapture(ev.pointerId); render(); return;
      }}
      const rings = findSmallRings(g);
      const hitRing = rings.find((r) => pointInPolygon(p, r.map((i) => g.atoms[i])));
      if (t === "mk-fill" && hitRing) {{
        pushUndo();
        g.ring_fills.push({{atoms: hitRing, color: "rgba(56,189,248,0.24)"}});
        render(); syncHostState(); return;
      }}
      if (t === "mk-var" && hitRing) {{
        pushUndo();
        const rcx = +(hitRing.reduce((s, i) => s + g.atoms[i].x, 0) / hitRing.length).toFixed(2);
        const rcy = +(hitRing.reduce((s, i) => s + g.atoms[i].y, 0) / hitRing.length).toFixed(2);
        const ci = g.atoms.length;
        g.atoms.push({{s: "*", x: rcx, y: rcy, multicenterCenter: true}});
        const ang = Math.atan2(p.y - rcy, p.x - rcx);
        const ri = g.atoms.length;
        g.atoms.push({{s: state.elem === "C" ? "R1" : state.elem, x: +(rcx + Math.cos(ang) * BOND_L * 1.45).toFixed(2), y: +(rcy + Math.sin(ang) * BOND_L * 1.45).toFixed(2)}});
        g.bonds.push({{a: ci, b: ri, o: 1, multicenter: true}});
        render(); syncHostState(); return;
      }}
      return;
    }}

    // Bond / Stereo / Query-Bond click on existing bond
    if (bi >= 0 && ai < 0) {{
      pushUndo();
      const b = g.bonds[bi];
      delete b.q; delete b.ez;
      if (t.startsWith("qb-")) {{
        b.o = 1; b.q = t.replace("qb-", "");
      }} else if (t === "st-wedge") {{
        if (b.o === 4) {{ const tmp = b.a; b.a = b.b; b.b = tmp; }} else b.o = 4;
      }} else if (t === "st-hash") {{
        if (b.o === 5) {{ const tmp = b.a; b.a = b.b; b.b = tmp; }} else b.o = 5;
      }} else if (t === "st-wavy") b.o = 6;
      else if (t === "st-bold") b.o = 7;
      else if (t === "st-ez") {{ b.o = 2; b.ez = true; }}
      else if (t === "bond-2") {{
        if (b.o === 2) b.side = ((b.side || 0) + 1) % 4;
        else {{ b.o = 2; b.side = 0; }}
      }} else if (t === "bond-3") b.o = 3;
      else b.o = b.o === 1 ? 2 : (b.o === 2 ? 3 : 1);
      render(); syncHostState(); return;
    }}

    // Start Bond Drawing from Atom or Empty Space
    pushUndo();
    let src = ai;
    let createdSrc = false;
    if (src < 0) {{
      src = g.atoms.length;
      const na = {{s: state.elem, x: +p.x.toFixed(2), y: +p.y.toFixed(2)}};
      if (state.iso) na.iso = state.iso;
      if (state.qLock) na.qlock = state.qLock;
      g.atoms.push(na);
      createdSrc = true;
    }}
    const newOrd = t === "bond-2" ? 2 : (t === "bond-3" ? 3 : (t === "st-wedge" ? 4 : (t === "st-hash" ? 5 : (t === "st-wavy" ? 6 : (t === "st-bold" ? 7 : 1)))));
    const spAng = sproutAngle(g, src, newOrd);
    state.drag = {{
      kind: "bond", src, createdSrc, ord: newOrd,
      q: t.startsWith("qb-") ? t.replace("qb-", "") : null,
      ez: t === "st-ez",
      x1: g.atoms[src].x, y1: g.atoms[src].y,
      x2: +(g.atoms[src].x + Math.cos(spAng) * BOND_L).toFixed(2),
      y2: +(g.atoms[src].y + Math.sin(spAng) * BOND_L).toFixed(2),
      moved: false, snapAi: -1
    }};
    svg.setPointerCapture(ev.pointerId);
    render();
  }});

  svg.addEventListener("pointermove", (ev) => {{
    const p = svgPoint(ev);
    const g = state.graph;
    state.hover.pt = p;
    state.hover.ai = hitAtom(g, p);
    state.hover.bi = state.hover.ai >= 0 ? -1 : hitBond(g, p);

    if (!state.drag) {{
      if (state.ringTool || state.hover.ai >= 0 || state.hover.bi >= 0) render();
      return;
    }}
    const d = state.drag;
    if (d.kind === "pan") {{
      const rect = svg.getBoundingClientRect();
      state.cam.x = d.cx0 - (ev.clientX - d.sx) * (state.cam.w / (rect.width || 680));
      state.cam.y = d.cy0 - (ev.clientY - d.sy) * (state.cam.h / (rect.height || 356));
      updateViewBox(); return;
    }}
    if (d.kind === "move-sel") {{
      const dx = p.x - d.p0.x, dy = p.y - d.p0.y;
      d.orig.forEach((pos, idx) => {{
        g.atoms[idx].x = +(pos.x + dx).toFixed(2);
        g.atoms[idx].y = +(pos.y + dy).toFixed(2);
      }});
      render(); return;
    }}
    if (d.kind === "rot-sel") {{
      const da = Math.atan2(p.y - d.cy, p.x - d.cx) - d.a0;
      const cs = Math.cos(da), sn = Math.sin(da);
      d.orig.forEach((pos, idx) => {{
        const rx = pos.x - d.cx, ry = pos.y - d.cy;
        g.atoms[idx].x = +(d.cx + rx * cs - ry * sn).toFixed(2);
        g.atoms[idx].y = +(d.cy + rx * sn + ry * cs).toFixed(2);
      }});
      render(); return;
    }}
    if (d.kind === "erase-sweep") {{
      if (state.hover.ai >= 0) deleteAtomAt(g, state.hover.ai);
      else if (state.hover.bi >= 0) g.bonds.splice(state.hover.bi, 1);
      render(); return;
    }}
    if (d.kind === "box") {{ d.x2 = p.x; d.y2 = p.y; render(); return; }}
    if (d.kind === "lasso") {{ d.pts.push(p); render(); return; }}
    if (d.kind === "arrow" || d.kind === "map" || d.kind === "curv" || d.kind === "bracket") {{
      d.moved = true; d.x2 = p.x; d.y2 = p.y; render(); return;
    }}
    if (d.kind === "chain") {{
      const dx = p.x - d.start.x, dy = p.y - d.start.y, dist = Math.hypot(dx, dy);
      const count = Math.max(2, Math.min(24, Math.floor(dist / (BOND_L * 0.86)) + 1));
      const baseAng = Math.round(Math.atan2(dy, dx) / (Math.PI / 6)) * (Math.PI / 6);
      const pts = [d.start];
      for (let k = 1; k < count; k++) {{
        const prev = pts[k - 1];
        const a = baseAng + (k % 2 === 1 ? -Math.PI / 6 : Math.PI / 6);
        pts.push({{x: +(prev.x + Math.cos(a) * BOND_L).toFixed(2), y: +(prev.y + Math.sin(a) * BOND_L).toFixed(2)}});
      }}
      d.pts = pts;
      render(); return;
    }}
    if (d.kind === "bond") {{
      if (Math.hypot(p.x - d.x1, p.y - d.y1) > 7) d.moved = true;
      const near = hitAtom(g, p, 14);
      if (near >= 0 && near !== d.src) {{
        d.x2 = g.atoms[near].x; d.y2 = g.atoms[near].y; d.snapAi = near;
      }} else {{
        d.snapAi = -1;
        if (d.moved) {{
          const snapStep = ev.shiftKey ? Math.PI / 36 : Math.PI / 6;
          const ang = Math.round(Math.atan2(p.y - d.y1, p.x - d.x1) / snapStep) * snapStep;
          d.x2 = +(d.x1 + Math.cos(ang) * BOND_L).toFixed(2);
          d.y2 = +(d.y1 + Math.sin(ang) * BOND_L).toFixed(2);
        }}
      }}
      render();
    }}
  }});

  svg.addEventListener("pointerup", () => {{
    if (!state.drag) return;
    const d = state.drag;
    const g = state.graph;
    state.drag = null;

    if (d.kind === "box") {{
      const x1 = Math.min(d.x1, d.x2), x2 = Math.max(d.x1, d.x2);
      const y1 = Math.min(d.y1, d.y2), y2 = Math.max(d.y1, d.y2);
      g.atoms.forEach((a, i) => {{ if (a.x >= x1 && a.x <= x2 && a.y >= y1 && a.y <= y2) state.selAtoms.add(i); }});
    }} else if (d.kind === "lasso" && d.pts.length >= 3) {{
      g.atoms.forEach((a, i) => {{ if (pointInPolygon(a, d.pts)) state.selAtoms.add(i); }});
    }} else if (d.kind === "arrow") {{
      pushUndo();
      g.arrows.push({{x1: +d.x1.toFixed(1), y1: +d.y1.toFixed(1), x2: +(d.moved ? d.x2 : d.x1 + 92).toFixed(1), y2: +(d.moved ? d.y2 : d.y1).toFixed(1), style: d.style, above: "", below: ""}});
    }} else if (d.kind === "map") {{
      const dst = hitAtom(g, {{x: d.x2, y: d.y2}}, 14);
      if (dst >= 0 && dst !== d.src) {{
        pushUndo();
        const m = g.atoms[d.src].map || state.nextMap++;
        g.atoms[d.src].map = m; g.atoms[dst].map = m;
        setToast(`Mapped atom [${{m}}]`);
      }}
    }} else if (d.kind === "curv" && Math.hypot(d.x2 - d.x1, d.y2 - d.y1) > 12) {{
      pushUndo();
      g.curved.push({{x1: +d.x1.toFixed(1), y1: +d.y1.toFixed(1), x2: +d.x2.toFixed(1), y2: +d.y2.toFixed(1), el: d.el}});
    }} else if (d.kind === "bracket" && Math.hypot(d.x2 - d.x1, d.y2 - d.y1) > 14) {{
      pushUndo();
      g.brackets.push({{x1: +d.x1.toFixed(1), y1: +d.y1.toFixed(1), x2: +d.x2.toFixed(1), y2: +d.y2.toFixed(1), label: "n"}});
    }} else if (d.kind === "chain") {{
      let prevIdx = d.start.ai;
      if (prevIdx < 0) {{
        prevIdx = g.atoms.length;
        g.atoms.push({{s: "C", x: d.pts[0].x, y: d.pts[0].y}});
      }}
      for (let k = 1; k < d.pts.length; k++) {{
        const ex = hitAtom(g, d.pts[k], 9);
        const curIdx = ex >= 0 ? ex : g.atoms.length;
        if (ex < 0) g.atoms.push({{s: "C", x: d.pts[k].x, y: d.pts[k].y}});
        if (curIdx !== prevIdx && bondExists(g, prevIdx, curIdx) < 0) g.bonds.push({{a: prevIdx, b: curIdx, o: 1}});
        prevIdx = curIdx;
      }}
    }} else if (d.kind === "bond") {{
      // Click on existing atom without dragging -> relabel if non-C element selected, else sprout!
      if (!d.moved && !d.createdSrc && (state.elem !== "C" || state.iso || state.qLock) && g.atoms[d.src].s !== state.elem) {{
        g.atoms[d.src].s = state.elem;
        if (state.iso) g.atoms[d.src].iso = state.iso; else delete g.atoms[d.src].iso;
        if (state.qLock) g.atoms[d.src].qlock = state.qLock; else delete g.atoms[d.src].qlock;
      }} else {{
        let dst = d.snapAi >= 0 ? d.snapAi : hitAtom(g, {{x: d.x2, y: d.y2}}, 10);
        if (dst < 0) {{
          dst = g.atoms.length;
          const na = {{s: d.createdSrc ? "C" : state.elem, x: d.x2, y: d.y2}};
          if (!d.createdSrc && state.iso) na.iso = state.iso;
          if (!d.createdSrc && state.qLock) na.qlock = state.qLock;
          g.atoms.push(na);
        }}
        if (dst !== d.src) {{
          const eb = bondExists(g, d.src, dst);
          if (eb >= 0) {{
            g.bonds[eb].o = g.bonds[eb].o === 1 ? 2 : 1;
          }} else {{
            const nb = {{a: d.src, b: dst, o: d.ord}};
            if (d.q) nb.q = d.q;
            if (d.ez) nb.ez = true;
            g.bonds.push(nb);
          }}
        }}
      }}
    }}
    render(); syncHostState();
  }});

  // Wheel Zoom
  svg.addEventListener("wheel", (ev) => {{
    ev.preventDefault();
    const factor = ev.deltaY < 0 ? 1.12 : 1 / 1.12;
    const nz = Math.max(0.4, Math.min(3.5, state.cam.zoom * factor));
    const p = svgPoint(ev);
    const nw = 680 / nz, nh = (root.classList.contains("is-tall") ? 520 : 356) / nz;
    state.cam.x = p.x - ((p.x - state.cam.x) / state.cam.w) * nw;
    state.cam.y = p.y - ((p.y - state.cam.y) / state.cam.h) * nh;
    state.cam.w = nw; state.cam.h = nh; state.cam.zoom = nz;
    updateViewBox();
  }}, {{passive: false}});

  function zoomBy(factor) {{
    const cx = state.cam.x + state.cam.w / 2, cy = state.cam.y + state.cam.h / 2;
    const nz = Math.max(0.4, Math.min(3.5, state.cam.zoom * factor));
    const nw = 680 / nz, nh = (root.classList.contains("is-tall") ? 520 : 356) / nz;
    state.cam.x = cx - nw / 2; state.cam.y = cy - nh / 2;
    state.cam.w = nw; state.cam.h = nh; state.cam.zoom = nz;
    updateViewBox();
  }}
  function fitZoom() {{
    const g = state.graph;
    const baseH = root.classList.contains("is-tall") ? 520 : 356;
    if (!g.atoms.length) {{
      state.cam = {{x: 0, y: 0, w: 680, h: baseH, zoom: 1}};
      updateViewBox(); return;
    }}
    const xs = g.atoms.map((a) => a.x), ys = g.atoms.map((a) => a.y);
    const pad = 55;
    const spanX = Math.max(180, Math.max(...xs) - Math.min(...xs) + pad * 2);
    const spanY = Math.max(120, Math.max(...ys) - Math.min(...ys) + pad * 2);
    const z = Math.min(1.6, Math.min(680 / spanX, baseH / spanY));
    const nw = 680 / z, nh = baseH / z;
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2, cy = (Math.min(...ys) + Math.max(...ys)) / 2;
    state.cam = {{x: cx - nw / 2, y: cy - nh / 2, w: nw, h: nh, zoom: z}};
    updateViewBox();
  }}
  document.getElementById("cdx-z-in").addEventListener("click", () => zoomBy(1.18));
  document.getElementById("cdx-z-out").addEventListener("click", () => zoomBy(1 / 1.18));
  document.getElementById("cdx-z-fit").addEventListener("click", fitZoom);

  // Top Bar Actions
  document.getElementById("cdx-act-new").addEventListener("click", () => {{
    pushUndo(); state.graph = normalizeGraph({{}}); state.selAtoms.clear(); render(); syncHostState();
  }});
  document.getElementById("cdx-act-undo").addEventListener("click", () => {{
    if (!state.undoStack.length) return;
    state.redoStack.push(clone(state.graph));
    state.graph = state.undoStack.pop(); render(); syncHostState();
  }});
  document.getElementById("cdx-act-redo").addEventListener("click", () => {{
    if (!state.redoStack.length) return;
    state.undoStack.push(clone(state.graph));
    state.graph = state.redoStack.pop(); render(); syncHostState();
  }});
  document.getElementById("cdx-act-dup").addEventListener("click", () => {{
    const g = state.graph;
    const src = state.selAtoms.size > 0 ? [...state.selAtoms] : g.atoms.map((_, i) => i);
    if (!src.length) return;
    pushUndo();
    const map = new Map();
    state.selAtoms.clear();
    src.forEach((i) => {{
      const ni = g.atoms.length;
      map.set(i, ni);
      g.atoms.push({{...clone(g.atoms[i]), x: +(g.atoms[i].x + 42).toFixed(2), y: +(g.atoms[i].y + 24).toFixed(2)}});
      state.selAtoms.add(ni);
    }});
    const snapBonds = [...g.bonds];
    snapBonds.forEach((b) => {{
      if (map.has(b.a) && map.has(b.b)) g.bonds.push({{...clone(b), a: map.get(b.a), b: map.get(b.b)}});
    }});
    selectTool("select", "sel-lasso");
    render(); syncHostState();
  }});
  document.getElementById("cdx-act-clean").addEventListener("click", () => clean2D(state.graph));
  document.getElementById("cdx-act-arom").addEventListener("click", () => {{
    pushUndo(); state.graph.arom_circles = !state.graph.arom_circles; render();
    setToast(state.graph.arom_circles ? "Thiele aromatic circles ON" : "Kekule double bonds ON");
  }});
  document.getElementById("cdx-act-expand").addEventListener("click", () => expandAbbreviations(state.graph));

  function transformTargetAtoms(fn) {{
    const g = state.graph;
    const idxs = state.selAtoms.size > 0 ? [...state.selAtoms] : g.atoms.map((_, i) => i);
    if (!idxs.length) return;
    pushUndo();
    const cx = idxs.reduce((s, i) => s + g.atoms[i].x, 0) / idxs.length;
    const cy = idxs.reduce((s, i) => s + g.atoms[i].y, 0) / idxs.length;
    idxs.forEach((i) => fn(g.atoms[i], cx, cy));
    render(); syncHostState();
  }}
  document.getElementById("cdx-act-fliph").addEventListener("click", () => transformTargetAtoms((a, cx) => {{ a.x = +(2 * cx - a.x).toFixed(2); }}));
  document.getElementById("cdx-act-flipv").addEventListener("click", () => transformTargetAtoms((a, _cx, cy) => {{ a.y = +(2 * cy - a.y).toFixed(2); }}));
  document.getElementById("cdx-act-rot").addEventListener("click", () => transformTargetAtoms((a, cx, cy) => {{
    const rx = a.x - cx, ry = a.y - cy, cs = Math.cos(Math.PI / 6), sn = Math.sin(Math.PI / 6);
    a.x = +(cx + rx * cs - ry * sn).toFixed(2); a.y = +(cy + rx * sn + ry * cs).toFixed(2);
  }}));
  document.getElementById("cdx-act-grid").addEventListener("click", () => stageWrap.classList.toggle("no-grid"));
  document.getElementById("cdx-act-tall").addEventListener("click", () => {{
    root.classList.toggle("is-tall"); fitZoom(); notifyResize();
  }});
  document.getElementById("cdx-query-mode").addEventListener("change", updateMetrics);

  // Modals: Periodic Table, Reaxys/SciFinder Query Generics, Import, Export, Templates
  function openModal(html) {{
    modalEl.innerHTML = html;
    backdropEl.hidden = false;
    const closeBtn = modalEl.querySelector("[data-close]");
    if (closeBtn) closeBtn.addEventListener("click", () => {{ backdropEl.hidden = true; }});
  }}
  backdropEl.addEventListener("click", (ev) => {{ if (ev.target === backdropEl) backdropEl.hidden = true; }});

  document.getElementById("cdx-open-pt").addEventListener("click", () => {{
    let cells = "";
    for (let r = 1; r <= 8; r++) {{
      for (let c = 1; c <= 18; c++) {{
        const item = PT_DATA.find((x) => x[2] === r && x[3] === c);
        if (item) {{
          cells += `<button type="button" class="cdx-pt-cell" data-pt="${{item[1]}}" style="background:${{item[4]}}"><small>${{item[0]}}</small>${{item[1]}}</button>`;
        }} else {{
          cells += `<div></div>`;
        }}
      }}
    }}
    openModal(`<div style="display:flex;justify-content:space-between;align-items:center">
        <strong>Periodic Table &amp; Isotopes</strong>
        <button type="button" class="cdx-ibtn" data-close="1">✕</button>
      </div>
      <div class="cdx-pt-grid">${{cells}}</div>
      <div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:4px;align-items:center">
        <span style="font-size:11px;font-weight:600;color:var(--cdx-muted)">Isotopes:</span>
        <button type="button" class="cdx-ibtn" data-iso="D:0" style="border:1px solid var(--cdx-border)">D (²H)</button>
        <button type="button" class="cdx-ibtn" data-iso="T:0" style="border:1px solid var(--cdx-border)">T (³H)</button>
        <button type="button" class="cdx-ibtn" data-iso="C:13" style="border:1px solid var(--cdx-border)">¹³C</button>
        <button type="button" class="cdx-ibtn" data-iso="N:15" style="border:1px solid var(--cdx-border)">¹⁵N</button>
        <button type="button" class="cdx-ibtn" data-iso="O:18" style="border:1px solid var(--cdx-border)">¹⁸O</button>
        <button type="button" class="cdx-ibtn" data-iso="F:19" style="border:1px solid var(--cdx-border)">¹⁹F</button>
      </div>`);
    modalEl.querySelectorAll("[data-pt]").forEach((b) => b.addEventListener("click", () => {{
      setActiveElem(b.dataset.pt, 0, null); backdropEl.hidden = true;
    }}));
    modalEl.querySelectorAll("[data-iso]").forEach((b) => b.addEventListener("click", () => {{
      const [s, m] = b.dataset.iso.split(":");
      setActiveElem(s, parseInt(m, 10) || 0, null); backdropEl.hidden = true;
    }}));
  }});

  document.getElementById("cdx-open-qry").addEventListener("click", () => {{
    const gens = [
      ["A","Any heavy atom (!H)"],["Q","Heteroatom (!C,!H)"],["X","Any halogen (F,Cl,Br,I)"],
      ["M","Any metal"],["*","Attachment point *"],["R1","R1 group"],["R2","R2 group"],["R3","R3 group"],["Ar","Aryl (Ar)"]
    ];
    openModal(`<div style="display:flex;justify-content:space-between;align-items:center">
        <strong>Reaxys / SciFinder Substructure Query Generics &amp; Atom Locks</strong>
        <button type="button" class="cdx-ibtn" data-close="1">✕</button>
      </div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-top:8px">
        ${{gens.map(([k, d]) => `<button type="button" class="cdx-ibtn" data-qel="${{k}}" style="justify-content:flex-start;border:1px solid var(--cdx-border);padding:4px 8px"><b>${{k}}</b>&nbsp;<span style="font-size:10.5px;color:var(--cdx-muted)">${{d}}</span></button>`).join("")}}
      </div>
      <div style="margin-top:10px;display:flex;gap:6px;align-items:center;flex-wrap:wrap">
        <span style="font-size:11px;font-weight:600">Atom List / NOT List:</span>
        <input id="cdx-alist" value="[N,O,S]" style="height:25px;padding:0 6px;border:1px solid var(--cdx-border);border-radius:4px;background:var(--cdx-frame)" />
        <button type="button" class="cdx-ibtn is-active" id="cdx-alist-use" style="padding:0 9px">Use List</button>
      </div>
      <div style="margin-top:10px;display:flex;gap:5px;align-items:center;flex-wrap:wrap">
        <span style="font-size:11px;font-weight:600">Substructure Atom Locks:</span>
        <button type="button" class="cdx-ibtn" data-qlk="s*" style="border:1px solid var(--cdx-border);padding:0 8px">s* (Lock Open Sites / No Substitution)</button>
        <button type="button" class="cdx-ibtn" data-qlk="R0" style="border:1px solid var(--cdx-border);padding:0 8px">R0 (Chain Atom Only)</button>
        <button type="button" class="cdx-ibtn" data-qlk="R" style="border:1px solid var(--cdx-border);padding:0 8px">R (Must Be In Ring)</button>
      </div>`);
    modalEl.querySelectorAll("[data-qel]").forEach((b) => b.addEventListener("click", () => {{
      document.getElementById("cdx-query-mode").value = "substructure";
      setActiveElem(b.dataset.qel, 0, null); backdropEl.hidden = true;
    }}));
    modalEl.querySelector("#cdx-alist-use").addEventListener("click", () => {{
      const v = modalEl.querySelector("#cdx-alist").value.trim() || "[N,O]";
      document.getElementById("cdx-query-mode").value = "substructure";
      setActiveElem(v.startsWith("[") ? v : `[${{v}}]`, 0, null); backdropEl.hidden = true;
    }});
    modalEl.querySelectorAll("[data-qlk]").forEach((b) => b.addEventListener("click", () => {{
      const lk = b.dataset.qlk;
      document.getElementById("cdx-query-mode").value = "substructure";
      if (state.selAtoms.size > 0) {{
        pushUndo();
        state.selAtoms.forEach((i) => {{ state.graph.atoms[i].qlock = lk; }});
        render();
      }} else setActiveElem(state.elem, state.iso, lk);
      backdropEl.hidden = true;
    }}));
  }});

  // Templates & Functional Groups Modal
  document.getElementById("cdx-act-tmpl").addEventListener("click", () => {{
    const fgs = Object.keys(ABBR);
    const tmplEntries = Object.entries(CATALOG).filter(([k]) => k !== "blank" && k !== "empty");
    openModal(`<div style="display:flex;justify-content:space-between;align-items:center">
        <strong>Functional Group Stamps &amp; Structure Templates</strong>
        <button type="button" class="cdx-ibtn" data-close="1">✕</button>
      </div>
      <div style="font-size:11px;font-weight:600;color:var(--cdx-muted);margin:6px 0 4px">FUNCTIONAL &amp; PROTECTING GROUPS (click to select stamp, then click/drag on canvas; use R→At to expand)</div>
      <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px">
        ${{fgs.map((fg) => `<button type="button" class="cdx-ibtn" data-fg="${{fg}}" style="border:1px solid var(--cdx-border);font-weight:600">${{fg}}</button>`).join("")}}
      </div>
      <div style="font-size:11px;font-weight:600;color:var(--cdx-muted);margin:10px 0 4px">SCAFFOLDS, CONFORMERS &amp; NAMED REACTIONS</div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:4px">
        ${{tmplEntries.map(([k, v]) => `<button type="button" class="cdx-ibtn" data-load="${{k}}" style="justify-content:space-between;border:1px solid var(--cdx-border);padding:4px 8px"><span>${{esc(v.name || k)}}</span><small style="opacity:0.65">${{(v.atoms || []).length}}a</small></button>`).join("")}}
      </div>`);
    modalEl.querySelectorAll("[data-fg]").forEach((b) => b.addEventListener("click", () => {{
      setActiveElem(b.dataset.fg, 0, null); backdropEl.hidden = true;
    }}));
    modalEl.querySelectorAll("[data-load]").forEach((b) => b.addEventListener("click", () => {{
      const item = CATALOG[b.dataset.load];
      if (item) {{ pushUndo(); state.graph = normalizeGraph(item); fitZoom(); render(); syncHostState(); }}
      backdropEl.hidden = true;
    }}));
  }});

  // Import Modal (SMILES / Molfile V2000 / CDXML)
  document.getElementById("cdx-act-import").addEventListener("click", () => {{
    openModal(`<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
        <strong>Import Structure (SMILES / Reaction SMILES / MDL Molfile V2000)</strong>
        <button type="button" class="cdx-ibtn" data-close="1">✕</button>
      </div>
      <textarea id="cdx-imp-txt" class="cdx-code" placeholder="Paste SMILES (e.g. CC(=O)Oc1ccccc1C(=O)O or Brc1ccccc1>>c1ccc(-c2ccccc2)cc1) or MDL Molfile V2000 block..."></textarea>
      <div style="margin-top:8px;display:flex;justify-content:flex-end;gap:6px">
        <button type="button" class="cdx-cta" id="cdx-imp-go">Load onto Canvas</button>
      </div>`);
    modalEl.querySelector("#cdx-imp-go").addEventListener("click", () => {{
      const txt = modalEl.querySelector("#cdx-imp-txt").value.trim();
      if (!txt) return;
      const parsed = txt.includes("V2000") ? parseMolfileV2000(txt) : parseSmilesClient(txt);
      if (parsed && parsed.atoms.length) {{
        pushUndo(); state.graph = parsed; fitZoom(); render(); syncHostState();
        backdropEl.hidden = true; setToast("Loaded structure onto canvas");
      }} else setToast("Could not parse input");
    }});
  }});

  // Export Modal (SMILES, SMARTS, Molfile V2000, CDXML, SVG)
  function showExportModal(fmt = "mol") {{
    const g = state.graph;
    const getBody = (f) => f === "smiles" ? graphToSmiles(g, false) : (f === "smarts" ? graphToSmiles(g, true) : (f === "cdxml" ? toCdxml(g) : (f === "svg" ? svg.outerHTML : toMolfileV2000(g))));
    openModal(`<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
        <div style="display:flex;gap:4px">
          <button type="button" class="cdx-ibtn ${{fmt==="smiles"?"is-active":""}}" data-ef="smiles">SMILES</button>
          <button type="button" class="cdx-ibtn ${{fmt==="smarts"?"is-active":""}}" data-ef="smarts">SMARTS Query</button>
          <button type="button" class="cdx-ibtn ${{fmt==="mol"?"is-active":""}}" data-ef="mol">Molfile V2000</button>
          <button type="button" class="cdx-ibtn ${{fmt==="cdxml"?"is-active":""}}" data-ef="cdxml">ACS 1996 CDXML</button>
          <button type="button" class="cdx-ibtn ${{fmt==="svg"?"is-active":""}}" data-ef="svg">SVG</button>
        </div>
        <button type="button" class="cdx-ibtn" data-close="1">✕</button>
      </div>
      <textarea id="cdx-exp-txt" class="cdx-code" readonly>${{esc(getBody(fmt))}}</textarea>
      <div style="margin-top:8px;display:flex;justify-content:flex-end;gap:6px">
        <button type="button" class="cdx-cta" id="cdx-exp-copy">Copy to Clipboard</button>
      </div>`);
    modalEl.querySelectorAll("[data-ef]").forEach((b) => b.addEventListener("click", () => showExportModal(b.dataset.ef)));
    modalEl.querySelector("#cdx-exp-copy").addEventListener("click", () => {{
      const val = modalEl.querySelector("#cdx-exp-txt").value;
      if (navigator.clipboard) navigator.clipboard.writeText(val).catch(() => {{}});
      setToast("Copied to clipboard");
    }});
  }}
  document.getElementById("cdx-act-export").addEventListener("click", () => showExportModal("mol"));

  function downloadBlob(text, mime, filename) {{
    const url = URL.createObjectURL(new Blob([text], {{type: mime}}));
    const a = document.createElement("a"); a.href = url; a.download = filename; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }}
  document.getElementById("cdx-btn-cdxml").addEventListener("click", () => downloadBlob(toCdxml(state.graph), "chemical/x-cdxml", "structure.cdxml"));
  document.getElementById("cdx-btn-mol").addEventListener("click", () => downloadBlob(toMolfileV2000(state.graph), "chemical/x-mdl-molfile", "structure.mol"));

  // Keyboard Shortcuts (ChemDraw / Reaxys / SciFinder standard)
  document.addEventListener("keydown", (ev) => {{
    if (ev.target && ["INPUT","TEXTAREA","SELECT"].includes(ev.target.tagName)) return;
    if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "z") {{
      ev.preventDefault(); document.getElementById(ev.shiftKey ? "cdx-act-redo" : "cdx-act-undo").click(); return;
    }}
    if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "y") {{
      ev.preventDefault(); document.getElementById("cdx-act-redo").click(); return;
    }}
    if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "d") {{
      ev.preventDefault(); document.getElementById("cdx-act-dup").click(); return;
    }}
    if (ev.key === "Delete" || ev.key === "Backspace") {{
      if (state.selAtoms.size > 0) {{
        pushUndo();
        [...state.selAtoms].sort((a, b) => b - a).forEach((i) => deleteAtomAt(state.graph, i));
        render(); syncHostState(); return;
      }}
      if (state.hover.ai >= 0) {{ pushUndo(); deleteAtomAt(state.graph, state.hover.ai); render(); syncHostState(); return; }}
    }}
    const k = ev.key;
    if (k === "Escape" || k === "v" || k === "V") selectTool("select", "sel-lasso");
    else if (k === "1") selectTool("bond", "bond-1");
    else if (k === "2") selectTool("bond", "bond-2");
    else if (k === "3") selectTool("bond", "bond-3");
    else if (k === "w" || k === "W") selectTool("stereo", "st-wedge");
    else if (k === "h" || k === "H") selectTool("stereo", "st-hash");
    else if (k === "e" || k === "E") selectTool("erase", "erase");
    else if (["c","n","o","s","p","f","i","b"].includes(k.toLowerCase()) && state.hover.ai >= 0) {{
      pushUndo(); state.graph.atoms[state.hover.ai].s = k.toUpperCase(); render(); syncHostState();
    }}
  }});

  // Universal Host Bridge (Inline Agent Reply / MCP Apps / Live Sync Server / Clipboard)
  let rpcId = 1;
  function postHost(msg) {{
    try {{ if (window.parent && window.parent !== window) window.parent.postMessage(msg, "*"); }} catch (_e) {{}}
  }}
  function notifyResize() {{
    const rect = root.getBoundingClientRect();
    postHost({{jsonrpc:"2.0", method:"ui/notifications/size-changed", params:{{width:Math.ceil(rect.width||760), height:Math.ceil(rect.height||470)}}}});
  }}
  function syncHostState() {{
    const qMode = document.getElementById("cdx-query-mode").value;
    const smi = graphToSmiles(state.graph, qMode === "substructure");
    if (hostBridge && typeof hostBridge.setWidgetState === "function") {{
      try {{
        hostBridge.setWidgetState({{
          modelContent: {{smiles: smi, queryMode: qMode, style: state.style, formula: document.getElementById("cdx-m-formula").textContent}},
          privateContent: {{graph: state.graph}}
        }}).catch(() => {{}});
      }} catch (_e) {{}}
    }}
  }}

  window.addEventListener("message", (ev) => {{
    const d = ev.data;
    if (!d || typeof d !== "object") return;
    const res = d.params?.structuredContent || d.params?.result || d.result;
    if (res && res.graph) {{
      state.graph = normalizeGraph(res.graph); fitZoom(); render();
    }}
  }});
  ["open" + "ai:set_globals", "z" + "code:set_globals"].forEach((evName) => {{
    window.addEventListener(evName, (ev) => {{
      const ws = ev.detail?.globals?.widgetState;
      if (ws?.privateContent?.graph) {{ state.graph = normalizeGraph(ws.privateContent.graph); render(); }}
    }});
  }});

  document.getElementById("cdx-btn-3d").addEventListener("click", () => {{
    const smi = graphToSmiles(state.graph, false);
    if (!smi) {{ setToast("Draw a molecule first"); return; }}
    postHost({{jsonrpc:"2.0", id:++rpcId, method:"tools/call", params:{{name:"view_molecule_3d", arguments:{{smiles:smi, query:smi}}}}}});
    if (hostBridge && typeof hostBridge.sendFollowUpMessage === "function") {{
      hostBridge.sendFollowUpMessage({{prompt:`Show 3D conformer in Mol* for SMILES: ${{smi}}`, title:"Open in 3D Mol*"}});
    }} else setToast("Requested 3D Mol* for " + smi);
  }});

  document.getElementById("cdx-btn-send").addEventListener("click", async () => {{
    const qMode = document.getElementById("cdx-query-mode").value;
    const smi = graphToSmiles(state.graph, false);
    const smarts = graphToSmiles(state.graph, true);
    const cdxml = toCdxml(state.graph);
    const mol = toMolfileV2000(state.graph);
    const prompt = `Edited 2D structure (${{qMode}} mode, style=${{state.style}}): SMILES=${{smi || "(custom)"}} | SMARTS=${{smarts || "(none)"}} | Formula=${{document.getElementById("cdx-m-formula").textContent}}. Render editable ACS 1996 CDXML / run requested analysis.`;

    if (window.__CDX_LIVE_SYNC_URL__) {{
      try {{
        await fetch(window.__CDX_LIVE_SYNC_URL__, {{
          method: "POST", headers: {{"Content-Type": "application/json"}},
          body: JSON.stringify({{smiles: smi, smarts, query_mode: qMode, style: state.style, cdxml, molfile: mol, graph: state.graph}})
        }});
      }} catch (_e) {{}}
    }}
    if (hostBridge && typeof hostBridge.sendFollowUpMessage === "function") {{
      syncHostState();
      await hostBridge.sendFollowUpMessage({{prompt, title: "Transfer Structure to Agent"}});
      return;
    }}
    postHost({{jsonrpc:"2.0", id:++rpcId, method:"ui/message", params:{{role:"user", content:[{{type:"text", text:prompt}}]}}}});
    if (navigator.clipboard) navigator.clipboard.writeText(prompt).catch(() => {{}});
    setToast("Transferred structure & copied prompt to clipboard");
  }});

  if (typeof ResizeObserver !== "undefined") {{
    new ResizeObserver(() => notifyResize()).observe(root);
  }}
  postHost({{jsonrpc:"2.0", id:++rpcId, method:"ui/initialize", params:{{appInfo:{{name:"chemdraw-2d-studio", version:"2.0.0"}}}}}});
  fitZoom();
  render();
}})();
</script>
</div>"""

def render_drawing_studio_app_html(
    initial_payload: dict[str, Any] | None = None,
    *,
    live_sync_url: str | None = None,
) -> str:
    """Render the standalone / MCP-App HTML document wrapping the 2D Studio fragment."""
    fragment = render_drawing_studio_fragment(initial_payload)
    # Mark standalone theme auto-detection on root element
    fragment = fragment.replace('id="cdx-studio-root"', 'id="cdx-studio-root" data-standalone="1"', 1)
    sync_boot = (
        f"<script>window.__CDX_LIVE_SYNC_URL__ = {_html_json(live_sync_url)};</script>\n"
        if live_sync_url
        else ""
    )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        "<title>ChemDraw Toolkit · Interactive 2D Studio</title>\n"
        "<style>html,body{margin:0;padding:0;background:transparent;}</style>\n"
        "</head>\n"
        "<body>\n"
        f"{sync_boot}"
        f"{fragment}\n"
        "</body>\n"
        "</html>\n"
    )


def _write_html_artifact(
    html_text: str,
    *,
    source: Path | None,
    output_path: str | None,
    tag: str,
) -> Path:
    destination = artifact_safety.resolve_destination(
        source=source,
        output_path=output_path,
        tag=tag,
        suffix=".html",
    )
    _, published = artifact_safety.stage_validate_publish(
        destination,
        lambda staged: staged.write_text(html_text, encoding="utf-8"),
    )
    return published


def view_molecule_3d(
    query: str = "aspirin",
    *,
    structure_path: str | None = None,
    smiles: str | None = None,
    pdb_id: str | None = None,
    format: str | None = None,
    representation: str = "ball-and-stick",
    output_path: str | None = None,
    launch_browser: bool = False,
) -> dict[str, Any]:
    """Build an interactive 3D Mol* + offline WebGL/Canvas viewer (MCP App + standalone HTML).

    Accepts a PDB/mmCIF/SDF/MOL/XYZ/CDXML file path, a SMILES string, a chemical name
    (e.g. ``"aspirin"``, ``"caffeine"``, ``"taxol"``), or a 4-character PDB ID
    (e.g. ``"1CRN"``, ``"6LU7"``). Returns an MCP Apps UI resource hint plus a
    self-contained standalone HTML viewer path.
    """
    source_anchor: Path | None = None
    warnings: list[str] = []
    payload: dict[str, Any] = {
        "title": query or pdb_id or "Molecule 3D",
        "representation": representation,
        "format": (format or "sdf").lower(),
        "source_kind": "builtin",
        "mol_data": None,
        "pdb_data": None,
        "smiles": None,
        "pdb_id": None,
        "formula": None,
        "molecular_weight": None,
        "scene": {"atoms": [], "bonds": []},
        "is_macromolecule": False,
    }

    candidate_file: Path | None = None
    if structure_path:
        candidate_file = Path(structure_path).expanduser().resolve()
        if not candidate_file.is_file():
            raise FileNotFoundError(f"Structure file not found: {candidate_file}")
    elif query and Path(query).expanduser().is_file():
        candidate_file = Path(query).expanduser().resolve()

    if candidate_file is not None:
        source_anchor = candidate_file
        ext = candidate_file.suffix.lower()
        payload["title"] = candidate_file.stem
        if ext == ".cdxml":
            mol, extracted_smi = _cdxml_to_rdkit_mol(candidate_file)
            built = _mol_3d_from_rdkit(mol, title=candidate_file.stem)
            payload.update(built)
            if extracted_smi and not payload.get("smiles"):
                payload["smiles"] = extracted_smi
            payload["source_kind"] = "cdxml-3d"
        elif ext in {".sdf", ".mol"}:
            from rdkit import Chem

            text = candidate_file.read_text(encoding="utf-8", errors="replace")
            mol = Chem.MolFromMolBlock(text, removeHs=False)
            if mol is not None:
                from rdkit.Chem import Descriptors, rdMolDescriptors

                conf = mol.GetConformer()
                atoms = [
                    {
                        "idx": i,
                        "s": a.GetSymbol(),
                        "x": round(float(conf.GetAtomPosition(i).x), 4),
                        "y": round(float(conf.GetAtomPosition(i).y), 4),
                        "z": round(float(conf.GetAtomPosition(i).z), 4),
                    }
                    for i, a in enumerate(mol.GetAtoms())
                ]
                bonds = [
                    {
                        "a": int(b.GetBeginAtomIdx()),
                        "b": int(b.GetEndAtomIdx()),
                        "o": 2 if b.GetBondType() == Chem.BondType.DOUBLE else (3 if b.GetBondType() == Chem.BondType.TRIPLE else 1),
                    }
                    for b in mol.GetBonds()
                ]
                payload.update({
                    "format": "sdf",
                    "mol_data": text,
                    "smiles": Chem.MolToSmiles(Chem.RemoveHs(mol)),
                    "formula": rdMolDescriptors.CalcMolFormula(mol),
                    "molecular_weight": round(float(Descriptors.MolWt(mol)), 3),
                    "scene": {"atoms": atoms, "bonds": bonds},
                    "source_kind": "sdf-file",
                })
            else:
                payload.update({"format": "sdf", "mol_data": text, "source_kind": "sdf-file"})
        elif ext in {".pdb", ".ent", ".cif", ".mmcif"}:
            text = candidate_file.read_text(encoding="utf-8", errors="replace")
            atoms, bonds, is_macro = _parse_pdb_or_cif_scene(text, ext)
            fmt = "mmcif" if ext in {".cif", ".mmcif"} else "pdb"
            payload.update({
                "format": fmt,
                "mol_data": text if len(text) <= 524288 else text[:524288],
                "scene": {"atoms": atoms, "bonds": bonds},
                "is_macromolecule": is_macro,
                "source_kind": "pdb-file",
            })
            if len(text) > 524288:
                warnings.append("Structure exceeded 512 KB inline payload limit; truncated preview in MCP response.")
        elif ext == ".xyz":
            text = candidate_file.read_text(encoding="utf-8", errors="replace")
            atoms, bonds = _parse_xyz_scene(text)
            payload.update({
                "format": "xyz",
                "mol_data": text,
                "scene": {"atoms": atoms, "bonds": bonds},
                "source_kind": "xyz-file",
            })
        else:
            raise ValueError(f"Unsupported 3D structure extension {ext!r}: {candidate_file}")
    elif pdb_id or (not smiles and query and _PDB_CODE_RE.fullmatch(query.strip())):
        code = (pdb_id or query).strip().upper()
        payload.update({
            "title": f"PDB {code}",
            "pdb_id": code,
            "format": (format or "mmcif").lower(),
            "is_macromolecule": True,
            "source_kind": "rcsb-pdb",
        })
    else:
        from rdkit import Chem

        target_smiles = smiles
        title = query or "Molecule"
        source_kind = "smiles"
        if not target_smiles:
            target_smiles, title, source_kind = _resolve_smiles_input(query)
        if not target_smiles:
            raise ValueError(f"Could not interpret 3D structure target {query!r}; pass SMILES, file path, or PDB ID.")
        mol = Chem.MolFromSmiles(target_smiles)
        if mol is None:
            raise ValueError(f"Invalid SMILES for 3D viewer: {target_smiles!r}")
        built = _mol_3d_from_rdkit(mol, title=title)
        payload.update(built)
        payload["source_kind"] = source_kind

    html_text = render_molstar_app_html(payload)
    html_file = _write_html_artifact(
        html_text,
        source=source_anchor,
        output_path=output_path,
        tag="molstar-viewer",
    )
    viewer_url = html_file.as_uri()
    opened_browser = False
    if launch_browser:
        try:
            opened_browser = bool(webbrowser.open(viewer_url))
        except Exception as exc:
            warnings.append(f"Could not launch browser window: {exc}")

    atom_count = len((payload.get("scene") or {}).get("atoms") or [])
    bond_count = len((payload.get("scene") or {}).get("bonds") or [])
    artifacts = artifact_safety.artifact_records([html_file])
    outputs = {
        "title": payload["title"],
        "format": payload["format"],
        "representation": payload["representation"],
        "smiles": payload.get("smiles"),
        "pdb_id": payload.get("pdb_id"),
        "formula": payload.get("formula"),
        "molecular_weight": payload.get("molecular_weight"),
        "atom_count": atom_count,
        "bond_count": bond_count,
        "html_path": str(html_file),
        "viewer_url": viewer_url,
        "ui_resource_uri": MOLSTAR_RESOURCE_URI,
        "opened_browser": opened_browser,
        "source_kind": payload["source_kind"],
    }
    return {
        "ok": True,
        **outputs,
        "mol_data": payload.get("mol_data"),
        "pdb_data": payload.get("pdb_data"),
        "scene": payload.get("scene"),
        "is_macromolecule": payload.get("is_macromolecule", False),
        "outputs": outputs,
        "warnings": warnings,
        "artifacts": artifacts,
        "metadata": {"network_used": False, "artifacts": artifacts},
    }


view_molecule_3d._chemdraw_mcp_meta = {"ui": {"resourceUri": MOLSTAR_RESOURCE_URI}}  # type: ignore[attr-defined]


def open_drawing_studio(
    template: str = "blank",
    *,
    cdxml_path: str | None = None,
    smiles: str | None = None,
    name: str | None = None,
    style: str = "acs1996",
    output_path: str | None = None,
    fragment_path: str | None = None,
    launch_browser: bool = False,
) -> dict[str, Any]:
    """Open the interactive 2D ChemDraw Studio with ring fusion, drag-bond drawing & templates.

    Outputs both a standalone/MCP-App HTML document (``html_path``) and a pure inline HTML
    fragment without document tags (``fragment_path``) so conversational agent hosts can
    mount the 2D molecular canvas directly inline inside an assistant reply.
    """
    source_anchor: Path | None = None
    warnings: list[str] = []
    style_slug = (style or "acs1996").strip().lower()
    if style_slug not in _STYLE_PRESETS:
        warnings.append(f"Unknown style {style!r}; falling back to 'acs1996'.")
        style_slug = "acs1996"

    if cdxml_path:
        src = Path(cdxml_path).expanduser().resolve()
        if not src.is_file():
            raise FileNotFoundError(f"CDXML file not found: {src}")
        source_anchor = src
        graph = _cdxml_to_studio_graph(src)
        graph["name"] = name or src.stem
        graph["category"] = "Loaded CDXML"
    elif smiles:
        if ">>" in smiles:
            lhs, rhs = smiles.split(">>", 1)
            left = _smiles_to_studio_graph(lhs, offset_x=125.0, offset_y=145.0, bond_scale=23.0)
            right = _smiles_to_studio_graph(rhs, offset_x=435.0, offset_y=145.0, bond_scale=23.0)
            off = len(left["atoms"])
            graph = {
                "name": name or smiles,
                "template_key": "custom",
                "category": "Reaction SMILES",
                "smiles": smiles,
                "atoms": left["atoms"] + right["atoms"],
                "bonds": left["bonds"] + [{"a": b["a"] + off, "b": b["b"] + off, "o": b["o"]} for b in right["bonds"]],
                "arrows": [{"x1": 225, "y1": 145, "x2": 325, "y2": 145, "style": "solid", "above": "", "below": ""}],
            }
        else:
            built = _smiles_to_studio_graph(smiles, offset_x=275.0, offset_y=142.0, bond_scale=28.0)
            graph = {
                "name": name or smiles,
                "template_key": "custom",
                "category": "Custom SMILES",
                "smiles": smiles,
                **built,
            }
    else:
        norm = (template or "blank").strip().lower().replace("-", "_").replace(" ", "_")
        if norm in _STUDIO_TEMPLATES:
            graph = _build_studio_graph_for_template(norm)
            if name:
                graph["name"] = name
        else:
            resolved_smi, title, _ = _resolve_smiles_input(template)
            if resolved_smi is None:
                available = ", ".join(sorted(_STUDIO_TEMPLATES))
                raise ValueError(f"Unknown studio template {template!r}. Available: {available}")
            built = _smiles_to_studio_graph(resolved_smi, offset_x=275.0, offset_y=142.0, bond_scale=28.0)
            graph = {
                "name": name or title,
                "template_key": "custom",
                "category": "Resolved Molecule",
                "smiles": resolved_smi,
                **built,
            }

    formula, mw, dbe = _compute_graph_metrics(graph)
    payload = {
        "graph": graph,
        "style": style_slug,
        "styles": _STYLE_PRESETS,
    }
    html_text = render_drawing_studio_app_html(payload)
    html_file = _write_html_artifact(
        html_text,
        source=source_anchor,
        output_path=output_path,
        tag="drawing-studio",
    )
    published_files = [html_file]
    frag_file: Path | None = None
    if fragment_path is not None:
        frag_text = render_drawing_studio_fragment(payload)
        frag_file = _write_html_artifact(
            frag_text,
            source=source_anchor,
            output_path=fragment_path,
            tag="drawing-studio-fragment",
        )
        published_files.append(frag_file)

    studio_url = html_file.as_uri()
    opened_browser = False
    if launch_browser:
        try:
            opened_browser = bool(webbrowser.open(studio_url))
        except Exception as exc:
            warnings.append(f"Could not launch browser window: {exc}")

    artifacts = artifact_safety.artifact_records(published_files)
    outputs = {
        "title": graph.get("name", template),
        "template": graph.get("template_key", template),
        "style": style_slug,
        "formula": formula,
        "molecular_weight": mw,
        "dbe": dbe,
        "atom_count": len(graph.get("atoms") or []),
        "bond_count": len(graph.get("bonds") or []),
        "available_templates": sorted(_STUDIO_TEMPLATES),
        "html_path": str(html_file),
        "fragment_path": str(frag_file) if frag_file is not None else None,
        "studio_url": studio_url,
        "ui_resource_uri": DRAWING_STUDIO_RESOURCE_URI,
        "opened_browser": opened_browser,
    }
    return {
        "ok": True,
        **outputs,
        "graph": graph,
        "outputs": outputs,
        "warnings": warnings,
        "artifacts": artifacts,
        "metadata": {"network_used": False, "artifacts": artifacts},
    }


open_drawing_studio._chemdraw_mcp_meta = {"ui": {"resourceUri": DRAWING_STUDIO_RESOURCE_URI}}  # type: ignore[attr-defined]


def serve_drawing_studio(
    *,
    template: str = "blank",
    cdxml_path: str | None = None,
    smiles: str | None = None,
    style: str = "acs1996",
    sync_dir: str | Path = ".",
    port: int = 0,
    open_browser: bool = True,
) -> tuple[ThreadingHTTPServer, str, Path]:
    """Start a local loopback HTTP bridge so terminal CLI agents receive live 2D edits."""
    sync_folder = Path(sync_dir).expanduser().resolve()
    sync_folder.mkdir(parents=True, exist_ok=True)
    info = open_drawing_studio(
        template=template,
        cdxml_path=cdxml_path,
        smiles=smiles,
        style=style,
        launch_browser=False,
    )
    payload = {"graph": info["graph"], "style": info["style"], "styles": _STYLE_PRESETS}
    html_bytes = render_drawing_studio_app_html(payload, live_sync_url="/api/studio-sync").encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _fmt: str, *_args: Any) -> None:
            return

        def do_GET(self) -> None:  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(html_bytes)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/studio-sync":
                self.send_response(404)
                self.end_headers()
                return
            length = int(self.headers.get("Content-Length") or "0")
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            (sync_folder / "studio-live.cdxml").write_text(str(body.get("cdxml") or ""), encoding="utf-8")
            (sync_folder / "studio-live.json").write_text(
                json.dumps(
                    {"smiles": body.get("smiles"), "style": body.get("style"), "graph": body.get("graph")},
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            resp = json.dumps({"ok": True, "cdxml_path": str(sync_folder / "studio-live.cdxml")}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    actual_port = server.server_address[1]
    url = f"http://127.0.0.1:{actual_port}/"
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    return server, url, sync_folder / "studio-live.cdxml"


UI_APP_TOOLS = {
    "view_molecule_3d": view_molecule_3d,
    "open_drawing_studio": open_drawing_studio,
}
