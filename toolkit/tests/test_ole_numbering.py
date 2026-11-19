"""New embedded objects never reuse a number the document already uses."""

import zipfile

from cdxml_toolkit.office import doc_from_template


def test_numbering_continues_after_what_the_package_holds(tmp_path):
    source = tmp_path / "deck.pptx"
    with zipfile.ZipFile(source, "w") as out:
        out.writestr("ppt/embeddings/oleObject3.bin", b"x")
        out.writestr("ppt/media/olePreview2.emf", b"x")
        out.writestr("ppt/slides/_rels/slide1.xml.rels",
                     '<Relationships><Relationship Id="rIdOle7" Target="a"/>'
                     '<Relationship Id="rIdOleImg4" Target="b"/></Relationships>')
        out.writestr("ppt/slides/slide1.xml", "<p/>")
    assert doc_from_template._highest_ole_index(source) == 7


def test_a_package_without_objects_starts_at_one(tmp_path):
    source = tmp_path / "plain.docx"
    with zipfile.ZipFile(source, "w") as out:
        out.writestr("word/document.xml", "<w/>")
        out.writestr("word/_rels/document.xml.rels", '<Relationships><Relationship Id="rId1" Target="a"/></Relationships>')
    assert doc_from_template._highest_ole_index(source) == 0


def test_both_fillers_start_from_the_highest_number_in_use():
    import inspect

    for filler in (doc_from_template.pass2_pptx, doc_from_template.pass2_docx):
        body = inspect.getsource(filler)
        assert "ole_counter = first_free = _highest_ole_index(input_path)" in body
        assert "ole_counter = 0" not in body
