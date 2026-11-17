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

    Designed for inline mounting inside conversational agent hosts (inline visualization surfaces,
    <agent-embed>, MCP Apps iframes) as well as standalone HTML wrapping.
    """
    catalog = _studio_template_catalog()
    payload = initial_payload or {"graph": catalog["aspirin"], "style": "acs1996", "styles": _STYLE_PRESETS}
    if "styles" not in payload:
        payload = {**payload, "styles": _STYLE_PRESETS}
    initial_json = _html_json(payload)
    catalog_json = _html_json(catalog)
    return f"""<div id="cdx-studio-root" class="cdx-studio-shell" role="region" aria-label="Interactive 2D Molecular Drawing Studio">
<style>
  #cdx-studio-root {{
    --cdx-bg: var(--background, #f8fafc);
    --cdx-panel: var(--card, #ffffff);
    --cdx-muted-bg: var(--muted, #f1f5f9);
    --cdx-fg: var(--foreground, #0f172a);
    --cdx-muted: var(--muted-foreground, #475569);
    --cdx-border: var(--border, rgba(15,23,42,0.13));
    --cdx-accent: var(--primary, #0284c7);
    --cdx-accent-fg: var(--primary-foreground, #ffffff);
    box-sizing: border-box;
    width: 100%;
    color: var(--cdx-fg);
    font: 12.5px/1.35 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}
  @media (prefers-color-scheme: dark) {{
    #cdx-studio-root[data-standalone="1"] {{
      --cdx-bg: #0d1117;
      --cdx-panel: #161b22;
      --cdx-muted-bg: #21262d;
      --cdx-fg: #e6edf3;
      --cdx-muted: #8b949e;
      --cdx-border: rgba(240,246,252,0.14);
      --cdx-accent: #38bdf8;
      --cdx-accent-fg: #06121d;
    }}
  }}
  #cdx-studio-root *, #cdx-studio-root *::before, #cdx-studio-root *::after {{ box-sizing: border-box; }}
  #cdx-studio-root .cdx-ribbon {{
    display: flex; flex-wrap: wrap; align-items: center; gap: 4px;
    padding: 6px 8px; background: var(--cdx-panel);
    border: 1px solid var(--cdx-border); border-radius: 10px;
  }}
  #cdx-studio-root .cdx-sep {{ width: 1px; height: 18px; background: var(--cdx-border); margin: 0 2px; }}
  #cdx-studio-root button, #cdx-studio-root select, #cdx-studio-root input {{
    background: var(--cdx-muted-bg); color: var(--cdx-fg);
    border: 1px solid var(--cdx-border); border-radius: 6px;
    padding: 3.5px 7px; font-size: 11.5px; font-family: inherit; line-height: 1.25;
  }}
  #cdx-studio-root button {{ cursor: pointer; font-weight: 500; transition: border-color .12s, background .12s; }}
  #cdx-studio-root button:hover {{ border-color: var(--cdx-accent); }}
  #cdx-studio-root button.is-active {{
    background: var(--cdx-accent); color: var(--cdx-accent-fg); border-color: var(--cdx-accent);
  }}
  #cdx-studio-root button.cdx-cta {{
    background: #0284c7; color: #ffffff; border-color: #0284c7; font-weight: 600;
  }}
  #cdx-studio-root .cdx-body {{
    display: grid; grid-template-columns: 196px 1fr; gap: 6px; min-height: 326px;
  }}
  @media (max-width: 640px) {{
    #cdx-studio-root .cdx-body {{ grid-template-columns: 1fr; }}
  }}
  #cdx-studio-root .cdx-side {{
    background: var(--cdx-panel); border: 1px solid var(--cdx-border); border-radius: 10px;
    padding: 7px; display: flex; flex-direction: column; gap: 6px; max-height: 336px; overflow-y: auto; overflow-x: hidden;
  }}
  #cdx-studio-root .cdx-tabs {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 3px; }}
  #cdx-studio-root .cdx-tabs button {{ padding: 3px 2px; font-size: 10.5px; text-align: center; min-width: 0; }}
  #cdx-studio-root .cdx-cat {{ font-size: 10.5px; font-weight: 600; color: var(--cdx-muted);
    text-transform: uppercase; letter-spacing: 0.04em; margin: 4px 0 2px; }}
  #cdx-studio-root .cdx-tbtn {{
    width: 100%; text-align: left; display: flex; justify-content: space-between;
    align-items: center; padding: 4px 6px; margin-bottom: 3px; background: transparent;
  }}
  #cdx-studio-root .cdx-grid4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; }}
  #cdx-studio-root .cdx-grid3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; }}
  #cdx-studio-root .cdx-stage {{
    position: relative; background: #ffffff; border: 1px solid var(--cdx-border);
    border-radius: 10px; overflow: hidden; display: flex; align-items: center; justify-content: center;
    background-image: radial-gradient(rgba(15,23,42,0.07) 1px, transparent 0);
    background-size: 18px 18px; min-height: 320px;
  }}
  #cdx-studio-root #cdx-svg {{
    width: 100%; height: 328px; display: block; user-select: none; touch-action: none; cursor: crosshair;
  }}
  #cdx-studio-root .cdx-overlay {{
    position: absolute; top: 7px; left: 8px; right: 8px; display: flex;
    justify-content: space-between; align-items: center; pointer-events: none; gap: 6px;
  }}
  #cdx-studio-root .cdx-overlay > * {{ pointer-events: auto; }}
  #cdx-studio-root .cdx-pill {{
    background: rgba(255,255,255,0.92); color: #0f172a; border: 1px solid rgba(15,23,42,0.14);
    border-radius: 999px; padding: 2px 8px; font-size: 11px; font-weight: 500;
  }}
  #cdx-studio-root .cdx-footer {{
    display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 6px;
    padding: 5px 9px; background: var(--cdx-panel); border: 1px solid var(--cdx-border); border-radius: 10px;
  }}
  #cdx-studio-root .cdx-metrics {{
    display: flex; flex-wrap: wrap; align-items: center; gap: 10px; font-size: 11.5px;
  }}
  #cdx-studio-root .cdx-metrics code {{
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11px;
    background: var(--cdx-muted-bg); padding: 1px 5px; border-radius: 4px;
  }}
  #cdx-studio-root textarea {{
    width: 100%; height: 96px; resize: vertical; background: var(--cdx-muted-bg); color: var(--cdx-fg);
    border: 1px solid var(--cdx-border); border-radius: 6px; padding: 5px;
    font: 10.5px/1.3 ui-monospace, Menlo, monospace;
  }}
  #cdx-studio-root .cdx-swatches {{ display: flex; gap: 3px; align-items: center; }}
  #cdx-studio-root .cdx-swatch {{ width: 16px; height: 16px; border-radius: 50%; padding: 0; border: 1.5px solid rgba(15,23,42,0.28); }}
</style>

  <div class="cdx-ribbon" role="toolbar" aria-label="Drawing tools">
    <button type="button" data-tool="move" title="Move / Drag (V)">Move</button>
    <button type="button" data-tool="bond-1" class="is-active" title="Single Bond - click or drag (1)">Single</button>
    <button type="button" data-tool="bond-2" title="Double Bond (2)">Double</button>
    <button type="button" data-tool="bond-3" title="Triple Bond (3)">Triple</button>
    <button type="button" data-tool="wedge" title="Solid Wedge - click again to flip (W)">Wedge</button>
    <button type="button" data-tool="hash" title="Hashed Wedge - click again to flip (H)">Hash</button>
    <button type="button" data-tool="wavy" title="Wavy Stereo Bond">Wavy</button>
    <span class="cdx-sep"></span>
    <button type="button" data-tool="ring-ph" title="Benzene - click bond to fuse, atom to sprout (6)">Ph (6)</button>
    <button type="button" data-tool="ring-6" title="Cyclohexane ring">Cy-6</button>
    <button type="button" data-tool="ring-5" title="Cyclopentane ring (5)">Cp-5</button>
    <button type="button" data-tool="ring-pyr" title="Pyridine ring">Pyr</button>
    <span class="cdx-sep"></span>
    <button type="button" data-tool="arrow" title="Add or cycle reaction arrow">Arrow &rarr;</button>
    <button type="button" data-tool="plus" title="Add reaction plus sign">+</button>
    <button type="button" data-tool="highlight" title="Click inside a ring to shade">Ring Fill</button>
    <div class="cdx-swatches" aria-label="Highlight color">
      <button type="button" class="cdx-swatch" data-hl="#dbeafe" style="background:#dbeafe" aria-label="JACS Blue"></button>
      <button type="button" class="cdx-swatch" data-hl="#ccfbf1" style="background:#ccfbf1" aria-label="Teal"></button>
      <button type="button" class="cdx-swatch" data-hl="#fef3c7" style="background:#fef3c7" aria-label="Amber"></button>
      <button type="button" class="cdx-swatch" data-hl="#ffe4e6" style="background:#ffe4e6" aria-label="Rose"></button>
    </div>
    <button type="button" data-tool="erase" title="Erase atom, bond, or arrow (E / Del)">Erase</button>
    <span class="cdx-sep"></span>
    <button type="button" id="cdx-rot-l" title="Rotate -15 deg">&#8634;</button>
    <button type="button" id="cdx-rot-r" title="Rotate +15 deg">&#8635;</button>
    <button type="button" id="cdx-flip-h" title="Flip horizontal">&#8644;</button>
    <button type="button" id="cdx-clean" title="Center structure">Center</button>
    <button type="button" id="cdx-undo" title="Undo (Ctrl+Z)">Undo</button>
    <button type="button" id="cdx-redo" title="Redo (Ctrl+Y)">Redo</button>
    <button type="button" id="cdx-clear" title="Clear canvas">Clear</button>
  </div>

  <div class="cdx-body">
    <aside class="cdx-side">
      <div class="cdx-tabs" role="tablist">
        <button type="button" data-pane="tmpl" class="is-active">Templates</button>
        <button type="button" data-pane="atoms">Atoms/FG</button>
        <button type="button" data-pane="io">SMILES</button>
      </div>
      <div id="cdx-pane-tmpl"></div>
      <div id="cdx-pane-atoms" hidden>
        <div class="cdx-cat">Elements (click or hover+key)</div>
        <div class="cdx-grid4" id="cdx-elems">
          <button type="button" data-elem="C" class="is-active">C</button>
          <button type="button" data-elem="N">N</button>
          <button type="button" data-elem="O">O</button>
          <button type="button" data-elem="S">S</button>
          <button type="button" data-elem="F">F</button>
          <button type="button" data-elem="Cl">Cl</button>
          <button type="button" data-elem="Br">Br</button>
          <button type="button" data-elem="I">I</button>
          <button type="button" data-elem="P">P</button>
          <button type="button" data-elem="B">B</button>
          <button type="button" data-elem="Si">Si</button>
          <button type="button" data-elem="Pd">Pd</button>
        </div>
        <div class="cdx-cat">Formal Charge</div>
        <div class="cdx-grid3">
          <button type="button" data-chg="1">+1</button>
          <button type="button" data-chg="0">0</button>
          <button type="button" data-chg="-1">&minus;1</button>
        </div>
        <div class="cdx-cat">Functional Groups (1-click)</div>
        <div class="cdx-grid3" id="cdx-groups">
          <button type="button" data-fg="CF3">CF3</button>
          <button type="button" data-fg="OMe">OMe</button>
          <button type="button" data-fg="NO2">NO2</button>
          <button type="button" data-fg="CN">CN</button>
          <button type="button" data-fg="COOH">COOH</button>
          <button type="button" data-fg="CO2Et">CO2Et</button>
          <button type="button" data-fg="Boc">Boc</button>
          <button type="button" data-fg="Bpin">Bpin</button>
          <button type="button" data-fg="OTs">OTs</button>
          <button type="button" data-fg="TMS">TMS</button>
          <button type="button" data-fg="Bn">Bn</button>
          <button type="button" data-fg="tBu">tBu</button>
        </div>
      </div>
      <div id="cdx-pane-io" hidden>
        <div class="cdx-cat">Load SMILES / Reaction</div>
        <div style="display:flex;gap:4px;">
          <input id="cdx-smi-in" type="text" placeholder="e.g. c1ccccc1Br" style="width:100%" />
          <button type="button" id="cdx-smi-load">Load</button>
        </div>
        <div class="cdx-cat">ACS 1996 CDXML</div>
        <textarea id="cdx-xml-box" readonly aria-label="Generated CDXML"></textarea>
      </div>
    </aside>

    <div class="cdx-stage">
      <div class="cdx-overlay">
        <span class="cdx-pill" id="cdx-status" aria-live="polite">Drag from an atom to draw bonds (30&deg; snap) &middot; Click bond with Ph(6) to fuse ring</span>
        <select id="cdx-style-sel" aria-label="Journal style" style="background:rgba(255,255,255,0.94);color:#0f172a;border-color:rgba(15,23,42,0.18);"></select>
      </div>
      <svg id="cdx-svg" viewBox="0 0 560 290" xmlns="http://www.w3.org/2000/svg">
        <title>2D Molecular Canvas</title>
      </svg>
    </div>
  </div>

  <div class="cdx-footer">
    <div class="cdx-metrics">
      <span><strong id="cdx-f-formula">-</strong></span>
      <span>MW <code id="cdx-f-mw">-</code></span>
      <span>DBE <code id="cdx-f-dbe">0</code></span>
      <span>SMILES <code id="cdx-f-smi" style="max-width:210px;display:inline-block;overflow:hidden;text-overflow:ellipsis;vertical-align:bottom;">-</code></span>
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:4px;">
      <button type="button" id="cdx-copy-smi">Copy SMILES</button>
      <button type="button" id="cdx-dl-cdxml">.cdxml</button>
      <button type="button" id="cdx-dl-svg">.svg</button>
      <button type="button" id="cdx-open-3d">3D Mol*</button>
      <button type="button" id="cdx-send-host" class="cdx-cta">Send to Agent</button>
    </div>
  </div>

<script>
(() => {{
  const root = document.getElementById("cdx-studio-root");
  if (!root) return;
  const q = (sel) => root.querySelector(sel);
  const qa = (sel) => Array.from(root.querySelectorAll(sel));

  const INITIAL = {initial_json};
  const CATALOG = {catalog_json};
  const STYLES = INITIAL.styles || {{ acs1996: {{ label: "ACS 1996 / JACS", bondLength: 14.4, lineWidth: 0.6, font: "Arial", labelSize: 10 }} }};
  const WEIGHTS = {{ H:1.008, B:10.81, C:12.011, N:14.007, O:15.999, F:18.998, Mg:24.305, Si:28.085, P:30.974, S:32.06, Cl:35.45, Br:79.904, Pd:106.42, I:126.904 }};
  const VALENCE = {{ H:1, B:3, C:4, N:3, O:2, Si:4, P:3, S:2, F:1, Cl:1, Br:1, I:1 }};
  const ELEM_NUM = {{ H:1, B:5, C:6, N:7, O:8, F:9, Mg:12, Si:14, P:15, S:16, Cl:17, Br:35, Pd:46, I:53 }};
  const SUPER_FORMULAS = {{
    Me:{{C:1,H:3}}, Et:{{C:2,H:5}}, tBu:{{C:4,H:9}}, Ph:{{C:6,H:5}}, Bn:{{C:7,H:7}},
    CF3:{{C:1,F:3}}, OMe:{{C:1,H:3,O:1}}, NO2:{{N:1,O:2}}, CN:{{C:1,N:1}},
    COOH:{{C:1,H:1,O:2}}, CO2Et:{{C:3,H:5,O:2}}, Boc:{{C:5,H:9,O:2}},
    OTs:{{C:7,H:7,O:3,S:1}}, Bpin:{{B:1,C:6,H:12,O:2}}, TMS:{{Si:1,C:3,H:9}}
  }};
  const SUPER_SMILES = {{
    Me:"C", Et:"CC", tBu:"C(C)(C)C", Ph:"c1ccccc1", Bn:"Cc1ccccc1",
    CF3:"C(F)(F)F", OMe:"OC", NO2:"[N+](=O)[O-]", CN:"C#N",
    COOH:"C(=O)O", CO2Et:"C(=O)OCC", Boc:"C(=O)OC(C)(C)C",
    OTs:"OS(=O)(=O)c1ccc(C)cc1", Bpin:"B1OC(C)(C)C(C)(C)O1", TMS:"[Si](C)(C)C"
  }};
  const ATOM_COLORS = {{
    O:"#b91c1c", N:"#1d4ed8", S:"#a16207", P:"#c2410c", F:"#15803d",
    Cl:"#15803d", Br:"#92400e", I:"#7e22ce", B:"#be123c", Pd:"#0e7490", Si:"#475569"
  }};

  const hostGlobal = window["open" + "ai"];
  const savedWidget = hostGlobal && hostGlobal.widgetState && hostGlobal.widgetState.modelContent;

  function cloneGraph(g) {{
    const base = JSON.parse(JSON.stringify(g || CATALOG.aspirin));
    base.atoms = base.atoms || [];
    base.bonds = base.bonds || [];
    base.arrows = base.arrows || [];
    base.pluses = base.pluses || [];
    base.texts = base.texts || [];
    base.circles = base.circles || [];
    base.spokes = base.spokes || [];
    base.ring_fills = base.ring_fills || [];
    return base;
  }}

  let state = {{
    graph: cloneGraph((savedWidget && savedWidget.graph) || (INITIAL && INITIAL.graph) || CATALOG.aspirin),
    style: (savedWidget && savedWidget.style) || (INITIAL && INITIAL.style) || "acs1996",
    tool: "bond-1",
    elem: "C",
    fg: null,
    hlColor: "#dbeafe",
    hoverAtom: -1,
    hoverBond: -1,
    drag: null,
    undoStack: [],
    redoStack: []
  }};

  const svg = q("#cdx-svg");
  const statusEl = q("#cdx-status");
  const styleSel = q("#cdx-style-sel");

  Object.entries(STYLES).forEach(([slug, cfg]) => {{
    const opt = document.createElement("option");
    opt.value = slug;
    opt.textContent = cfg.label || slug;
    styleSel.appendChild(opt);
  }});
  styleSel.value = state.style in STYLES ? state.style : "acs1996";

  function setStatus(msg) {{ statusEl.textContent = msg; }}

  function persistHostState() {{
    if (hostGlobal && typeof hostGlobal.setWidgetState === "function") {{
      const smi = graphToSmiles(state.graph);
      hostGlobal.setWidgetState({{
        modelContent: {{ title: state.graph.name || "Structure", smiles: smi, style: state.style, graph: state.graph }},
        privateContent: {{ tool: state.tool }}
      }}).catch(() => {{}});
    }}
  }}

  function pushUndo() {{
    state.undoStack.push(JSON.stringify(state.graph));
    if (state.undoStack.length > 45) state.undoStack.shift();
    state.redoStack = [];
  }}

  function esc(s) {{
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }}

  function buildTemplatePane() {{
    const pane = q("#cdx-pane-tmpl");
    const groups = {{}};
    Object.entries(CATALOG).forEach(([k, g]) => {{
      const cat = g.category || "Molecules";
      (groups[cat] = groups[cat] || []).push([k, g]);
    }});
    pane.innerHTML = "";
    Object.entries(groups).forEach(([cat, items]) => {{
      const hdr = document.createElement("div");
      hdr.className = "cdx-cat";
      hdr.textContent = cat;
      pane.appendChild(hdr);
      items.forEach(([key, g]) => {{
        const b = document.createElement("button");
        b.type = "button";
        b.className = "cdx-tbtn" + (state.graph.template_key === key ? " is-active" : "");
        b.innerHTML = `<span>${{esc(g.name)}}</span><span style="opacity:.65;font-size:10px">${{(g.atoms || []).length}}a</span>`;
        b.addEventListener("click", () => {{
          pushUndo();
          state.graph = cloneGraph(g);
          render();
          buildTemplatePane();
          persistHostState();
          setStatus("Loaded template: " + g.name);
        }});
        pane.appendChild(b);
      }});
    }});
  }}

  function neighbours(g) {{
    const nb = g.atoms.map(() => []);
    g.bonds.forEach((b, bi) => {{
      if (b.a < nb.length && b.b < nb.length) {{
        nb[b.a].push({{ to: b.b, bi, o: b.o || 1 }});
        nb[b.b].push({{ to: b.a, bi, o: b.o || 1 }});
      }}
    }});
    return nb;
  }}

  // Find small rings (size 3..8) for asymmetric ChemDraw double-bond inset and ring highlights
  function findSmallRings(g) {{
    const nb = neighbours(g);
    const rings = [];
    const seen = new Set();
    g.bonds.forEach((b, bi) => {{
      const start = b.a, goal = b.b;
      const queue = [[start]];
      while (queue.length) {{
        const path = queue.shift();
        if (path.length > 8) continue;
        const cur = path[path.length - 1];
        if (cur === goal && path.length >= 3) {{
          const key = [...path].sort((x, y) => x - y).join(",");
          if (!seen.has(key)) {{
            seen.add(key);
            rings.push(path);
          }}
          break;
        }}
        for (const edge of nb[cur] || []) {{
          if (edge.bi === bi) continue;
          if (!path.includes(edge.to)) queue.push([...path, edge.to]);
        }}
      }}
    }});
    return rings;
  }}

  function bondLength(g) {{
    if (!g.bonds.length) return 28;
    let sum = 0, cnt = 0;
    g.bonds.forEach((b) => {{
      const a1 = g.atoms[b.a], a2 = g.atoms[b.b];
      if (a1 && a2) {{
        const d = Math.hypot(a2.x - a1.x, a2.y - a1.y);
        if (d > 6) {{ sum += d; cnt++; }}
      }}
    }});
    return cnt ? Math.max(20, Math.min(36, sum / cnt)) : 28;
  }}

  function sproutAngle(g, ai, order) {{
    const nb = neighbours(g)[ai] || [];
    const base = g.atoms[ai];
    if (!nb.length) return -Math.PI / 6;
    const angles = nb.map((e) => Math.atan2(g.atoms[e.to].y - base.y, g.atoms[e.to].x - base.x)).sort((a, b) => a - b);
    if (nb.length === 1) {{
      const inOrd = nb[0].o;
      if (order === 3 || inOrd === 3 || (order === 2 && inOrd === 2)) return angles[0] + Math.PI;
      const c1 = angles[0] + (Math.PI * 2) / 3, c2 = angles[0] - (Math.PI * 2) / 3;
      const score = (ang) => {{
        const tx = base.x + Math.cos(ang) * 28, ty = base.y + Math.sin(ang) * 28;
        let minD = 9999;
        g.atoms.forEach((a, idx) => {{ if (idx !== ai) minD = Math.min(minD, Math.hypot(a.x - tx, a.y - ty)); }});
        return minD;
      }};
      return score(c1) >= score(c2) ? c1 : c2;
    }}
    let bestGap = -1, bestMid = angles[0] + Math.PI;
    for (let i = 0; i < angles.length; i++) {{
      const a1 = angles[i], a2 = i + 1 < angles.length ? angles[i + 1] : angles[0] + Math.PI * 2;
      const gap = a2 - a1;
      if (gap > bestGap) {{ bestGap = gap; bestMid = a1 + gap / 2; }}
    }}
    return bestMid;
  }}

  function findBond(g, u, v) {{
    return g.bonds.findIndex((b) => (b.a === u && b.b === v) || (b.a === v && b.b === u));
  }}

  function fuseRingOnBond(g, bi, sides, aromatic, heteroN) {{
    const bond = g.bonds[bi];
    if (!bond) return;
    const pA = g.atoms[bond.a], pB = g.atoms[bond.b];
    const dx = pB.x - pA.x, dy = pB.y - pA.y;
    const L = Math.hypot(dx, dy) || 28;
    const ux = dx / L, uy = dy / L;
    const R = L / (2 * Math.sin(Math.PI / sides));
    const apothem = L / (2 * Math.tan(Math.PI / sides));
    const mx = (pA.x + pB.x) / 2, my = (pA.y + pB.y) / 2;
    const c1 = {{ x: mx - uy * apothem, y: my + ux * apothem }};
    const c2 = {{ x: mx + uy * apothem, y: my - ux * apothem }};
    const crowd = (c) => g.atoms.reduce((acc, a, idx) => (idx === bond.a || idx === bond.b) ? acc : acc + 1 / Math.max(4, Math.hypot(a.x - c.x, a.y - c.y)), 0);
    const center = crowd(c1) <= crowd(c2) ? c1 : c2;
    const angA = Math.atan2(pA.y - center.y, pA.x - center.x);
    const angB = Math.atan2(pB.y - center.y, pB.x - center.x);
    let step = angB - angA;
    while (step <= -Math.PI) step += Math.PI * 2;
    while (step > Math.PI) step -= Math.PI * 2;
    const dir = step > 0 ? 1 : -1;
    const dTheta = dir * ((Math.PI * 2) / sides);

    const ringAtoms = [bond.a, bond.b];
    for (let k = 2; k < sides; k++) {{
      const ang = angA + dTheta * k;
      const vx = +(center.x + Math.cos(ang) * R).toFixed(2);
      const vy = +(center.y + Math.sin(ang) * R).toFixed(2);
      let existing = g.atoms.findIndex((a) => Math.hypot(a.x - vx, a.y - vy) < 9.5);
      if (existing < 0) {{
        existing = g.atoms.length;
        const sym = (heteroN && k === 3) ? "N" : "C";
        g.atoms.push({{ s: sym, x: vx, y: vy }});
      }}
      ringAtoms.push(existing);
    }}
    const nb = neighbours(g);
    const hasDouble = (ai) => (nb[ai] || []).some((e) => e.o === 2);
    for (let k = 1; k < sides; k++) {{
      const u = ringAtoms[k], v = ringAtoms[(k + 1) % sides];
      if (findBond(g, u, v) < 0) {{
        let ord = 1;
        if (aromatic && (k % 2 === 1) && !hasDouble(u) && !hasDouble(v)) ord = 2;
        g.bonds.push({{ a: u, b: v, o: ord }});
      }}
    }}
  }}

  function placeFreeRing(g, cx, cy, sides, aromatic, heteroN) {{
    const L = bondLength(g);
    const R = L / (2 * Math.sin(Math.PI / sides));
    const start = g.atoms.length;
    for (let k = 0; k < sides; k++) {{
      const ang = -Math.PI / 2 + (Math.PI * 2 * k) / sides;
      const sym = (heteroN && k === 2) ? "N" : "C";
      g.atoms.push({{ s: sym, x: +(cx + Math.cos(ang) * R).toFixed(2), y: +(cy + Math.sin(ang) * R).toFixed(2) }});
    }}
    for (let k = 0; k < sides; k++) {{
      g.bonds.push({{ a: start + k, b: start + ((k + 1) % sides), o: (aromatic && k % 2 === 0) ? 2 : 1 }});
    }}
    return start;
  }}

  function attachGroup(g, ai, fg) {{
    const L = bondLength(g);
    const ang = sproutAngle(g, ai, 1);
    const base = g.atoms[ai];
    const nx = +(base.x + Math.cos(ang) * L).toFixed(2);
    const ny = +(base.y + Math.sin(ang) * L).toFixed(2);
    if (fg === "CF3") {{
      const ci = g.atoms.length;
      g.atoms.push({{ s: "C", x: nx, y: ny }});
      g.bonds.push({{ a: ai, b: ci, o: 1 }});
      [ang, ang + Math.PI / 2, ang - Math.PI / 2].forEach((fa) => {{
        const fi = g.atoms.length;
        g.atoms.push({{ s: "F", x: +(nx + Math.cos(fa) * L * 0.92).toFixed(2), y: +(ny + Math.sin(fa) * L * 0.92).toFixed(2) }});
        g.bonds.push({{ a: ci, b: fi, o: 1 }});
      }});
    }} else if (fg === "CN") {{
      const ci = g.atoms.length, ni = ci + 1;
      g.atoms.push({{ s: "C", x: nx, y: ny }});
      g.atoms.push({{ s: "N", x: +(nx + Math.cos(ang) * L).toFixed(2), y: +(ny + Math.sin(ang) * L).toFixed(2) }});
      g.bonds.push({{ a: ai, b: ci, o: 1 }}, {{ a: ci, b: ni, o: 3 }});
    }} else if (fg === "COOH") {{
      const ci = g.atoms.length, o1 = ci + 1, o2 = ci + 2;
      g.atoms.push({{ s: "C", x: nx, y: ny }});
      g.atoms.push({{ s: "O", x: +(nx + Math.cos(ang + Math.PI / 3) * L).toFixed(2), y: +(ny + Math.sin(ang + Math.PI / 3) * L).toFixed(2) }});
      g.atoms.push({{ s: "O", x: +(nx + Math.cos(ang - Math.PI / 3) * L).toFixed(2), y: +(ny + Math.sin(ang - Math.PI / 3) * L).toFixed(2) }});
      g.bonds.push({{ a: ai, b: ci, o: 1 }}, {{ a: ci, b: o1, o: 2 }}, {{ a: ci, b: o2, o: 1 }});
    }} else if (fg === "tBu") {{
      const ci = g.atoms.length;
      g.atoms.push({{ s: "C", x: nx, y: ny }});
      g.bonds.push({{ a: ai, b: ci, o: 1 }});
      [ang, ang + Math.PI * 0.55, ang - Math.PI * 0.55].forEach((ma) => {{
        const mi = g.atoms.length;
        g.atoms.push({{ s: "C", x: +(nx + Math.cos(ma) * L).toFixed(2), y: +(ny + Math.sin(ma) * L).toFixed(2) }});
        g.bonds.push({{ a: ci, b: mi, o: 1 }});
      }});
    }} else {{
      const gi = g.atoms.length;
      g.atoms.push({{ s: fg, x: nx, y: ny }});
      g.bonds.push({{ a: ai, b: gi, o: 1 }});
    }}
  }}

  // Lightweight DFS SMILES serializer (handles rings, branches, stereo/orders, superatoms, and reaction arrows)
  function componentSmiles(g, compAtoms) {{
    if (!compAtoms.length) return "";
    const inSet = new Set(compAtoms);
    const adj = new Map();
    compAtoms.forEach((i) => adj.set(i, []));
    const edgeKey = (u, v) => (u < v ? u + ":" + v : v + ":" + u);
    const bondOrd = new Map();
    g.bonds.forEach((b) => {{
      if (inSet.has(b.a) && inSet.has(b.b)) {{
        const ord = b.o >= 4 ? 1 : (b.o || 1);
        adj.get(b.a).push(b.b);
        adj.get(b.b).push(b.a);
        bondOrd.set(edgeKey(b.a, b.b), ord);
      }}
    }});
    const visited = new Set();
    const parent = new Map();
    const treeChildren = new Map();
    compAtoms.forEach((i) => treeChildren.set(i, []));
    const backEdges = [];
    const seenBack = new Set();

    function dfsTree(u) {{
      visited.add(u);
      for (const v of adj.get(u)) {{
        if (!visited.has(v)) {{
          parent.set(v, u);
          treeChildren.get(u).push(v);
          dfsTree(v);
        }} else if (parent.get(u) !== v) {{
          const ek = edgeKey(u, v);
          if (!seenBack.has(ek)) {{
            seenBack.add(ek);
            backEdges.push([u, v]);
          }}
        }}
      }}
    }}
    dfsTree(compAtoms[0]);

    const ringTags = new Map();
    compAtoms.forEach((i) => ringTags.set(i, []));
    backEdges.forEach(([u, v], idx) => {{
      const num = idx + 1;
      const tag = num >= 10 ? "%" + num : String(num);
      const bSym = bondOrd.get(edgeKey(u, v)) === 2 ? "=" : (bondOrd.get(edgeKey(u, v)) === 3 ? "#" : "");
      ringTags.get(u).push(bSym + tag);
      ringTags.get(v).push(tag);
    }});

    function atomToken(i) {{
      const a = g.atoms[i];
      const s = a.s || "C";
      if (SUPER_SMILES[s] && (adj.get(i) || []).length <= 1) return SUPER_SMILES[s];
      const chg = a.chg || 0;
      const organic = new Set(["B","C","N","O","P","S","F","Cl","Br","I"]);
      if (!chg && organic.has(s)) return s;
      const chgStr = chg > 0 ? (chg === 1 ? "+" : "+" + chg) : (chg < 0 ? (chg === -1 ? "-" : String(chg)) : "");
      return "[" + s + chgStr + "]";
    }}

    function emit(u, p) {{
      let prefix = "";
      if (p !== null) {{
        const ord = bondOrd.get(edgeKey(p, u)) || 1;
        prefix = ord === 2 ? "=" : (ord === 3 ? "#" : "");
      }}
      let out = prefix + atomToken(u) + (ringTags.get(u) || []).join("");
      const kids = treeChildren.get(u) || [];
      for (let k = 0; k < kids.length; k++) {{
        const childSmi = emit(kids[k], u);
        out += (k < kids.length - 1) ? "(" + childSmi + ")" : childSmi;
      }}
      return out;
    }}
    return emit(compAtoms[0], null);
  }}

  function graphToSmiles(g) {{
    if (!g.atoms.length) return "";
    const nb = neighbours(g);
    const seen = new Set();
    const comps = [];
    for (let i = 0; i < g.atoms.length; i++) {{
      if (seen.has(i)) continue;
      const comp = [];
      const qList = [i];
      seen.add(i);
      while (qList.length) {{
        const u = qList.shift();
        comp.push(u);
        for (const e of nb[u]) {{
          if (!seen.has(e.to)) {{ seen.add(e.to); qList.push(e.to); }}
        }}
      }}
      comps.push(comp);
    }}
    if (g.arrows && g.arrows.length) {{
      const ar = g.arrows[0];
      const midX = (ar.x1 + ar.x2) / 2;
      const left = [], right = [];
      comps.forEach((c) => {{
        const avgX = c.reduce((s, idx) => s + g.atoms[idx].x, 0) / c.length;
        (avgX <= midX ? left : right).push(componentSmiles(g, c));
      }});
      if (left.length && right.length) return left.join(".") + ">>" + right.join(".");
    }}
    return comps.map((c) => componentSmiles(g, c)).filter(Boolean).join(".");
  }}

  // Lightweight client-side SMILES parser for instant interactive loading without backend roundtrip
  function parseSmilesClient(smi) {{
    const clean = (smi || "").trim();
    if (!clean) return null;
    if (clean.includes(">>")) {{
      const [lhs, rhs] = clean.split(">>");
      const gL = parseSmilesSingle(lhs, 130, 145, 24);
      const gR = parseSmilesSingle(rhs, 430, 145, 24);
      if (!gL || !gR) return null;
      const off = gL.atoms.length;
      return {{
        name: clean,
        atoms: [...gL.atoms, ...gR.atoms],
        bonds: [...gL.bonds, ...gR.bonds.map((b) => ({{ a: b.a + off, b: b.b + off, o: b.o }}))],
        arrows: [{{ x1: 235, y1: 145, x2: 325, y2: 145, style: "solid", above: "", below: "" }}],
        pluses: lhs.includes(".") ? [{{ x: 130, y: 145 }}] : [],
        texts: [], circles: [], spokes: [], ring_fills: []
      }};
    }}
    return parseSmilesSingle(clean, 275, 145, 27);
  }}

  function parseSmilesSingle(smi, cx, cy, L) {{
    const parts = smi.split(".").filter(Boolean);
    let allAtoms = [], allBonds = [];
    parts.forEach((part, pi) => {{
      const atoms = [], bonds = [];
      const stack = [];
      const rings = {{}};
      let prev = -1, pendingOrd = 1, i = 0;
      const aromSet = new Set();
      while (i < part.length) {{
        const ch = part[i];
        if (ch === "(") {{ stack.push(prev); i++; continue; }}
        if (ch === ")") {{ prev = stack.pop() ?? prev; i++; continue; }}
        if (ch === "=") {{ pendingOrd = 2; i++; continue; }}
        if (ch === "#") {{ pendingOrd = 3; i++; continue; }}
        if (ch === "-" || ch === "/" || ch === "\\\\") {{ pendingOrd = 1; i++; continue; }}
        if (ch >= "0" && ch <= "9") {{
          const d = ch;
          if (rings[d] !== undefined && prev >= 0) {{
            bonds.push({{ a: rings[d].idx, b: prev, o: pendingOrd > 1 ? pendingOrd : rings[d].ord }});
            delete rings[d];
          }} else if (prev >= 0) {{
            rings[d] = {{ idx: prev, ord: pendingOrd }};
          }}
          pendingOrd = 1; i++; continue;
        }}
        let sym = null, isArom = false, chg = 0;
        if (ch === "[") {{
          const end = part.indexOf("]", i);
          if (end < 0) break;
          const inner = part.slice(i + 1, end);
          const m = inner.match(/^([A-Za-z][a-z]?)/);
          sym = m ? m[1] : "C";
          if (/^[a-z]/.test(sym)) {{ isArom = true; sym = sym.toUpperCase(); }}
          if (inner.includes("+")) chg = 1;
          else if (inner.includes("-")) chg = -1;
          i = end + 1;
        }} else if (part.slice(i, i + 2) === "Cl" || part.slice(i, i + 2) === "Br") {{
          sym = part.slice(i, i + 2); i += 2;
        }} else if (/[A-Za-z]/.test(ch)) {{
          isArom = ch === ch.toLowerCase();
          sym = ch.toUpperCase(); i++;
        }} else {{ i++; continue; }}

        const cur = atoms.length;
        let x = cx + (pi - (parts.length - 1) / 2) * 110, y = cy;
        if (prev >= 0) {{
          const ang = sproutAngle({{ atoms, bonds }}, prev, pendingOrd);
          x = +(atoms[prev].x + Math.cos(ang) * L).toFixed(2);
          y = +(atoms[prev].y + Math.sin(ang) * L).toFixed(2);
        }}
        atoms.push(chg ? {{ s: sym, x, y, chg }} : {{ s: sym, x, y }});
        if (isArom) aromSet.add(cur);
        if (prev >= 0) {{
          const ord = (pendingOrd === 1 && aromSet.has(prev) && aromSet.has(cur) && (cur % 2 === 1)) ? 2 : pendingOrd;
          bonds.push({{ a: prev, b: cur, o: ord }});
        }}
        prev = cur; pendingOrd = 1;
      }}
      // Regularize simple 5/6-membered single rings cleanly
      const gTmp = {{ atoms, bonds }};
      const foundRings = findSmallRings(gTmp);
      if (foundRings.length === 1 && foundRings[0].length === atoms.length) {{
        const n = foundRings[0].length, R = L / (2 * Math.sin(Math.PI / n));
        foundRings[0].forEach((ai, k) => {{
          const ang = -Math.PI / 2 + (2 * Math.PI * k) / n;
          atoms[ai].x = +(cx + Math.cos(ang) * R).toFixed(2);
          atoms[ai].y = +(cy + Math.sin(ang) * R).toFixed(2);
        }});
      }}
      const off = allAtoms.length;
      allAtoms.push(...atoms);
      allBonds.push(...bonds.map((b) => ({{ a: b.a + off, b: b.b + off, o: b.o }})));
    }});
    return allAtoms.length ? {{ name: smi, atoms: allAtoms, bonds: allBonds, arrows: [], pluses: [], texts: [], circles: [], spokes: [], ring_fills: [] }} : null;
  }}

  function computeMetrics(g) {{
    const atoms = g.atoms || [], bonds = g.bonds || [];
    const deg = Array(atoms.length).fill(0);
    bonds.forEach((b) => {{
      const o = b.o >= 4 ? 1 : (b.o || 1);
      if (b.a < atoms.length) deg[b.a] += o;
      if (b.b < atoms.length) deg[b.b] += o;
    }});
    const counts = {{}};
    const implicitH = Array(atoms.length).fill(0);
    const overVal = Array(atoms.length).fill(false);
    atoms.forEach((a, i) => {{
      const s = a.s || "C";
      const chg = a.chg || 0;
      if (SUPER_FORMULAS[s]) {{
        Object.entries(SUPER_FORMULAS[s]).forEach(([el, n]) => {{ counts[el] = (counts[el] || 0) + n; }});
        return;
      }}
      if (WEIGHTS[s]) counts[s] = (counts[s] || 0) + 1;
      let v = VALENCE[s] || 0;
      if (s === "N" && chg === 1) v = 4;
      else if (s === "O" && chg === -1) v = 1;
      else if (s === "B" && chg === -1) v = 4;
      if (v > 0 && deg[i] > v && !["S", "P"].includes(s)) overVal[i] = true;
      const h = Math.max(0, v - deg[i]);
      implicitH[i] = h;
      if (h) counts.H = (counts.H || 0) + h;
    }});
    let formula = "";
    ["C", "H"].forEach((k) => {{ if (counts[k]) formula += k + (counts[k] > 1 ? counts[k] : ""); }});
    Object.keys(counts).filter((k) => k !== "C" && k !== "H").sort().forEach((k) => {{
      formula += k + (counts[k] > 1 ? counts[k] : "");
    }});
    const mw = Object.entries(counts).reduce((acc, [k, n]) => acc + (WEIGHTS[k] || 0) * n, 0);
    const cN = counts.C || 0, hN = counts.H || 0, nN = counts.N || 0;
    const hal = (counts.F || 0) + (counts.Cl || 0) + (counts.Br || 0) + (counts.I || 0);
    const dbe = atoms.length ? Math.max(0, Math.round(cN + 1 - (hN + hal - nN) / 2)) : 0;
    return {{ formula: formula || "-", mw: mw ? mw.toFixed(2) : "-", dbe, implicitH, overVal }};
  }}

  function generateCdxml(g) {{
    const preset = STYLES[state.style] || STYLES.acs1996;
    const scale = (preset.bondLength || 14.4) / 28.0;
    let id = 100;
    const nid = () => String(++id);
    const lines = [
      '<?xml version="1.0" encoding="UTF-8"?>',
      '<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd">',
      `<CDXML BondLength="${{preset.bondLength || 14.4}}" LabelFont="3" LabelSize="${{preset.labelSize || 10}}">`,
      '  <page id="1" WidthPages="1" HeightPages="1">',
      '    <fragment id="2">'
    ];
    const atomIds = (g.atoms || []).map((a) => {{
      const aid = nid();
      const x = (a.x * scale + 60).toFixed(2);
      const y = (a.y * scale + 60).toFixed(2);
      const el = ELEM_NUM[a.s];
      const chgAttr = a.chg ? ` Charge="${{a.chg}}"` : "";
      if (a.s === "C" && !a.chg) {{
        lines.push(`      <n id="${{aid}}" p="${{x}} ${{y}}"/>`);
      }} else if (el) {{
        const elAttr = el === 6 ? "" : ` Element="${{el}}"`;
        lines.push(`      <n id="${{aid}}" p="${{x}} ${{y}}"${{elAttr}}${{chgAttr}}><t p="${{x}} ${{y}}"><s>${{esc(a.s)}}</s></t></n>`);
      }} else {{
        lines.push(`      <n id="${{aid}}" p="${{x}} ${{y}}" NodeType="Fragment"><t p="${{x}} ${{y}}"><s>${{esc(a.s)}}</s></t></n>`);
      }}
      return aid;
    }});
    (g.bonds || []).forEach((b) => {{
      const a = atomIds[b.a], c = atomIds[b.b];
      if (!a || !c) return;
      const bid = nid();
      const orderAttr = b.o === 2 || b.o === 3 ? ` Order="${{b.o}}"` : "";
      const dispAttr = b.o === 4 ? ' Display="WedgeBegin"' : (b.o === 5 ? ' Display="WedgedHashBegin"' : (b.o === 6 ? ' Display="Wavy"' : ""));
      lines.push(`      <b id="${{bid}}" B="${{a}}" E="${{c}}"${{orderAttr}}${{dispAttr}}/>`);
    }});
    lines.push("    </fragment>");
    (g.arrows || []).forEach((ar) => {{
      const x1 = (ar.x1 * scale + 60).toFixed(2), y1 = (ar.y1 * scale + 60).toFixed(2);
      const x2 = (ar.x2 * scale + 60).toFixed(2), y2 = (ar.y2 * scale + 60).toFixed(2);
      lines.push(`    <arrow id="${{nid()}}" Head3D="${{x2}} ${{y2}} 0" Tail3D="${{x1}} ${{y1}} 0" ArrowheadType="Solid"/>`);
    }});
    lines.push("  </page>", "</CDXML>");
    return lines.join("\\n");
  }}

  function formatAtomLabel(g, nb, metrics, i) {{
    const a = g.atoms[i];
    const h = metrics.implicitH[i] || 0;
    const chg = a.chg || 0;
    const chgSup = chg ? (chg > 0 ? (chg === 1 ? "+" : chg + "+") : (chg === -1 ? "−" : Math.abs(chg) + "−")) : "";
    const sub = (n) => (n > 1 ? ["","","₂","₃","₄"][n] || String(n) : "");
    if (SUPER_FORMULAS[a.s] && a.s !== "Ph") {{
      return a.s.replace(/(\\d+)/g, (m) => ["₀","₁","₂","₃","₄","₅","₆","₇","₈","₉"][Number(m)] || m);
    }}
    if (!h) return a.s + chgSup;
    const hPart = "H" + sub(h);
    const edges = nb[i] || [];
    // Put H on left (HO-, H2N-) when bonds point predominantly right
    const avgDx = edges.length ? edges.reduce((acc, e) => acc + (g.atoms[e.to].x - a.x), 0) / edges.length : -1;
    if (avgDx > 6 && ["O", "N", "S", "F", "Cl", "Br", "I"].includes(a.s) && !chgSup) {{
      return hPart + a.s;
    }}
    return a.s + hPart + chgSup;
  }}

  function render() {{
    const g = state.graph;
    const atoms = g.atoms || [], bonds = g.bonds || [];
    const nb = neighbours(g);
    const rings = findSmallRings(g);
    const metrics = computeMetrics(g);
    const preset = STYLES[state.style] || STYLES.acs1996;
    const sw = preset.lineWidth ? Math.max(1.55, preset.lineWidth * 2.75) : 1.75;
    const parts = [];

    // 1. JACS Pastel Ring Highlights
    (g.ring_fills || []).forEach((rf) => {{
      const pts = (rf.atoms || []).map((idx) => atoms[idx]).filter(Boolean);
      if (pts.length >= 3) {{
        parts.push(`<polygon points="${{pts.map((p) => p.x + "," + p.y).join(" ")}}" fill="${{rf.color || '#dbeafe'}}" opacity="0.85"/>`);
      }}
    }});

    // 2. Newman Circles & Spokes
    (g.circles || []).forEach((c) => {{
      parts.push(`<circle cx="${{c.cx}}" cy="${{c.cy}}" r="${{c.r}}" fill="#ffffff" stroke="#0f172a" stroke-width="${{sw}}"/>`);
    }});
    (g.spokes || []).forEach((s) => {{
      parts.push(`<line x1="${{s[0]}}" y1="${{s[1]}}" x2="${{s[2]}}" y2="${{s[3]}}" stroke="#0f172a" stroke-width="${{sw}}" stroke-linecap="round"/>`);
    }});

    // Map each bond to a ring centroid if part of a 3..8 ring
    const bondRingCenter = new Map();
    rings.forEach((ring) => {{
      const rcx = ring.reduce((s, idx) => s + atoms[idx].x, 0) / ring.length;
      const rcy = ring.reduce((s, idx) => s + atoms[idx].y, 0) / ring.length;
      for (let k = 0; k < ring.length; k++) {{
        const u = ring[k], v = ring[(k + 1) % ring.length];
        const bi = findBond(g, u, v);
        if (bi >= 0 && (!bondRingCenter.has(bi) || ring.length === 6)) {{
          bondRingCenter.set(bi, {{ x: rcx, y: rcy }});
        }}
      }}
    }});

    // 3. Bonds
    bonds.forEach((b, bi) => {{
      const a1 = atoms[b.a], a2 = atoms[b.b];
      if (!a1 || !a2) return;
      const dx = a2.x - a1.x, dy = a2.y - a1.y, len = Math.hypot(dx, dy) || 1;
      const ux = dx / len, uy = dy / len;
      const nx = -uy, ny = ux;
      if (bi === state.hoverBond) {{
        parts.push(`<line x1="${{a1.x}}" y1="${{a1.y}}" x2="${{a2.x}}" y2="${{a2.y}}" stroke="rgba(2,132,199,0.22)" stroke-width="9" stroke-linecap="round"/>`);
      }}
      if (b.o === 4) {{
        parts.push(`<polygon points="${{a1.x}},${{a1.y}} ${{(a2.x + nx * 4.2).toFixed(1)}},${{(a2.y + ny * 4.2).toFixed(1)}} ${{(a2.x - nx * 4.2).toFixed(1)}},${{(a2.y - ny * 4.2).toFixed(1)}}" fill="#0f172a"/>`);
      }} else if (b.o === 5) {{
        for (let t = 0.18; t <= 0.98; t += 0.16) {{
          const px = a1.x + dx * t, py = a1.y + dy * t, hw = 4.2 * t;
          parts.push(`<line x1="${{(px + nx * hw).toFixed(1)}}" y1="${{(py + ny * hw).toFixed(1)}}" x2="${{(px - nx * hw).toFixed(1)}}" y2="${{(py - ny * hw).toFixed(1)}}" stroke="#0f172a" stroke-width="1.5"/>`);
        }}
      }} else if (b.o === 6) {{
        let d = `M ${{a1.x.toFixed(1)}} ${{a1.y.toFixed(1)}}`;
        const steps = 7;
        for (let k = 1; k <= steps; k++) {{
          const t = k / steps, sign = k % 2 === 0 ? 1 : -1;
          const cxp = a1.x + dx * (t - 0.5 / steps) + nx * 3.2 * sign;
          const cyp = a1.y + dy * (t - 0.5 / steps) + ny * 3.2 * sign;
          d += ` Q ${{cxp.toFixed(1)}} ${{cyp.toFixed(1)}}, ${{(a1.x + dx * t).toFixed(1)}} ${{(a1.y + dy * t).toFixed(1)}}`;
        }}
        parts.push(`<path d="${{d}}" fill="none" stroke="#0f172a" stroke-width="${{sw}}"/>`);
      }} else if (b.o === 2 && bondRingCenter.has(bi)) {{
        // Asymmetric ChemDraw ring double bond: primary bond on vertex line, inset pi-bond inside ring
        parts.push(`<line x1="${{a1.x}}" y1="${{a1.y}}" x2="${{a2.x}}" y2="${{a2.y}}" stroke="#0f172a" stroke-width="${{sw}}" stroke-linecap="round"/>`);
        const rc = bondRingCenter.get(bi);
        const mx = (a1.x + a2.x) / 2, my = (a1.y + a2.y) / 2;
        const side = (rc.x - mx) * nx + (rc.y - my) * ny >= 0 ? 1 : -1;
        const inset = 3.8 * side, trim = Math.min(4.8, len * 0.17);
        const ix1 = a1.x + ux * trim + nx * inset, iy1 = a1.y + uy * trim + ny * inset;
        const ix2 = a2.x - ux * trim + nx * inset, iy2 = a2.y - uy * trim + ny * inset;
        parts.push(`<line x1="${{ix1.toFixed(1)}}" y1="${{iy1.toFixed(1)}}" x2="${{ix2.toFixed(1)}}" y2="${{iy2.toFixed(1)}}" stroke="#0f172a" stroke-width="${{sw}}" stroke-linecap="round"/>`);
      }} else {{
        const offsets = b.o === 2 ? [-2.1, 2.1] : (b.o === 3 ? [-3.2, 0, 3.2] : [0]);
        offsets.forEach((off) => {{
          parts.push(`<line x1="${{(a1.x + nx * off).toFixed(1)}}" y1="${{(a1.y + ny * off).toFixed(1)}}" x2="${{(a2.x + nx * off).toFixed(1)}}" y2="${{(a2.y + ny * off).toFixed(1)}}" stroke="#0f172a" stroke-width="${{sw}}" stroke-linecap="round"/>`);
        }});
      }}
      parts.push(`<line data-bond="${{bi}}" x1="${{a1.x}}" y1="${{a1.y}}" x2="${{a2.x}}" y2="${{a2.y}}" stroke="transparent" stroke-width="11" style="cursor:pointer"/>`);
    }});

    // 4. Drag Preview Rubber-Band
    if (state.drag && state.drag.mode === "sprout") {{
      const {{ x1, y1, x2, y2, snapIdx }} = state.drag;
      parts.push(`<line x1="${{x1}}" y1="${{y1}}" x2="${{x2}}" y2="${{y2}}" stroke="#0284c7" stroke-width="2" stroke-dasharray="4 3"/>`);
      parts.push(`<circle cx="${{x2}}" cy="${{y2}}" r="${{snapIdx >= 0 ? 9 : 4.5}}" fill="rgba(2,132,199,0.22)" stroke="#0284c7" stroke-width="1.5"/>`);
    }}

    // 5. Reaction Arrows, Pluses & Texts
    (g.arrows || []).forEach((ar, ari) => {{
      const st = ar.style || "solid";
      if (st === "retro") {{
        parts.push(`<line x1="${{ar.x1}}" y1="${{ar.y1 - 2.5}}" x2="${{ar.x2 - 6}}" y2="${{ar.y2 - 2.5}}" stroke="#0f172a" stroke-width="1.6"/>`);
        parts.push(`<line x1="${{ar.x1}}" y1="${{ar.y1 + 2.5}}" x2="${{ar.x2 - 6}}" y2="${{ar.y2 + 2.5}}" stroke="#0f172a" stroke-width="1.6"/>`);
        parts.push(`<polyline points="${{ar.x2 - 9}},${{ar.y2 - 6}} ${{ar.x2}},${{ar.y2}} ${{ar.x2 - 9}},${{ar.y2 + 6}}" fill="none" stroke="#0f172a" stroke-width="1.8"/>`);
      }} else if (st === "eq") {{
        parts.push(`<line x1="${{ar.x1}}" y1="${{ar.y1 - 2.5}}" x2="${{ar.x2}}" y2="${{ar.y2 - 2.5}}" stroke="#0f172a" stroke-width="1.5"/>`);
        parts.push(`<polygon points="${{ar.x2}},${{ar.y2 - 2.5}} ${{ar.x2 - 8}},${{ar.y2 - 6.5}} ${{ar.x2 - 6}},${{ar.y2 - 2.5}}" fill="#0f172a"/>`);
        parts.push(`<line x1="${{ar.x1}}" y1="${{ar.y1 + 2.5}}" x2="${{ar.x2}}" y2="${{ar.y2 + 2.5}}" stroke="#0f172a" stroke-width="1.5"/>`);
        parts.push(`<polygon points="${{ar.x1}},${{ar.y1 + 2.5}} ${{ar.x1 + 8}},${{ar.y1 + 6.5}} ${{ar.x1 + 6}},${{ar.y1 + 2.5}}" fill="#0f172a"/>`);
      }} else {{
        parts.push(`<line x1="${{ar.x1}}" y1="${{ar.y1}}" x2="${{ar.x2}}" y2="${{ar.y2}}" stroke="#0f172a" stroke-width="1.8"/>`);
        parts.push(`<polygon points="${{ar.x2}},${{ar.y2}} ${{ar.x2 - 9}},${{ar.y2 - 4}} ${{ar.x2 - 7}},${{ar.y2}} ${{ar.x2 - 9}},${{ar.y2 + 4}}" fill="#0f172a"/>`);
      }}
      if (ar.above) parts.push(`<text data-arrow="${{ari}}" x="${{(ar.x1 + ar.x2) / 2}}" y="${{ar.y1 - 9}}" text-anchor="middle" font-family="${{preset.font || 'Arial'}},sans-serif" font-size="11" fill="#0f172a" style="cursor:pointer">${{esc(ar.above)}}</text>`);
      if (ar.below) parts.push(`<text data-arrow="${{ari}}" x="${{(ar.x1 + ar.x2) / 2}}" y="${{ar.y1 + 16}}" text-anchor="middle" font-family="${{preset.font || 'Arial'}},sans-serif" font-size="10.8" fill="#334155" style="cursor:pointer">${{esc(ar.below)}}</text>`);
      parts.push(`<line data-arrow="${{ari}}" x1="${{ar.x1}}" y1="${{ar.y1}}" x2="${{ar.x2}}" y2="${{ar.y2}}" stroke="transparent" stroke-width="12" style="cursor:pointer"/>`);
    }});
    (g.pluses || []).forEach((pl, pli) => {{
      parts.push(`<text data-plus="${{pli}}" x="${{pl.x}}" y="${{pl.y + 5}}" text-anchor="middle" font-family="Arial,sans-serif" font-size="15" font-weight="600" fill="#0f172a" style="cursor:pointer">+</text>`);
    }});
    (g.texts || []).forEach((tx, txi) => {{
      parts.push(`<text data-text="${{txi}}" x="${{tx.x}}" y="${{tx.y}}" text-anchor="middle" font-family="${{preset.font || 'Arial'}},sans-serif" font-size="11.2" font-weight="600" fill="#0f172a" style="cursor:pointer">${{esc(tx.text)}}</text>`);
    }});

    // 6. Atoms, Implicit Hydrogens, Charges & Valence Warnings
    atoms.forEach((a, ai) => {{
      if (metrics.overVal[ai]) {{
        parts.push(`<circle cx="${{a.x}}" cy="${{a.y}}" r="11.5" fill="rgba(239,68,68,0.16)" stroke="#ef4444" stroke-width="1.2"/>`);
      }} else if (ai === state.hoverAtom) {{
        parts.push(`<circle cx="${{a.x}}" cy="${{a.y}}" r="10" fill="rgba(2,132,199,0.18)"/>`);
      }}
      const showLabel = a.s !== "C" || Boolean(a.chg) || !(nb[ai] || []).length;
      if (showLabel) {{
        const lbl = formatAtomLabel(g, nb, metrics, ai);
        const col = ATOM_COLORS[a.s] || "#0f172a";
        const boxW = Math.max(15, lbl.length * 7.6);
        parts.push(`<rect x="${{(a.x - boxW / 2).toFixed(1)}}" y="${{(a.y - 8.5).toFixed(1)}}" width="${{boxW.toFixed(1)}}" height="16.5" rx="4" fill="#ffffff"/>`);
        parts.push(`<text x="${{a.x}}" y="${{a.y + 4.2}}" text-anchor="middle" font-family="${{preset.font || 'Arial'}},sans-serif" font-size="12" font-weight="700" fill="${{col}}">${{esc(lbl)}}</text>`);
      }}
      parts.push(`<circle data-atom="${{ai}}" cx="${{a.x}}" cy="${{a.y}}" r="10.5" fill="transparent" style="cursor:pointer"/>`);
    }});

    svg.innerHTML = parts.join("");

    const smi = graphToSmiles(g) || g.smiles || "-";
    q("#cdx-f-formula").textContent = metrics.formula;
    q("#cdx-f-mw").textContent = metrics.mw === "-" ? "-" : metrics.mw;
    q("#cdx-f-dbe").textContent = String(metrics.dbe);
    q("#cdx-f-smi").textContent = smi;
    q("#cdx-f-smi").title = smi;
    q("#cdx-xml-box").value = generateCdxml(g);
  }}

  function svgPt(evt) {{
    const r = svg.getBoundingClientRect();
    return {{
      x: ((evt.clientX - r.left) / (r.width || 560)) * 560,
      y: ((evt.clientY - r.top) / (r.height || 290)) * 290
    }};
  }}

  function nearestAtom(pt, excludeIdx = -1, radius = 15.5) {{
    let best = -1, bestD = radius;
    state.graph.atoms.forEach((a, idx) => {{
      if (idx === excludeIdx) return;
      const d = Math.hypot(a.x - pt.x, a.y - pt.y);
      if (d < bestD) {{ bestD = d; best = idx; }}
    }});
    return best;
  }}

  function orderForTool(t) {{
    return t === "bond-2" ? 2 : (t === "bond-3" ? 3 : (t === "wedge" ? 4 : (t === "hash" ? 5 : (t === "wavy" ? 6 : 1))));
  }}

  // Pointer interactions: drag-to-draw bonds, snap to close rings, move atoms/fragments, fuse rings
  svg.addEventListener("pointerdown", (e) => {{
    if (e.button !== 0) return;
    const pt = svgPt(e);
    const t = e.target;
    const atomAttr = t.getAttribute && t.getAttribute("data-atom");
    const bondAttr = t.getAttribute && t.getAttribute("data-bond");
    const arrowAttr = t.getAttribute && t.getAttribute("data-arrow");
    const plusAttr = t.getAttribute && t.getAttribute("data-plus");

    if (state.tool === "move") {{
      if (atomAttr !== null) {{
        pushUndo();
        state.drag = {{ mode: "move-atom", ai: Number(atomAttr), startPt: pt }};
        svg.setPointerCapture(e.pointerId);
      }} else if (arrowAttr !== null) {{
        pushUndo();
        const ar = state.graph.arrows[Number(arrowAttr)];
        state.drag = {{ mode: "move-arrow", ari: Number(arrowAttr), startPt: pt, orig: {{ ...ar }} }};
        svg.setPointerCapture(e.pointerId);
      }} else if (plusAttr !== null) {{
        pushUndo();
        state.drag = {{ mode: "move-plus", pli: Number(plusAttr) }};
        svg.setPointerCapture(e.pointerId);
      }}
      return;
    }}

    if (state.tool.startsWith("bond-") || ["wedge", "hash", "wavy"].includes(state.tool)) {{
      if (atomAttr !== null) {{
        const ai = Number(atomAttr);
        const a = state.graph.atoms[ai];
        state.drag = {{ mode: "sprout", fromIdx: ai, x1: a.x, y1: a.y, x2: a.x, y2: a.y, moved: false, snapIdx: -1 }};
        svg.setPointerCapture(e.pointerId);
        return;
      }}
    }}
  }});

  svg.addEventListener("pointermove", (e) => {{
    const pt = svgPt(e);
    if (!state.drag) {{
      const t = e.target;
      const ha = t.getAttribute && t.getAttribute("data-atom");
      const hb = t.getAttribute && t.getAttribute("data-bond");
      const na = ha !== null ? Number(ha) : -1;
      const nbIdx = hb !== null ? Number(hb) : -1;
      if (na !== state.hoverAtom || nbIdx !== state.hoverBond) {{
        state.hoverAtom = na; state.hoverBond = nbIdx; render();
      }}
      return;
    }}
    if (state.drag.mode === "move-atom") {{
      state.graph.atoms[state.drag.ai].x = +pt.x.toFixed(1);
      state.graph.atoms[state.drag.ai].y = +pt.y.toFixed(1);
      render();
    }} else if (state.drag.mode === "move-arrow") {{
      const dx = pt.x - state.drag.startPt.x, dy = pt.y - state.drag.startPt.y;
      const ar = state.graph.arrows[state.drag.ari];
      ar.x1 = +(state.drag.orig.x1 + dx).toFixed(1); ar.y1 = +(state.drag.orig.y1 + dy).toFixed(1);
      ar.x2 = +(state.drag.orig.x2 + dx).toFixed(1); ar.y2 = +(state.drag.orig.y2 + dy).toFixed(1);
      render();
    }} else if (state.drag.mode === "move-plus") {{
      state.graph.pluses[state.drag.pli].x = +pt.x.toFixed(1);
      state.graph.pluses[state.drag.pli].y = +pt.y.toFixed(1);
      render();
    }} else if (state.drag.mode === "sprout") {{
      const d = Math.hypot(pt.x - state.drag.x1, pt.y - state.drag.y1);
      if (d > 6) state.drag.moved = true;
      const snap = nearestAtom(pt, state.drag.fromIdx, 15.5);
      if (snap >= 0) {{
        state.drag.x2 = state.graph.atoms[snap].x;
        state.drag.y2 = state.graph.atoms[snap].y;
        state.drag.snapIdx = snap;
      }} else {{
        const L = e.shiftKey ? Math.max(16, d) : bondLength(state.graph);
        let ang = Math.atan2(pt.y - state.drag.y1, pt.x - state.drag.x1);
        if (!e.shiftKey) ang = Math.round(ang / (Math.PI / 12)) * (Math.PI / 12);
        state.drag.x2 = +(state.drag.x1 + Math.cos(ang) * L).toFixed(2);
        state.drag.y2 = +(state.drag.y1 + Math.sin(ang) * L).toFixed(2);
        state.drag.snapIdx = -1;
      }}
      render();
    }}
  }});

  svg.addEventListener("pointerup", (e) => {{
    if (!state.drag) return;
    const drag = state.drag;
    state.drag = null;
    if (drag.mode === "sprout") {{
      pushUndo();
      const ord = orderForTool(state.tool);
      if (drag.moved) {{
        let targetIdx = drag.snapIdx;
        if (targetIdx < 0) {{
          targetIdx = state.graph.atoms.length;
          state.graph.atoms.push({{ s: state.elem, x: drag.x2, y: drag.y2 }});
        }}
        const eb = findBond(state.graph, drag.fromIdx, targetIdx);
        if (eb >= 0) state.graph.bonds[eb].o = ord;
        else state.graph.bonds.push({{ a: drag.fromIdx, b: targetIdx, o: ord }});
        setStatus(drag.snapIdx >= 0 ? "Closed ring bond" : "Drew bond");
      }} else {{
        const ai = drag.fromIdx;
        if (state.fg) {{
          attachGroup(state.graph, ai, state.fg);
          setStatus("Attached -" + state.fg);
        }} else if (state.elem !== "C" && state.graph.atoms[ai].s !== state.elem && state.tool === "bond-1") {{
          state.graph.atoms[ai].s = state.elem;
          setStatus("Set atom to " + state.elem);
        }} else {{
          const L = bondLength(state.graph);
          const ang = sproutAngle(state.graph, ai, ord);
          const ni = state.graph.atoms.length;
          state.graph.atoms.push({{ s: state.elem, x: +(drag.x1 + Math.cos(ang) * L).toFixed(2), y: +(drag.y1 + Math.sin(ang) * L).toFixed(2) }});
          state.graph.bonds.push({{ a: ai, b: ni, o: ord }});
        }}
      }}
      render();
      persistHostState();
    }} else {{
      persistHostState();
    }}
  }});

  svg.addEventListener("click", (e) => {{
    if (state.tool === "move" || state.tool.startsWith("bond-") || ["wedge", "hash", "wavy"].includes(state.tool)) {{
      const t = e.target;
      const bondAttr = t.getAttribute && t.getAttribute("data-bond");
      if (bondAttr !== null && state.tool !== "move") {{
        pushUndo();
        const bi = Number(bondAttr);
        const b = state.graph.bonds[bi];
        if (["wedge", "hash", "wavy"].includes(state.tool)) {{
          const targetOrd = orderForTool(state.tool);
          if (b.o === targetOrd) {{ const tmp = b.a; b.a = b.b; b.b = tmp; }}
          else b.o = targetOrd;
        }} else if (state.tool === "bond-2") {{
          b.o = b.o === 2 ? 1 : 2;
        }} else if (state.tool === "bond-3") {{
          b.o = b.o === 3 ? 1 : 3;
        }} else {{
          b.o = b.o === 1 ? 2 : (b.o === 2 ? 3 : 1);
        }}
        render(); persistHostState(); return;
      }}
      // Empty canvas click with bond tool starts a 2-atom bond
      if (t === svg && state.tool !== "move") {{
        const pt = svgPt(e);
        pushUndo();
        const L = bondLength(state.graph);
        const i0 = state.graph.atoms.length;
        state.graph.atoms.push(
          {{ s: state.elem, x: +(pt.x - L * 0.43).toFixed(1), y: +(pt.y + L * 0.25).toFixed(1) }},
          {{ s: "C", x: +(pt.x + L * 0.43).toFixed(1), y: +(pt.y - L * 0.25).toFixed(1) }}
        );
        state.graph.bonds.push({{ a: i0, b: i0 + 1, o: orderForTool(state.tool) }});
        render(); persistHostState();
      }}
      return;
    }}

    const pt = svgPt(e);
    const t = e.target;
    const atomAttr = t.getAttribute && t.getAttribute("data-atom");
    const bondAttr = t.getAttribute && t.getAttribute("data-bond");
    const arrowAttr = t.getAttribute && t.getAttribute("data-arrow");
    const plusAttr = t.getAttribute && t.getAttribute("data-plus");

    if (state.tool === "erase") {{
      pushUndo();
      if (atomAttr !== null) {{
        const ai = Number(atomAttr);
        state.graph.bonds = state.graph.bonds.filter((b) => b.a !== ai && b.b !== ai)
          .map((b) => ({{ ...b, a: b.a > ai ? b.a - 1 : b.a, b: b.b > ai ? b.b - 1 : b.b }}));
        state.graph.atoms.splice(ai, 1);
        state.graph.ring_fills = [];
      }} else if (bondAttr !== null) {{
        state.graph.bonds.splice(Number(bondAttr), 1);
      }} else if (arrowAttr !== null) {{
        state.graph.arrows.splice(Number(arrowAttr), 1);
      }} else if (plusAttr !== null) {{
        state.graph.pluses.splice(Number(plusAttr), 1);
      }}
      render(); persistHostState(); return;
    }}

    if (state.tool.startsWith("ring-")) {{
      pushUndo();
      const sides = state.tool === "ring-5" ? 5 : 6;
      const arom = state.tool === "ring-ph" || state.tool === "ring-pyr";
      const hetN = state.tool === "ring-pyr";
      if (bondAttr !== null) {{
        fuseRingOnBond(state.graph, Number(bondAttr), sides, arom, hetN);
        setStatus("Fused " + sides + "-membered ring onto bond");
      }} else if (atomAttr !== null) {{
        const ai = Number(atomAttr), L = bondLength(state.graph), ang = sproutAngle(state.graph, ai, 1);
        const R = L / (2 * Math.sin(Math.PI / sides));
        const cx = state.graph.atoms[ai].x + Math.cos(ang) * (L + R);
        const cy = state.graph.atoms[ai].y + Math.sin(ang) * (L + R);
        const rStart = placeFreeRing(state.graph, cx, cy, sides, arom, hetN);
        let closest = rStart, minD = 9999;
        for (let k = rStart; k < rStart + sides; k++) {{
          const d = Math.hypot(state.graph.atoms[k].x - state.graph.atoms[ai].x, state.graph.atoms[k].y - state.graph.atoms[ai].y);
          if (d < minD) {{ minD = d; closest = k; }}
        }}
        state.graph.bonds.push({{ a: ai, b: closest, o: 1 }});
        setStatus("Sprouted ring substituent");
      }} else {{
        placeFreeRing(state.graph, pt.x, pt.y, sides, arom, hetN);
      }}
      render(); persistHostState(); return;
    }}

    if (state.tool === "arrow") {{
      pushUndo();
      if (arrowAttr !== null) {{
        const ar = state.graph.arrows[Number(arrowAttr)];
        ar.style = ar.style === "solid" ? "eq" : (ar.style === "eq" ? "retro" : "solid");
        setStatus("Cycled arrow style: " + ar.style);
      }} else {{
        state.graph.arrows.push({{ x1: +(pt.x - 45).toFixed(1), y1: +pt.y.toFixed(1), x2: +(pt.x + 45).toFixed(1), y2: +pt.y.toFixed(1), style: "solid", above: "cat., solvent", below: "rt, 2 h" }});
        setStatus("Added reaction arrow (double-click to edit conditions)");
      }}
      render(); persistHostState(); return;
    }}

    if (state.tool === "plus") {{
      pushUndo();
      state.graph.pluses.push({{ x: +pt.x.toFixed(1), y: +pt.y.toFixed(1) }});
      render(); persistHostState(); return;
    }}

    if (state.tool === "highlight") {{
      const rings = findSmallRings(state.graph);
      let hit = null, bestD = 38;
      rings.forEach((r) => {{
        const rcx = r.reduce((s, idx) => s + state.graph.atoms[idx].x, 0) / r.length;
        const rcy = r.reduce((s, idx) => s + state.graph.atoms[idx].y, 0) / r.length;
        const d = Math.hypot(rcx - pt.x, rcy - pt.y);
        if (d < bestD) {{ bestD = d; hit = r; }}
      }});
      if (hit) {{
        pushUndo();
        const key = [...hit].sort((a, b) => a - b).join(",");
        const idx = (state.graph.ring_fills || []).findIndex((rf) => [...rf.atoms].sort((a, b) => a - b).join(",") === key);
        if (idx >= 0 && state.graph.ring_fills[idx].color === state.hlColor) state.graph.ring_fills.splice(idx, 1);
        else if (idx >= 0) state.graph.ring_fills[idx].color = state.hlColor;
        else state.graph.ring_fills.push({{ atoms: hit, color: state.hlColor }});
        render(); persistHostState();
      }}
    }}
  }});

  // Double-click atom or arrow to edit custom label / conditions
  svg.addEventListener("dblclick", (e) => {{
    const t = e.target;
    const arrowAttr = t.getAttribute && t.getAttribute("data-arrow");
    const atomAttr = t.getAttribute && t.getAttribute("data-atom");
    if (arrowAttr !== null) {{
      const ar = state.graph.arrows[Number(arrowAttr)];
      const above = window.prompt("Reagents above arrow:", ar.above || "");
      if (above === null) return;
      const below = window.prompt("Conditions below arrow:", ar.below || "");
      pushUndo();
      ar.above = above;
      if (below !== null) ar.below = below;
      render(); persistHostState();
    }} else if (atomAttr !== null) {{
      const ai = Number(atomAttr);
      const val = window.prompt("Atom or superatom label (e.g. O, N, Boc, CF3, R1):", state.graph.atoms[ai].s);
      if (val && val.trim()) {{
        pushUndo();
        state.graph.atoms[ai].s = val.trim().slice(0, 8);
        render(); persistHostState();
      }}
    }}
  }});

  // Keyboard shortcuts (active when not typing in input)
  window.addEventListener("keydown", (e) => {{
    if (e.target && ["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName)) return;
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {{ e.preventDefault(); q("#cdx-undo").click(); return; }}
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") {{ e.preventDefault(); q("#cdx-redo").click(); return; }}
    const k = e.key.toLowerCase();
    if (state.hoverAtom >= 0 && ["c","n","o","s","p","f","b","i"].includes(k)) {{
      pushUndo();
      state.graph.atoms[state.hoverAtom].s = k.toUpperCase();
      render(); persistHostState(); return;
    }}
    const toolMap = {{ "1":"bond-1", "2":"bond-2", "3":"bond-3", "w":"wedge", "h":"hash", "6":"ring-ph", "5":"ring-5", "v":"move", "e":"erase", "delete":"erase", "backspace":"erase" }};
    if (toolMap[k]) {{
      const btn = q(`[data-tool="${{toolMap[k]}}"]`);
      if (btn) btn.click();
    }}
  }});

  function selectTool(toolName) {{
    state.tool = toolName;
    qa("[data-tool]").forEach((b) => b.classList.toggle("is-active", b.getAttribute("data-tool") === toolName));
  }}
  qa("[data-tool]").forEach((btn) => btn.addEventListener("click", () => {{ state.fg = null; qa("[data-fg]").forEach((x) => x.classList.remove("is-active")); selectTool(btn.getAttribute("data-tool")); }}));

  qa("[data-pane]").forEach((btn) => {{
    btn.addEventListener("click", () => {{
      const target = btn.getAttribute("data-pane");
      qa("[data-pane]").forEach((b) => b.classList.toggle("is-active", b === btn));
      ["tmpl", "atoms", "io"].forEach((p) => {{ q("#cdx-pane-" + p).hidden = p !== target; }});
    }});
  }});

  qa("[data-elem]").forEach((btn) => {{
    btn.addEventListener("click", () => {{
      state.elem = btn.getAttribute("data-elem");
      state.fg = null;
      qa("[data-elem]").forEach((b) => b.classList.toggle("is-active", b === btn));
      qa("[data-fg]").forEach((b) => b.classList.remove("is-active"));
      if (!state.tool.startsWith("bond-")) selectTool("bond-1");
      setStatus("Element brush: " + state.elem);
    }});
  }});

  qa("[data-chg]").forEach((btn) => {{
    btn.addEventListener("click", () => {{
      const c = Number(btn.getAttribute("data-chg"));
      if (state.hoverAtom >= 0) {{
        pushUndo();
        if (c === 0) delete state.graph.atoms[state.hoverAtom].chg;
        else state.graph.atoms[state.hoverAtom].chg = c;
        render(); persistHostState();
      }} else {{
        setStatus("Hover an atom or click after selecting charge");
      }}
    }});
  }});

  qa("[data-fg]").forEach((btn) => {{
    btn.addEventListener("click", () => {{
      state.fg = btn.getAttribute("data-fg");
      qa("[data-fg]").forEach((b) => b.classList.toggle("is-active", b === btn));
      qa("[data-elem]").forEach((b) => b.classList.remove("is-active"));
      selectTool("bond-1");
      setStatus("Click any atom to attach -" + state.fg);
    }});
  }});

  qa("[data-hl]").forEach((btn) => {{
    btn.addEventListener("click", () => {{
      state.hlColor = btn.getAttribute("data-hl");
      selectTool("highlight");
      setStatus("Click inside any ring to shade");
    }});
  }});

  function transformCoords(fn) {{
    const atoms = state.graph.atoms;
    if (!atoms.length) return;
    pushUndo();
    const cx = atoms.reduce((s, a) => s + a.x, 0) / atoms.length;
    const cy = atoms.reduce((s, a) => s + a.y, 0) / atoms.length;
    atoms.forEach((a) => {{
      const [nx, ny] = fn(a.x - cx, a.y - cy);
      a.x = +(cx + nx).toFixed(2);
      a.y = +(cy + ny).toFixed(2);
    }});
    render(); persistHostState();
  }}
  q("#cdx-rot-l").addEventListener("click", () => {{ const c = Math.cos(-Math.PI / 12), s = Math.sin(-Math.PI / 12); transformCoords((x, y) => [x * c - y * s, x * s + y * c]); }});
  q("#cdx-rot-r").addEventListener("click", () => {{ const c = Math.cos(Math.PI / 12), s = Math.sin(Math.PI / 12); transformCoords((x, y) => [x * c - y * s, x * s + y * c]); }});
  q("#cdx-flip-h").addEventListener("click", () => transformCoords((x, y) => [-x, y]));
  q("#cdx-clean").addEventListener("click", () => {{
    const atoms = state.graph.atoms;
    if (!atoms.length) return;
    pushUndo();
    const xs = atoms.map((a) => a.x), ys = atoms.map((a) => a.y);
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2, cy = (Math.min(...ys) + Math.max(...ys)) / 2;
    atoms.forEach((a) => {{ a.x = +(280 + (a.x - cx)).toFixed(2); a.y = +(145 + (a.y - cy)).toFixed(2); }});
    render(); persistHostState();
  }});
  q("#cdx-undo").addEventListener("click", () => {{
    if (!state.undoStack.length) return;
    state.redoStack.push(JSON.stringify(state.graph));
    state.graph = JSON.parse(state.undoStack.pop());
    render(); persistHostState();
  }});
  q("#cdx-redo").addEventListener("click", () => {{
    if (!state.redoStack.length) return;
    state.undoStack.push(JSON.stringify(state.graph));
    state.graph = JSON.parse(state.redoStack.pop());
    render(); persistHostState();
  }});
  q("#cdx-clear").addEventListener("click", () => {{
    pushUndo();
    state.graph = {{ name: "Custom", atoms: [], bonds: [], arrows: [], pluses: [], texts: [], circles: [], spokes: [], ring_fills: [] }};
    render(); persistHostState();
  }});
  styleSel.addEventListener("change", () => {{ state.style = styleSel.value; render(); persistHostState(); }});

  q("#cdx-smi-load").addEventListener("click", () => {{
    const raw = q("#cdx-smi-in").value.trim();
    const parsed = parseSmilesClient(raw);
    if (!parsed) {{ setStatus("Could not parse SMILES: " + raw); return; }}
    pushUndo();
    state.graph = parsed;
    render(); persistHostState();
    setStatus("Loaded SMILES: " + raw);
  }});

  q("#cdx-copy-smi").addEventListener("click", async () => {{
    const smi = graphToSmiles(state.graph) || state.graph.smiles || "";
    try {{ await navigator.clipboard.writeText(smi); setStatus("Copied SMILES: " + smi); }}
    catch (_e) {{ setStatus("SMILES: " + smi); }}
  }});
  q("#cdx-dl-cdxml").addEventListener("click", () => {{
    const blob = new Blob([generateCdxml(state.graph)], {{ type: "application/xml;charset=utf-8" }});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = ((state.graph.name || "structure").replace(/[^a-z0-9_-]+/gi, "_")) + ".cdxml";
    a.click();
  }});
  q("#cdx-dl-svg").addEventListener("click", () => {{
    const blob = new Blob([svg.outerHTML], {{ type: "image/svg+xml;charset=utf-8" }});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = ((state.graph.name || "structure").replace(/[^a-z0-9_-]+/gi, "_")) + ".svg";
    a.click();
  }});

  // Universal Multi-Host Bridge (Inline Surface API + MCP Apps JSON-RPC + Local Live-Sync + Clipboard Fallback)
  let rpcId = 1;
  function postHost(msg) {{ try {{ window.parent.postMessage(msg, "*"); }} catch (_e) {{}} }}
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
      return;
    }}
    if (msg.method === "ui/notifications/tool-result") {{
      const p = extractResultPayload(msg.params);
      if (p && p.graph) {{
        state.graph = cloneGraph(p.graph);
        if (p.style && p.style in STYLES) {{ state.style = p.style; styleSel.value = p.style; }}
        render(); buildTemplatePane();
      }}
    }}
  }});

  q("#cdx-open-3d").addEventListener("click", () => {{
    const smi = graphToSmiles(state.graph) || state.graph.smiles || state.graph.name || "aspirin";
    if (hostGlobal && typeof hostGlobal.sendFollowUpMessage === "function") {{
      hostGlobal.sendFollowUpMessage({{ prompt: "Open 3D Mol* viewer for SMILES: " + smi, title: "Open in 3D Mol*" }});
    }}
    postHost({{ jsonrpc: "2.0", id: ++rpcId, method: "tools/call", params: {{ name: "view_molecule_3d", arguments: {{ smiles: smi.split(">>").pop(), query: state.graph.name || "Structure" }} }} }});
    postHost({{ jsonrpc: "2.0", id: ++rpcId, method: "ui/message", params: {{ role: "user", content: [{{ type: "text", text: "Open 3D Mol* view for: " + smi }}] }} }});
    setStatus("Requested 3D Mol* view for " + smi);
  }});

  q("#cdx-send-host").addEventListener("click", async () => {{
    const cdxml = generateCdxml(state.graph);
    const smi = graphToSmiles(state.graph) || state.graph.smiles || "";
    const promptText = "Use this structure drawn in 2D Studio (style=" + state.style + ", SMILES=" + smi + ") and render editable ChemDraw CDXML:\\n\\n```xml\\n" + cdxml + "\\n```";

    try {{ await navigator.clipboard.writeText(promptText); }} catch (_e) {{}}
    if (window.__CDX_LIVE_SYNC_URL__) {{
      try {{
        await fetch(window.__CDX_LIVE_SYNC_URL__, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ smiles: smi, style: state.style, cdxml, graph: state.graph }})
        }});
        setStatus("Saved live to workspace + copied prompt ✓");
        return;
      }} catch (_e) {{}}
    }}
    if (hostGlobal && typeof hostGlobal.sendFollowUpMessage === "function") {{
      await hostGlobal.sendFollowUpMessage({{ prompt: promptText, title: "Render drawn structure in ChemDraw" }});
      setStatus("Sent structure to conversation ✓");
      return;
    }}
    postHost({{ jsonrpc: "2.0", id: ++rpcId, method: "ui/message", params: {{ role: "user", content: [{{ type: "text", text: promptText }}] }} }});
    setStatus("Sent to host & copied prompt to clipboard ✓");
  }});

  if (window.parent && window.parent !== window) {{
    postHost({{
      jsonrpc: "2.0", id: 1, method: "ui/initialize",
      params: {{ appInfo: {{ name: "cdxml-drawing-studio", version: "2.0.0" }}, appCapabilities: {{}}, protocolVersion: "2026-01-26" }}
    }});
    if (typeof ResizeObserver !== "undefined") {{
      const ro = new ResizeObserver((entries) => {{
        for (const entry of entries) {{
          const h = Math.ceil(entry.contentRect.height) + 8;
          const w = Math.ceil(entry.contentRect.width);
          if (h > 40) postHost({{ jsonrpc: "2.0", method: "ui/notifications/size-changed", params: {{ width: w, height: h }} }});
        }}
      }});
      ro.observe(root);
    }} else {{
      postHost({{ jsonrpc: "2.0", method: "ui/notifications/size-changed", params: {{ width: 880, height: 440 }} }});
    }}
  }}

  buildTemplatePane();
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
    template: str = "aspirin",
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
        norm = (template or "aspirin").strip().lower().replace("-", "_").replace(" ", "_")
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
    template: str = "aspirin",
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
