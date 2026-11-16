"""Interactive 3D Mol* viewer and 2D molecular drawing studio MCP App views."""

from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
import tempfile
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
    "acs1996": {"label": "ACS Document 1996 / JACS", "bondLength": 14.4, "lineWidth": 0.6, "font": "Arial", "labelSize": 10},
    "jacs": {"label": "JACS Publication", "bondLength": 14.4, "lineWidth": 0.6, "font": "Arial", "labelSize": 10},
    "angew": {"label": "Angewandte Chemie", "bondLength": 14.2, "lineWidth": 0.65, "font": "Helvetica", "labelSize": 10},
    "nature": {"label": "Nature Chemistry", "bondLength": 14.0, "lineWidth": 0.6, "font": "Helvetica", "labelSize": 9.5},
    "science": {"label": "Science", "bondLength": 13.8, "lineWidth": 0.58, "font": "Helvetica", "labelSize": 9.5},
    "rsc": {"label": "RSC Chemical Science", "bondLength": 14.4, "lineWidth": 0.6, "font": "Arial", "labelSize": 10},
    "wiley": {"label": "Wiley Advanced", "bondLength": 14.5, "lineWidth": 0.65, "font": "Arial", "labelSize": 10},
    "org_lett": {"label": "Organic Letters", "bondLength": 14.4, "lineWidth": 0.6, "font": "Arial", "labelSize": 10},
    "synthesis": {"label": "Synthesis / Synlett", "bondLength": 14.4, "lineWidth": 0.6, "font": "Arial", "labelSize": 10},
}

_ELEMENT_MAP = {
    1: "H", 5: "B", 6: "C", 7: "N", 8: "O", 9: "F", 11: "Na", 12: "Mg",
    14: "Si", 15: "P", 16: "S", 17: "Cl", 19: "K", 26: "Fe", 27: "Co",
    28: "Ni", 29: "Cu", 30: "Zn", 35: "Br", 44: "Ru", 46: "Pd", 53: "I",
}
_ATOMIC_WEIGHTS = {
    "H": 1.008, "B": 10.81, "C": 12.011, "N": 14.007, "O": 15.999,
    "F": 18.998, "Si": 28.085, "P": 30.974, "S": 32.06, "Cl": 35.45,
    "Fe": 55.845, "Ni": 58.693, "Cu": 63.546, "Zn": 65.38, "Br": 79.904,
    "Pd": 106.42, "I": 126.904,
}
_PDB_CODE_RE = re.compile(r"^[0-9][A-Za-z0-9]{3}$")
_INLINE_INLINE_SCRIPT_ESCAPE = "</script>"


def _html_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True).replace("</", "<\\/")


def _normalize_molecule_key(raw: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", raw.strip().lower()).strip()


def _resolve_smiles_input(query: str) -> tuple[str | None, str, str]:
    """Return (smiles, title, source_kind) for a query string."""
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
  html, body {{ margin: 0; padding: 0; height: 100%; background: var(--bg); color: var(--text);
    font: 13px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; overflow: hidden; }}
  .shell {{ display: flex; flex-direction: column; height: 100vh; min-height: 540px; }}
  .topbar {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 8px 12px;
    background: var(--panel); border-bottom: 1px solid var(--line); }}
  .brand {{ font-weight: 700; letter-spacing: 0.01em; display: flex; align-items: center; gap: 6px; }}
  .badge {{ font-size: 11px; padding: 2px 7px; border-radius: 999px; background: var(--panel-2);
    border: 1px solid var(--line); color: var(--accent); font-weight: 600; }}
  .spacer {{ flex: 1; }}
  .controls {{ display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }}
  button, select, input {{
    background: var(--panel-2); color: var(--text); border: 1px solid var(--line);
    border-radius: 7px; padding: 5px 9px; font-size: 12px; font-family: inherit;
  }}
  button {{ cursor: pointer; font-weight: 600; transition: border-color .15s, background .15s; }}
  button:hover {{ border-color: var(--accent); }}
  button.active {{ background: var(--accent); color: #081018; border-color: var(--accent); }}
  input[type="text"] {{ width: 150px; }}
  .stage-wrap {{ position: relative; flex: 1; display: grid; grid-template-columns: 1fr 240px; min-height: 0; }}
  @media (max-width: 720px) {{ .stage-wrap {{ grid-template-columns: 1fr; }} .sidebar {{ display: none; }} }}
  .stage {{ position: relative; width: 100%; height: 100%; overflow: hidden; }}
  #molstar-container, #fallback-canvas {{
    position: absolute; inset: 0; width: 100%; height: 100%;
  }}
  #molstar-container {{ display: none; }}
  #fallback-canvas {{ display: block; cursor: grab; }}
  #fallback-canvas:active {{ cursor: grabbing; }}
  .hud {{ position: absolute; left: 12px; bottom: 12px; padding: 6px 10px; border-radius: 8px;
    background: rgba(15,20,25,0.78); color: #e6edf3; border: 1px solid rgba(255,255,255,0.12);
    font-size: 11.5px; pointer-events: none; backdrop-filter: blur(8px); }}
  .sidebar {{ background: var(--panel); border-left: 1px solid var(--line); padding: 12px;
    display: flex; flex-direction: column; gap: 10px; overflow: auto; }}
  .card {{ background: var(--panel-2); border: 1px solid var(--line); border-radius: 9px; padding: 9px 10px; }}
  .card h4 {{ margin: 0 0 6px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); }}
  .kv {{ display: grid; grid-template-columns: auto 1fr; gap: 4px 10px; font-size: 12px; }}
  .kv span {{ color: var(--muted); }}
  .kv code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11.5px; word-break: break-all; }}
  .preset-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }}
  .status-dot {{ width: 8px; height: 8px; border-radius: 50%; background: var(--accent-2); display: inline-block; }}
</style>
</head>
<body data-theme="auto">
<div class="shell">
  <div class="topbar">
    <div class="brand">
      <span class="status-dot" id="engine-dot"></span>
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
      <button id="btn-spin" title="Toggle auto-rotation">Spin</button>
      <button id="btn-reset" title="Reset camera">Reset</button>
      <button id="btn-engine" title="Switch Mol* WebGL vs Built-in Canvas">Use Mol* WebGL</button>
      <input id="pdb-input" type="text" placeholder="PDB ID e.g. 1CRN" />
      <button id="btn-load-pdb">Load PDB</button>
      <button id="btn-ask-agent" title="Ask host agent to convert/open in 2D ChemDraw">Send to 2D Studio</button>
    </div>
  </div>
  <div class="stage-wrap">
    <div class="stage" id="stage">
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
          <button data-pdb="1CRN">1CRN Crambin</button>
          <button data-pdb="1UBQ">1UBQ Ubiquitin</button>
          <button data-pdb="6LU7">6LU7 Mpro</button>
          <button data-pdb="4HHB">4HHB Hemoglobin</button>
        </div>
      </div>
      <div class="card">
        <h4>Downloads &amp; Host</h4>
        <div style="display:flex; flex-direction:column; gap:6px;">
          <button id="btn-dl-data">Download Structure File</button>
          <button id="btn-drop-file">Load Local .pdb/.cif/.sdf</button>
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
    molstarViewer: null,
    molstarFailed: false
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
    return {{
      sx: w * 0.5 + x1 * scale * persp,
      sy: h * 0.5 - y2 * scale * persp,
      z: z2,
      p: persp
    }};
  }}

  function drawCanvas() {{
    if (state.engine !== "canvas") return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = canvas.clientWidth || 640, h = canvas.clientHeight || 480;
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {{
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
    }}
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    if (!normalized.atoms.length) {{
      ctx.fillStyle = "#93a1b5";
      ctx.font = "14px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(state.payload.pdb_id
        ? ("PDB " + state.payload.pdb_id + " ready — click 'Use Mol* WebGL' or load online")
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
        if (r >= 9 && p.a.s !== "C" && p.a.s !== "H") {{
          ctx.fillStyle = p.a.s === "S" ? "#111827" : "#ffffff";
          ctx.font = "bold " + Math.min(13, Math.round(r * 0.85)) + "px sans-serif";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(p.a.s, p.sx, p.sy + 0.5);
        }}
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
      hud.textContent = hasGl
        ? "Mol* CDN script unavailable in sandbox — using built-in 3D engine."
        : "Built-in 3D engine active (WebGL context unavailable in this pane).";
      badge.textContent = hasGl ? "Built-in 3D (Offline)" : "Built-in 3D Canvas";
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
      console.warn("Mol* fallback:", err);
      state.engine = "canvas";
      molstarEl.style.display = "none";
      canvas.style.display = "block";
      badge.textContent = "Built-in 3D Engine";
      engineBtn.textContent = "Use Mol* WebGL";
      hud.textContent = "WebGL fallback active (" + (err && err.message ? err.message : "offline") + ")";
      return false;
    }}
  }}

  async function loadIntoMolstar(p) {{
    if (!state.molstarViewer) return;
    await state.molstarViewer.plugin.clear();
    if (p.mol_data) {{
      const fmt = (p.format || "sdf").toLowerCase();
      const molFmt = fmt === "cif" ? "mmcif" : fmt;
      await state.molstarViewer.loadStructureFromData(p.mol_data, molFmt, {{ dataLabel: p.title || "Structure" }});
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

  // Mouse Orbit & Zoom
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
  document.getElementById("btn-reset").addEventListener("click", () => {{
    state.rotX = 0.35; state.rotY = 0.45; state.zoom = 1.0; drawCanvas();
  }});
  engineBtn.addEventListener("click", () => {{
    if (state.engine === "canvas") {{
      tryEnableMolstar();
    }} else {{
      state.engine = "canvas";
      molstarEl.style.display = "none";
      canvas.style.display = "block";
      badge.textContent = "Built-in 3D Engine";
      engineBtn.textContent = "Use Mol* WebGL";
      drawCanvas();
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

  // MCP Apps Host Bridge (JSON-RPC 2.0 over postMessage)
  let rpcId = 1;
  function postHost(msg) {{
    try {{ window.parent.postMessage(msg, "*"); }} catch (_err) {{}}
  }}
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
      if (msg.result.hostContext && msg.result.hostContext.theme) {{
        document.body.dataset.theme = msg.result.hostContext.theme;
      }}
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
    postHost({{
      jsonrpc: "2.0",
      id: ++rpcId,
      method: "tools/call",
      params: {{ name: "open_drawing_studio", arguments: {{ smiles: smi, name: state.payload.title || "molecule" }} }}
    }});
    postHost({{
      jsonrpc: "2.0",
      id: ++rpcId,
      method: "ui/message",
      params: {{
        role: "user",
        content: [{{ type: "text", text: "Open this structure in 2D ChemDraw Studio: " + (smi || state.payload.title || "3D structure") }}]
      }}
    }});
  }});

  if (window.parent && window.parent !== window) {{
    postHost({{
      jsonrpc: "2.0",
      id: 1,
      method: "ui/initialize",
      params: {{ appInfo: {{ name: "cdxml-molstar-viewer", version: "1.0.0" }}, appCapabilities: {{}}, protocolVersion: "2026-01-26" }}
    }});
    postHost({{ jsonrpc: "2.0", method: "ui/notifications/size-changed", params: {{ width: 920, height: 620 }} }});
  }}

  applyPayload(state.payload);
  // Upgrade to Mol* WebGL automatically when loaded from CDN; keep responsive canvas underneath while loading
  window.addEventListener("load", () => {{
    if (window.molstar && window.molstar.Viewer) tryEnableMolstar();
  }});
  function tick() {{
    if (state.spin && !dragging && state.engine === "canvas") {{
      state.rotY += 0.008;
      drawCanvas();
    }}
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
    "paracetamol": {"name": "Paracetamol", "smiles": "CC(=O)Nc1ccc(O)cc1", "category": "Molecules"},
    "ibuprofen": {"name": "Ibuprofen", "smiles": "CC(C)Cc1ccc(C(C)C(=O)O)cc1", "category": "Molecules"},
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
            {"s": "C", "x": 110, "y": 140}, {"s": "C", "x": 155, "y": 118}, {"s": "C", "x": 205, "y": 136},
            {"s": "C", "x": 235, "y": 106}, {"s": "C", "x": 190, "y": 128}, {"s": "C", "x": 140, "y": 110},
            {"s": "O", "x": 235, "y": 68}, {"s": "H", "x": 110, "y": 176},
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
            {"s": "C", "x": 170, "y": 135}, {"s": "Me", "x": 170, "y": 78}, {"s": "H", "x": 120, "y": 165},
            {"s": "H", "x": 220, "y": 165}, {"s": "Me", "x": 170, "y": 198}, {"s": "H", "x": 115, "y": 102},
            {"s": "H", "x": 225, "y": 102},
        ],
        "bonds": [
            {"a": 0, "b": 1, "o": 1}, {"a": 0, "b": 2, "o": 1}, {"a": 0, "b": 3, "o": 1},
        ],
        "circles": [{"cx": 170, "cy": 135, "r": 26}],
        "spokes": [
            [170, 161, 170, 190], [148, 122, 124, 108], [192, 122, 216, 108],
        ],
    },
    "suzuki_coupling": {
        "name": "Suzuki-Miyaura Coupling",
        "category": "Reaction Templates",
        "smiles": "Brc1ccccc1.OB(O)c1ccc(C)cc1",
        "arrows": [{"x1": 215, "y1": 140, "x2": 310, "y2": 140, "above": "Pd(PPh3)4 (5 mol%)", "below": "K2CO3, THF/H2O, 80 °C"}],
        "product_smiles": "Cc1ccc(-c2ccccc2)cc1",
    },
    "amide_coupling": {
        "name": "HATU Amide Coupling",
        "category": "Reaction Templates",
        "smiles": "O=C(O)c1ccccc1.Nc1ccc(F)cc1",
        "arrows": [{"x1": 215, "y1": 140, "x2": 310, "y2": 140, "above": "HATU, DIPEA", "below": "DMF, rt, 2 h"}],
        "product_smiles": "O=C(Nc1ccc(F)cc1)c1ccccc1",
    },
    "buchwald_hartwig": {
        "name": "Buchwald-Hartwig Amination",
        "category": "Reaction Templates",
        "smiles": "Clc1ccc(OC)cc1.C1CCNCC1",
        "arrows": [{"x1": 215, "y1": 140, "x2": 310, "y2": 140, "above": "Pd2(dba)3, RuPhos", "below": "NaOtBu, PhMe, 100 °C"}],
        "product_smiles": "COc1ccc(N2CCCCC2)cc1",
    },
    "catalytic_cycle": {
        "name": "Pd(0)/Pd(II) Catalytic Cycle",
        "category": "Reaction Templates",
        "smiles": "[Pd]",
        "texts": [
            {"x": 200, "y": 55, "text": "LnPd(0)"},
            {"x": 320, "y": 140, "text": "Ar-Pd(II)-X"},
            {"x": 200, "y": 225, "text": "Ar-Pd(II)-R"},
            {"x": 85, "y": 140, "text": "Ar-R + HX"},
            {"x": 265, "y": 82, "text": "OA: Ar-X"},
            {"x": 272, "y": 195, "text": "TM: R-M"},
            {"x": 122, "y": 195, "text": "RE: Product"},
        ],
    },
    "sar_2x2": {
        "name": "SAR Substrate Scope Scaffold",
        "category": "Reaction Templates",
        "smiles": "c1ccc(C(=O)N[C@@H](C)c2ccccc2)cc1",
        "texts": [
            {"x": 200, "y": 235, "text": "1a (R = H, 92%) | 1b (R = OMe, 95%) | 1c (R = CF3, 81%)"},
        ],
    },
}


def _smiles_to_studio_graph(smiles: str, *, offset_x: float = 135.0, offset_y: float = 135.0, bond_scale: float = 28.0) -> dict[str, Any]:
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

    xs = [p[0] for p in raw_coords]
    ys = [p[1] for p in raw_coords]
    cx = (min(xs) + max(xs)) * 0.5
    cy = (min(ys) + max(ys)) * 0.5

    atoms = []
    for i, atom in enumerate(mol.GetAtoms()):
        rx, ry = raw_coords[i]
        atoms.append({
            "s": atom.GetSymbol(),
            "x": round(offset_x + (rx - cx) * factor, 2),
            "y": round(offset_y - (ry - cy) * factor, 2),
        })
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
        atoms.append({"s": sym, "x": x, "y": y})

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
        bonds.append({"a": id_to_idx[b_id], "b": id_to_idx[e_id], "o": order})

    if all_pts:
        xs = [p[0] for p in all_pts]
        ys = [p[1] for p in all_pts]
        cx, cy = (min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5
        span = max(max(xs) - min(xs), max(ys) - min(ys), 10.0)
        scale = min(2.2, max(1.0, 220.0 / span))
        for atom in atoms:
            atom["x"] = round(210.0 + (atom["x"] - cx) * scale, 2)
            atom["y"] = round(140.0 + (atom["y"] - cy) * scale, 2)
    return {"atoms": atoms, "bonds": bonds}


def _build_studio_graph_for_template(key: str) -> dict[str, Any]:
    tmpl = _STUDIO_TEMPLATES[key]
    graph: dict[str, Any] = {
        "name": tmpl["name"],
        "template_key": key,
        "category": tmpl.get("category", "Molecules"),
        "atoms": [],
        "bonds": [],
        "arrows": list(tmpl.get("arrows") or []),
        "texts": list(tmpl.get("texts") or []),
        "circles": list(tmpl.get("circles") or []),
        "spokes": list(tmpl.get("spokes") or []),
    }
    if "atoms" in tmpl:
        graph["atoms"] = [dict(a) for a in tmpl["atoms"]]
        graph["bonds"] = [dict(b) for b in tmpl["bonds"]]
    elif "arrows" in tmpl and "product_smiles" in tmpl:
        left = _smiles_to_studio_graph(tmpl["smiles"], offset_x=118.0, offset_y=140.0, bond_scale=23.0)
        right = _smiles_to_studio_graph(tmpl["product_smiles"], offset_x=435.0, offset_y=140.0, bond_scale=23.0)
        offset = len(left["atoms"])
        graph["atoms"] = left["atoms"] + right["atoms"]
        graph["bonds"] = left["bonds"] + [
            {"a": b["a"] + offset, "b": b["b"] + offset, "o": b["o"]} for b in right["bonds"]
        ]
        graph["smiles"] = f"{tmpl['smiles']}>>{tmpl['product_smiles']}"
    elif "smiles" in tmpl:
        built = _smiles_to_studio_graph(tmpl["smiles"], offset_x=200.0, offset_y=135.0, bond_scale=28.0)
        graph["atoms"] = built["atoms"]
        graph["bonds"] = built["bonds"]
        graph["smiles"] = tmpl["smiles"]
    return graph


def _studio_template_catalog() -> dict[str, dict[str, Any]]:
    return {key: _build_studio_graph_for_template(key) for key in _STUDIO_TEMPLATES}


def _compute_graph_metrics(graph: dict[str, Any]) -> tuple[str, float, int]:
    from collections import Counter

    valence = {"H": 1, "B": 3, "C": 4, "N": 3, "O": 2, "S": 2, "P": 3, "F": 1, "Cl": 1, "Br": 1, "I": 1}
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
        if sym in _ATOMIC_WEIGHTS:
            counts[sym] += 1
        elif sym == "Me":
            counts["C"] += 1
            counts["H"] += 3
        imp_h = max(0, valence.get(sym, 0) - order_sum[i])
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


def render_drawing_studio_app_html(initial_payload: dict[str, Any] | None = None) -> str:
    """Render the self-contained 2D ChemDraw Template & Drawing Studio MCP App HTML page."""
    catalog = _studio_template_catalog()
    payload = initial_payload or {"graph": catalog["aspirin"], "style": "acs1996", "styles": _STYLE_PRESETS}
    if "styles" not in payload:
        payload = {**payload, "styles": _STYLE_PRESETS}
    initial_json = _html_json(payload)
    catalog_json = _html_json(catalog)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ChemDraw Toolkit · Interactive 2D Studio</title>
<style>
  :root {{
    --bg: #f5f7fa; --panel: #ffffff; --panel-2: #edf2f7;
    --line: rgba(15,23,42,0.12); --text: #0f172a; --muted: #475569;
    --accent: #0284c7; --accent-soft: rgba(2,132,199,0.12); --ink: #0f172a;
    --paper: #ffffff;
  }}
  @media (prefers-color-scheme: dark) {{
    body[data-theme="auto"] {{
      --bg: #0f1419; --panel: #161d25; --panel-2: #1f2934;
      --line: rgba(148,163,184,0.18); --text: #e6edf3; --muted: #93a1b5;
      --accent: #38bdf8; --accent-soft: rgba(56,189,248,0.16); --ink: #0f172a;
      --paper: #ffffff;
    }}
  }}
  body[data-theme="dark"] {{
    --bg: #0f1419; --panel: #161d25; --panel-2: #1f2934;
    --line: rgba(148,163,184,0.18); --text: #e6edf3; --muted: #93a1b5;
    --accent: #38bdf8; --accent-soft: rgba(56,189,248,0.16); --ink: #0f172a;
    --paper: #ffffff;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; height: 100%; background: var(--bg); color: var(--text);
    font: 13px/1.4 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; overflow: hidden; }}
  .app {{ display: grid; grid-template-rows: auto 1fr auto; height: 100vh; min-height: 560px; }}
  .toolbar {{ display: flex; flex-wrap: wrap; align-items: center; gap: 6px; padding: 8px 12px;
    background: var(--panel); border-bottom: 1px solid var(--line); }}
  .title {{ font-weight: 700; margin-right: 6px; }}
  .sep {{ width: 1px; height: 22px; background: var(--line); margin: 0 2px; }}
  button, select, input {{
    background: var(--panel-2); color: var(--text); border: 1px solid var(--line);
    border-radius: 7px; padding: 5px 8px; font-size: 12px; font-family: inherit;
  }}
  button {{ cursor: pointer; font-weight: 600; }}
  button:hover {{ border-color: var(--accent); }}
  button.active {{ background: var(--accent); color: #ffffff; border-color: var(--accent); }}
  .workspace {{ display: grid; grid-template-columns: 220px 1fr 220px; min-height: 0; }}
  @media (max-width: 820px) {{ .workspace {{ grid-template-columns: 185px 1fr; }} .inspector {{ display: none; }} }}
  .gallery, .inspector {{ background: var(--panel); padding: 10px; overflow: auto; }}
  .gallery {{ border-right: 1px solid var(--line); }}
  .inspector {{ border-left: 1px solid var(--line); display: flex; flex-direction: column; gap: 10px; }}
  .group-title {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted);
    margin: 10px 0 6px; font-weight: 700; }}
  .group-title:first-child {{ margin-top: 2px; }}
  .tmpl-btn {{ width: 100%; text-align: left; padding: 6px 8px; margin-bottom: 4px; display: flex;
    justify-content: space-between; align-items: center; background: transparent; }}
  .tmpl-btn.active {{ background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }}
  .canvas-area {{ position: relative; padding: 14px; display: flex; align-items: center; justify-content: center;
    background: radial-gradient(circle at 1px 1px, var(--line) 1px, transparent 0);
    background-size: 20px 20px; overflow: hidden; }}
  #chem-svg {{ width: 100%; height: 100%; max-width: 780px; max-height: 520px; background: var(--paper);
    border-radius: 12px; border: 1px solid var(--line); box-shadow: 0 12px 32px rgba(2,6,23,0.12);
    user-select: none; cursor: crosshair; }}
  .card {{ background: var(--panel-2); border: 1px solid var(--line); border-radius: 9px; padding: 9px; }}
  .card h4 {{ margin: 0 0 6px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); }}
  .stat-row {{ display: flex; justify-content: space-between; align-items: baseline; gap: 8px; font-size: 12px; margin: 3px 0; }}
  .stat-row code {{ font-family: ui-monospace, Menlo, monospace; text-align: right; }}
  .elem-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; }}
  .statusbar {{ display: flex; align-items: center; justify-content: space-between; padding: 6px 12px;
    background: var(--panel); border-top: 1px solid var(--line); font-size: 12px; color: var(--muted); }}
  textarea {{ width: 100%; height: 84px; resize: vertical; background: var(--bg); color: var(--text);
    border: 1px solid var(--line); border-radius: 6px; padding: 6px; font: 11px/1.35 ui-monospace, monospace; }}
</style>
</head>
<body data-theme="auto">
<div class="app">
  <div class="toolbar">
    <span class="title">ChemDraw Studio</span>
    <button data-tool="bond-1" class="active">Bond (1)</button>
    <button data-tool="bond-2">Double (2)</button>
    <button data-tool="bond-3">Triple (3)</button>
    <button data-tool="wedge">Wedge</button>
    <button data-tool="ring-6">Benzene</button>
    <button data-tool="ring-5">Ring-5</button>
    <button data-tool="erase">Erase</button>
    <span class="sep"></span>
    <button id="btn-undo">Undo</button>
    <button id="btn-clean">Clean</button>
    <select id="style-select"></select>
    <span class="sep"></span>
    <button id="btn-dl-cdxml">Download CDXML</button>
    <button id="btn-dl-svg">Download SVG</button>
    <button id="btn-view-3d" title="Open in Mol* 3D Viewer">3D Mol*</button>
    <button id="btn-send-agent" class="active">Render in ChemDraw</button>
  </div>
  <div class="workspace">
    <aside class="gallery" id="template-gallery"></aside>
    <main class="canvas-area">
      <svg id="chem-svg" viewBox="0 0 560 280" xmlns="http://www.w3.org/2000/svg"></svg>
    </main>
    <aside class="inspector">
      <div class="card">
        <h4>Atom Brush</h4>
        <div class="elem-grid" id="elem-palette">
          <button data-elem="C" class="active">C</button>
          <button data-elem="N">N</button>
          <button data-elem="O">O</button>
          <button data-elem="S">S</button>
          <button data-elem="F">F</button>
          <button data-elem="Cl">Cl</button>
          <button data-elem="Br">Br</button>
          <button data-elem="P">P</button>
        </div>
      </div>
      <div class="card">
        <h4>Telemetry</h4>
        <div class="stat-row"><span>Template</span><code id="stat-name">-</code></div>
        <div class="stat-row"><span>Style</span><code id="stat-style">acs1996</code></div>
        <div class="stat-row"><span>Formula</span><code id="stat-formula">-</code></div>
        <div class="stat-row"><span>MW</span><code id="stat-mw">-</code></div>
        <div class="stat-row"><span>Atoms / Bonds</span><code id="stat-counts">0 / 0</code></div>
      </div>
      <div class="card">
        <h4>Live CDXML Preview</h4>
        <textarea id="cdxml-preview" readonly></textarea>
      </div>
    </aside>
  </div>
  <div class="statusbar">
    <span id="hint-text">Click an atom to grow a chain/ring, click a bond to cycle order, or pick a template from the left.</span>
    <span id="host-badge">ACS Document 1996 Ready</span>
  </div>
</div>
<script>
(() => {{
  const INITIAL = {initial_json};
  const CATALOG = {catalog_json};
  const STYLES = INITIAL.styles || {{ acs1996: {{ label: "ACS 1996", bondLength: 14.4, font: "Arial", labelSize: 10 }} }};
  const WEIGHTS = {{ H:1.008, B:10.81, C:12.011, N:14.007, O:15.999, F:18.998, P:30.974, S:32.06, Cl:35.45, Br:79.904 }};
  const VALENCE = {{ H:1, B:3, C:4, N:3, O:2, P:3, S:2, F:1, Cl:1, Br:1 }};
  const ELEM_NUM = {{ H:1, B:5, C:6, N:7, O:8, F:9, P:15, S:16, Cl:17, Br:35 }};

  let state = {{
    graph: JSON.parse(JSON.stringify((INITIAL && INITIAL.graph) || CATALOG.aspirin)),
    style: (INITIAL && INITIAL.style) || "acs1996",
    tool: "bond-1",
    elem: "C",
    history: []
  }};

  const svg = document.getElementById("chem-svg");
  const gallery = document.getElementById("template-gallery");
  const styleSelect = document.getElementById("style-select");

  Object.entries(STYLES).forEach(([slug, cfg]) => {{
    const opt = document.createElement("option");
    opt.value = slug;
    opt.textContent = cfg.label || slug;
    styleSelect.appendChild(opt);
  }});
  styleSelect.value = state.style in STYLES ? state.style : "acs1996";

  function buildGallery() {{
    const groups = {{}};
    Object.entries(CATALOG).forEach(([key, g]) => {{
      const cat = g.category || "Templates";
      (groups[cat] = groups[cat] || []).push([key, g]);
    }});
    gallery.innerHTML = "";
    Object.entries(groups).forEach(([cat, items]) => {{
      const h = document.createElement("div");
      h.className = "group-title";
      h.textContent = cat;
      gallery.appendChild(h);
      items.forEach(([key, g]) => {{
        const btn = document.createElement("button");
        btn.className = "tmpl-btn" + (state.graph.template_key === key ? " active" : "");
        btn.innerHTML = `<span>${{g.name}}</span><span style="opacity:.6;font-size:11px">${{(g.atoms || []).length}}a</span>`;
        btn.addEventListener("click", () => {{
          pushUndo();
          state.graph = JSON.parse(JSON.stringify(g));
          render();
          buildGallery();
        }});
        gallery.appendChild(btn);
      }});
    }});
  }}

  function pushUndo() {{
    state.history.push(JSON.stringify(state.graph));
    if (state.history.length > 30) state.history.shift();
  }}

  function esc(s) {{
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
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
    atoms.forEach((a, i) => {{
      const s = a.s || "C";
      if (WEIGHTS[s]) counts[s] = (counts[s] || 0) + 1;
      else if (s === "Me") {{ counts.C = (counts.C || 0) + 1; counts.H = (counts.H || 0) + 3; }}
      const h = Math.max(0, (VALENCE[s] || 0) - deg[i]);
      if (h) counts.H = (counts.H || 0) + h;
    }});
    let formula = "";
    ["C", "H"].forEach((k) => {{ if (counts[k]) formula += k + (counts[k] > 1 ? counts[k] : ""); }});
    Object.keys(counts).filter((k) => k !== "C" && k !== "H").sort().forEach((k) => {{
      formula += k + (counts[k] > 1 ? counts[k] : "");
    }});
    const mw = Object.entries(counts).reduce((acc, [k, n]) => acc + (WEIGHTS[k] || 0) * n, 0);
    return {{ formula: formula || "-", mw: mw ? mw.toFixed(2) : "-" }};
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
      const x = (a.x * scale + 80).toFixed(2);
      const y = (a.y * scale + 80).toFixed(2);
      const el = ELEM_NUM[a.s] || 6;
      const elAttr = el === 6 ? "" : ` Element="${{el}}"`;
      if (a.s === "C") {{
        lines.push(`      <n id="${{aid}}" p="${{x}} ${{y}}"/>`);
      }} else {{
        lines.push(`      <n id="${{aid}}" p="${{x}} ${{y}}"${{elAttr}}><t p="${{x}} ${{y}}"><s>${{esc(a.s)}}</s></t></n>`);
      }}
      return aid;
    }});
    (g.bonds || []).forEach((b) => {{
      const a = atomIds[b.a], c = atomIds[b.b];
      if (!a || !c) return;
      const bid = nid();
      const orderAttr = b.o === 2 || b.o === 3 ? ` Order="${{b.o}}"` : "";
      const dispAttr = b.o === 4 ? ' Display="WedgeBegin"' : (b.o === 5 ? ' Display="WedgedHashBegin"' : "");
      lines.push(`      <b id="${{bid}}" B="${{a}}" E="${{c}}"${{orderAttr}}${{dispAttr}}/>`);
    }});
    lines.push("    </fragment>", "  </page>", "</CDXML>");
    return lines.join("\\n");
  }}

  function cleanLayout() {{
    const atoms = state.graph.atoms || [];
    if (!atoms.length) return;
    const xs = atoms.map((a) => a.x), ys = atoms.map((a) => a.y);
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
    const cy = (Math.min(...ys) + Math.max(...ys)) / 2;
    atoms.forEach((a) => {{ a.x = +(270 + (a.x - cx)).toFixed(2); a.y = +(140 + (a.y - cy)).toFixed(2); }});
  }}

  function render() {{
    const g = state.graph;
    const atoms = g.atoms || [], bonds = g.bonds || [];
    const parts = [];
    const preset = STYLES[state.style] || STYLES.acs1996;
    const sw = preset.lineWidth ? Math.max(1.5, preset.lineWidth * 2.8) : 1.8;

    // Optional Newman circles/spokes
    (g.circles || []).forEach((c) => {{
      parts.push(`<circle cx="${{c.cx}}" cy="${{c.cy}}" r="${{c.r}}" fill="none" stroke="#0f172a" stroke-width="${{sw}}"/>`);
    }});
    (g.spokes || []).forEach((s) => {{
      parts.push(`<line x1="${{s[0]}}" y1="${{s[1]}}" x2="${{s[2]}}" y2="${{s[3]}}" stroke="#0f172a" stroke-width="${{sw}}" stroke-linecap="round"/>`);
    }});

    // Bonds
    bonds.forEach((b, bi) => {{
      const a1 = atoms[b.a], a2 = atoms[b.b];
      if (!a1 || !a2) return;
      const dx = a2.x - a1.x, dy = a2.y - a1.y, len = Math.hypot(dx, dy) || 1;
      const nx = -dy / len, ny = dx / len;
      if (b.o === 4) {{
        parts.push(`<polygon data-bond="${{bi}}" points="${{a1.x}},${{a1.y}} ${{(a2.x + nx * 4).toFixed(1)}},${{(a2.y + ny * 4).toFixed(1)}} ${{(a2.x - nx * 4).toFixed(1)}},${{(a2.y - ny * 4).toFixed(1)}}" fill="#0f172a"/>`);
      }} else if (b.o === 5) {{
        for (let t = 0.2; t <= 0.95; t += 0.16) {{
          const px = a1.x + dx * t, py = a1.y + dy * t, hw = 4 * t;
          parts.push(`<line x1="${{(px + nx * hw).toFixed(1)}}" y1="${{(py + ny * hw).toFixed(1)}}" x2="${{(px - nx * hw).toFixed(1)}}" y2="${{(py - ny * hw).toFixed(1)}}" stroke="#0f172a" stroke-width="1.5"/>`);
        }}
      }} else {{
        const offsets = b.o === 2 ? [-2.2, 2.2] : (b.o === 3 ? [-3.1, 0, 3.1] : [0]);
        offsets.forEach((off) => {{
          parts.push(`<line data-bond="${{bi}}" x1="${{(a1.x + nx * off).toFixed(1)}}" y1="${{(a1.y + ny * off).toFixed(1)}}" x2="${{(a2.x + nx * off).toFixed(1)}}" y2="${{(a2.y + ny * off).toFixed(1)}}" stroke="#0f172a" stroke-width="${{sw}}" stroke-linecap="round"/>`);
        }});
      }}
      parts.push(`<line data-bond="${{bi}}" x1="${{a1.x}}" y1="${{a1.y}}" x2="${{a2.x}}" y2="${{a2.y}}" stroke="transparent" stroke-width="12" style="cursor:pointer"/>`);
    }});

    // Arrows & Labels (reaction schemes)
    (g.arrows || []).forEach((ar) => {{
      parts.push(`<line x1="${{ar.x1}}" y1="${{ar.y1}}" x2="${{ar.x2}}" y2="${{ar.y2}}" stroke="#0f172a" stroke-width="1.8"/>`);
      parts.push(`<polygon points="${{ar.x2}},${{ar.y2}} ${{ar.x2 - 9}},${{ar.y2 - 4}} ${{ar.x2 - 7}},${{ar.y2}} ${{ar.x2 - 9}},${{ar.y2 + 4}}" fill="#0f172a"/>`);
      if (ar.above) parts.push(`<text x="${{(ar.x1 + ar.x2) / 2}}" y="${{ar.y1 - 9}}" text-anchor="middle" font-family="Arial,sans-serif" font-size="11" fill="#0f172a">${{esc(ar.above)}}</text>`);
      if (ar.below) parts.push(`<text x="${{(ar.x1 + ar.x2) / 2}}" y="${{ar.y1 + 16}}" text-anchor="middle" font-family="Arial,sans-serif" font-size="11" fill="#334155">${{esc(ar.below)}}</text>`);
    }});
    (g.texts || []).forEach((tx) => {{
      parts.push(`<text x="${{tx.x}}" y="${{tx.y}}" text-anchor="middle" font-family="Arial,sans-serif" font-size="11.5" font-weight="600" fill="#0f172a">${{esc(tx.text)}}</text>`);
    }});

    // Heteroatom labels & hit circles
    atoms.forEach((a, ai) => {{
      if (a.s !== "C") {{
        const color = a.s === "O" ? "#b91c1c" : (a.s === "N" ? "#1d4ed8" : (a.s === "S" ? "#a16207" : (a.s === "F" || a.s === "Cl" ? "#15803d" : "#0f172a")));
        parts.push(`<circle cx="${{a.x}}" cy="${{a.y}}" r="9" fill="#ffffff"/>`);
        parts.push(`<text x="${{a.x}}" y="${{a.y + 4}}" text-anchor="middle" font-family="${{preset.font || 'Arial'}},sans-serif" font-size="12.5" font-weight="700" fill="${{color}}">${{esc(a.s)}}</text>`);
      }}
      parts.push(`<circle data-atom="${{ai}}" cx="${{a.x}}" cy="${{a.y}}" r="11" fill="transparent" style="cursor:pointer"/>`);
    }});

    svg.innerHTML = parts.join("");

    const m = computeMetrics(g);
    document.getElementById("stat-name").textContent = g.name || "Custom";
    document.getElementById("stat-style").textContent = state.style;
    document.getElementById("stat-formula").textContent = m.formula;
    document.getElementById("stat-mw").textContent = m.mw + (m.mw === "-" ? "" : " g/mol");
    document.getElementById("stat-counts").textContent = `${{atoms.length}} / ${{bonds.length}}`;
    document.getElementById("cdxml-preview").value = generateCdxml(g);
  }}

  function svgPoint(evt) {{
    const rect = svg.getBoundingClientRect();
    return {{
      x: ((evt.clientX - rect.left) / rect.width) * 560,
      y: ((evt.clientY - rect.top) / rect.height) * 280
    }};
  }}

  function growFromAtom(ai, order) {{
    const base = state.graph.atoms[ai];
    const step = 28;
    const angles = [];
    state.graph.bonds.forEach((b) => {{
      const other = b.a === ai ? b.b : (b.b === ai ? b.a : -1);
      if (other >= 0) {{
        const p = state.graph.atoms[other];
        angles.push(Math.atan2(p.y - base.y, p.x - base.x));
      }}
    }});
    let bestAngle = -Math.PI / 6;
    if (angles.length === 1) bestAngle = angles[0] + Math.PI / 3;
    else if (angles.length >= 2) bestAngle = (angles[0] + angles[1]) / 2 + Math.PI;
    const ni = state.graph.atoms.length;
    state.graph.atoms.push({{ s: state.elem, x: +(base.x + Math.cos(bestAngle) * step).toFixed(2), y: +(base.y + Math.sin(bestAngle) * step).toFixed(2) }});
    state.graph.bonds.push({{ a: ai, b: ni, o: order }});
  }}

  function addRing(cx, cy, sides) {{
    const r = 27;
    const start = state.graph.atoms.length;
    for (let k = 0; k < sides; k++) {{
      const ang = (Math.PI * 2 * k) / sides - Math.PI / 2;
      state.graph.atoms.push({{ s: "C", x: +(cx + Math.cos(ang) * r).toFixed(2), y: +(cy + Math.sin(ang) * r).toFixed(2) }});
      state.graph.bonds.push({{ a: start + k, b: start + ((k + 1) % sides), o: (sides === 6 && k % 2 === 0) ? 2 : 1 }});
    }}
  }}

  svg.addEventListener("click", (e) => {{
    const target = e.target;
    const atomAttr = target.getAttribute && target.getAttribute("data-atom");
    const bondAttr = target.getAttribute && target.getAttribute("data-bond");
    pushUndo();
    if (atomAttr !== null) {{
      const ai = Number(atomAttr);
      if (state.tool === "erase") {{
        state.graph.bonds = state.graph.bonds.filter((b) => b.a !== ai && b.b !== ai)
          .map((b) => ({{ ...b, a: b.a > ai ? b.a - 1 : b.a, b: b.b > ai ? b.b - 1 : b.b }}));
        state.graph.atoms.splice(ai, 1);
      }} else if (state.elem !== state.graph.atoms[ai].s && state.tool === "bond-1") {{
        state.graph.atoms[ai].s = state.elem;
      }} else {{
        const ord = state.tool === "bond-2" ? 2 : (state.tool === "bond-3" ? 3 : (state.tool === "wedge" ? 4 : 1));
        growFromAtom(ai, ord);
      }}
      render();
      return;
    }}
    if (bondAttr !== null) {{
      const bi = Number(bondAttr);
      if (state.tool === "erase") {{
        state.graph.bonds.splice(bi, 1);
      }} else {{
        const b = state.graph.bonds[bi];
        b.o = b.o === 1 ? 2 : (b.o === 2 ? 3 : 1);
      }}
      render();
      return;
    }}
    const pt = svgPoint(e);
    if (state.tool === "ring-6") addRing(pt.x, pt.y, 6);
    else if (state.tool === "ring-5") addRing(pt.x, pt.y, 5);
    else if (state.tool !== "erase") {{
      const ni = state.graph.atoms.length;
      state.graph.atoms.push({{ s: state.elem, x: +pt.x.toFixed(1), y: +pt.y.toFixed(1) }});
      growFromAtom(ni, state.tool === "bond-2" ? 2 : 1);
    }}
    render();
  }});

  document.querySelectorAll("[data-tool]").forEach((btn) => {{
    btn.addEventListener("click", () => {{
      document.querySelectorAll("[data-tool]").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.tool = btn.getAttribute("data-tool");
    }});
  }});
  document.querySelectorAll("[data-elem]").forEach((btn) => {{
    btn.addEventListener("click", () => {{
      document.querySelectorAll("[data-elem]").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.elem = btn.getAttribute("data-elem");
    }});
  }});
  document.getElementById("btn-undo").addEventListener("click", () => {{
    if (!state.history.length) return;
    state.graph = JSON.parse(state.history.pop());
    render();
  }});
  document.getElementById("btn-clean").addEventListener("click", () => {{ pushUndo(); cleanLayout(); render(); }});
  styleSelect.addEventListener("change", () => {{ state.style = styleSelect.value; render(); }});
  document.getElementById("btn-dl-cdxml").addEventListener("click", () => {{
    const blob = new Blob([generateCdxml(state.graph)], {{ type: "application/xml;charset=utf-8" }});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = ((state.graph.name || "drawing").replace(/[^a-z0-9_-]+/gi, "_")) + ".cdxml";
    a.click();
  }});
  document.getElementById("btn-dl-svg").addEventListener("click", () => {{
    const blob = new Blob([svg.outerHTML], {{ type: "image/svg+xml;charset=utf-8" }});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = ((state.graph.name || "drawing").replace(/[^a-z0-9_-]+/gi, "_")) + ".svg";
    a.click();
  }});

  let rpcId = 1;
  function postHost(msg) {{
    try {{ window.parent.postMessage(msg, "*"); }} catch (_e) {{}}
  }}
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
      if (msg.result.hostContext && msg.result.hostContext.theme) {{
        document.body.dataset.theme = msg.result.hostContext.theme;
      }}
      return;
    }}
    if (msg.method === "ui/notifications/host-context-changed" && msg.params && msg.params.theme) {{
      document.body.dataset.theme = msg.params.theme;
    }}
    if (msg.method === "ui/notifications/tool-result") {{
      const p = extractResultPayload(msg.params);
      if (p && p.graph) {{
        state.graph = p.graph;
        if (p.style && p.style in STYLES) {{ state.style = p.style; styleSelect.value = p.style; }}
        render();
        buildGallery();
      }}
    }}
  }});

  document.getElementById("btn-view-3d").addEventListener("click", () => {{
    const target = state.graph.smiles || state.graph.name || "aspirin";
    postHost({{ jsonrpc: "2.0", id: ++rpcId, method: "tools/call", params: {{ name: "view_molecule_3d", arguments: {{ query: target }} }} }});
    postHost({{ jsonrpc: "2.0", id: ++rpcId, method: "ui/message", params: {{ role: "user", content: [{{ type: "text", text: "Open 3D Mol* view for: " + target }}] }} }});
  }});
  document.getElementById("btn-send-agent").addEventListener("click", () => {{
    const cdxml = generateCdxml(state.graph);
    postHost({{
      jsonrpc: "2.0",
      id: ++rpcId,
      method: "ui/message",
      params: {{
        role: "user",
        content: [{{
          type: "text",
          text: "Save and render this " + state.style + " CDXML from ChemDraw Studio:\\n\\n```xml\\n" + cdxml + "\\n```"
        }}]
      }}
    }});
  }});

  if (window.parent && window.parent !== window) {{
    postHost({{
      jsonrpc: "2.0",
      id: 1,
      method: "ui/initialize",
      params: {{ appInfo: {{ name: "cdxml-drawing-studio", version: "1.0.0" }}, appCapabilities: {{}}, protocolVersion: "2026-01-26" }}
    }});
    postHost({{ jsonrpc: "2.0", method: "ui/notifications/size-changed", params: {{ width: 960, height: 640 }} }});
  }}

  buildGallery();
  render();
}})();
</script>
</body>
</html>
"""


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
    launch_browser: bool = False,
) -> dict[str, Any]:
    """Open the interactive 2D ChemDraw Studio with reaction & scaffold templates.

    Supports 17 curated templates (molecules, 3D chair/Newman conformers, Suzuki,
    amide coupling, Buchwald-Hartwig, catalytic cycle, SAR scaffold), arbitrary
    SMILES, or loading an existing ``.cdxml`` file for live browser/MCP-App editing.
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
        built = _smiles_to_studio_graph(smiles, offset_x=200.0, offset_y=135.0, bond_scale=28.0)
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
            built = _smiles_to_studio_graph(resolved_smi, offset_x=200.0, offset_y=135.0, bond_scale=28.0)
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
    studio_url = html_file.as_uri()
    opened_browser = False
    if launch_browser:
        try:
            opened_browser = bool(webbrowser.open(studio_url))
        except Exception as exc:
            warnings.append(f"Could not launch browser window: {exc}")

    artifacts = artifact_safety.artifact_records([html_file])
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


UI_APP_TOOLS = {
    "view_molecule_3d": view_molecule_3d,
    "open_drawing_studio": open_drawing_studio,
}
