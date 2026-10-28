"""chemdraw_com_call: static program checks against the COM catalog, then execution on fakes."""

from types import SimpleNamespace

import pytest

from cdxml_toolkit.mcp_runtime import com_call
from cdxml_toolkit.mcp_runtime.tool_registry import build_registry

OPEN_DOCUMENT = [
    {"op": "get", "member": "Documents", "as": "docs"},
    {"op": "call", "target": "docs", "member": "Add", "as": "doc"},
    {"op": "get", "target": "doc", "member": "Objects", "as": "objs"},
    {"op": "get", "target": "objs", "member": "MolecularWeight"},
]


def refusal(program, **options):
    with pytest.raises(ValueError) as caught:
        com_call.validate_program(program, **options)
    return str(caught.value)


def test_a_valid_program_is_normalised_with_the_type_of_every_alias():
    steps = com_call.validate_program(OPEN_DOCUMENT)
    assert [step["target"] for step in steps] == ["app", "docs", "doc", "objs"]
    assert steps[1]["result_type"] == "IChemDrawDocument"
    assert steps[2]["result_type"] == "IChemDrawObjects"


def test_unknown_members_and_wrong_access_are_refused():
    assert "IChemDrawDocuments has no member Foo" in refusal(
        [{"op": "get", "member": "Documents", "as": "d"}, {"op": "get", "target": "d", "member": "Foo"}])
    assert "not writable" in refusal(
        [{"op": "get", "member": "Documents", "as": "d"}, {"op": "set", "target": "d", "member": "Count", "value": 1}])
    assert "is a property" in refusal([{"op": "call", "member": "Visible"}])
    assert "is a method" in refusal([{"op": "get", "member": "UpdateRunLevel"}])
    assert com_call.validate_program([{"op": "set", "member": "Visible", "value": False}])


def test_argument_counts_follow_the_catalog():
    docs = {"op": "get", "member": "Documents", "as": "d"}
    assert "takes at most 0" in refusal([docs, {"op": "call", "target": "d", "member": "Add", "args": [1]}])
    assert "needs at least 1" in refusal(
        [docs, {"op": "call", "target": "d", "member": "Open", "args": []}], allow_file_io=True)


@pytest.mark.parametrize(
    "member, target_chain",
    [("Quit", []), ("Print", ["doc"]), ("PrintOut", ["doc"]), ("Paste", ["doc"]), ("Copy", ["objs"]), ("Cut", ["objs"])],
)
def test_members_with_side_effects_outside_the_document_are_blocked(member, target_chain):
    program = OPEN_DOCUMENT[:3] + [{"op": "call", "target": target_chain[0] if target_chain else "app", "member": member}]
    assert "blocked" in refusal(program, allow_file_io=True, allow_overwrite=True)


def test_menus_and_preference_changes_are_blocked():
    assert "blocked" in refusal([{"op": "get", "member": "MenuBars"}])
    assert "blocked" in refusal(
        [{"op": "get", "member": "Preferences", "as": "p"}, {"op": "set", "target": "p", "member": "PNGResolution", "value": 72}])
    assert com_call.validate_program(
        [{"op": "get", "member": "Preferences", "as": "p"}, {"op": "get", "target": "p", "member": "PNGResolution"}])


def test_file_members_need_the_opt_in_and_overwriting_members_need_two():
    open_step = [{"op": "get", "member": "Documents", "as": "d"},
                 {"op": "call", "target": "d", "member": "Open", "args": ["C:/x/in.cdxml"], "as": "doc"}]
    assert "allow_file_io" in refusal(open_step)
    assert com_call.validate_program(open_step, allow_file_io=True)
    save_as = open_step + [{"op": "call", "target": "doc", "member": "SaveAs", "args": ["C:/x/out.png"]}]
    assert "allow_file_io" in refusal(save_as)
    save = open_step + [{"op": "call", "target": "doc", "member": "Save"}]
    assert "allow_overwrite" in refusal(save, allow_file_io=True)
    assert com_call.validate_program(save, allow_file_io=True, allow_overwrite=True)
    close_true = open_step + [{"op": "call", "target": "doc", "member": "Close", "args": [True]}]
    assert "allow_overwrite" in refusal(close_true, allow_file_io=True)
    close_false = open_step + [{"op": "call", "target": "doc", "member": "Close", "args": [False]}]
    assert com_call.validate_program(close_false, allow_file_io=True)


def test_allow_overwrite_needs_allow_file_io():
    with pytest.raises(ValueError, match="allow_overwrite requires allow_file_io"):
        com_call.chemdraw_com_call(OPEN_DOCUMENT, allow_overwrite=True)


def test_aliases_are_checked():
    assert "reserved" in refusal([{"op": "get", "member": "Documents", "as": "app"}])
    assert "already used" in refusal([{"op": "get", "member": "Documents", "as": "a"}, {"op": "get", "member": "Documents", "as": "a"}])
    assert "unknown alias" in refusal([{"op": "get", "target": "nope", "member": "Count"}])
    assert "alias" in refusal([{"op": "get", "member": "Documents", "as": "bad name"}])


def test_item_results_get_the_element_type_of_their_collection():
    steps = com_call.validate_program([
        {"op": "get", "member": "Documents", "as": "docs"},
        {"op": "call", "target": "docs", "member": "Item", "args": [1], "as": "first"},
        {"op": "get", "target": "first", "member": "Objects"},
    ])
    assert steps[1]["result_type"] == "IChemDrawDocument"
    assert "has no member Nonsense" in refusal([
        {"op": "get", "member": "Documents", "as": "docs"},
        {"op": "call", "target": "docs", "member": "Item", "args": [1], "as": "first"},
        {"op": "get", "target": "first", "member": "Nonsense"},
    ])


def test_constants_are_resolved_from_the_catalog_enumerations():
    steps = com_call.validate_program([
        {"op": "get", "member": "Documents", "as": "d"},
        {"op": "call", "target": "d", "member": "Add", "as": "doc"},
        {"op": "get", "target": "doc", "member": "Objects", "as": "o"},
        {"op": "call", "target": "o", "member": "Scale", "args": [1.0]},
        {"op": "set", "target": "doc", "member": "Magnification", "value": {"constant": "kCDFormatPNG"}},
    ])
    assert isinstance(steps[-1]["value"], int)
    assert "unknown constant" in refusal([
        {"op": "set", "member": "Visible", "value": {"constant": "kNothing"}}])


def test_iterate_needs_a_collection_and_known_members():
    docs = {"op": "get", "member": "Documents", "as": "docs"}
    ok = com_call.validate_program([docs, {"op": "iterate", "target": "docs", "members": ["FullName"]}])
    assert ok[1]["element_type"] == "IChemDrawDocument"
    assert "not a collection" in refusal([{"op": "iterate", "target": "app", "members": ["name"]}])
    assert "has no member" in refusal([docs, {"op": "iterate", "target": "docs", "members": ["Nope"]}])
    assert "blocked" in refusal([docs, {"op": "iterate", "target": "docs", "members": ["Print"]}])


def test_program_shape_limits():
    assert "non-empty list" in refusal([])
    assert "at most" in refusal([{"op": "get", "member": "Documents"}] * (com_call.MAX_PROGRAM_STEPS + 1))
    assert "must be an object" in refusal(["get"])
    assert "unsupported operation" in refusal([{"op": "exec", "member": "x"}])
    assert "JSON" in refusal([{"op": "get", "member": object()}])


# ------------------------------------------------------------------ execution on fakes


class FakeDocument:
    def __init__(self, calls, directory=None):
        self.calls = calls
        self.directory = directory
        self.Objects = SimpleNamespace(MolecularWeight=94.11, Count=2, Formula="C6H6O",
                                       Atoms=FakeCollection([SimpleNamespace(Charge=0, ElementNumber=6),
                                                             SimpleNamespace(Charge=-1, ElementNumber=8)]))
        self.FullName = "C:/fake/doc.cdxml"

    def Close(self, *args):
        self.calls.append(("Close", args))

    def SaveAs(self, filename, *rest):
        self.calls.append(("SaveAs", filename))
        open(filename, "wb").write(b"saved")


class FakeCollection:
    def __init__(self, items):
        self.items = items
        self.Count = len(items)

    def Item(self, index):
        return self.items[index - 1]


class FakeApplication:
    def __init__(self, calls, open_documents=0):
        self.calls = calls
        self.Visible = True
        self.documents = []
        self.Documents = SimpleNamespace(
            Count=open_documents, Add=self._add, Open=self._open, Item=lambda index: self.documents[index - 1])
        self.name = "ChemDraw"

    def _add(self):
        document = FakeDocument(self.calls)
        self.documents.append(document)
        return document

    def _open(self, filename, *rest):
        self.calls.append(("Open", filename))
        return self._add()

    def Quit(self):
        self.calls.append(("Quit", ()))


@pytest.fixture
def fake(monkeypatch):
    calls = []
    application = FakeApplication(calls)

    class Session:
        def __enter__(self):
            return application, True

        def __exit__(self, *exc):
            if self._owned:
                application.Quit()

        _owned = True

    monkeypatch.setattr(com_call, "_open_application", lambda: Session())
    monkeypatch.setattr(com_call, "_windows", lambda: True)
    return SimpleNamespace(calls=calls, application=application)


def test_values_are_returned_and_objects_are_summarised(fake):
    result = com_call.chemdraw_com_call(OPEN_DOCUMENT)
    assert result["ok"] is True
    values = [item["value"] for item in result["outputs"]["results"]]
    assert values[0] == {"object": "IChemDrawDocuments"}
    assert values[1] == {"object": "IChemDrawDocument"}
    assert values[3] == 94.11
    assert result["metadata"]["network_used"] is False


def test_iterate_reads_the_listed_members_and_truncates(fake):
    program = OPEN_DOCUMENT[:3] + [
        {"op": "get", "target": "objs", "member": "Atoms", "as": "atoms"},
        {"op": "iterate", "target": "atoms", "members": ["Charge", "ElementNumber"]},
    ]
    full = com_call.chemdraw_com_call(program)["outputs"]["results"][-1]["value"]
    assert full == {"count": 2, "items": [{"index": 1, "Charge": 0, "ElementNumber": 6},
                                          {"index": 2, "Charge": -1, "ElementNumber": 8}], "truncated": False}
    short = com_call.chemdraw_com_call(program, max_items=1)["outputs"]["results"][-1]["value"]
    assert len(short["items"]) == 1 and short["truncated"] is True


def test_documents_the_program_created_are_closed_without_saving_and_the_application_quits(fake):
    com_call.chemdraw_com_call(OPEN_DOCUMENT)
    assert ("Close", (False,)) in fake.calls and fake.calls[-1][0] == "Quit"


def test_save_as_refuses_an_existing_target_and_writes_a_new_one(fake, tmp_path):
    source = tmp_path / "in.cdxml"
    source.write_text("<CDXML/>", encoding="utf-8")
    target = tmp_path / "out.png"
    program = [
        {"op": "get", "member": "Documents", "as": "d"},
        {"op": "call", "target": "d", "member": "Open", "args": [str(source)], "as": "doc"},
        {"op": "call", "target": "doc", "member": "SaveAs", "args": [str(target)]},
    ]
    result = com_call.chemdraw_com_call(program, allow_file_io=True)
    assert target.read_bytes() == b"saved"
    assert [item["path"] for item in result["metadata"]["artifacts"]] == [str(target)]
    with pytest.raises(FileExistsError):
        com_call.chemdraw_com_call(program, allow_file_io=True)
    assert target.read_bytes() == b"saved"


def test_open_needs_an_existing_file_and_save_as_needs_a_known_format(fake, tmp_path):
    missing = [{"op": "get", "member": "Documents", "as": "d"},
               {"op": "call", "target": "d", "member": "Open", "args": [str(tmp_path / "no.cdxml")]}]
    with pytest.raises(FileNotFoundError):
        com_call.chemdraw_com_call(missing, allow_file_io=True)
    odd = [{"op": "get", "member": "Documents", "as": "d"},
           {"op": "call", "target": "d", "member": "Add", "as": "doc"},
           {"op": "call", "target": "doc", "member": "SaveAs", "args": [str(tmp_path / "x.exe")]}]
    with pytest.raises(ValueError, match="format"):
        com_call.chemdraw_com_call(odd, allow_file_io=True)


def test_other_platforms_report_chemdraw_as_unavailable(monkeypatch):
    monkeypatch.setattr(com_call, "_windows", lambda: False)
    with pytest.raises(com_call.ComCallError) as caught:
        com_call.chemdraw_com_call(OPEN_DOCUMENT)
    assert caught.value.error_code == "chemdraw_unavailable"


def test_registered_as_a_native_tool_with_its_own_timeout():
    registry = build_registry()
    spec = registry["chemdraw_com_call"]
    assert spec.resource_class == "chemdraw_com" and spec.timeout_seconds == 240
    assert "chemdraw_com_call" not in build_registry("core")


def test_a_failed_quit_after_a_call_is_logged(monkeypatch, caplog):
    from contextlib import nullcontext
    from cdxml_toolkit.mcp_runtime import native_renderer

    class Application:
        Documents = SimpleNamespace(Count=0)
        Visible = True

        def Quit(self):
            raise RuntimeError("the RPC server is unavailable")

    monkeypatch.setattr(native_renderer, "_com_apartment", nullcontext)
    monkeypatch.setattr(native_renderer, "_acquire_application", lambda: (Application(), True))
    with caplog.at_level("WARNING", logger=com_call.__name__):
        with com_call._open_application() as (_, owned):
            assert owned is True
    assert [r.levelname for r in caplog.records] == ["WARNING"]
    assert "RuntimeError" in caplog.text and "RPC server" not in caplog.text
