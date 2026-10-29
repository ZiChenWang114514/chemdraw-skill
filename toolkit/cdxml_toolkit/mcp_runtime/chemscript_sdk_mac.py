"""ChemScript SDK programs on macOS, without the .NET SDK.

ChemScript exists only for Windows.  This module emulates the part of its
object model that the toolkit's own ChemScript server uses (``StructureData``,
``ReactionData``, ``LargestCommonSubstructure`` and their atom maps), backed by
the same ChemDraw for macOS, OPSIN and RDKit backend as
:mod:`cdxml_toolkit.chemdraw.chemscript_mac`.  ``execute_chemscript_sdk``
programs written against those members run unchanged; any other type or
member is refused with a clear error, and ``inspect_chemscript_sdk`` lists
exactly what is emulated.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
import tempfile
from typing import Any, Optional

NAMESPACE = "CambridgeSoft.ChemScript16"
ASSEMBLY = f"{NAMESPACE} (macOS emulation: ChemDraw for macOS, OPSIN, RDKit)"

# File extensions read as text, by mimetype.
_TEXT_FORMATS = {
    ".cdxml": "text/xml",
    ".xml": "text/xml",
    ".mol": "chemical/x-mdl-molfile",
    ".sdf": "chemical/x-mdl-molfile",
    ".sd": "chemical/x-mdl-molfile",
    ".rxn": "chemical/x-mdl-rxn",
    ".cml": "chemical/x-cml",
    ".smi": "chemical/x-smiles",
    ".smiles": "chemical/x-smiles",
    ".inchi": "chemical/x-inchi",
}
_CDXML = ("text/xml", "chemical/x-cdxml")


class _Named:
    def __init__(self, full_name: str):
        self.FullName = full_name

    def __str__(self) -> str:
        return self.FullName


class _Type(_Named):
    """Stand-in for System.Type, enough for the program runtime and serializer."""

    IsEnum = False
    IsValueType = False

    def __init__(self, cls: type, interfaces: tuple[str, ...] = ()):
        super().__init__(f"{NAMESPACE}.{cls.__name__}")
        self.Name = cls.__name__
        self.cls = cls
        self._interfaces = interfaces

    def GetInterfaces(self):
        return [_Named(name) for name in self._interfaces]


def _as_content(data: str, mimetype: Optional[str], *, reaction: bool = False):
    """Data that the backend can only read as content, never as a file path.

    The backend reads a string naming an existing file as that file, but
    ChemScript's ``LoadData`` takes data only; files go through ``LoadFile`` and
    ``ReadFile``, which need ``allow_file_io``.  Data that happens to name a file
    (a SMILES such as ``CCO`` beside a file of that name) is handed over as a
    molfile or RXN block instead; anything else naming a file is not data.
    Returns ``(data, mimetype)``, or ``None`` when the data cannot be loaded.
    """
    if not os.path.lexists(data):
        return data, mimetype
    from rdkit import Chem, RDLogger
    from rdkit.Chem import AllChem, rdChemReactions

    RDLogger.DisableLog("rdApp.*")
    try:
        if reaction:
            if ">" in data:
                rxn = AllChem.ReactionFromSmarts(data, useSmiles=True)
                return rdChemReactions.ReactionToRxnBlock(rxn), "chemical/x-mdl-rxn"
            return None
        mol = Chem.MolFromInchi(data) if data.startswith("InChI=") else Chem.MolFromSmiles(data)
    except Exception:
        return None
    finally:
        RDLogger.EnableLog("rdApp.*")
    if mol is None:
        return None
    AllChem.Compute2DCoords(mol)
    return Chem.MolToMolBlock(mol), "chemical/x-mdl-molfile"


def _backend():
    from cdxml_toolkit.chemdraw import chemscript_mac

    return chemscript_mac.shared()


def _call(command: str, **args) -> dict:
    result = _backend().call(command, {key: value for key, value in args.items() if value is not None})
    if not result.get("ok"):
        raise RuntimeError(result.get("error") or f"ChemScript emulation command {command} failed")
    return result


class _Emulated:
    def GetType(self):
        return TYPES[type(self).__name__]


class Atom(_Emulated):
    def __init__(self, name: str):
        self.Name = name

    def __eq__(self, other):
        return isinstance(other, Atom) and other.Name == self.Name

    def __hash__(self):
        return hash(self.Name)

    def __str__(self) -> str:
        return self.Name


class Bond(_Emulated):
    def __init__(self, first: Atom, second: Atom, order: float):
        self.Atom1, self.Atom2, self.Order = first, second, order

    def __str__(self) -> str:
        return f"{self.Atom1.Name}-{self.Atom2.Name}"


class AtomMap(_Emulated):
    """Atom-to-atom map, keyed like a .NET dictionary (``Keys``, ``map[atom]``)."""

    def __init__(self, pairs: dict[str, str]):
        self._map = {Atom(key): Atom(value) for key, value in pairs.items()}

    @property
    def Keys(self):
        return list(self._map)

    @property
    def Count(self):
        return len(self._map)

    def __getitem__(self, atom):
        return self._map[atom if isinstance(atom, Atom) else Atom(str(atom))]

    def __iter__(self):
        return iter(self._map)

    def __len__(self):
        return len(self._map)


class StructureData(_Emulated):
    def __init__(self):
        self._data: Optional[str] = None
        self._format: Optional[str] = None
        self._properties: Optional[dict] = None

    # -- loading -----------------------------------------------------------
    @staticmethod
    def _valid(data: str, mimetype: Optional[str]) -> bool:
        try:
            _call("write_data", source=data, source_format=mimetype, target_format="chemical/x-smiles")
        except Exception:
            return False
        return True

    @classmethod
    def LoadData(cls, data: str, mimetype: Optional[str] = None):
        if not isinstance(data, str) or not data.strip():
            return None
        content = _as_content(data, mimetype)
        if content is None or not cls._valid(*content):
            return None
        data, mimetype = content
        structure = cls()
        structure._data, structure._format = data, mimetype
        return structure

    @classmethod
    def LoadFile(cls, path: str, mimetype: Optional[str] = None):
        structure = cls()
        return structure if structure.ReadFile(path, mimetype) else None

    def ReadFile(self, path: str, mimetype: Optional[str] = None) -> bool:
        source = Path(path).expanduser()
        if not source.is_file():
            return False
        text_format = mimetype or _TEXT_FORMATS.get(source.suffix.lower())
        if text_format:
            data = source.read_text(encoding="utf-8", errors="replace")
        else:
            # Binary ChemDraw files (CDX) are read by ChemDraw into CDXML.
            try:
                data = _call("write_data", source=str(source), target_format="text/xml")["data"]
            except Exception:
                return False
            text_format = "text/xml"
        content = _as_content(data, text_format)
        if content is None or not self._valid(*content):
            return False
        self._data, self._format = content
        self._properties = None
        return True

    @staticmethod
    def MimeTypes():
        return _call("mimetypes")["mimetypes"]

    def _source(self) -> dict:
        if self._data is None:
            raise RuntimeError("StructureData is empty; load data first")
        return {"source": self._data, "format": self._format}

    # -- readings ----------------------------------------------------------
    def _property(self, key: str):
        # One ChemDraw reading answers every property, so a program asking for all of them
        # starts ChemDraw once per structure.
        if self._properties is None:
            self._properties = _call("get_properties", **self._source())
        return self._properties[key]

    def Formula(self) -> str:
        return self._property("formula")

    @property
    def Weight(self) -> Optional[float]:
        return self._property("weight")

    @property
    def ExactMass(self) -> Optional[float]:
        return self._property("exact_mass")

    @property
    def ElementalAnalysis(self) -> Optional[str]:
        return self._property("elemental_analysis")

    @property
    def Inchi(self) -> str:
        return self.WriteData("chemical/x-inchi").strip()

    @property
    def TotalCharge(self) -> int:
        from rdkit import Chem

        mol = Chem.MolFromSmiles(self.WriteData("chemical/x-smiles"))
        if mol is None:
            raise RuntimeError("ChemDraw's SMILES of this structure could not be read")
        return Chem.GetFormalCharge(mol)

    def ChemicalName(self) -> str:
        return _call("get_name", **self._source())["name"]

    @property
    def Atoms(self):
        return [Atom(name) for name in _call("atoms", **self._source())["atoms"]]

    @property
    def Bonds(self):
        bonds = _call("atoms", **self._source())["bonds"]
        return [Bond(Atom(first), Atom(second), order) for first, second, order in bonds]

    def WriteData(self, mimetype: str = "text/xml") -> str:
        source = self._source()
        if mimetype in _CDXML and self._format in _CDXML:
            return self._data
        return _call("write_data", source=source["source"], source_format=source["format"],
                     target_format=mimetype)["data"]

    def WriteFile(self, path: str, mimetype: Optional[str] = None) -> bool:
        destination = Path(path).expanduser().resolve()
        text_format = mimetype or _TEXT_FORMATS.get(destination.suffix.lower())
        if text_format:
            destination.write_text(self.WriteData(text_format), encoding="utf-8")
            return True
        # Binary and picture formats (CDX, PNG, SVG, ...) come from ChemDraw.
        with tempfile.TemporaryDirectory(prefix="cdx-sdk-") as workspace:
            staged = Path(workspace) / "structure.cdxml"
            staged.write_text(self.WriteData("text/xml"), encoding="utf-8")
            _call("convert", input=str(staged), output=str(destination))
        return True

    # -- edits -------------------------------------------------------------
    def CleanupStructure(self) -> bool:
        with tempfile.TemporaryDirectory(prefix="cdx-sdk-") as workspace:
            staged = Path(workspace) / "structure.cdxml"
            cleaned = Path(workspace) / "cleaned.cdxml"
            staged.write_text(self.WriteData("text/xml"), encoding="utf-8")
            _call("cleanup", input=str(staged), output=str(cleaned))
            self._data, self._format = cleaned.read_text(encoding="utf-8"), "text/xml"
            self._properties = None
        return True

    def Overlay(self, target: "StructureData") -> bool:
        result = _call("overlay", source=self._data, source_format=self._format,
                       target=target._data, target_format=target._format)
        if result["success"]:
            self._data, self._format = result["aligned_cdxml"], "text/xml"
            self._properties = None
        return bool(result["success"])

    # -- searches ----------------------------------------------------------
    def ContainsSubstructure(self, query: "StructureData") -> bool:
        return bool(_call("contains_substructure", target=self._data, target_format=self._format,
                          query=query._data, query_format=query._format)["contains"])

    def AtomByAtomSearch(self, target: "StructureData"):
        maps = _call("substructure_search", target=target._data, target_format=target._format,
                     query=self._data, query_format=self._format)["maps"]
        return [AtomMap(mapping) for mapping in maps]

    def __str__(self) -> str:
        return f"StructureData({self._format or 'empty'})"


class ReactionData(_Emulated):
    def __init__(self):
        self._data: Optional[str] = None
        self._format: Optional[str] = None
        self._reading: Optional[dict] = None

    @classmethod
    def LoadData(cls, data: str, mimetype: Optional[str] = None):
        if not isinstance(data, str) or not data.strip():
            return None
        content = _as_content(data, mimetype, reaction=True)
        if content is None:
            return None
        data, mimetype = content
        reaction = cls()
        try:
            if data.lstrip().startswith("<"):
                # CDXML reactions are read by ChemDraw from a file.
                with tempfile.TemporaryDirectory(prefix="cdx-sdk-") as workspace:
                    staged = Path(workspace) / "reaction.cdxml"
                    staged.write_text(data, encoding="utf-8")
                    reaction._reading = _call("load_reaction", source=str(staged))
            else:
                reaction._reading = _call("load_reaction", source=data)
        except Exception:
            return None
        reaction._data, reaction._format = data, mimetype
        return reaction

    @classmethod
    def LoadFile(cls, path: str, mimetype: Optional[str] = None):
        if not os.path.isfile(path):
            return None
        reaction = cls()
        try:
            reaction._reading = _call("load_reaction", source=str(Path(path).resolve()))
        except Exception:
            return None
        reaction._data, reaction._format = str(Path(path).resolve()), None
        return reaction

    def _components(self, side: str):
        return [StructureData.LoadData(item["smiles"], "chemical/x-smiles") for item in self._reading[side]]

    @property
    def Reactants(self):
        return self._components("reactants")

    @property
    def Products(self):
        return self._components("products")

    def Formula(self) -> str:
        return self._reading["formula"]

    def WriteData(self, mimetype: str = "chemical/x-mdl-rxn") -> str:
        if mimetype in ("chemical/x-smiles", "chemical/x-daylight-smiles"):
            return ".".join(i["smiles"] for i in self._reading["reactants"]) + ">>" + \
                ".".join(i["smiles"] for i in self._reading["products"])
        return _call("write_data", source=self._data, source_format=self._format,
                     target_format=mimetype)["data"]

    def WriteFile(self, path: str, mimetype: Optional[str] = None) -> bool:
        destination = Path(path).expanduser().resolve()
        text_format = mimetype or _TEXT_FORMATS.get(destination.suffix.lower())
        if not text_format:
            raise RuntimeError(f"The macOS emulation writes reactions as text formats, not {destination.suffix}")
        destination.write_text(self.WriteData(text_format), encoding="utf-8")
        return True

    def __str__(self) -> str:
        return "ReactionData"


class LargestCommonSubstructure(_Emulated):
    def __init__(self, mapping: list[dict], common_smiles: Optional[str] = None):
        self._mapping = mapping
        self._common_smiles = common_smiles

    @classmethod
    def Compute(cls, first: StructureData, second: StructureData):
        result = _call("largest_common_substructure", mol1=first._data, mol1_format=first._format,
                       mol2=second._data, mol2_format=second._format)
        return cls(result["atom_map"], result.get("common_smiles")) if result["atom_map"] else None

    def CommonSubstructure(self) -> Optional[StructureData]:
        return StructureData.LoadData(self._common_smiles, "chemical/x-smiles") if self._common_smiles else None

    def AtomMapM1(self) -> AtomMap:
        return AtomMap({item["common"]: item["mol1"] for item in self._mapping})

    def AtomMapM2(self) -> AtomMap:
        return AtomMap({item["common"]: item["mol2"] for item in self._mapping})

    def __str__(self) -> str:
        return f"LargestCommonSubstructure({len(self._mapping)} atoms)"


_DICTIONARY = ("System.Collections.IDictionary", "System.Collections.IEnumerable")
TYPES = {
    cls.__name__: _Type(cls, _DICTIONARY if cls is AtomMap else ())
    for cls in (StructureData, ReactionData, LargestCommonSubstructure, AtomMap, Atom, Bond)
}

# Emulated public members: (type, kind, name, signature, static, operations).
_MEMBERS = [
    ("StructureData", "constructor", ".ctor", "Void .ctor()", False, ("construct",)),
    ("StructureData", "method", "LoadData", "StructureData LoadData(String data, String mimetype = null)", True, ("call_static",)),
    ("StructureData", "method", "LoadFile", "StructureData LoadFile(String path, String mimetype = null)", True, ("call_static",)),
    ("StructureData", "method", "MimeTypes", "String[] MimeTypes()", True, ("call_static",)),
    ("StructureData", "method", "ReadFile", "Boolean ReadFile(String path, String mimetype = null)", False, ("call",)),
    ("StructureData", "method", "Formula", "String Formula()", False, ("call",)),
    ("StructureData", "method", "ChemicalName", "String ChemicalName()", False, ("call",)),
    ("StructureData", "method", "WriteData", "String WriteData(String mimetype)", False, ("call",)),
    ("StructureData", "method", "WriteFile", "Boolean WriteFile(String path, String mimetype = null)", False, ("call",)),
    ("StructureData", "method", "CleanupStructure", "Boolean CleanupStructure()", False, ("call",)),
    ("StructureData", "method", "Overlay", "Boolean Overlay(StructureData target)", False, ("call",)),
    ("StructureData", "method", "ContainsSubstructure", "Boolean ContainsSubstructure(StructureData query)", False, ("call",)),
    ("StructureData", "method", "AtomByAtomSearch", "AtomMap[] AtomByAtomSearch(StructureData target)", False, ("call",)),
    ("StructureData", "property", "Weight", "Double Weight", False, ("get",)),
    ("StructureData", "property", "ExactMass", "Double ExactMass", False, ("get",)),
    ("StructureData", "property", "ElementalAnalysis", "String ElementalAnalysis", False, ("get",)),
    ("StructureData", "property", "Inchi", "String Inchi", False, ("get",)),
    ("StructureData", "property", "TotalCharge", "Int32 TotalCharge", False, ("get",)),
    ("StructureData", "property", "Atoms", "Atom[] Atoms", False, ("get",)),
    ("StructureData", "property", "Bonds", "Bond[] Bonds", False, ("get",)),
    ("ReactionData", "method", "LoadData", "ReactionData LoadData(String data, String mimetype = null)", True, ("call_static",)),
    ("ReactionData", "method", "LoadFile", "ReactionData LoadFile(String path, String mimetype = null)", True, ("call_static",)),
    ("ReactionData", "method", "Formula", "String Formula()", False, ("call",)),
    ("ReactionData", "method", "WriteData", "String WriteData(String mimetype)", False, ("call",)),
    ("ReactionData", "method", "WriteFile", "Boolean WriteFile(String path, String mimetype = null)", False, ("call",)),
    ("ReactionData", "property", "Reactants", "StructureData[] Reactants", False, ("get",)),
    ("ReactionData", "property", "Products", "StructureData[] Products", False, ("get",)),
    ("LargestCommonSubstructure", "method", "Compute",
     "LargestCommonSubstructure Compute(StructureData m1, StructureData m2)", True, ("call_static",)),
    ("LargestCommonSubstructure", "method", "CommonSubstructure", "StructureData CommonSubstructure()", False, ("call",)),
    ("LargestCommonSubstructure", "method", "AtomMapM1", "AtomMap AtomMapM1()", False, ("call",)),
    ("LargestCommonSubstructure", "method", "AtomMapM2", "AtomMap AtomMapM2()", False, ("call",)),
    ("AtomMap", "property", "Keys", "Atom[] Keys", False, ("get",)),
    ("AtomMap", "property", "Count", "Int32 Count", False, ("get",)),
    ("Atom", "property", "Name", "String Name", False, ("get",)),
    ("Bond", "property", "Atom1", "Atom Atom1", False, ("get",)),
    ("Bond", "property", "Atom2", "Atom Atom2", False, ("get",)),
    ("Bond", "property", "Order", "Double Order", False, ("get",)),
]
_ALLOWED = {(owner, name, operation) for owner, _k, name, _s, _st, ops in _MEMBERS for operation in ops}


class MacSdkRuntime:
    """The program runtime interface of ``ChemScriptRuntime``, for the emulation."""

    assembly = _Named(ASSEMBLY)

    def reflection_type(self, name: str) -> _Type:
        candidate = str(name).strip()
        for prefix in (f"{NAMESPACE}.", "CambridgeSoft.ChemScript."):
            if candidate.startswith(prefix):
                candidate = candidate[len(prefix):]
        if candidate not in TYPES:
            raise ValueError(f"ChemScript type {name} is not available in the macOS emulation")
        return TYPES[candidate]

    def python_type(self, name: str):
        return self.reflection_type(name).cls

    def resolve_argument(self, value: Any, aliases: dict[str, Any], *, unsafe: bool):
        if isinstance(value, list):
            return [self.resolve_argument(item, aliases, unsafe=unsafe) for item in value]
        if not isinstance(value, dict):
            return value
        if set(value) == {"$ref"}:
            if value["$ref"] not in aliases:
                raise ValueError(f"Unknown object alias: {value['$ref']}")
            return aliases[value["$ref"]]
        if set(value) == {"$bytes_base64"}:
            try:
                return base64.b64decode(value["$bytes_base64"], validate=True)
            except (ValueError, TypeError) as exc:
                raise ValueError("Invalid base64 byte argument") from exc
        if len(value) == 1 and next(iter(value)).startswith("$"):
            raise ValueError(f"{next(iter(value))} arguments are not available in the macOS emulation")
        return {key: self.resolve_argument(item, aliases, unsafe=unsafe) for key, item in value.items()}

    def member_is_interop(self, reflection_type, member: str) -> bool:
        return False

    def check_member(self, owner: Any, member: str, operation: str) -> None:
        """Refuse anything that is not an emulated public member (no Python internals)."""
        if isinstance(owner, _Type):
            name = owner.Name
        elif isinstance(owner, _Emulated):
            name = type(owner).__name__
        else:
            raise ValueError(f"{operation} {member} is not available on {type(owner).__name__} values")
        if (name, member, operation) not in _ALLOWED:
            raise ValueError(f"{name}.{member} ({operation}) is not available in the macOS emulation; "
                             "inspect_chemscript_sdk lists the emulated members")

    def catalog(self) -> tuple[list[dict], list[dict]]:
        types = [{"name": item.FullName, "kind": "class"} for item in TYPES.values()]
        members = [
            {
                "type": f"{NAMESPACE}.{owner}",
                "kind": kind,
                "name": name,
                "signature": signature,
                "static": static,
                "classification": "sdk_api",
                "execution_op": operations[0] if kind != "property" else list(operations),
                "reason": None,
            }
            for owner, kind, name, signature, static, operations in _MEMBERS
        ]
        return types, members
