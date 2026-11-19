"""A caller may use input_path, output_path and output_dir where the choice is unambiguous."""

from cdxml_toolkit.mcp_runtime import tool_registry, tool_worker


def _names(tool):
    return tool_worker.common_path_names(tool_registry.build_registry()[tool].function)


def test_a_tool_with_one_required_file_argument_answers_to_input_path():
    assert _names("render_to_png") == {"input_path": "cdxml_path"}
    assert _names("extract_structures_from_document")["input_path"] == "path"
    assert _names("extract_structures_from_document")["output_dir"] == "out_dir"
    assert _names("predict_retrosynthesis").get("output_path") == "output_cdxml"


def test_nothing_is_offered_when_the_choice_is_not_unique_or_the_name_exists():
    assert "input_path" not in _names("embed_cdxml_in_office")  # a drawing and a document
    assert "input_path" not in _names("fill_office_template")
    assert _names("convert_cdx_cdxml") == {}  # already input_path and output_path
    assert _names("rdkit_workbench") == {}  # takes **kwargs


def test_the_alias_never_points_at_a_missing_or_duplicate_parameter():
    import inspect

    for name, spec in tool_registry.build_registry().items():
        parameters = inspect.signature(spec.function).parameters
        aliases = tool_worker.common_path_names(spec.function)
        assert set(aliases.values()) <= set(parameters), name
        assert not set(aliases) & set(parameters), name
        assert len(set(aliases.values())) == len(aliases), name
        assert not aliases.get("input_path", "").startswith("output"), name


def test_the_worker_applies_the_alias_and_keeps_an_explicit_argument():
    function = tool_registry.build_registry()["render_to_png"].function
    kwargs = {"input_path": "a.cdxml"}
    tool_worker._use_common_path_names(function, kwargs)
    assert kwargs == {"cdxml_path": "a.cdxml"}
    both = {"input_path": "a.cdxml", "cdxml_path": "b.cdxml"}
    tool_worker._use_common_path_names(function, both)
    assert both == {"input_path": "a.cdxml", "cdxml_path": "b.cdxml"}  # left for the binder to refuse
