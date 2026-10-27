"""Parse, select, edit and serialize a CDXML document without losing anything."""

from __future__ import annotations

from functools import lru_cache
import math
from pathlib import Path
import re
from typing import Any, Iterable, Optional
import xml.etree.ElementTree as ET

# Attributes that hold the id of another object: (element, attribute) -> single id or list of ids.
# Taken from the catalog; zero means "no object" in an id list.
REFERENCES = {
    ("b", "B"): False,
    ("b", "E"): False,
    ("n", "BondOrdering"): True,
    ("bracketedgroup", "BracketedObjectIDs"): True,
    ("bracketattachment", "GraphicID"): False,
    ("graphic", "SupersededBy"): False,
    ("chemicalproperty", "ChemicalPropertyDisplayID"): False,
}

_STEP = re.compile(r"^(?P<tag>\*|[A-Za-z_][\w.-]*)?(?:#(?P<id>\d+))?(?P<filters>(?:\[[^\]=\[]+=[^\]\[]*\])*)$")
_FILTER = re.compile(r"\[([^\]=\[]+)=([^\]\[]*)\]")
_ENCODING = re.compile(rb"""^\s*<\?xml[^>]*encoding\s*=\s*["']([A-Za-z0-9._-]+)["']""")


@lru_cache(maxsize=1)
def catalog_index() -> dict[str, dict[str, dict[str, Any]]]:
    """Catalog elements as ``{element: {attribute: {kind, values?}}}``."""
    from cdxml_toolkit.catalog import classify

    index: dict[str, dict[str, dict[str, Any]]] = {}
    for element in classify.load_catalog("cdxml")["elements"]:
        index[element["name"]] = {
            attribute["name"]: {key: value for key, value in attribute.items() if key in ("kind", "values")}
            for attribute in element.get("attributes", [])
        }
    return index


def _decode(data: bytes) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8")
    match = _ENCODING.match(data[:400])
    encoding = match.group(1).decode("ascii") if match else "utf-8"
    return data.decode(encoding)


def _is_element(node: ET.Element) -> bool:
    return isinstance(node.tag, str)


def _text(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        return " ".join(_text(item) for item in value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _number(value: str) -> bool:
    try:
        return math.isfinite(float(value))
    except ValueError:
        return False


class Document:
    """A parsed CDXML file; ``prologue`` is the text before the root element."""

    def __init__(self, root: ET.Element, prologue: str = "", encoding: str = "utf-8") -> None:
        self.root = root
        self.prologue = prologue
        self.encoding = encoding

    # ------------------------------------------------------------------ reading
    def elements(self) -> Iterable[ET.Element]:
        return (node for node in self.root.iter() if _is_element(node))

    def parent_map(self) -> dict[int, ET.Element]:
        """``{id(child): parent}`` for the whole tree; rebuild it after an edit."""
        return {id(child): node for node in self.elements() for child in node}

    def parent_of(self, element: ET.Element, parents: Optional[dict[int, ET.Element]] = None) -> Optional[ET.Element]:
        return (parents if parents is not None else self.parent_map()).get(id(element))

    def ids(self) -> set[str]:
        return {node.get("id") for node in self.elements() if node.get("id") is not None}

    def select(self, selector: str) -> list[ET.Element]:
        """Elements matching ``step > step ...``; a step is ``tag#id[Attr=value]...``.

        The first step matches anywhere in the document, later steps match direct children.
        ``*`` matches any tag.
        """
        if not isinstance(selector, str) or not selector.strip():
            raise ValueError("selector must be a non-empty string such as 'fragment > n[Element=8]'")
        steps = []
        for part in selector.split(">"):
            part = part.strip()
            match = _STEP.match(part) if part else None
            if match is None or not any((match["tag"], match["id"], match["filters"])):
                raise ValueError(f"Invalid selector step {part!r} in {selector!r}; use tag#id[Attr=value]")
            filters = [(name.strip(), value.strip().strip("\"'")) for name, value in _FILTER.findall(match["filters"])]
            steps.append((match["tag"], match["id"], filters))

        def matches(node: ET.Element, step) -> bool:
            tag, identifier, filters = step
            if tag not in (None, "*") and node.tag != tag:
                return False
            if identifier is not None and node.get("id") != identifier:
                return False
            return all(node.get(name) == value for name, value in filters)

        found = [node for node in self.elements() if matches(node, steps[0])]
        for step in steps[1:]:
            found = [child for node in found for child in node if _is_element(child) and matches(child, step)]
        unique: list[ET.Element] = []
        for node in found:
            if not any(node is seen for seen in unique):
                unique.append(node)
        return unique

    def path_of(self, element: ET.Element, parents: Optional[dict[int, ET.Element]] = None) -> str:
        parents = parents if parents is not None else self.parent_map()
        parts = []
        node: Optional[ET.Element] = element
        while node is not None:
            parts.append(node.tag + (f"#{node.get('id')}" if node.get("id") else ""))
            node = parents.get(id(node))
        return "/".join(reversed(parts))

    def describe(self, element: ET.Element, parents: Optional[dict[int, ET.Element]] = None) -> dict[str, Any]:
        parents = parents if parents is not None else self.parent_map()
        parent = self.parent_of(element, parents)
        entry: dict[str, Any] = {
            "tag": element.tag,
            "id": element.get("id"),
            "path": self.path_of(element, parents),
            "parent": None if parent is None else {"tag": parent.tag, "id": parent.get("id")},
            "attributes": dict(element.attrib),
            "children": sum(1 for child in element if _is_element(child)),
        }
        text = (element.text or "").strip()
        if text:
            entry["text"] = text
        return entry

    # ----------------------------------------------------------------- checking
    def check(self) -> list[dict[str, Any]]:
        """Structural problems: duplicate ids and references to objects that do not exist."""
        issues: list[dict[str, Any]] = []
        seen: dict[str, ET.Element] = {}
        for node in self.elements():
            identifier = node.get("id")
            if identifier is None:
                continue
            if identifier in seen:
                issues.append({"code": "duplicate_id", "id": identifier, "tag": node.tag})
            seen[identifier] = node
        for node in self.elements():
            for attribute, is_list in ((attr, REFERENCES[(node.tag, attr)]) for attr in node.attrib if (node.tag, attr) in REFERENCES):
                for target in self._targets(node.get(attribute), is_list):
                    if target not in seen:
                        issues.append({"code": "dangling_reference", "tag": node.tag, "id": node.get("id"),
                                       "attribute": attribute, "target": target})
        return issues

    @staticmethod
    def _targets(value: Optional[str], is_list: bool) -> list[str]:
        tokens = (value or "").split() if is_list else [(value or "").strip()]
        return [token for token in tokens if token and token != "0"]

    def _referrers(self, subtree: set[int], ids: set[str]) -> list[dict[str, Any]]:
        found = []
        for node in self.elements():
            if id(node) in subtree:
                continue
            for attribute in node.attrib:
                if (node.tag, attribute) in REFERENCES:
                    hit = set(self._targets(node.get(attribute), REFERENCES[(node.tag, attribute)])) & ids
                    if hit:
                        found.append({"tag": node.tag, "id": node.get("id"), "attribute": attribute, "targets": sorted(hit)})
        return found

    # ------------------------------------------------------------------ editing
    @staticmethod
    def _validate(tag: str, name: str, value: str, *, present: bool, allow_unknown: bool) -> None:
        known = catalog_index().get(tag, {})
        if name not in known:
            if not (present or allow_unknown):
                raise ValueError(
                    f"{name} is not an attribute of <{tag}> in the ChemDraw catalog "
                    "(pass allow_unknown to set it anyway)"
                )
            return
        kind = known[name]["kind"]
        tokens = value.split()
        if kind in ("integer", "number") and not (len(tokens) == 1 and _number(tokens[0])):
            raise ValueError(f"{name}={value!r} is not a valid {kind} value for <{tag}>")
        if kind == "numbers" and not (tokens and all(_number(token) for token in tokens)):
            raise ValueError(f"{name}={value!r} is not a valid list of numbers for <{tag}>")

    def set_properties(self, element: ET.Element, props: dict[str, Any], *, allow_unknown: bool = False) -> dict[str, tuple]:
        """Set, replace or (with ``None``) remove attributes; returns ``{name: (old, new)}``."""
        updates: dict[str, Optional[str]] = {}
        for name, value in props.items():
            if name == "id":
                raise ValueError("id cannot be changed or removed; delete the element and add a new one")
            if value is None:
                updates[name] = None
                continue
            text = _text(value)
            self._validate(element.tag, name, text, present=name in element.attrib, allow_unknown=allow_unknown)
            updates[name] = text
        changes: dict[str, tuple] = {}
        for name, text in updates.items():
            old = element.attrib.get(name)
            if old == text:
                continue
            if text is None:
                del element.attrib[name]
            else:
                element.set(name, text)
            changes[name] = (old, text)
        return changes

    def next_id(self) -> int:
        numbers = [int(identifier) for identifier in self.ids() if identifier.isdigit()]
        return max(numbers, default=0) + 1

    def add(
        self,
        parent: ET.Element,
        tag: str,
        props: Optional[dict[str, Any]] = None,
        *,
        children: Optional[list[dict[str, Any]]] = None,
        text: Optional[str] = None,
        allow_unknown: bool = False,
    ) -> ET.Element:
        """Append a new element (and nested ``children``) to ``parent``; ids are assigned."""
        index = catalog_index()
        if tag not in index and not allow_unknown:
            raise ValueError(f"<{tag}> is not a CDXML element in the ChemDraw catalog (pass allow_unknown to add it anyway)")
        props = dict(props or {})
        if "id" in props:
            if _text(props["id"]) in self.ids():
                raise ValueError(f"id {_text(props['id'])} is already used")
        elif "id" in index.get(tag, {}):
            props["id"] = self.next_id()
        element = ET.SubElement(parent, tag)
        try:
            for name, value in props.items():
                if value is None:
                    continue
                rendered = _text(value)
                self._validate(tag, name, rendered, present=False, allow_unknown=allow_unknown or name == "id")
                element.set(name, rendered)
            if text is not None:
                element.text = text
            for child in children or []:
                self.add(element, child["tag"], child.get("props"), children=child.get("children"),
                         text=child.get("text"), allow_unknown=allow_unknown)
        except Exception:
            parent.remove(element)
            raise
        return element

    def delete(self, element: ET.Element) -> int:
        """Remove ``element`` and its subtree; refuse the root and objects other objects point at."""
        if element is self.root:
            raise ValueError("The root element cannot be deleted")
        parent = self.parent_of(element)
        if parent is None:
            raise ValueError("Element is not part of this document")
        subtree = [node for node in element.iter() if _is_element(node)]
        ids = {node.get("id") for node in subtree if node.get("id")}
        referrers = self._referrers({id(node) for node in subtree}, ids)
        if referrers:
            raise ValueError(f"Refusing to delete; the objects are still referenced by {referrers[:5]}")
        parent.remove(element)
        return len(subtree)

    # ------------------------------------------------------------------ writing
    def dumps(self) -> str:
        body = ET.tostring(self.root, encoding="unicode")
        prologue = self.prologue
        if prologue and not prologue.endswith("\n"):
            prologue += "\n"
        return prologue + body + "\n"

    def dump_bytes(self) -> bytes:
        return self.dumps().encode(self.encoding, errors="xmlcharrefreplace")


def parse(source: str | bytes) -> Document:
    """Parse CDXML text or bytes; the root must be ``CDXML``."""
    text = _decode(source) if isinstance(source, bytes) else source
    declared = _ENCODING.match(text[:400].encode("ascii", errors="replace"))
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True))
    try:
        parser.feed(source)
        root = parser.close()
    except ET.ParseError as exc:
        raise ValueError(f"Not well-formed XML: {exc}") from exc
    if root.tag != "CDXML":
        raise ValueError(f"Not a CDXML document: the root element is <{root.tag}>, expected <CDXML>")
    start = re.search(r"<CDXML\b", text)
    prologue = text[: start.start()] if start else ""
    encoding = declared.group(1).decode("ascii") if declared else "utf-8"
    return Document(root, prologue.lstrip("﻿"), encoding)


def load(path: str | Path) -> Document:
    return parse(Path(path).read_bytes())
