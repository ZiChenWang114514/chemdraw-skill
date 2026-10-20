#!/usr/bin/env python3
"""
structure_from_image.py — Extract chemical structures from images using DECIMER.

Takes a PNG/JPG image or a PDF page and returns SMILES + 2D atom coordinates
for every detected chemical structure.

Pipeline
--------
1. Input  : image file (PNG/JPG) or PDF (one page extracted per run)
2. Segment: detect and crop individual structure regions using OpenCV
            (white-background connected-component / contour approach)
3. DECIMER: convert each cropped image to SMILES
            (DECIMER Image Transformer v2, ~285 MB model, downloaded on first run)
4. RDKit  : SMILES → 2D coordinates (Compute2DCoords)
5. Output : JSON with SMILES + normalised atom/bond data per structure,
            ready for cdxml_builder.py; optionally write CDXML directly.

Usage
-----
Single image, JSON output:
    python structure_from_image.py --input image.png --output structures.json

PDF page (0-indexed):
    python structure_from_image.py --input paper.pdf --page 0 --output out.json

Pipe straight to CDXML builder (multi-molecule page):
    python structure_from_image.py --input image.png | python cdxml_builder.py --mode multi

Hand-drawn structures (uses DECIMER hand-drawn model):
    python structure_from_image.py --input sketch.png --hand-drawn

Skip segmentation (whole image is one structure):
    python structure_from_image.py --input single_structure.png --no-segment

Output JSON format
------------------
[
  {
    "index": 0,
    "smiles": "c1ccccc1",
    "bbox": [x0, y0, x1, y1],         # pixel coords in the input image
    "atoms": [
      {"index": 1, "symbol": "C", "x": 200.0, "y": 300.0},
      ...
    ],
    "bonds": [
      {"index": 1, "order": 1, "atom1": 1, "atom2": 2},
      ...
    ]
  },
  ...
]

Notes
-----
- DECIMER models download to ~/.data/DECIMER-V2/ on first run (~570 MB total).
- TensorFlow 2.20 prints hardware-capability warnings to stderr; these are harmless.
- Segmentation uses an OpenCV contour approach tuned for white-background publication
  figures. For densely packed figures (multiple overlapping structures) it works best
  on clean, high-resolution images (≥150 DPI equivalent).
- Coordinates are normalised to ACS 1996 style (bond length 14.40 pt) by
  coord_normalizer.normalize_coords().
"""

import argparse
import json
import math
import os
import sys
import tempfile
from copy import deepcopy
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Optional heavy imports (warn gracefully if missing)
# ---------------------------------------------------------------------------

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import pymupdf  # PyMuPDF — PDF rendering
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem
    HAS_RDKIT = True
except ImportError:
    HAS_RDKIT = False

# ---------------------------------------------------------------------------
# DECIMER lazy loader — loads ONE model on demand, not both at import time.
#
# Upstream DECIMER eagerly loads both the standard AND hand-drawn models
# (~332 MB each) at import time via module-level get_models().  This takes
# ~50 s on CPU.  We bypass that by loading only the model we need, only
# when predict is first called, cutting cold-start roughly in half.
# ---------------------------------------------------------------------------
import threading as _threading

_decimer_predict = None
_decimer_mode = None  # tracks which model is loaded: "standard" or "hand_drawn"
_decimer_lock = _threading.Lock()


def _load_decimer(hand_drawn: bool = False):
    """Lazy-load DECIMER, loading only the requested model (not both).

    On first call, loads TensorFlow + one DECIMER SavedModel (~25 s instead
    of ~50 s).  Subsequent calls with the same ``hand_drawn`` flag return
    instantly.  If the flag changes, the other model is loaded on demand.

    Thread-safe: a lock prevents duplicate loads when the MCP server's
    background preload thread and a tool call race.
    """
    global _decimer_predict, _decimer_mode
    requested = "hand_drawn" if hand_drawn else "standard"

    if _decimer_predict is not None and _decimer_mode == requested:
        return _decimer_predict

    with _decimer_lock:
        # Double-check after acquiring the lock (another thread may have
        # finished loading while we waited).
        if _decimer_predict is not None and _decimer_mode == requested:
            return _decimer_predict

        try:
            import tensorflow as tf
            import pystow
        except ImportError as exc:
            raise ImportError(
                "DECIMER is not installed. Run:\n"
                "  pip install cdxml-toolkit-community[decimer]\n"
                f"Original error: {exc}"
            ) from exc

        # Bypass DECIMER's __init__.py which eagerly loads BOTH models (~50 s).
        # Instead, load only the two helper submodules we need (utils,
        # pre_process) via importlib, then tf.saved_model.load for ONE model.
        import importlib.util, sys, types, pickle

        spec = importlib.util.find_spec("DECIMER")
        if spec is None or spec.submodule_search_locations is None:
            raise ImportError("DECIMER package not found")
        pkg_dir = spec.submodule_search_locations[0]

        # Register a stub DECIMER package so submodule imports resolve
        if "DECIMER" not in sys.modules:
            stub = types.ModuleType("DECIMER")
            stub.__path__ = [pkg_dir]
            stub.__package__ = "DECIMER"
            sys.modules["DECIMER"] = stub

        def _load_submodule(name):
            fqn = f"DECIMER.{name}"
            if fqn in sys.modules:
                return sys.modules[fqn]
            sub_spec = importlib.util.spec_from_file_location(
                fqn, os.path.join(pkg_dir, f"{name}.py"),
            )
            mod = importlib.util.module_from_spec(sub_spec)
            sys.modules[fqn] = mod
            sub_spec.loader.exec_module(mod)
            return mod

        utils = _load_submodule("utils")
        pre_process = _load_submodule("pre_process")

        # Locate models on disk (downloads ~570 MB on first run)
        default_path = pystow.join("DECIMER-V2")
        model_urls = {
            "DECIMER": "https://zenodo.org/record/8300489/files/models.zip",
            "DECIMER_HandDrawn": "https://zenodo.org/records/10781330/files/DECIMER_HandDrawn_model.zip",
        }
        model_paths = utils.ensure_models(
            default_path=default_path, model_urls=model_urls,
        )

        # Load tokenizer (fast, ~0 s)
        tokenizer_path = os.path.join(
            model_paths["DECIMER"], "assets", "tokenizer_SMILES.pkl"
        )
        try:
            with open(tokenizer_path, "rb") as f:
                tokenizer = pickle.load(f)
        except ModuleNotFoundError:
            # Keras 2→3 compat: redirect keras.preprocessing.text
            class _K2Unpickler(pickle.Unpickler):
                def find_class(self, module, name):
                    if module.startswith("keras."):
                        module = module.replace("keras.", "tensorflow.keras.", 1)
                    return super().find_class(module, name)
            with open(tokenizer_path, "rb") as f:
                tokenizer = _K2Unpickler(f).load()

        # Load only the requested model (~25 s instead of ~50 s for both)
        model_key = "DECIMER_HandDrawn" if hand_drawn else "DECIMER"
        model = tf.saved_model.load(model_paths[model_key])

        def _predict(image_input, confidence=False, hand_drawn=False):
            """Predict SMILES from an image (numpy array or file path)."""
            chemical_structure = pre_process.decode_image(image_input)
            predicted_tokens, confidence_values = model(
                tf.constant(chemical_structure)
            )
            outputs = [tokenizer.index_word[i] for i in predicted_tokens[0].numpy()]
            smiles = (
                "".join(str(t) for t in outputs)
                .replace("<start>", "")
                .replace("<end>", "")
            )
            smiles = utils.decoder(smiles)

            if confidence:
                conf_pairs = [
                    (
                        utils.decoder(
                            tokenizer.index_word[predicted_tokens[0].numpy()[i]]
                        ),
                        confidence_values[i].numpy(),
                    )
                    for i in range(len(confidence_values))
                ]
                # strip <start>/<end> tokens
                conf_pairs = conf_pairs[1:-1]
                return smiles, conf_pairs

            return smiles

        _decimer_predict = _predict
        _decimer_mode = requested
        return _decimer_predict


# ---------------------------------------------------------------------------
# Image I/O
# ---------------------------------------------------------------------------

def load_image(path: str, page: int = 0) -> "np.ndarray":
    """
    Load an image from a PNG/JPG file or from a specific page of a PDF.

    Returns an RGB numpy array (H x W x 3).
    """
    if not HAS_CV2:
        raise RuntimeError("opencv-python is required. Run: pip install opencv-python")

    ext = os.path.splitext(path)[1].lower()

    if ext == ".pdf":
        if not HAS_PYMUPDF:
            raise RuntimeError("PyMuPDF is required for PDF input. Run: pip install pymupdf")
        doc = pymupdf.open(path)
        if page >= len(doc):
            raise ValueError(f"PDF has {len(doc)} pages; requested page {page} (0-indexed)")
        pg = doc[page]
        # Render at 150 DPI (matrix scale = 150/72)
        matrix = pymupdf.Matrix(150 / 72, 150 / 72)
        pix = pg.get_pixmap(matrix=matrix, alpha=False)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        doc.close()
        # PyMuPDF returns RGB; convert to BGR for OpenCV
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")
    return img


# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------

_MIN_STRUCTURE_AREA_PX = 1500   # ignore regions smaller than this (noise)
_MIN_SIDE_PX = 40               # ignore regions thinner than this
_PADDING_PX = 12                # padding around detected bounding boxes
_MAX_AREA_FRACTION = 0.90       # ignore boxes covering >90% of image (whole-page)
_MIN_ASPECT_RATIO = 0.15        # reject very wide/tall thin strips (text lines, arrows)
_MAX_SMILES_LEN = 500           # truncated/garbage DECIMER outputs above this length


def _to_gray_binary(bgr: "np.ndarray") -> "np.ndarray":
    """Convert BGR image to a binary mask where dark (non-white) pixels are 1."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    # Otsu threshold; for white-background publication figures this finds ink
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return binary


def _merge_nearby_boxes(
    boxes: List[Tuple[int, int, int, int]],
    gap: int = 30,
) -> List[Tuple[int, int, int, int]]:
    """
    Iteratively merge bounding boxes that are close together (within `gap` pixels).
    This groups fragmented bond lines and labels that belong to one structure.
    """
    if not boxes:
        return []

    changed = True
    while changed:
        changed = False
        merged: List[Tuple[int, int, int, int]] = []
        used = [False] * len(boxes)
        for i, (x0, y0, x1, y1) in enumerate(boxes):
            if used[i]:
                continue
            # Expand by gap for proximity test
            ex0, ey0, ex1, ey1 = x0 - gap, y0 - gap, x1 + gap, y1 + gap
            for j, (ax0, ay0, ax1, ay1) in enumerate(boxes):
                if used[j] or j == i:
                    continue
                # Overlap test on expanded box
                if ax0 <= ex1 and ax1 >= ex0 and ay0 <= ey1 and ay1 >= ey0:
                    x0 = min(x0, ax0)
                    y0 = min(y0, ay0)
                    x1 = max(x1, ax1)
                    y1 = max(y1, ay1)
                    ex0, ey0, ex1, ey1 = x0 - gap, y0 - gap, x1 + gap, y1 + gap
                    used[j] = True
                    changed = True
            merged.append((x0, y0, x1, y1))
            used[i] = True
        boxes = merged
    return boxes


def _adaptive_gap(boxes: List[Tuple[int, int, int, int]]) -> int:
    """
    Compute an adaptive merge gap based on inter-box distances.

    Finds the minimum edge-to-edge distance between each pair of boxes,
    then uses the median of these nearest-neighbour distances.  The gap is
    set to 50% of that median, clamped to [8, 40].  This prevents merging
    truly distinct structures in dense figures while still grouping
    fragments that belong to one molecule.

    Falls back to 25 if there are fewer than 3 boxes.
    """
    n = len(boxes)
    if n < 3:
        return 25  # reasonable default for sparse images

    # Compute minimum edge-to-edge distance for each box to its nearest neighbour
    def _edge_dist(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
        ax0, ay0, ax1, ay1 = a
        bx0, by0, bx1, by1 = b
        dx = max(0, max(ax0 - bx1, bx0 - ax1))
        dy = max(0, max(ay0 - by1, by0 - ay1))
        return (dx**2 + dy**2) ** 0.5

    nn_dists = []
    for i in range(n):
        min_d = float("inf")
        for j in range(n):
            if i == j:
                continue
            d = _edge_dist(boxes[i], boxes[j])
            if d < min_d:
                min_d = d
        nn_dists.append(min_d)

    nn_dists.sort()
    median_nn = nn_dists[len(nn_dists) // 2]

    # Gap = 50% of median nearest-neighbour distance
    gap = int(median_nn * 0.50)
    return max(8, min(40, gap))


def segment_structures(
    bgr: "np.ndarray",
    merge_gap: Optional[int] = None,
) -> List[Tuple["np.ndarray", Tuple[int, int, int, int]]]:
    """
    Detect chemical structure regions in a BGR image.

    Returns a list of (cropped_bgr, (x0, y0, x1, y1)) tuples, one per detected
    structure, sorted left→right, top→bottom.

    Parameters
    ----------
    bgr       : BGR image array (from OpenCV)
    merge_gap : pixel gap for merging nearby boxes.  None = adaptive
                (computed from median box size).  Set to 0 to disable merging.

    Strategy: threshold → morphological close to fill small gaps → find external
    contours → filter by area/size → merge nearby boxes → crop with padding.
    """
    if not HAS_CV2:
        raise RuntimeError("opencv-python is required.")

    h, w = bgr.shape[:2]
    total_px = h * w

    binary = _to_gray_binary(bgr)

    # Morphological close: connect nearby ink pixels (bond lines, letters)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=3)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    raw_boxes: List[Tuple[int, int, int, int]] = []
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        area = cw * ch
        if area < _MIN_STRUCTURE_AREA_PX:
            continue
        if cw < _MIN_SIDE_PX or ch < _MIN_SIDE_PX:
            continue
        if area > _MAX_AREA_FRACTION * total_px:
            continue
        # Reject very thin horizontal/vertical strips (text lines, arrows)
        aspect = min(cw, ch) / max(cw, ch)
        if aspect < _MIN_ASPECT_RATIO:
            continue
        raw_boxes.append((x, y, x + cw, y + ch))

    if not raw_boxes:
        # Fall back to the whole image as one region
        return [(bgr.copy(), (0, 0, w, h))]

    gap = merge_gap if merge_gap is not None else _adaptive_gap(raw_boxes)
    merged = _merge_nearby_boxes(raw_boxes, gap=gap)

    # Sort top→bottom, left→right (row then column)
    merged.sort(key=lambda b: (b[1] // 100, b[0]))

    results = []
    for x0, y0, x1, y1 in merged:
        # Add padding, clamp to image bounds
        px0 = max(0, x0 - _PADDING_PX)
        py0 = max(0, y0 - _PADDING_PX)
        px1 = min(w, x1 + _PADDING_PX)
        py1 = min(h, y1 + _PADDING_PX)
        crop = bgr[py0:py1, px0:px1]
        results.append((crop, (px0, py0, px1, py1)))

    return results


# ---------------------------------------------------------------------------
# SMILES → atom/bond data via RDKit
# ---------------------------------------------------------------------------

def _ring_double_bond_side(
    mol: "Chem.Mol",
    bond: "Chem.Bond",
) -> Optional[str]:
    """
    For a double bond that is part of a ring, determine whether the second
    bond line should be drawn to the Right or Left (relative to bond direction
    begin→end).  Returns None for non-ring double bonds.

    Strategy: find the ring neighbour of the begin atom that is NOT the end
    atom; the cross-product of (end-begin) × (neighbour-begin) gives the
    side.  Positive z → neighbour is to the left → double bond offset Right,
    and vice-versa.  This matches ChemDraw's DoublePosition convention.
    """
    if not bond.IsInRing():
        return None
    conf = mol.GetConformer()
    bi = bond.GetBeginAtomIdx()
    ei = bond.GetEndAtomIdx()
    bx, by = conf.GetAtomPosition(bi).x, conf.GetAtomPosition(bi).y
    ex, ey = conf.GetAtomPosition(ei).x, conf.GetAtomPosition(ei).y
    dx, dy = ex - bx, ey - by  # bond vector

    # Find a ring neighbour of begin-atom (other than end-atom)
    ri = mol.GetRingInfo()
    # Find the smallest ring containing this bond.  For fused ring systems
    # (e.g. thienopyrimidine), using only the smallest ring's atoms ensures
    # the double-bond offset points toward the ring interior, not outward
    # (which would look exocyclic).
    containing_rings = [ring for ring in ri.AtomRings()
                        if bi in ring and ei in ring]
    if not containing_rings:
        return None
    smallest_ring = min(containing_rings, key=len)
    ring_atoms = set(smallest_ring)

    for nb in mol.GetAtomWithIdx(bi).GetNeighbors():
        ni = nb.GetIdx()
        if ni == ei:
            continue
        if ni not in ring_atoms:
            continue
        nx, ny = conf.GetAtomPosition(ni).x, conf.GetAtomPosition(ni).y
        # Cross product z-component: (bond vec) × (neighbour vec from begin)
        cross_z = dx * (ny - by) - dy * (nx - bx)
        # Positive cross → neighbour is to the left of bond direction
        # ChemDraw DoublePosition="Right" means the second line is on the
        # right side of the bond (i.e. away from the ring interior when
        # neighbour is to the left)
        return "Right" if cross_z > 0 else "Left"

    return None


def _rdkit_mol_to_atom_bond_dicts(
    mol: "Chem.Mol",
    offset_index: int = 0,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Convert an RDKit Mol (with 2D conformer, already Kekulized) to atom/bond
    dicts matching the format expected by coord_normalizer / cdxml_builder.

    Atom indices are 1-based and offset by `offset_index` to allow unique
    numbering across multiple molecules.

    The mol MUST have been Kekulized with clearAromaticFlags=True before
    calling this function, so that all bonds have explicit SINGLE/DOUBLE/TRIPLE
    types (no AROMATIC).  This is required for correct ChemDraw rendering —
    ChemDraw 16 does not recognise Order="1.5" as an aromatic bond.
    """
    from ..chemistry_semantics import require_supported
    require_supported(mol)
    # Chiral tags alone do not set bond directions. Wedge the FINAL coordinates.
    Chem.WedgeMolBonds(mol, mol.GetConformer())
    source_cx = Chem.MolToCXSmiles(mol, Chem.SmilesWriteParams(), Chem.CXSmilesFields.CX_ENHANCEDSTEREO)
    enhanced = {}
    group_names = {Chem.StereoGroupType.STEREO_AND: 'And',
                   Chem.StereoGroupType.STEREO_OR: 'Or',
                   Chem.StereoGroupType.STEREO_ABSOLUTE: 'Absolute'}
    for group_num, group in enumerate(mol.GetStereoGroups(), 1):
        for atom in group.GetAtoms():
            enhanced[atom.GetIdx()] = (group_names[group.GetGroupType()], group_num)
    conf = mol.GetConformer()
    atoms = []
    rdkit_to_local: Dict[int, int] = {}  # rdkit 0-based → output 1-based
    for i, atom in enumerate(mol.GetAtoms()):
        pos = conf.GetAtomPosition(i)
        local_idx = i + 1 + offset_index
        rdkit_to_local[i] = local_idx
        a: Dict = {
            "index": local_idx,
            "symbol": atom.GetSymbol(),
            "x": round(float(pos.x), 4),
            "y": round(float(pos.y), 4),
        }
        charge = atom.GetFormalCharge()
        if charge != 0:
            a["charge"] = charge
        # GetTotalNumHs works even after Kekulize
        nh = atom.GetTotalNumHs(includeNeighbors=False)
        if atom.GetSymbol() != "C":
            a["num_hydrogens"] = nh
        isotope = atom.GetIsotope()
        if isotope:
            a["isotope"] = isotope
        a['atomic_number'] = atom.GetAtomicNum()
        if i in enhanced:
            a['enhanced_stereo_type'], a['enhanced_stereo_group'] = enhanced[i]
        if i == 0:
            a['_source_cxsmiles'] = source_cx
        atoms.append(a)

    bonds = []
    for bi, bond in enumerate(mol.GetBonds()):
        order_map = {
            Chem.BondType.SINGLE: 1,
            Chem.BondType.DOUBLE: 2,
            Chem.BondType.TRIPLE: 3,
            # AROMATIC should not appear after Kekulize, but keep as fallback
            Chem.BondType.AROMATIC: 2,
        }
        order = order_map.get(bond.GetBondType(), 1)

        # Bond direction for wedge/dash stereo
        cfg = 0
        bd = bond.GetBondDir()
        if bd == Chem.BondDir.BEGINWEDGE:
            cfg = 1
        elif bd == Chem.BondDir.BEGINDASH:
            cfg = 6

        bond_dict: Dict = {
            "index": bi + 1 + offset_index,
            "order": order,
            "atom1": rdkit_to_local[bond.GetBeginAtomIdx()],
            "atom2": rdkit_to_local[bond.GetEndAtomIdx()],
            "cfg": cfg,
        }

        # For in-ring double bonds, add DoublePosition so ChemDraw draws the
        # second line on the correct (inside-ring) side.
        if order == 2:
            side = _ring_double_bond_side(mol, bond)
            if side:
                bond_dict["double_pos"] = side

        bonds.append(bond_dict)

    return atoms, bonds


def smiles_to_coords(smiles: str, offset_index: int = 0) -> Optional[Dict]:
    """
    Convert a SMILES string to 2D atom/bond data using RDKit.

    Returns a dict with "atoms" and "bonds" lists (raw RDKit Angstrom units),
    or None if the SMILES is invalid or coordinate generation fails.
    """
    if not HAS_RDKIT:
        raise RuntimeError("RDKit is required. Activate the LLMChem conda environment.")

    if not smiles or smiles.strip() in ("", "FAILED", "N/A"):
        return None

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    # Generate 2D coords directly on heavy atoms.  Previous versions did
    # AddHs → Compute2DCoords → RemoveHs, but that causes RDKit to lay out
    # alkyl chains in a straight line (all bonds collinear) instead of a
    # proper zigzag, because the algorithm spaces out explicit H positions
    # and the heavy-atom backbone becomes linear.
    result = AllChem.Compute2DCoords(mol)
    if result != 0:
        return None

    # Kekulize AFTER coord generation so bond orders are explicit SINGLE/DOUBLE.
    # clearAromaticFlags=True ensures GetBondType() returns SINGLE/DOUBLE, not
    # AROMATIC — required for correct ChemDraw rendering (no Order="1.5").
    try:
        Chem.Kekulize(mol, clearAromaticFlags=True)
    except Exception:
        # If Kekulization fails (unusual), proceed anyway; aromatic bonds will
        # be mapped to order=2 as a fallback in _rdkit_mol_to_atom_bond_dicts.
        pass

    atoms, bonds = _rdkit_mol_to_atom_bond_dicts(mol, offset_index=offset_index)
    return {"atoms": atoms, "bonds": bonds}


# ---------------------------------------------------------------------------
# Coordinate normalisation (inline, no import dependency on coord_normalizer)
# ---------------------------------------------------------------------------

from ..constants import (
    ACS_BOND_LENGTH as ACS_BOND_LENGTH_PT,
    CDXML_HEADER as _CDXML_HEADER,
    CDXML_FOOTER as _CDXML_FOOTER,
    ACS_LABEL_FONT, ACS_LABEL_SIZE, ACS_LABEL_FACE,
    ACS_CAPTION_SIZE, ACS_HASH_SPACING, ACS_MARGIN_WIDTH,
    ACS_LINE_WIDTH, ACS_BOLD_WIDTH, ACS_BOND_LENGTH_STR,
    ACS_BOND_SPACING, ACS_CHAIN_ANGLE_STR,
)


def _average_bond_length(atoms: List[Dict], bonds: List[Dict]) -> float:
    if not bonds:
        return 1.0
    xy = {a["index"]: (a["x"], a["y"]) for a in atoms}
    lengths = [
        math.hypot(
            xy.get(b["atom1"], (0, 0))[0] - xy.get(b["atom2"], (0, 0))[0],
            xy.get(b["atom1"], (0, 0))[1] - xy.get(b["atom2"], (0, 0))[1],
        )
        for b in bonds
        if math.hypot(
            xy.get(b["atom1"], (0, 0))[0] - xy.get(b["atom2"], (0, 0))[0],
            xy.get(b["atom1"], (0, 0))[1] - xy.get(b["atom2"], (0, 0))[1],
        ) > 1e-6
    ]
    return sum(lengths) / len(lengths) if lengths else 1.0


def normalize_for_cdxml(
    atoms: List[Dict],
    bonds: List[Dict],
    center_x: float = 200.0,
    center_y: float = 300.0,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Scale + flip-y + centre coordinates for CDXML output (ACS 1996, 14.40 pt bonds).
    RDKit coords are Angstroms, y-up. CDXML is points, y-down.
    """
    atoms = deepcopy(atoms)
    bonds = deepcopy(bonds)

    if not atoms:
        return atoms, bonds

    # Flip y
    for a in atoms:
        a["y"] = -a["y"]

    # Scale
    avg_bl = _average_bond_length(atoms, bonds)
    if avg_bl > 1e-6:
        scale = ACS_BOND_LENGTH_PT / avg_bl
        for a in atoms:
            a["x"] *= scale
            a["y"] *= scale

    # Centre
    xs = [a["x"] for a in atoms]
    ys = [a["y"] for a in atoms]
    cx = (min(xs) + max(xs)) / 2.0
    cy = (min(ys) + max(ys)) / 2.0
    for a in atoms:
        a["x"] = round(a["x"] - cx + center_x, 3)
        a["y"] = round(a["y"] - cy + center_y, 3)

    return atoms, bonds


# ---------------------------------------------------------------------------
# Mass data enrichment
# ---------------------------------------------------------------------------

def enrich_with_mass_data(results: List[Dict]) -> None:
    """Add formula, mw, exact_mass, and adducts to each extracted structure.

    Mutates *results* in place.  Requires RDKit; silently skips if unavailable.
    """
    if not HAS_RDKIT:
        return

    from rdkit.Chem import Descriptors, rdMolDescriptors

    for entry in results:
        smiles = entry.get("smiles", "").strip()
        if not smiles:
            continue
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            continue

        exact_mass_full = Descriptors.ExactMolWt(mol)
        mw = Descriptors.MolWt(mol)
        formula = rdMolDescriptors.CalcMolFormula(mol)

        # Salt splitting: neutral = largest fragment
        frags = Chem.GetMolFrags(mol, asMols=True)
        if len(frags) > 1:
            neutral_mol = max(frags, key=lambda m: m.GetNumHeavyAtoms())
            exact_mass = Descriptors.ExactMolWt(neutral_mol)
        else:
            exact_mass = exact_mass_full

        entry["formula"] = formula
        entry["mw"] = round(mw, 4)
        entry["exact_mass"] = round(exact_mass, 5)
        entry["exact_mass_full"] = round(exact_mass_full, 5)
        entry["adducts"] = {
            "[M+H]+": round(exact_mass + 1.00728, 5),
            "[M-H]-": round(exact_mass - 1.00728, 5),
            "[M+Na]+": round(exact_mass + 22.98922, 5),
            "[M+formate]-": round(exact_mass + 44.99820, 5),
        }


# ---------------------------------------------------------------------------
# Main extraction pipeline
# ---------------------------------------------------------------------------

def _extract_structures_raw(
    image_path: str,
    page: int = 0,
    segment: bool = True,
    hand_drawn: bool = False,
    verbose: bool = False,
    merge_gap: Optional[int] = None,
) -> List[Dict]:
    """
    Full pipeline: image → segmented crops → SMILES → 2D coords.

    This is the internal low-level function.  Call extract_structures_from_image()
    for the public API that returns structured JSON.

    Parameters
    ----------
    image_path : path to PNG/JPG/PDF
    page       : PDF page number (0-indexed); ignored for image files
    segment    : if False, treat whole image as one structure
    hand_drawn : use DECIMER hand-drawn model
    verbose    : print progress to stderr
    merge_gap  : pixel gap for merging nearby boxes during segmentation.
                 None = adaptive (based on median box size).  0 = no merging.

    Returns
    -------
    List of dicts, one per detected structure:
        {
          "index": int,
          "smiles": str,
          "confidence": float or None,   # mean per-token DECIMER confidence, 0-1
          "bbox": [x0, y0, x1, y1],
          "atoms": [...],
          "bonds": [...]
        }
    """
    def log(msg: str):
        if verbose:
            print(f"[structure_from_image] {msg}", file=sys.stderr)

    # 1. Load image
    log(f"Loading {image_path}" + (f" page {page}" if image_path.lower().endswith(".pdf") else ""))
    bgr = load_image(image_path, page=page)
    h, w = bgr.shape[:2]
    log(f"Image size: {w}x{h} px")

    # 2. Segment
    if segment:
        log("Segmenting structures...")
        regions = segment_structures(bgr, merge_gap=merge_gap)
        log(f"Found {len(regions)} candidate region(s)")
    else:
        regions = [(bgr.copy(), (0, 0, w, h))]
        log("Skipping segmentation (--no-segment)")

    # 3. Load DECIMER (deferred)
    log("Loading DECIMER model (may take a moment on first call)...")
    predict_fn = _load_decimer(hand_drawn=hand_drawn)

    # 4. Process each region
    results: List[Dict] = []
    atom_offset = 0

    for i, (crop, bbox) in enumerate(regions):
        log(f"Processing region {i+1}/{len(regions)} — bbox {bbox}")

        # Try to call DECIMER with confidence=True to get per-token scores.
        # Falls back to confidence=False if the version doesn't support it.
        raw_confidence = None
        try:
            result = predict_fn(crop, confidence=True, hand_drawn=hand_drawn)
            if isinstance(result, tuple):
                smiles, raw_confidence = result[0], result[1]
            else:
                smiles = result
        except TypeError:
            # Older DECIMER versions don't accept numpy; fall back to temp file
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                tmp_path = tf.name
            try:
                cv2.imwrite(tmp_path, crop)
                try:
                    result = predict_fn(tmp_path, confidence=True)
                    if isinstance(result, tuple):
                        smiles, raw_confidence = result[0], result[1]
                    else:
                        smiles = result
                except TypeError:
                    smiles = predict_fn(tmp_path)
            finally:
                os.unlink(tmp_path)
        except Exception as exc:
            log(f"  DECIMER failed: {exc}")
            smiles = ""

        smiles = smiles.strip() if smiles else ""

        # Sanity check: abnormally long SMILES usually means DECIMER is reading
        # text/arrows/noise rather than a chemical structure.
        if len(smiles) > _MAX_SMILES_LEN:
            log(f"  SMILES too long ({len(smiles)} chars) — discarding as noise")
            smiles = ""
            raw_confidence = None

        # Compute a single confidence scalar from per-token scores
        confidence = _compute_confidence_score(raw_confidence)

        log(f"  SMILES: {smiles or '(none)'}"
            + (f"  confidence: {confidence:.3f}" if confidence is not None else ""))

        # 5. SMILES → 2D coordinates
        mol_data = None
        if smiles:
            mol_data = smiles_to_coords(smiles, offset_index=atom_offset)
            if mol_data is None:
                log(f"  RDKit could not parse SMILES: {smiles}")
            else:
                # Normalise to ACS 1996 CDXML coords.
                # Use a fixed origin here; final placement is done in
                # results_to_cdxml() based on actual bounding boxes.
                atoms_norm, bonds_norm = normalize_for_cdxml(
                    mol_data["atoms"],
                    mol_data["bonds"],
                    center_x=200.0,
                    center_y=300.0,
                )
                mol_data["atoms"] = atoms_norm
                mol_data["bonds"] = bonds_norm
                atom_offset += len(mol_data["atoms"])

        entry: Dict = {
            "index": i,
            "smiles": smiles,
            "confidence": confidence,
            "bbox": list(bbox),
        }
        if mol_data:
            entry["atoms"] = mol_data["atoms"]
            entry["bonds"] = mol_data["bonds"]
        else:
            entry["atoms"] = []
            entry["bonds"] = []

        results.append(entry)

    # Enrich with mass data (formula, MW, exact_mass, adducts)
    enrich_with_mass_data(results)

    log(f"Done. {len(results)} structure(s) extracted.")
    return results


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

def _compute_confidence_score(
    raw_confidence: Optional[list],
) -> Optional[float]:
    """
    Reduce DECIMER's per-token confidence list to a single scalar in [0, 1].

    DECIMER returns a list of (token, score) tuples when called with
    confidence=True.  This function computes the geometric mean of the
    scores, which is more sensitive to low-confidence tokens than the
    arithmetic mean and better reflects overall prediction reliability.

    Returns None if no confidence data is available.
    """
    if not raw_confidence:
        return None

    scores = []
    for item in raw_confidence:
        if isinstance(item, (tuple, list)) and len(item) >= 2:
            try:
                scores.append(float(item[1]))
            except (TypeError, ValueError):
                pass
        else:
            try:
                scores.append(float(item))
            except (TypeError, ValueError):
                pass

    if not scores:
        return None

    # Geometric mean (log-space to avoid underflow)
    import math as _math
    log_sum = sum(_math.log(max(s, 1e-9)) for s in scores)
    return round(_math.exp(log_sum / len(scores)), 4)


# ---------------------------------------------------------------------------
# Nearby text label detection
# ---------------------------------------------------------------------------

def _detect_nearby_labels(
    bgr: "np.ndarray",
    structure_bboxes: List[Tuple[int, int, int, int]],
    search_margin: int = 80,
) -> List[Optional[str]]:
    """
    Detect text labels near each structure bounding box in the image.

    Uses a two-phase strategy:
    1. Find candidate text regions via OpenCV contours (small, elongated blobs
       that look like text lines rather than structure fragments).
    2. If pytesseract or easyocr is available, OCR those regions and associate
       the nearest text label to each structure.  If neither is installed,
       returns None for every structure.

    Parameters
    ----------
    bgr              : BGR image array
    structure_bboxes : list of (x0, y0, x1, y1) for each detected structure
    search_margin    : how many pixels outside the structure bbox to search
                       for associated text labels

    Returns
    -------
    List of str|None, one per structure.  Each entry is the detected label
    text (stripped) or None if no label was found or OCR is unavailable.
    """
    if not HAS_CV2 or not structure_bboxes:
        return [None] * len(structure_bboxes)

    import numpy as np

    h, w = bgr.shape[:2]

    # --- Phase 1: Find candidate text regions ---
    # Text regions tend to be: small area, high aspect ratio (wide and short),
    # located outside the structure bounding boxes.
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Use a smaller morphological kernel to preserve text character separations
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Build a mask of structure regions (to exclude them from label search)
    structure_set = set()
    for (sx0, sy0, sx1, sy1) in structure_bboxes:
        for px in range(max(0, sx0), min(w, sx1)):
            for py in range(max(0, sy0), min(h, sy1)):
                structure_set.add((px, py))

    text_blobs: List[Tuple[int, int, int, int]] = []
    for cnt in contours:
        cx, cy, cw, ch = cv2.boundingRect(cnt)
        area = cw * ch

        # Skip tiny noise and huge blobs
        if area < 50 or area > 0.05 * h * w:
            continue

        # Text lines are wider than they are tall (aspect > 1.5), or are
        # narrow vertical labels.  Very square blobs are likely structure parts.
        aspect = max(cw, ch) / max(min(cw, ch), 1)
        if aspect < 1.5:
            continue

        # Skip blobs that overlap significantly with any structure bbox
        blob_cx = cx + cw // 2
        blob_cy = cy + ch // 2
        in_structure = False
        for (sx0, sy0, sx1, sy1) in structure_bboxes:
            if sx0 <= blob_cx <= sx1 and sy0 <= blob_cy <= sy1:
                in_structure = True
                break
        if in_structure:
            continue

        text_blobs.append((cx, cy, cx + cw, cy + ch))

    if not text_blobs:
        return [None] * len(structure_bboxes)

    # --- Phase 2: Try OCR on the candidates ---
    # Check for OCR availability (pytesseract preferred, easyocr fallback)
    ocr_fn = _get_ocr_fn()
    if ocr_fn is None:
        # No OCR available; return None for all structures but record that
        # text blobs were detected (useful for debugging).
        return [None] * len(structure_bboxes)

    # Associate each text blob with the nearest structure (by edge distance)
    labels = [None] * len(structure_bboxes)

    for (bx0, by0, bx1, by1) in text_blobs:
        # Check if this blob falls within the search_margin of any structure
        best_dist = float("inf")
        best_idx = -1

        for si, (sx0, sy0, sx1, sy1) in enumerate(structure_bboxes):
            # Expand structure bbox by search_margin
            ex0, ey0 = sx0 - search_margin, sy0 - search_margin
            ex1, ey1 = sx1 + search_margin, sy1 + search_margin

            # Check if blob centre is within expanded bbox
            bcx, bcy = (bx0 + bx1) // 2, (by0 + by1) // 2
            if ex0 <= bcx <= ex1 and ey0 <= bcy <= ey1:
                # Compute edge-to-edge distance
                dx = max(0, max(sx0 - bx1, bx0 - sx1))
                dy = max(0, max(sy0 - by1, by0 - sy1))
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    best_idx = si

        if best_idx < 0:
            continue

        # OCR the blob
        try:
            crop = bgr[by0:by1, bx0:bx1]
            text = ocr_fn(crop).strip()
        except Exception:
            text = None

        if text:
            # Append to existing label (a structure can have multiple labels)
            existing = labels[best_idx]
            labels[best_idx] = f"{existing} {text}".strip() if existing else text

    return labels


def _get_ocr_fn():
    """
    Return a callable f(bgr_crop) -> str that performs OCR on a BGR image crop.

    Tries pytesseract first, then easyocr.  Returns None if neither is available.
    """
    # Try pytesseract (fastest, most common)
    try:
        import pytesseract
        from PIL import Image as _PILImage

        def _tesseract_ocr(bgr_crop: "np.ndarray") -> str:
            rgb = cv2.cvtColor(bgr_crop, cv2.COLOR_BGR2RGB)
            pil_img = _PILImage.fromarray(rgb)
            return pytesseract.image_to_string(pil_img, config="--psm 7").strip()

        return _tesseract_ocr
    except ImportError:
        pass

    # Try easyocr (slower startup, but no external binary required)
    try:
        import easyocr

        _reader = easyocr.Reader(["en"], gpu=False, verbose=False)

        def _easyocr_ocr(bgr_crop: "np.ndarray") -> str:
            results = _reader.readtext(bgr_crop, detail=0)
            return " ".join(results).strip()

        return _easyocr_ocr
    except ImportError:
        pass

    return None


# ---------------------------------------------------------------------------
# Public API: extract_structures_from_image
# ---------------------------------------------------------------------------

def extract_structures_from_image(
    image_path: str,
    page: int = 0,
    segment: bool = True,
    hand_drawn: bool = False,
    verbose: bool = False,
    merge_gap: Optional[int] = None,
    detect_labels: bool = True,
) -> Dict:
    """
    Extract all chemical structures from an image using DECIMER.

    Takes a PNG, JPG, or PDF path and returns a structured JSON dict with every
    detected molecule, its SMILES, DECIMER confidence score, bounding box in
    image pixel coordinates, and (when OCR is available) any nearby text label.

    Parameters
    ----------
    image_path    : path to PNG/JPG/PDF image file
    page          : PDF page index (0-based); ignored for raster images
    segment       : if True (default), segment the image into individual
                    structure regions before passing each to DECIMER.
                    Set False when the whole image is a single structure.
    hand_drawn    : use the DECIMER hand-drawn model instead of the default
                    printed-structure model
    verbose       : print progress messages to stderr
    merge_gap     : pixel gap for merging nearby segmentation boxes.
                    None = adaptive (median-based).  0 = no merging.
    detect_labels : if True (default), attempt to detect text labels near
                    each structure.  Requires pytesseract or easyocr to
                    return non-None label values; without an OCR library the
                    label field is always null.

    Returns
    -------
    dict with the following keys:

        ok           (bool)  True on success, False on error
        image_path   (str)   Absolute path of the input image
        structures   (list)  One entry per detected structure:
            smiles       (str)        DECIMER-predicted SMILES (may be "")
            confidence   (float|null) Geometric-mean per-token DECIMER score
                                      in [0, 1], or null if unavailable
            bbox         (list)       [x0, y0, x1, y1] pixel coords (top-left,
                                      bottom-right) in the input image
            label        (str|null)   Nearby text label detected by OCR, or null
        error        (str)   Only present on failure (ok=False)

    Examples
    --------
    >>> from cdxml_toolkit.image.structure_from_image import extract_structures_from_image
    >>> result = extract_structures_from_image("scheme.png")
    >>> if result["ok"]:
    ...     for s in result["structures"]:
    ...         print(s["smiles"], s["confidence"])

    Notes
    -----
    - DECIMER models are downloaded to ~/.data/DECIMER-V2/ on first run (~570 MB).
    - Confidence uses geometric mean of per-character DECIMER scores, making it
      sensitive to low-confidence characters.  Scores above ~0.85 are reliable;
      below ~0.70 the SMILES should be verified manually.
    - Labels are detected only when pytesseract or easyocr is installed.
      Install either with: pip install pytesseract  or  pip install easyocr
    - For backward-compatible low-level access (returns List[Dict] with atoms/bonds),
      use _extract_structures_raw() directly.
    """
    abs_path = os.path.abspath(image_path)

    # Guard: DECIMER is required
    try:
        _load_decimer(hand_drawn=hand_drawn)
    except ImportError as exc:
        return {
            "ok": False,
            "image_path": abs_path,
            "structures": [],
            "error": str(exc),
        }

    # Guard: OpenCV is required for segmentation and label detection
    if not HAS_CV2:
        return {
            "ok": False,
            "image_path": abs_path,
            "structures": [],
            "error": (
                "opencv-python is required. "
                "Install with: pip install opencv-python"
            ),
        }

    try:
        raw = _extract_structures_raw(
            image_path=image_path,
            page=page,
            segment=segment,
            hand_drawn=hand_drawn,
            verbose=verbose,
            merge_gap=merge_gap,
        )
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "image_path": abs_path,
            "structures": [],
            "error": str(exc),
        }
    except Exception as exc:
        return {
            "ok": False,
            "image_path": abs_path,
            "structures": [],
            "error": f"Extraction failed: {exc}",
        }

    # Detect nearby text labels (spatial proximity + optional OCR)
    labels: List[Optional[str]] = [None] * len(raw)
    if detect_labels and HAS_CV2 and raw:
        try:
            bgr = load_image(image_path, page=page)
            bboxes = [tuple(entry["bbox"]) for entry in raw]
            labels = _detect_nearby_labels(bgr, bboxes)  # type: ignore[arg-type]
        except Exception:
            # Label detection is best-effort; never fail the whole extraction
            labels = [None] * len(raw)

    structures = []
    for entry, label in zip(raw, labels):
        structures.append({
            "smiles": entry.get("smiles", ""),
            "confidence": entry.get("confidence"),
            "bbox": entry.get("bbox", []),
            "label": label,
        })

    return {
        "ok": True,
        "image_path": abs_path,
        "structures": structures,
    }


# ---------------------------------------------------------------------------
# CDXML output (optional, wraps cdxml_builder)
# ---------------------------------------------------------------------------

def _format_cdxml_header(bbox: str) -> str:
    """Format CDXML_HEADER template with ACS Document 1996 style constants."""
    return _CDXML_HEADER.format(
        bbox=bbox,
        label_font=ACS_LABEL_FONT,
        label_size=ACS_LABEL_SIZE,
        label_face=ACS_LABEL_FACE,
        caption_size=ACS_CAPTION_SIZE,
        hash_spacing=ACS_HASH_SPACING,
        margin_width=ACS_MARGIN_WIDTH,
        line_width=ACS_LINE_WIDTH,
        bold_width=ACS_BOLD_WIDTH,
        bond_length=ACS_BOND_LENGTH_STR,
        bond_spacing=ACS_BOND_SPACING,
        chain_angle=ACS_CHAIN_ANGLE_STR,
    )


def _best_smiles_component(smiles: str) -> str:
    """
    For a dot-separated multi-component SMILES, return the single component
    that is most likely to be the real chemical structure (largest heavy-atom
    count that is also a valid RDKit molecule).  Filters out junk fragments
    like lone alkyne chains, single atoms, very short chains, etc.
    """
    if "." not in smiles:
        return smiles

    parts = smiles.split(".")
    best = ""
    best_score = -1

    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Quick atom-count heuristic before RDKit parse
        heavy = sum(1 for c in part if c.isupper())
        if heavy < 3:
            continue
        # Penalise pure alkyne/alkene chains (no rings, no heteroatoms)
        has_heteroatom = any(c in part for c in "NOSFPClBrI")
        has_ring = "1" in part or "2" in part or "3" in part or "@" in part
        score = heavy * 10 + (50 if has_heteroatom else 0) + (30 if has_ring else 0)
        if score > best_score:
            best = part
            best_score = score

    return best if best else smiles.split(".")[0]


def _translate_atoms_xml(frag_xml: str, dx: float, dy: float) -> str:
    """
    Shift all coordinate attributes in a fragment XML string by (dx, dy).
    Handles: p="x y"  and  BoundingBox="x1 y1 x2 y2".
    Both patterns appear in <fragment>, <n>, and <t> elements.
    """
    import re

    def shift_p(m: "re.Match") -> str:
        x, y = float(m.group(1)), float(m.group(2))
        return f'p="{x + dx:.3f} {y + dy:.3f}"'

    def shift_bb(m: "re.Match") -> str:
        vals = [float(v) for v in m.group(1).split()]
        shifted = [
            f"{vals[0] + dx:.3f}", f"{vals[1] + dy:.3f}",
            f"{vals[2] + dx:.3f}", f"{vals[3] + dy:.3f}",
        ]
        return f'BoundingBox="{" ".join(shifted)}"'

    frag_xml = re.sub(r'\bp="([-\d.]+)\s+([-\d.]+)"', shift_p, frag_xml)
    frag_xml = re.sub(r'\bBoundingBox="((?:[-\d.]+ ?){4})"', shift_bb, frag_xml)
    return frag_xml


def results_to_cdxml(results: List[Dict]) -> str:
    """
    Convert extracted structures to a CDXML document (multiple molecules on one page).

    Each valid structure is placed left-to-right, spaced by its actual atom
    bounding box.  The correct translation is computed from the fragment's
    real atom x/y range (atoms were normalised to centre ≈ (200, 300)), then
    shifted so fragment i lands at (x_cursor + half_width, ROW_Y).

    Multi-component SMILES (dot-separated) are filtered to retain only the
    largest / most drug-like component before building.

    Requires cdxml_builder.py to be importable from the same directory.
    """
    import importlib.util
    import xml.etree.ElementTree as ET

    _dir = os.path.dirname(os.path.abspath(__file__))
    try:
        spec = importlib.util.spec_from_file_location(
            "cdxml_builder", os.path.join(_dir, "cdxml_builder.py")
        )
        cdxml_builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cdxml_builder)
    except Exception as exc:
        raise ImportError(f"Could not import cdxml_builder.py: {exc}") from exc

    PAGE_MARGIN = 36.0      # pt from page left edge to first atom bbox left
    MOL_GAP = 40.0          # pt gap between adjacent molecule bounding boxes
    ROW_Y = 300.0           # y-centre for the row of molecules
    LABEL_PAD = 10.0        # extra pt added around atom bbox for labels

    # --- Build each molecule, measure its atom bbox, then place ---
    placed_fragments: List[str] = []
    half_heights: List[float] = []
    x_cursor = PAGE_MARGIN
    start_id = 1000

    for entry in results:
        atoms = entry.get("atoms", [])
        bonds = entry.get("bonds", [])
        if not atoms:
            continue

        # If this entry came from a multi-component SMILES, re-derive coords
        # from only the best component so we don't get a stacked mess.
        smiles = entry.get("smiles", "")
        if smiles and "." in smiles:
            best = _best_smiles_component(smiles)
            if best != smiles:
                mol_data = smiles_to_coords(best, offset_index=0)
                if mol_data:
                    atoms, bonds = normalize_for_cdxml(
                        mol_data["atoms"], mol_data["bonds"],
                        center_x=200.0, center_y=300.0,
                    )

        # Measure actual atom coordinate bounding box
        xs = [a["x"] for a in atoms]
        ys = [a["y"] for a in atoms]
        atom_xmin = min(xs);  atom_xmax = max(xs)
        atom_ymin = min(ys);  atom_ymax = max(ys)
        mol_w = (atom_xmax - atom_xmin) + LABEL_PAD * 2
        mol_h = (atom_ymax - atom_ymin) + LABEL_PAD * 2
        mol_w = max(mol_w, ACS_BOND_LENGTH_PT * 2)
        mol_h = max(mol_h, ACS_BOND_LENGTH_PT * 2)

        # Build fragment XML (atoms are centred near (200, 300) already)
        cdxml_str = cdxml_builder.build_molecule_cdxml(atoms, bonds, start_id=start_id)
        root = ET.fromstring(cdxml_str)
        page_el = root.find("page")
        if page_el is None:
            continue
        frag_xmls = [ET.tostring(f, encoding="unicode") for f in page_el.findall("fragment")]
        if not frag_xmls:
            continue

        # Compute atom bbox centre in the built (origin) coordinates
        origin_cx = (atom_xmin + atom_xmax) / 2.0
        origin_cy = (atom_ymin + atom_ymax) / 2.0

        # Target position: centre of the slot we're placing this molecule into
        target_cx = x_cursor + mol_w / 2.0
        target_cy = ROW_Y

        dx = target_cx - origin_cx
        dy = target_cy - origin_cy

        for fxml in frag_xmls:
            placed_fragments.append(_translate_atoms_xml(fxml, dx, dy))

        half_heights.append(mol_h / 2.0)
        x_cursor += mol_w + MOL_GAP
        start_id += len(atoms) * 3 + 200

    if not placed_fragments:
        return ""

    page_width = x_cursor - MOL_GAP + PAGE_MARGIN
    page_height = ROW_Y + max(half_heights) + PAGE_MARGIN
    page_bb = f"0 0 {page_width:.1f} {page_height:.1f}"
    page_content = "\n  ".join(placed_fragments)

    return (
        _format_cdxml_header(page_bb) + "\n"
        f'<page BoundingBox="{page_bb}">\n'
        f'  {page_content}\n'
        '</page>\n'
        + _CDXML_FOOTER + "\n"
    )


def results_to_cdxml_chemscript(
    results: List[Dict],
    verbose: bool = False,
) -> str:
    """
    Convert extracted structures to CDXML using ChemScript for cleanup.

    For each structure with a valid SMILES, ChemScript's smiles_to_cdxml()
    is called — this runs CleanupStructure() internally, producing
    ChemDraw-native coordinates with proper aromaticity, bond lengths,
    and ACS 1996 style.  The resulting fragment XMLs are then laid out
    left-to-right on a single page.

    Requires chemscript_bridge.py to be importable from the same directory,
    and a working ChemDraw + ChemScript 32-bit environment.
    """
    import importlib.util
    import xml.etree.ElementTree as ET
    import re

    def log(msg: str):
        if verbose:
            print(f"[structure_from_image] {msg}", file=sys.stderr)

    # Import chemscript_bridge
    _dir = os.path.dirname(os.path.abspath(__file__))
    try:
        spec = importlib.util.spec_from_file_location(
            "chemscript_bridge", os.path.join(_dir, "chemscript_bridge.py")
        )
        csb_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(csb_module)
    except Exception as exc:
        raise ImportError(
            f"Could not import chemscript_bridge.py: {exc}\n"
            "The --cleanup flag requires ChemDraw and chemscript_bridge."
        ) from exc

    PAGE_MARGIN = 36.0
    MOL_GAP = 40.0
    ROW_Y = 300.0
    LABEL_PAD = 10.0

    # --- Build each molecule via ChemScript, extract fragment, measure bbox ---
    log("Opening ChemScript bridge...")
    cs = csb_module.ChemScriptBridge()

    frag_data: List[Tuple[str, float, float, float, float]] = []
    # Each item: (fragment_xml, xmin, ymin, xmax, ymax)

    try:
        for entry in results:
            smiles = entry.get("smiles", "").strip()
            if not smiles:
                continue

            # For multi-component SMILES, pick the best fragment
            if "." in smiles:
                smiles = _best_smiles_component(smiles)

            log(f"  ChemScript: {smiles[:60]}...")
            try:
                cdxml_str = cs.smiles_to_cdxml(smiles)
            except Exception as exc:
                log(f"  ChemScript failed for {smiles[:40]}: {exc}")
                continue

            if not cdxml_str or "<CDXML" not in cdxml_str:
                log(f"  ChemScript returned empty CDXML")
                continue

            # Parse the CDXML and extract all <fragment> elements + measure coords
            root = ET.fromstring(cdxml_str)
            page_el = root.find("page")
            if page_el is None:
                continue

            for frag in page_el.findall("fragment"):
                frag_xml = ET.tostring(frag, encoding="unicode")

                # Measure atom positions from <n> elements
                xs, ys = [], []
                for n in frag.findall("n"):
                    p = n.get("p")
                    if p:
                        parts = p.split()
                        if len(parts) >= 2:
                            xs.append(float(parts[0]))
                            ys.append(float(parts[1]))

                if not xs:
                    continue

                frag_data.append((
                    frag_xml,
                    min(xs), min(ys), max(xs), max(ys),
                ))
    finally:
        cs.close()

    if not frag_data:
        return ""

    # --- Lay out fragments left-to-right ---
    placed_fragments: List[str] = []
    half_heights: List[float] = []
    x_cursor = PAGE_MARGIN

    for frag_xml, xmin, ymin, xmax, ymax in frag_data:
        mol_w = (xmax - xmin) + LABEL_PAD * 2
        mol_h = (ymax - ymin) + LABEL_PAD * 2
        mol_w = max(mol_w, ACS_BOND_LENGTH_PT * 2)
        mol_h = max(mol_h, ACS_BOND_LENGTH_PT * 2)

        origin_cx = (xmin + xmax) / 2.0
        origin_cy = (ymin + ymax) / 2.0

        target_cx = x_cursor + mol_w / 2.0
        target_cy = ROW_Y

        dx = target_cx - origin_cx
        dy = target_cy - origin_cy

        placed_fragments.append(_translate_atoms_xml(frag_xml, dx, dy))
        half_heights.append(mol_h / 2.0)
        x_cursor += mol_w + MOL_GAP

    if not placed_fragments:
        return ""

    page_width = x_cursor - MOL_GAP + PAGE_MARGIN
    page_height = ROW_Y + max(half_heights) + PAGE_MARGIN
    page_bb = f"0 0 {page_width:.1f} {page_height:.1f}"
    page_content = "\n  ".join(placed_fragments)

    return (
        _format_cdxml_header(page_bb) + "\n"
        f'<page BoundingBox="{page_bb}">\n'
        f'  {page_content}\n'
        '</page>\n'
        + _CDXML_FOOTER + "\n"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="structure_from_image.py",
        description="Extract chemical structures from images using DECIMER.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Notes")[0].split("Usage\n-----")[1].strip(),
    )
    p.add_argument("--input", "-i", required=True,
                   help="Input image (PNG/JPG) or PDF file")
    p.add_argument("--output", "-o", default="-",
                   help="Output file path; '-' writes JSON to stdout (default)")
    p.add_argument("--page", type=int, default=0,
                   help="PDF page to process, 0-indexed (default: 0)")
    p.add_argument("--format", choices=["json", "cdxml"], default="json",
                   help="Output format (default: json)")
    p.add_argument("--no-segment", dest="segment", action="store_false",
                   help="Treat whole image as a single structure (skip segmentation)")
    p.add_argument("--hand-drawn", action="store_true",
                   help="Use DECIMER hand-drawn model")
    p.add_argument("--cleanup", action="store_true",
                   help="Use ChemScript to clean up structures — produces "
                        "ChemDraw-native coordinates, proper aromaticity, "
                        "and ACS 1996 style (requires ChemDraw + chemscript_bridge)")
    p.add_argument("--gap", type=int, default=None,
                   help="Merge gap in pixels for segmentation box merging. "
                        "Default: adaptive (based on image density). "
                        "Use 0 to disable merging entirely.")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="Print progress messages to stderr")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not os.path.isfile(args.input):
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        return 1

    if not HAS_CV2:
        print("ERROR: opencv-python not installed. Run: pip install opencv-python",
              file=sys.stderr)
        return 1

    try:
        results = extract_structures_from_image(
            image_path=args.input,
            page=args.page,
            segment=args.segment,
            hand_drawn=args.hand_drawn,
            verbose=args.verbose,
            merge_gap=args.gap,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc(file=sys.stderr)
        return 1

    # Format output
    if args.format == "cdxml":
        try:
            if args.cleanup:
                output_str = results_to_cdxml_chemscript(
                    results, verbose=args.verbose,
                )
            else:
                output_str = results_to_cdxml(results)
        except Exception as exc:
            print(f"ERROR building CDXML: {exc}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc(file=sys.stderr)
            return 1
        if not output_str:
            print("WARNING: No valid structures to write to CDXML.", file=sys.stderr)
            return 1
    else:
        output_str = json.dumps(results, indent=2)

    # Write output
    if args.output == "-":
        print(output_str)
    else:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(output_str)
        if args.verbose:
            print(f"Wrote {args.output}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
