"""ChemScript-compatible chemistry backend for macOS.

ChemScript, the .NET SDK behind :class:`ChemScriptBridge`, exists only on
Windows.  On macOS the same commands are answered in-process, with the reply
shapes of ``_chemscript_server.py`` so bridge callers do not change:

* ChemDraw for macOS (AppleScript) gives its own readings and edits:
  Struct=Name, Name=Struct, Clean Up, SMILES, formula, masses, elemental
  analysis and file conversion.
* OPSIN resolves names offline before ChemDraw is asked, because ChemDraw
  answers a name it cannot interpret with a modal alert.
* RDKit does graph work: substructure search, MCS, overlay and InChI.
"""

from __future__ import annotations

from functools import reduce
import os
from pathlib import Path
import re
import tempfile
import traceback
from typing import Any, Callable, Optional
import warnings
import weakref

from . import mac_automation

# Short alias -> mimetype (as in _chemscript_server.MIME_ALIASES).
MIME_ALIASES = {
    "cdxml": "text/xml",
    "cdx": "chemical/x-cdx",
    "smiles": "chemical/x-smiles",
    "smi": "chemical/x-smiles",
    "inchi": "chemical/x-inchi",
    "name": "chemical/x-name",
    "mol": "chemical/x-mdl-molfile",
    "molv3": "chemical/x-mdl-molfile-v3000",
    "rxn": "chemical/x-mdl-rxn",
    "rxnv3": "chemical/x-mdl-rxn-v3000",
    "cml": "chemical/x-cml",
}

# Mimetype -> the kind of data this backend reads or writes.
_KINDS = {
    "text/xml": "cdxml",
    "chemical/x-cdxml": "cdxml",
    "chemical/x-cdx": "cdx",
    "chemical/x-smiles": "smiles",
    "chemical/x-daylight-smiles": "smiles",
    "chemical/x-inchi": "inchi",
    "chemical/x-inchikey": "inchikey",
    "chemical/x-name": "name",
    "chemical/x-mdl-molfile": "mol",
    "chemical/x-mdl-molfile-v3000": "molv3",
    "chemical/x-mdl-sdfile": "mol",
    "chemical/x-mdl-rxn": "rxn",
    "chemical/x-mdl-rxn-v3000": "rxn",
    "chemical/x-cml": "cml",
}

# Files ChemDraw for macOS opens directly.
CHEMDRAW_INPUTS = {".cdx", ".cdxml", ".mol", ".sdf", ".sd", ".rxn", ".cml", ".skc", ".ct", ".rdf"}

# RDKit reads CDXML coordinates y-up, scaled so the document's BondLength is
# 1.5; molecules remember the points per RDKit unit to be written back.
_RDKIT_BOND_LENGTH = 1.5
_ACS_BOND_LENGTH = 14.4
_SCALE_PROP = "_cdxml_points_per_unit"
_BOND_LENGTH = re.compile(r'<CDXML\b[^>]*?\bBondLength="([0-9.]+)"', re.S)


def resolve_mime(fmt: str) -> str:
    if "/" in fmt:
        return fmt
    return MIME_ALIASES.get(fmt.lower().lstrip("."), fmt)


def _kind(fmt: str) -> str:
    try:
        return _KINDS[resolve_mime(fmt).lower()]
    except KeyError:
        raise ValueError(f"Unsupported format: {fmt}") from None


def opsin_name_to_smiles(name: str) -> Optional[str]:
    """Resolve a chemical name offline with OPSIN, or return None."""
    from ..resolve.jre_manager import ensure_java_on_path

    if not ensure_java_on_path(download=False):
        return None
    try:
        from py2opsin import py2opsin
    except ImportError:
        return None
    with tempfile.TemporaryDirectory(prefix="cdx-opsin-") as workspace, warnings.catch_warnings():
        warnings.simplefilter("ignore")
        smiles = py2opsin(name, tmp_fpath=os.path.join(workspace, "names.txt"))
    return smiles or None


def _atom_name(mol, index: int) -> str:
    return f"{mol.GetAtomWithIdx(index).GetSymbol()}{index + 1}"


def _split_reaction(smiles: str) -> tuple[list[str], list[str]]:
    parts = smiles.split(">")
    if len(parts) != 3:
        raise ValueError(f"Not a reaction: {smiles}")
    reactants, _agents, products = parts
    return [s for s in reactants.split(".") if s], [s for s in products.split(".") if s]


def _formula(smiles: str) -> Optional[str]:
    from rdkit import Chem
    from rdkit.Chem.rdMolDescriptors import CalcMolFormula

    mol = Chem.MolFromSmiles(smiles)
    return CalcMolFormula(mol) if mol is not None else None


def _canonical(smiles: str) -> str:
    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles)
    return Chem.MolToSmiles(mol) if mol is not None else smiles


def _with_coordinates(mol):
    from rdkit.Chem import rdDepictor

    if mol.GetNumConformers() == 0:
        rdDepictor.Compute2DCoords(mol)
    return mol


def _average_bond_length(mol) -> float:
    conformer = mol.GetConformer()
    lengths = [
        (conformer.GetAtomPosition(b.GetBeginAtomIdx()) - conformer.GetAtomPosition(b.GetEndAtomIdx())).Length()
        for b in mol.GetBonds()
    ]
    return sum(lengths) / len(lengths) if lengths else _RDKIT_BOND_LENGTH


def _scaled(mol, factor: float):
    from rdkit import Chem

    copy = Chem.Mol(mol)
    conformer = copy.GetConformer()
    for index in range(copy.GetNumAtoms()):
        position = conformer.GetAtomPosition(index)
        conformer.SetAtomPosition(index, (position.x * factor, position.y * factor, 0.0))
    return copy


def rdkit_to_cdxml(mol) -> str:
    """CDXML for an RDKit molecule, keeping its coordinates and atom order."""
    from rdkit import Chem

    from ..cdxml_builder import build_molecule_cdxml
    from ..image.structure_from_image import _rdkit_mol_to_atom_bond_dicts

    drawn = Chem.RWMol(_with_coordinates(Chem.Mol(mol)))
    try:
        Chem.Kekulize(drawn, clearAromaticFlags=True)
    except Exception:
        pass
    if mol.HasProp(_SCALE_PROP):
        scale = mol.GetDoubleProp(_SCALE_PROP)
    else:
        scale = _ACS_BOND_LENGTH / _average_bond_length(drawn)
    atoms, bonds = _rdkit_mol_to_atom_bond_dicts(drawn)
    for atom in atoms:
        atom["x"] = atom["x"] * scale
        atom["y"] = -atom["y"] * scale
    return build_molecule_cdxml(atoms, bonds)


class MacChemScript:
    """Answer ChemScript server commands with ChemDraw for macOS, OPSIN and RDKit."""

    def __init__(
        self,
        session: Optional[Any] = None,
        *,
        opsin: Optional[Callable[[str], Optional[str]]] = None,
    ):
        self.session = session or mac_automation.MacChemDrawSession(timeout_seconds=60)
        self._opsin = opsin or opsin_name_to_smiles
        self._rejected_names: dict[str, str] = {}
        self._names: dict[str, Optional[str]] = {}
        self._name_smiles: dict[str, Optional[str]] = {}
        self._workspace: Optional[Path] = None
        self._files = 0
        # Quit a ChemDraw this backend launched even when the bridge is never closed.
        self._release = weakref.finalize(self, self.session.close)

    def close(self) -> None:
        self._release()

    def call(self, cmd: str, args: dict) -> dict:
        handler = getattr(self, f"cmd_{cmd}", None) if re.fullmatch(r"[a-z_]+", str(cmd)) else None
        if handler is None:
            return {"ok": False, "error": f"Unknown command: {cmd}"}
        if not self._release.alive:
            self._release = weakref.finalize(self, self.session.close)
        with tempfile.TemporaryDirectory(prefix="cdx-chemscript-") as workspace:
            self._workspace = Path(workspace)
            try:
                return handler(dict(args))
            except mac_automation.MacAutomationError as exc:
                return {"ok": False, "error": str(exc), "error_code": exc.error_code}
            except Exception as exc:
                return {"ok": False, "error": str(exc), "traceback": traceback.format_exc()}
            finally:
                self._workspace = None

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _new_file(self, suffix: str) -> Path:
        self._files += 1
        return self._workspace / f"structure{self._files}{suffix}"

    def _write(self, suffix: str, text: str) -> Path:
        path = self._new_file(suffix)
        path.write_text(text, encoding="utf-8")
        return path

    @staticmethod
    def _detect(data: str) -> str:
        from rdkit import Chem, RDLogger

        text = data.lstrip()
        if text.startswith("<"):
            return "cml" if "<cml" in text[:200].lower() else "cdxml"
        if text.startswith("$RXN"):
            return "rxn"
        if "M  END" in text:
            return "mol"
        if text.startswith("InChI="):
            return "inchi"
        RDLogger.DisableLog("rdApp.*")
        try:
            if ">" in text or Chem.MolFromSmiles(text) is not None:
                return "smiles"
        finally:
            RDLogger.EnableLog("rdApp.*")
        return "name"

    def _stage(self, source: str, fmt: Optional[str] = None) -> Path:
        """A file ChemDraw can open holding ``source`` (a path or data)."""
        if os.path.isfile(source):
            path = Path(source)
            if path.suffix.lower() in CHEMDRAW_INPUTS:
                return path
            source = path.read_text(encoding="utf-8", errors="replace").strip()
        kind = _kind(fmt) if fmt else self._detect(source)
        if kind == "name":
            return self._name_file(source)
        if kind in ("smiles", "inchi"):
            return self._smiles_file(source if kind == "smiles" else self._inchi_smiles(source))
        suffix = {"cdxml": ".cdxml", "mol": ".mol", "molv3": ".mol", "rxn": ".rxn", "cml": ".cml"}.get(kind)
        if suffix is None:
            raise ValueError(f"Could not load: {source[:80]}")
        return self._write(suffix, source)

    @staticmethod
    def _inchi_smiles(inchi: str) -> str:
        from rdkit import Chem

        mol = Chem.MolFromInchi(inchi)
        if mol is None:
            raise ValueError(f"Could not parse InChI: {inchi}")
        return Chem.MolToSmiles(mol)

    def _smiles_file(self, smiles: str) -> Path:
        from rdkit import Chem
        from rdkit.Chem import AllChem, rdChemReactions, rdDepictor

        if ">" in smiles:
            reaction = AllChem.ReactionFromSmarts(smiles, useSmiles=True)
            if reaction is None:
                raise ValueError(f"Could not parse SMILES: {smiles}")
            for template in (*reaction.GetReactants(), *reaction.GetAgents(), *reaction.GetProducts()):
                rdDepictor.Compute2DCoords(template)
            return self._write(".rxn", rdChemReactions.ReactionToRxnBlock(reaction))
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError(f"Could not parse SMILES: {smiles}")
        rdDepictor.Compute2DCoords(mol)
        # Not a molfile: ChemDraw for macOS stalls opening molfiles wider than its page.
        return self._write(".cdxml", rdkit_to_cdxml(mol))

    def _resolve_name(self, name: str) -> Optional[str]:
        if name not in self._name_smiles:
            self._name_smiles[name] = self._opsin(name)
        return self._name_smiles[name]

    def _name_file(self, name: str) -> Path:
        smiles = self._resolve_name(name)
        if smiles:
            return self._smiles_file(smiles)
        if name in self._rejected_names:
            # Each rejection costs ChemDraw an alert and a restart; name probing repeats names.
            raise ValueError(f"Could not resolve name: {name} ({self._rejected_names[name]})")
        destination = self._new_file(".cdxml")
        try:
            self.session.name_to_structure(name, destination)
        except mac_automation.MacAutomationError as exc:
            if exc.error_code not in ("name_not_recognized", "chemdraw_in_use"):
                raise
            if exc.error_code == "name_not_recognized":
                self._rejected_names[name] = str(exc)
            raise ValueError(f"Could not resolve name: {name} ({exc})") from exc
        return destination

    def _read(self, path: Path, *, names: bool = False, saves: tuple = (), clean: Optional[str] = None) -> dict:
        """ChemDraw's reading of ``path``; optionally clean, name and save copies."""
        steps = ["select-all"]
        if clean:
            steps += ["menu", "Structure", clean]
        steps += ["query"]
        named = None
        if names:
            named = self._new_file(".cdxml")
            steps += ["menu", "Structure", "Convert Structure to Name", "save", str(named), "ChemDraw XML"]
        for destination in saves:
            destination = Path(destination).expanduser().resolve()
            steps += ["save", str(destination), mac_automation.save_type_for(destination)]
        answers = self.session.run_steps(path, steps)
        smiles, formula, weight, exact, analysis = (answers + [""] * 5)[:5]
        reading = {"smiles": smiles, "formula": formula, "weight": mac_automation.query_number(weight),
                   "exact_mass": mac_automation.query_number(exact), "elemental_analysis": analysis or None}
        if named is not None:
            reading["names"] = mac_automation.new_captions(path, named)
        return reading

    def _rdkit(self, source: str, fmt: Optional[str] = None):
        """RDKit molecule for ``source``, keeping file coordinates and atom order."""
        from rdkit import Chem

        if os.path.isfile(source):
            path = Path(source)
            suffix = path.suffix.lower()
            if suffix in (".mol", ".sdf", ".sd"):
                return Chem.MolFromMolFile(str(path))
            if suffix == ".cdxml":
                return self._from_cdxml(path.read_text(encoding="utf-8", errors="replace"))
            if suffix in CHEMDRAW_INPUTS:
                molfile = self._new_file(".mol")
                self._read(path, saves=(molfile,))
                return Chem.MolFromMolFile(str(molfile))
            source = path.read_text(encoding="utf-8", errors="replace").strip()
        kind = _kind(fmt) if fmt else self._detect(source)
        if kind == "smiles":
            return Chem.MolFromSmiles(source)
        if kind == "inchi":
            return Chem.MolFromInchi(source)
        if kind in ("mol", "molv3"):
            return Chem.MolFromMolBlock(source)
        if kind == "cdxml":
            return self._from_cdxml(source)
        if kind == "name":
            smiles = self._resolve_name(source)
            if smiles:
                return Chem.MolFromSmiles(smiles)
            return Chem.MolFromSmiles(self._read(self._name_file(source))["smiles"])
        raise ValueError(f"Could not load: {source[:80]}")

    @staticmethod
    def _from_cdxml(text: str):
        from rdkit import Chem

        match = _BOND_LENGTH.search(text)
        if match:
            bond_length = float(match.group(1))
        else:
            bond_length = _ACS_BOND_LENGTH
            text = re.sub(r"<CDXML\b", f'<CDXML BondLength="{bond_length}"', text, count=1)
        molecules = [mol for mol in Chem.MolsFromCDXML(text) if mol is not None]
        if not molecules:
            return None
        combined = reduce(Chem.CombineMols, molecules)
        combined.SetDoubleProp(_SCALE_PROP, bond_length / _RDKIT_BOND_LENGTH)
        return combined

    def _structure_names(self, path: Path) -> list:
        """ChemDraw's names for ``path``, asked twice when the first answer is empty.

        ChemDraw for macOS occasionally saves the document before Convert Structure to
        Name has added its caption, so one empty answer is not yet "cannot be named".
        """
        return self._read(path, names=True)["names"] or self._read(path, names=True)["names"]

    def _name_of_smiles(self, smiles: str) -> Optional[str]:
        if smiles not in self._names:
            names = self._structure_names(self._smiles_file(smiles))
            self._names[smiles] = "; ".join(names) or None
        return self._names[smiles]

    def _component(self, smiles: str, include_cdxml: bool = False) -> dict:
        info = {"smiles": _canonical(smiles), "formula": _formula(smiles), "name": self._name_of_smiles(smiles)}
        if include_cdxml:
            output = self._new_file(".cdxml")
            self._read(self._smiles_file(smiles), clean="Clean Up Structure", saves=(output,))
            info["cdxml"] = output.read_text(encoding="utf-8")
        return info

    def _cdxml(self, path: Path, output: Optional[str], *, clean: bool) -> dict:
        target = self._new_file(".cdxml")
        saves = [target]
        if output:
            saves.append(output)
        cleanup = None
        if clean:
            cleanup = "Clean Up Reaction" if path.suffix.lower() == ".rxn" else "Clean Up Structure"
        reading = self._read(path, clean=cleanup, saves=tuple(saves))
        return {"cdxml": target.read_text(encoding="utf-8"), **reading}

    # ------------------------------------------------------------------
    # Commands (same names, arguments and replies as _chemscript_server)
    # ------------------------------------------------------------------

    def cmd_ping(self, args: dict) -> dict:
        return {"ok": True, "message": "ChemScript-compatible macOS backend ready"}

    def cmd_convert(self, args: dict) -> dict:
        source, output = Path(args["input"]), Path(args["output"])
        if not source.is_file():
            return {"ok": False, "error": f"Could not load: {source}"}
        staged = self._stage(str(source))
        if output.suffix.lower() in (".smi", ".smiles"):
            reading = self._read(staged)
            output.write_text(reading["smiles"] + "\n", encoding="utf-8")
        else:
            reading = self._read(staged, saves=(output,))
        if not reading["smiles"]:
            return {"ok": False, "error": f"Could not load: {source}"}
        kind = "reaction" if ">" in reading["smiles"] else "structure"
        return {"ok": True, "type": kind, "formula": reading["formula"]}

    def cmd_name_to_cdxml(self, args: dict) -> dict:
        name = args["name"]
        try:
            staged = self._name_file(name)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        result = self._cdxml(staged, args.get("output"), clean=True)
        return {"ok": True, "cdxml": result["cdxml"], "smiles": result["smiles"], "formula": result["formula"]}

    def cmd_smiles_to_cdxml(self, args: dict) -> dict:
        smiles = args["smiles"]
        try:
            staged = self._smiles_file(smiles)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        result = self._cdxml(staged, args.get("output"), clean=True)
        return {"ok": True, "cdxml": result["cdxml"], "smiles": smiles, "formula": result["formula"]}

    def cmd_cleanup(self, args: dict) -> dict:
        source = args["input"]
        output = args.get("output") or source
        reading = self._read(self._stage(source), clean="Clean Up Structure", saves=(output,))
        if not reading["smiles"]:
            return {"ok": False, "error": f"Could not load: {source}"}
        return {"ok": True, "formula": reading["formula"]}

    def cmd_get_info(self, args: dict) -> dict:
        from rdkit import Chem

        source = args["source"]
        reading = self._read(self._stage(source, args.get("format")), names=True)
        smiles = reading["smiles"]
        if not smiles:
            return {"ok": False, "error": f"Could not load: {source}"}
        if ">" in smiles:
            reactants, products = _split_reaction(smiles)
            return {
                "ok": True,
                "type": "reaction",
                "formula": reading["formula"],
                "reactants": [self._component(item) for item in reactants],
                "products": [self._component(item) for item in products],
            }
        mol = Chem.MolFromSmiles(smiles)
        return {
            "ok": True,
            "type": "structure",
            "formula": reading["formula"],
            "smiles": smiles,
            "name": "; ".join(reading["names"]) or None,
            "inchi": (Chem.MolToInchi(mol) or None) if mol is not None else None,
            "atom_count": mol.GetNumAtoms() if mol is not None else None,
            "bond_count": mol.GetNumBonds() if mol is not None else None,
        }

    def cmd_get_name(self, args: dict) -> dict:
        source, fmt = args["source"], args.get("format")
        if not os.path.isfile(source) and (fmt and _kind(fmt) == "smiles" or not fmt and self._detect(source) == "smiles"):
            name = self._name_of_smiles(source)
        else:
            name = "; ".join(self._structure_names(self._stage(source, fmt))) or None
        if not name:
            return {"ok": False, "error": "ChemDraw could not name this structure"}
        return {"ok": True, "name": name}

    def cmd_get_formula(self, args: dict) -> dict:
        source = args["source"]
        reading = self._read(self._stage(source, args.get("format")))
        if not reading["formula"]:
            return {"ok": False, "error": f"Could not load: {source}"}
        return {"ok": True, "formula": reading["formula"]}

    def cmd_get_properties(self, args: dict) -> dict:
        """Formula, weight, exact mass and elemental analysis from one ChemDraw reading."""
        source = args["source"]
        reading = self._read(self._stage(source, args.get("format")))
        if not reading["formula"]:
            return {"ok": False, "error": f"Could not load: {source}"}
        return {"ok": True, **{key: reading[key] for key in ("formula", "weight", "exact_mass", "elemental_analysis")}}

    def _pair(self, args: dict, first: str, second: str):
        one = self._rdkit(args[first], args.get(f"{first}_format"))
        two = self._rdkit(args[second], args.get(f"{second}_format"))
        if one is None:
            raise ValueError(f"Could not load {first}: {args[first]}")
        if two is None:
            raise ValueError(f"Could not load {second}: {args[second]}")
        return one, two

    def cmd_contains_substructure(self, args: dict) -> dict:
        target, query = self._pair(args, "target", "query")
        return {"ok": True, "contains": bool(target.HasSubstructMatch(query))}

    def cmd_substructure_search(self, args: dict) -> dict:
        target, query = self._pair(args, "target", "query")
        maps = [
            {_atom_name(query, q): _atom_name(target, t) for q, t in enumerate(match)}
            for match in target.GetSubstructMatches(query, uniquify=False, maxMatches=1000)
        ]
        return {"ok": True, "contains": bool(maps), "maps": maps}

    def cmd_write_data(self, args: dict) -> dict:
        from rdkit import Chem

        source, source_format = args["source"], args.get("source_format")
        kind = _kind(args["target_format"])
        is_file = os.path.isfile(source)
        if kind == "name":
            result = self.cmd_get_name({"source": source, "format": source_format})
            if not result["ok"]:
                return result
            return {"ok": True, "data": result["name"]}
        if kind in ("cdxml", "rxn") or (is_file and kind in ("smiles", "mol")):
            staged = self._stage(source, source_format)
            if kind == "smiles":
                data = self._read(staged)["smiles"]
            else:
                output = self._new_file({"cdxml": ".cdxml", "rxn": ".rxn", "mol": ".mol"}[kind])
                self._read(staged, clean=None if is_file else "Clean Up Structure", saves=(output,))
                data = output.read_text(encoding="utf-8")
            return {"ok": True, "data": data}
        mol = self._rdkit(source, source_format)
        if mol is None:
            return {"ok": False, "error": f"Could not load: {source}"}
        if kind == "smiles":
            data = Chem.MolToSmiles(mol)
        elif kind == "inchi":
            data = Chem.MolToInchi(mol)
        elif kind == "inchikey":
            data = Chem.MolToInchiKey(mol)
        elif kind == "mol":
            data = Chem.MolToMolBlock(_with_coordinates(mol))
        elif kind == "molv3":
            data = Chem.MolToV3KMolBlock(_with_coordinates(mol))
        else:
            raise ValueError(f"Unsupported target format: {args['target_format']}")
        return {"ok": True, "data": data}

    def cmd_load_reaction(self, args: dict) -> dict:
        from rdkit.Chem import AllChem, rdChemReactions

        source, output = args["source"], args.get("output")
        formula = None
        if os.path.isfile(source):
            reading = self._read(self._stage(source), saves=(output,) if output else ())
            smiles, formula = reading["smiles"], reading["formula"]
        elif source.lstrip().startswith("$RXN"):
            smiles = rdChemReactions.ReactionToSmiles(rdChemReactions.ReactionFromRxnBlock(source))
        else:
            smiles = source
        if ">" not in smiles:
            return {"ok": False, "error": f"Could not load reaction: {source}"}
        reactants, products = _split_reaction(smiles)
        include = bool(args.get("include_cdxml"))
        result = {
            "ok": True,
            "formula": formula,
            "reactants": [self._component(item, include) for item in reactants],
            "products": [self._component(item, include) for item in products],
        }
        if not formula:
            result["formula"] = " >> ".join(
                " + ".join(item["formula"] or "?" for item in result[side]) for side in ("reactants", "products")
            )
        if output and not os.path.isfile(source):
            reaction = AllChem.ReactionFromSmarts(smiles, useSmiles=True)
            Path(output).write_text(rdChemReactions.ReactionToRxnBlock(reaction), encoding="utf-8")
        return result

    def cmd_largest_common_substructure(self, args: dict) -> dict:
        from rdkit import Chem
        from rdkit.Chem import rdFMCS

        first, second = self._pair(args, "mol1", "mol2")
        found = rdFMCS.FindMCS([first, second], timeout=30, ringMatchesRingOnly=True)
        if not found.numAtoms:
            return {"ok": True, "atom_map": []}
        common = Chem.MolFromSmarts(found.smartsString)
        one, two = first.GetSubstructMatch(common), second.GetSubstructMatch(common)
        mapping = [
            {"common": _atom_name(common, k), "mol1": _atom_name(first, one[k]), "mol2": _atom_name(second, two[k])}
            for k in range(min(len(one), len(two)))
        ]
        # The common part as mol1 holds it; Kekulé form, since a ring cut open cannot stay aromatic.
        kekule = Chem.Mol(first)
        Chem.Kekulize(kekule, clearAromaticFlags=True)
        bonds = [first.GetBondBetweenAtoms(one[b.GetBeginAtomIdx()], one[b.GetEndAtomIdx()]).GetIdx()
                 for b in common.GetBonds()]
        common_smiles = Chem.MolFragmentToSmiles(kekule, atomsToUse=list(one), bondsToUse=bonds or None,
                                                 kekuleSmiles=True) if one else None
        return {"ok": True, "atom_map": mapping, "common_atom_count": len(mapping), "common_smiles": common_smiles}

    def cmd_overlay(self, args: dict) -> dict:
        from rdkit import Chem
        from rdkit.Chem import rdDepictor, rdFMCS

        mol, reference = self._pair(args, "source", "target")
        _with_coordinates(reference)
        found = rdFMCS.FindMCS([mol, reference], timeout=30, ringMatchesRingOnly=True)
        success = False
        aligned = Chem.Mol(mol)
        if found.numAtoms:
            # Depict at RDKit's bond length, then return to the reference's scale.
            factor = _average_bond_length(reference) / _RDKIT_BOND_LENGTH
            pattern = Chem.MolFromSmarts(found.smartsString)
            try:
                rdDepictor.GenerateDepictionMatching2DStructure(
                    aligned, _scaled(reference, 1 / factor), refPatt=pattern
                )
                aligned = _scaled(aligned, factor)
                if reference.HasProp(_SCALE_PROP):
                    aligned.SetDoubleProp(_SCALE_PROP, reference.GetDoubleProp(_SCALE_PROP))
                success = True
            except ValueError:
                aligned = Chem.Mol(mol)
        return {"ok": True, "aligned_cdxml": rdkit_to_cdxml(aligned), "success": success}

    def cmd_substructure_align(self, args: dict) -> dict:
        from rdkit import Chem

        target, query = self._pair(args, "target", "query")
        _with_coordinates(target)
        _with_coordinates(query)
        return {
            "ok": True,
            "contains": bool(target.HasSubstructMatch(query)),
            "query_mol": Chem.MolToMolBlock(query),
            "target_mol": Chem.MolToMolBlock(target),
            "target_cdxml": rdkit_to_cdxml(target),
            "query_cdxml": rdkit_to_cdxml(query),
        }

    def cmd_atoms(self, args: dict) -> dict:
        """Atom names (as in substructure maps) and bonds of one structure."""
        mol = self._rdkit(args["source"], args.get("format"))
        if mol is None:
            return {"ok": False, "error": f"Could not load: {args['source']}"}
        return {
            "ok": True,
            "atoms": [_atom_name(mol, index) for index in range(mol.GetNumAtoms())],
            "bonds": [
                [_atom_name(mol, bond.GetBeginAtomIdx()), _atom_name(mol, bond.GetEndAtomIdx()),
                 bond.GetBondTypeAsDouble()]
                for bond in mol.GetBonds()
            ],
        }

    def cmd_mimetypes(self, args: dict) -> dict:
        return {"ok": True, "mimetypes": sorted(_KINDS)}


_shared: Optional[MacChemScript] = None


def shared() -> MacChemScript:
    """The process's MacChemScript, so every ChemScriptBridge drives one ChemDraw.

    A second session would find the first one's ChemDraw running, take it for
    the user's and refuse name conversion (``chemdraw_in_use``).
    """
    global _shared
    if _shared is None:
        _shared = MacChemScript()
    return _shared
