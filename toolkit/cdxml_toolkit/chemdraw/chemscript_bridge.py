#!/usr/bin/env python3
"""
ChemScript Bridge — Python wrapper around PerkinElmer's ChemScript .NET library.

Provides native access to ChemDraw's chemical intelligence: format conversion,
name↔structure, structure cleanup, substructure search, reaction handling, and
more — all from Python.

Architecture:
    ChemScript's .NET DLL is 32-bit, so we run a thin JSON-RPC server
    (_chemscript_server.py) under a 32-bit Python environment (chemscript32)
    and communicate via subprocess stdin/stdout.

Usage (CLI):
    python chemscript_bridge.py convert input.cdx output.cdxml
    python chemscript_bridge.py name2struct "morpholine" -o output.cdxml
    python chemscript_bridge.py smiles2struct "C1COCCN1" -o morpholine.cdxml
    python chemscript_bridge.py cleanup messy.cdxml -o clean.cdxml
    python chemscript_bridge.py info structure.cdx
    python chemscript_bridge.py search --target target.cdx --query query.cdx
    python chemscript_bridge.py reaction input.cdx --list
    python chemscript_bridge.py lcs mol1.cdx mol2.cdx

Python API:
    from cdxml_toolkit.chemdraw.chemscript_bridge import ChemScriptBridge
    cs = ChemScriptBridge()
    cdxml = cs.name_to_cdxml("morpholine")
    cs.convert_file("input.cdx", "output.cdxml")
"""

import argparse
import json
import os
import re
import struct
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..constants import ACS_STYLE

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CONFIG_PATH = Path.home() / ".chemscript_config.json"

# Default 32-bit Python path (chemscript32 conda env)
DEFAULT_PYTHON32 = None  # auto-detected

# ACS Document 1996 style attributes to inject into ChemScript CDXML output.
# Imported from constants.py — kept as module-level alias for backward compat.
ACS_STYLE_ATTRS = ACS_STYLE


def _dll_bitness(path: str) -> Optional[int]:
    """Read PE header to determine 32 or 64 bit. Returns 32, 64, or None."""
    try:
        with open(path, "rb") as f:
            if f.read(2) != b"MZ":
                return None
            f.seek(0x3C)
            pe_offset = struct.unpack("<I", f.read(4))[0]
            f.seek(pe_offset)
            if f.read(4) != b"PE\x00\x00":
                return None
            machine = struct.unpack("<H", f.read(2))[0]
            return {0x14C: 32, 0x8664: 64}.get(machine)
    except (OSError, struct.error):
        return None


def _find_chemdraw_root() -> Optional[str]:
    """Find ChemDraw/ChemOffice vendor install root via COM registry.

    Looks up the ChemDraw.Application ProgID → CLSID → LocalServer32 path,
    then walks up the directory tree to the vendor folder (child of
    Program Files or Program Files (x86)).

    Returns the vendor root (e.g. ``C:\\Program Files (x86)\\PerkinElmerInformatics``)
    or None if ChemDraw is not registered.
    """
    try:
        import winreg
    except ImportError:
        return None

    # Step 1: ProgID → CLSID
    try:
        key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT,
                             "ChemDraw.Application\\CLSID")
        clsid = winreg.QueryValue(key, "")
        winreg.CloseKey(key)
    except OSError:
        return None

    # Step 2: CLSID → executable path (try 32-bit and 64-bit registry views)
    exe_path = None
    subkey = f"SOFTWARE\\Classes\\CLSID\\{clsid}\\LocalServer32"
    for access in [winreg.KEY_READ | winreg.KEY_WOW64_32KEY,
                   winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
                   winreg.KEY_READ]:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey, 0, access)
            raw = winreg.QueryValue(key, "")
            winreg.CloseKey(key)
            # Strip /Automation flags and quotes
            exe_path = raw.split("/")[0].strip().strip('"')
            break
        except OSError:
            continue

    if not exe_path or not os.path.isfile(exe_path):
        return None

    # Step 3: walk up to the vendor root (child of Program Files)
    path = os.path.dirname(exe_path)
    program_files = {p.lower() for p in ["program files", "program files (x86)"]}
    while path:
        parent = os.path.dirname(path)
        if os.path.basename(parent).lower() in program_files:
            return path
        if parent == path:
            break
        path = parent
    return None


def _find_chemscript_dlls(root: str) -> Optional[Dict[str, str]]:
    """Search a directory tree for ChemScript DLLs.

    Expects to find two DLLs with 'chemscript' in the filename:
    the smaller one is the managed .NET assembly (API surface), the larger
    one is the native C++ engine.

    Returns dict with keys ``dll_dir``, ``assembly``, ``native_path``,
    ``bitness`` or None if not found.
    """
    dlls = []
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if "chemscript" in f.lower() and f.lower().endswith(".dll"):
                full = os.path.join(dirpath, f)
                try:
                    size = os.path.getsize(full)
                except OSError:
                    continue
                dlls.append((full, size))

    if len(dlls) < 2:
        return None

    # Sort by size: smallest = managed assembly, largest = native engine
    dlls.sort(key=lambda x: x[1])
    managed_path = dlls[0][0]
    native_path = dlls[-1][0]

    # Derive assembly name from managed DLL filename (strip .dll extension)
    assembly = os.path.splitext(os.path.basename(managed_path))[0]
    dll_dir = os.path.dirname(managed_path)
    bitness = _dll_bitness(native_path)

    return {
        "dll_dir": dll_dir,
        "assembly": assembly,
        "native_path": native_path,
        "managed_path": managed_path,
        "bitness": bitness,
    }


def _find_python_for_chemscript(bitness: Optional[int] = None) -> Optional[str]:
    """Locate a Python interpreter suitable for ChemScript.

    Checks saved config first, then scans for conda envs named
    ``chemscript32`` (for 32-bit DLLs) or ``chemscript`` / current
    interpreter (for 64-bit DLLs).
    """
    cfg = _load_config()
    saved = cfg.get("python32")
    if saved and os.path.isfile(saved):
        return saved

    # For 64-bit DLLs, the current interpreter may work
    if bitness == 64:
        return sys.executable

    # Scan for chemscript32 conda env (32-bit DLLs)
    candidates = [
        Path.home() / "miniconda3" / "envs" / "chemscript32" / "python.exe",
        Path(os.environ.get("CONDA_PREFIX", "")) / ".." / "chemscript32" / "python.exe",
        Path(os.environ.get("USERPROFILE", "")) / "miniconda3" / "envs" / "chemscript32" / "python.exe",
        Path(os.environ.get("USERPROFILE", "")) / "Anaconda3" / "envs" / "chemscript32" / "python.exe",
    ]
    for p in candidates:
        try:
            resolved = p.resolve()
            if resolved.exists():
                return str(resolved)
        except OSError:
            continue
    return None


def _load_config() -> dict:
    """Load saved config (python32 path, DLL path, etc.)."""
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_config(cfg: dict):
    """Persist config."""
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    except OSError as e:
        print(f"Warning: could not save config: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CDXML post-processing — inject ACS 1996 style
# ---------------------------------------------------------------------------

def _inject_acs_style(cdxml: str) -> str:
    """
    Post-process CDXML from ChemScript to inject ACS Document 1996 style.

    ChemScript defaults to BondLength=30; we rescale to 14.40 and set other
    ACS style attributes on the root <CDXML> element.
    """
    if not cdxml or "<CDXML" not in cdxml:
        return cdxml

    # Parse the current BondLength from ChemScript output
    bl_match = re.search(r'BondLength="([^"]+)"', cdxml)
    cs_bond_length = float(bl_match.group(1)) if bl_match else 30.0
    target_bond_length = float(ACS_STYLE_ATTRS["BondLength"])

    if cs_bond_length <= 0:
        cs_bond_length = 30.0
    scale = target_bond_length / cs_bond_length

    # Inject/replace style attributes on the root <CDXML> element
    for attr, val in ACS_STYLE_ATTRS.items():
        pat = re.compile(rf'\b{attr}="[^"]*"')
        if pat.search(cdxml):
            cdxml = pat.sub(f'{attr}="{val}"', cdxml)
        else:
            # Insert before the closing > of <CDXML ...>
            cdxml = re.sub(
                r"(<CDXML\b[^>]*?)(>)",
                rf'\1 {attr}="{val}"\2',
                cdxml,
                count=1,
            )

    # Rescale all coordinate values if scale != 1.0
    if abs(scale - 1.0) > 0.001:
        cdxml = _rescale_cdxml_coords(cdxml, scale)

    return cdxml


def _rescale_cdxml_coords(cdxml: str, scale: float) -> str:
    """Rescale point coordinates (p=, BoundingBox=) in CDXML by a factor."""

    def _scale_point(match: re.Match) -> str:
        attr = match.group(1)
        values = match.group(2)
        nums = values.split()
        scaled = " ".join(f"{float(n) * scale:.2f}" for n in nums)
        return f'{attr}="{scaled}"'

    # Scale p="x y" (node positions)
    cdxml = re.sub(r'(p)="([^"]+)"', _scale_point, cdxml)
    # Scale BoundingBox="l t r b"
    cdxml = re.sub(r'(BoundingBox)="([^"]+)"', _scale_point, cdxml)

    return cdxml


# ---------------------------------------------------------------------------
# ChemScriptBridge class — Python API
# ---------------------------------------------------------------------------

class ChemScriptBridge:
    """
    High-level Python interface to ChemScript via a 32-bit subprocess server.

    Usage:
        cs = ChemScriptBridge()
        cdxml = cs.name_to_cdxml("morpholine")
        cs.convert_file("in.cdx", "out.cdxml")
    """

    def __init__(self, python32_path: str = None):
        self._proc: Optional[subprocess.Popen] = None
        cfg = _load_config()
        bitness = cfg.get("bitness")
        self._python32 = (python32_path
                          or cfg.get("python32")
                          or _find_python_for_chemscript(bitness))
        if self._python32 is None:
            raise RuntimeError(
                "Could not find Python for ChemScript.\n"
                "Run 'cdxml-doctor' for setup instructions,\n"
                "or specify the path: ChemScriptBridge(python32_path=r'C:\\...\\python.exe')"
            )
        # Save for next time
        if cfg.get("python32") != self._python32:
            cfg["python32"] = self._python32
            _save_config(cfg)

        self._server_script = str(
            Path(__file__).resolve().parent / "_chemscript_server.py"
        )

    def _ensure_server(self):
        """Start the server subprocess if not already running."""
        if self._proc is not None and self._proc.poll() is None:
            return
        cmd = [self._python32, self._server_script]
        # Pass DLL config from ~/.chemscript_config.json so the server
        # can locate the correct ChemScript DLL (ChemDraw 15 vs 16).
        cfg = _load_config()
        if cfg.get("dll_dir"):
            cmd += ["--dll-dir", cfg["dll_dir"]]
        if cfg.get("assembly"):
            cmd += ["--assembly", cfg["assembly"]]
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        # Wait for ready signal
        ready_line = self._proc.stdout.readline()
        if not ready_line:
            err = self._proc.stderr.read()
            raise RuntimeError(f"ChemScript server failed to start: {err}")
        ready = json.loads(ready_line)
        if not ready.get("ready"):
            raise RuntimeError(f"ChemScript server unexpected: {ready}")

    def _call(self, cmd: str, **args) -> dict:
        """Send a command to the server and return the response."""
        self._ensure_server()
        request = json.dumps({"cmd": cmd, "args": args})
        self._proc.stdin.write(request + "\n")
        self._proc.stdin.flush()
        resp_line = self._proc.stdout.readline()
        if not resp_line:
            err = self._proc.stderr.read() if self._proc.stderr else "no output"
            raise RuntimeError(f"ChemScript server died: {err}")
        return json.loads(resp_line)

    def close(self):
        """Shut down the server."""
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.stdin.write(json.dumps({"cmd": "quit"}) + "\n")
                self._proc.stdin.flush()
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()
        self._proc = None

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def convert_file(self, input_path: str, output_path: str) -> dict:
        """
        Convert a chemistry file between formats.

        Supported: CDX, CDXML, MOL, SDF, RXN, SMILES.
        Format determined by file extension.
        """
        result = self._call("convert", input=os.path.abspath(input_path),
                            output=os.path.abspath(output_path))
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "Conversion failed"))
        # Post-process CDXML output for ACS style
        if output_path.lower().endswith(".cdxml"):
            self._postprocess_cdxml(output_path)
        return result

    def name_to_cdxml(self, name: str, output: str = None) -> str:
        """
        Convert a chemical name to CDXML string.

        Args:
            name: Chemical name (e.g. "morpholine", "benzene").
            output: Optional file path to write CDXML.

        Returns:
            CDXML string with ACS 1996 style.
        """
        result = self._call("name_to_cdxml", name=name,
                            output=os.path.abspath(output) if output else None)
        if not result.get("ok"):
            raise RuntimeError(result.get("error", f"Name resolution failed: {name}"))
        cdxml = _inject_acs_style(result["cdxml"])
        if output:
            Path(output).write_text(cdxml, encoding="utf-8")
        return cdxml

    def smiles_to_cdxml(self, smiles: str, output: str = None) -> str:
        """
        Convert a SMILES string to CDXML.

        Args:
            smiles: SMILES string (e.g. "C1COCCN1").
            output: Optional file path to write CDXML.

        Returns:
            CDXML string with ACS 1996 style.
        """
        result = self._call("smiles_to_cdxml", smiles=smiles,
                            output=os.path.abspath(output) if output else None)
        if not result.get("ok"):
            raise RuntimeError(result.get("error", f"SMILES parse failed: {smiles}"))
        cdxml = _inject_acs_style(result["cdxml"])
        if output:
            Path(output).write_text(cdxml, encoding="utf-8")
        return cdxml

    def cleanup(self, input_path: str, output: str = None) -> str:
        """
        Clean up a structure file — normalize coordinates, bond lengths, etc.

        Args:
            input_path: Path to structure file.
            output: Output path (defaults to overwriting input).

        Returns:
            Output file path.
        """
        out = output or input_path
        result = self._call("cleanup",
                            input=os.path.abspath(input_path),
                            output=os.path.abspath(out))
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "Cleanup failed"))
        if out.lower().endswith(".cdxml"):
            self._postprocess_cdxml(out)
        return out

    def get_name(self, source: str) -> str:
        """Get IUPAC name for a structure file or SMILES string."""
        args = {"source": source}
        if os.path.isfile(source):
            args["source"] = os.path.abspath(source)
        result = self._call("get_name", **args)
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "Name lookup failed"))
        return result["name"]

    def get_formula(self, source: str) -> str:
        """Get molecular formula for a structure file or SMILES string."""
        args = {"source": source}
        if os.path.isfile(source):
            args["source"] = os.path.abspath(source)
        result = self._call("get_formula", **args)
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "Formula lookup failed"))
        return result["formula"]

    def get_info(self, source: str) -> dict:
        """
        Get full chemical info: name, formula, SMILES, InChI, atom/bond count.

        Works with both structure files and reaction files.
        """
        args = {"source": source}
        if os.path.isfile(source):
            args["source"] = os.path.abspath(source)
        result = self._call("get_info", **args)
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "Info lookup failed"))
        return result

    def contains_substructure(self, target: str, query: str) -> bool:
        """
        Check if target contains query as a substructure.

        Args can be file paths or SMILES strings.
        """
        t_args = {"target": os.path.abspath(target) if os.path.isfile(target) else target}
        q_args = {"query": os.path.abspath(query) if os.path.isfile(query) else query}
        if not os.path.isfile(target):
            t_args["target_format"] = "smiles"
        if not os.path.isfile(query):
            q_args["query_format"] = "smiles"
        result = self._call("contains_substructure", **t_args, **q_args)
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "Substructure search failed"))
        return result["contains"]

    def substructure_search(self, target: str, query: str) -> dict:
        """
        Perform atom-by-atom substructure search.

        Returns dict with 'contains' bool and 'maps' list of atom mappings.
        """
        t_args = {"target": os.path.abspath(target) if os.path.isfile(target) else target}
        q_args = {"query": os.path.abspath(query) if os.path.isfile(query) else query}
        if not os.path.isfile(target):
            t_args["target_format"] = "smiles"
        if not os.path.isfile(query):
            q_args["query_format"] = "smiles"
        result = self._call("substructure_search", **t_args, **q_args)
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "Substructure search failed"))
        return result

    def load_reaction(self, source: str, include_cdxml: bool = False) -> dict:
        """
        Load a reaction file and return component information.

        Args:
            source: Path to reaction file (CDX, RXN) or reaction SMILES.
            include_cdxml: If True, include CDXML for each component.

        Returns:
            Dict with 'formula', 'reactants', 'products'.
        """
        args = {"source": source, "include_cdxml": include_cdxml}
        if os.path.isfile(source):
            args["source"] = os.path.abspath(source)
        else:
            args["format"] = "smiles"
        result = self._call("load_reaction", **args)
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "Reaction load failed"))
        return result

    def largest_common_substructure(self, mol1: str, mol2: str) -> dict:
        """
        Find the largest common substructure between two molecules.

        Args can be file paths or SMILES strings.

        Returns:
            Dict with 'atom_map' and 'common_atom_count'.
        """
        args = {}
        args["mol1"] = os.path.abspath(mol1) if os.path.isfile(mol1) else mol1
        args["mol2"] = os.path.abspath(mol2) if os.path.isfile(mol2) else mol2
        if not os.path.isfile(mol1):
            args["mol1_format"] = "smiles"
        if not os.path.isfile(mol2):
            args["mol2_format"] = "smiles"
        result = self._call("largest_common_substructure", **args)
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "LCS failed"))
        return result

    def overlay(self, source: str, target: str,
                source_format: str = None,
                target_format: str = None) -> Tuple[str, bool]:
        """
        Overlay (2D-align) a molecule onto a reference molecule.

        Args:
            source: File path or CDXML string of the molecule to align.
            target: File path or CDXML string of the reference molecule.
            source_format: Format hint for source (optional).
            target_format: Format hint for target (optional).

        Returns:
            Tuple of (aligned_cdxml_string, success_bool).
        """
        args = {}
        args["source"] = os.path.abspath(source) if os.path.isfile(source) else source
        args["target"] = os.path.abspath(target) if os.path.isfile(target) else target
        if source_format:
            args["source_format"] = source_format
        if target_format:
            args["target_format"] = target_format
        result = self._call("overlay", **args)
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "Overlay failed"))
        cdxml = _inject_acs_style(result["aligned_cdxml"])
        return cdxml, result.get("success", False)

    def substructure_align(self, query: str, target: str,
                           query_format: str = None,
                           target_format: str = None) -> Optional[List]:
        """
        Align a small molecule (query) to its substructure match in a
        larger molecule (target).

        Uses ChemScript to confirm substructure match and get SMILES,
        then RDKit for atom-index mapping (avoiding ChemScript naming bugs).

        Returns a list of (x, y) positions for each query atom (in the
        query's CDXML atom iteration order), taken from the matched
        target atoms.  Returns None if no substructure match was found.
        """
        import re as _re
        from xml.etree import ElementTree as ET

        args = {}
        args["query"] = os.path.abspath(query) if os.path.isfile(query) else query
        args["target"] = os.path.abspath(target) if os.path.isfile(target) else target
        if query_format:
            args["query_format"] = query_format
        if target_format:
            args["target_format"] = target_format
        result = self._call("substructure_align", **args)
        if not result.get("ok") or not result.get("contains"):
            return None

        target_cdxml = result.get("target_cdxml", "")
        query_cdxml = result.get("query_cdxml", "")
        target_mol_block = result.get("target_mol", "")
        query_mol_block = result.get("query_mol", "")

        if not target_cdxml or not target_mol_block or not query_mol_block:
            return None

        # --- Use RDKit for substructure matching via MOL blocks ---
        # MOL block atom order is guaranteed to match ChemScript's iteration
        # order (both come from the same StructureData), so RDKit atom indices
        # from the MOL block = ChemScript atom indices = CDXML <n> order.
        try:
            from rdkit import Chem
        except ImportError:
            return None

        # ChemScript MOL blocks may have aromatic bonds that RDKit can't
        # kekulize, so parse without sanitization then sanitize everything
        # except kekulization.
        target_mol = Chem.MolFromMolBlock(target_mol_block, sanitize=False)
        if target_mol:
            Chem.SanitizeMol(
                target_mol,
                Chem.SanitizeFlags.SANITIZE_ALL
                ^ Chem.SanitizeFlags.SANITIZE_KEKULIZE,
            )
        query_mol = Chem.MolFromMolBlock(query_mol_block, sanitize=False)
        if query_mol:
            Chem.SanitizeMol(query_mol)
        if target_mol is None or query_mol is None:
            return None

        match = target_mol.GetSubstructMatch(query_mol)
        if not match:
            return None
        # match[i] = target atom index that corresponds to query atom i

        # --- Parse target CDXML to extract atom positions ---
        clean = _re.sub(r'<!DOCTYPE[^>]*>', '', target_cdxml)
        clean = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', clean)
        try:
            troot = ET.fromstring(clean)
        except ET.ParseError:
            return None

        target_positions = []
        for n in troot.iter("n"):
            p = n.get("p", "")
            if p:
                try:
                    px, py = p.split()[:2]
                    target_positions.append((float(px), float(py)))
                except (ValueError, IndexError):
                    target_positions.append(None)
            else:
                target_positions.append(None)

        # Build positions for each query atom
        positions = []
        for qi in range(len(match)):
            ti = match[qi]  # target atom index
            if ti < len(target_positions) and target_positions[ti] is not None:
                positions.append(target_positions[ti])
            else:
                positions.append(None)

        return positions

    def write_data(self, source: str, target_format: str,
                   source_format: str = None) -> str:
        """
        Convert a structure to a specific format string.

        Args:
            source: File path or data string.
            target_format: Output format (smiles, inchi, mol, cdxml, name, etc.).
            source_format: Input format hint (optional).

        Returns:
            Data string in target format.
        """
        args = {"target_format": target_format}
        if os.path.isfile(source):
            args["source"] = os.path.abspath(source)
        else:
            args["source"] = source
            if source_format:
                args["source_format"] = source_format
        result = self._call("write_data", **args)
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "WriteData failed"))
        return result["data"]

    def mimetypes(self) -> List[str]:
        """List all supported mimetypes."""
        result = self._call("mimetypes")
        return result.get("mimetypes", [])

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _postprocess_cdxml(self, path: str):
        """Read a CDXML file written by ChemScript and inject ACS style."""
        try:
            text = Path(path).read_text(encoding="utf-8")
            text = _inject_acs_style(text)
            Path(path).write_text(text, encoding="utf-8")
        except Exception as e:
            print(f"Warning: CDXML post-processing failed: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI interface
# ---------------------------------------------------------------------------


def _cli_configure(args) -> int:
    """Auto-detect ChemDraw/ChemScript and save config."""
    cfg = _load_config()
    dll_info = None

    # --- Detect ChemScript DLLs ---
    # 1. Local bundled DLLs
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_dll_dir = os.path.join(script_dir, "chemscript_dlls")
    dll_info = _find_chemscript_dlls(local_dll_dir)
    if dll_info:
        print(f"  ChemScript DLL: {dll_info['managed_path']} (bundled)")

    # 2. Auto-detect via ChemDraw COM registry
    if not dll_info:
        root = _find_chemdraw_root()
        if root:
            print(f"  ChemDraw root:  {root}")
            dll_info = _find_chemscript_dlls(root)
            if dll_info:
                print(f"  Managed DLL:    {dll_info['managed_path']}")
                print(f"  Native DLL:     {dll_info['native_path']}")
                print(f"  Bitness:        {dll_info['bitness']}-bit")
        else:
            print("  ChemDraw:       not found in COM registry")

    if dll_info:
        cfg["dll_dir"] = dll_info["dll_dir"]
        cfg["assembly"] = dll_info["assembly"]
        cfg["bitness"] = dll_info["bitness"]
    else:
        print("  WARNING: ChemScript DLLs not found.")
        print("  ChemDraw with ChemScript must be installed.")

    # --- Detect Python for ChemScript ---
    bitness = dll_info["bitness"] if dll_info else None
    py = cfg.get("python32") or _find_python_for_chemscript(bitness)
    if py:
        cfg["python32"] = py
        print(f"  Python:         {py}")
    else:
        print("  WARNING: No suitable Python found for ChemScript.")
        if bitness == 32:
            print("  Run 'cdxml-doctor' for 32-bit Python setup instructions.")
        elif bitness == 64:
            print("  A 64-bit Python with pythonnet should work.")
        else:
            print("  Run 'cdxml-doctor' for setup instructions.")

    _save_config(cfg)
    print(f"\n  Config saved to: {CONFIG_PATH}")
    return 0


def _cli_ping(args, cs: ChemScriptBridge) -> int:
    """Test that the ChemScript bridge is working."""
    result = cs._call("ping")
    if result.get("ok"):
        print("ChemScript bridge OK: server is responding")
        return 0
    else:
        print(f"ChemScript bridge FAILED: {result.get('error', 'unknown')}", file=sys.stderr)
        return 1


def _cli_convert(args, cs: ChemScriptBridge) -> int:
    result = cs.convert_file(args.input, args.output)
    kind = result.get("type", "unknown")
    formula = result.get("formula", "?")
    print(f"Converted ({kind}): {formula}", file=sys.stderr)
    print(f"Written to {args.output}", file=sys.stderr)
    return 0


def _cli_name2struct(args, cs: ChemScriptBridge) -> int:
    output = args.output
    if output == "-":
        cdxml = cs.name_to_cdxml(args.name)
        print(cdxml)
    else:
        cdxml = cs.name_to_cdxml(args.name, output=output)
        print(f"Written to {output}", file=sys.stderr)
    return 0


def _cli_smiles2struct(args, cs: ChemScriptBridge) -> int:
    output = args.output
    if output == "-":
        cdxml = cs.smiles_to_cdxml(args.smiles)
        print(cdxml)
    else:
        cdxml = cs.smiles_to_cdxml(args.smiles, output=output)
        print(f"Written to {output}", file=sys.stderr)
    return 0


def _cli_cleanup(args, cs: ChemScriptBridge) -> int:
    output = args.output or args.input
    cs.cleanup(args.input, output=output)
    print(f"Cleaned up → {output}", file=sys.stderr)
    return 0


def _cli_info(args, cs: ChemScriptBridge) -> int:
    info = cs.get_info(args.source)
    if info.get("type") == "structure":
        print(f"Type:    structure")
        print(f"Name:    {info.get('name', '(unknown)')}")
        print(f"Formula: {info.get('formula', '?')}")
        print(f"SMILES:  {info.get('smiles', '?')}")
        if info.get("inchi"):
            print(f"InChI:   {info['inchi']}")
        print(f"Atoms:   {info.get('atom_count', '?')}")
        print(f"Bonds:   {info.get('bond_count', '?')}")
    elif info.get("type") == "reaction":
        print(f"Type:    reaction")
        print(f"Formula: {info.get('formula', '?')}")
        print(f"Reactants ({len(info.get('reactants', []))}):")
        for i, rct in enumerate(info.get("reactants", []), 1):
            name = rct.get("name") or "(unknown)"
            print(f"  {i}. {rct['formula']} - {name} [{rct['smiles']}]")
        print(f"Products ({len(info.get('products', []))}):")
        for i, prod in enumerate(info.get("products", []), 1):
            name = prod.get("name") or "(unknown)"
            print(f"  {i}. {prod['formula']} - {name} [{prod['smiles']}]")
    else:
        print(json.dumps(info, indent=2))
    return 0


def _cli_search(args, cs: ChemScriptBridge) -> int:
    if args.atom_map:
        result = cs.substructure_search(args.target, args.query)
        print(f"Contains substructure: {result['contains']}")
        if result["maps"]:
            for i, m in enumerate(result["maps"], 1):
                print(f"  Map {i}:")
                for k, v in m.items():
                    print(f"    {k} -> {v}")
    else:
        found = cs.contains_substructure(args.target, args.query)
        print(f"Contains substructure: {found}")
    return 0


def _cli_reaction(args, cs: ChemScriptBridge) -> int:
    info = cs.load_reaction(args.input, include_cdxml=args.cdxml)
    print(f"Reaction: {info['formula']}")
    print(f"Reactants ({len(info['reactants'])}):")
    for i, rct in enumerate(info["reactants"], 1):
        name = rct.get("name") or "(unknown)"
        print(f"  {i}. {rct['formula']} - {name} [{rct['smiles']}]")
    print(f"Products ({len(info['products'])}):")
    for i, prod in enumerate(info["products"], 1):
        name = prod.get("name") or "(unknown)"
        print(f"  {i}. {prod['formula']} - {name} [{prod['smiles']}]")
    if args.json:
        print(json.dumps(info, indent=2))
    return 0


def _cli_lcs(args, cs: ChemScriptBridge) -> int:
    result = cs.largest_common_substructure(args.mol1, args.mol2)
    print(f"Common atoms: {result.get('common_atom_count', 0)}")
    for entry in result.get("atom_map", []):
        print(f"  {entry['common']}: mol1={entry['mol1']}, mol2={entry['mol2']}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="ChemScript Bridge — access ChemDraw's chemical intelligence from Python.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
        Examples:
          %(prog)s convert input.cdx output.cdxml
          %(prog)s name2struct "morpholine" -o morpholine.cdxml
          %(prog)s smiles2struct "C1COCCN1" -o morpholine.cdxml
          %(prog)s cleanup messy.cdxml -o clean.cdxml
          %(prog)s info structure.cdx
          %(prog)s search --target target.cdx --query query.cdx
          %(prog)s reaction input.cdx --list
          %(prog)s lcs "C1(C)CCCC1CCO" "C1CCCC1C"
        """),
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # configure — no ChemScript needed
    sub.add_parser("configure", help="Auto-detect ChemDraw version and save config")

    # ping — test bridge connectivity
    sub.add_parser("ping", help="Test ChemScript bridge connectivity")

    # convert
    p = sub.add_parser("convert", help="Convert between chemical file formats")
    p.add_argument("input", help="Input file (CDX, CDXML, MOL, RXN, etc.)")
    p.add_argument("output", help="Output file (format from extension)")

    # name2struct
    p = sub.add_parser("name2struct", help="Chemical name → CDXML structure")
    p.add_argument("name", help="Chemical name (e.g. 'morpholine')")
    p.add_argument("-o", "--output", default="-", help="Output CDXML file (default: stdout)")

    # smiles2struct
    p = sub.add_parser("smiles2struct", help="SMILES → CDXML structure")
    p.add_argument("smiles", help="SMILES string")
    p.add_argument("-o", "--output", default="-", help="Output CDXML file (default: stdout)")

    # cleanup
    p = sub.add_parser("cleanup", help="Clean up structure coordinates")
    p.add_argument("input", help="Input structure file")
    p.add_argument("-o", "--output", default=None, help="Output file (default: overwrite input)")

    # info
    p = sub.add_parser("info", help="Get chemical info (name, formula, SMILES, etc.)")
    p.add_argument("source", help="Structure/reaction file or SMILES string")

    # search
    p = sub.add_parser("search", help="Substructure search")
    p.add_argument("--target", required=True, help="Target structure (file or SMILES)")
    p.add_argument("--query", required=True, help="Query substructure (file or SMILES)")
    p.add_argument("--atom-map", action="store_true", help="Show atom-by-atom mapping")

    # reaction
    p = sub.add_parser("reaction", help="Extract reaction components")
    p.add_argument("input", help="Reaction file (CDX, RXN) or reaction SMILES")
    p.add_argument("--list", action="store_true", dest="list_components",
                   help="List reactants and products")
    p.add_argument("--cdxml", action="store_true", help="Include CDXML for each component")
    p.add_argument("--json", action="store_true", help="Output full JSON")

    # lcs
    p = sub.add_parser("lcs", help="Largest common substructure")
    p.add_argument("mol1", help="First molecule (file or SMILES)")
    p.add_argument("mol2", help="Second molecule (file or SMILES)")

    args = parser.parse_args(argv)

    # 'configure' doesn't need a running ChemScript server
    if args.command == "configure":
        return _cli_configure(args)

    try:
        cs = ChemScriptBridge()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    try:
        dispatch = {
            "ping": _cli_ping,
            "convert": _cli_convert,
            "name2struct": _cli_name2struct,
            "smiles2struct": _cli_smiles2struct,
            "cleanup": _cli_cleanup,
            "info": _cli_info,
            "search": _cli_search,
            "reaction": _cli_reaction,
            "lcs": _cli_lcs,
        }
        handler = dispatch[args.command]
        return handler(args, cs)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    finally:
        cs.close()


if __name__ == "__main__":
    sys.exit(main())
