"""OLE display size of embedded ChemDraw objects (root, page-sized and missing BoundingBoxes)."""
from __future__ import annotations

from cdxml_toolkit.office.ole_embedder import content_size_emu, get_cdxml_content_size

EMU = 12700


def _write(tmp_path, body, root_attrs=""):
    path = tmp_path / "figure.cdxml"
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<CDXML BondLength="14.4"{root_attrs}><page id="1">{body}</page></CDXML>\n',
        encoding="utf-8",
    )
    return path


def test_root_bounding_box_is_used_when_present(tmp_path):
    path = _write(tmp_path, '<fragment id="2"><n id="3" p="0 0"/></fragment>',
                  ' BoundingBox="10 20 110 70"')
    assert get_cdxml_content_size(path, scale=1.0) == (100 * EMU, 50 * EMU)


def test_reversed_rectangle_corners_do_not_give_negative_size(tmp_path):
    # ChemDraw stores rectangles as "right bottom left top"; two boxes side by side used to
    # yield a negative height and made batch embedding fail.
    body = ('<graphic id="2" BoundingBox="96 107 64 91" GraphicType="Rectangle"/>'
            '<graphic id="3" BoundingBox="341 107 309 91" GraphicType="Rectangle"/>')
    width, height = get_cdxml_content_size(_write(tmp_path, body), scale=1.0)
    assert (width, height) == ((341 - 64) * EMU, (107 - 91) * EMU)


def test_atoms_text_and_arrows_without_bounding_boxes_are_measured(tmp_path):
    body = ('<fragment id="2"><n id="3" p="20 40"/><n id="4" p="60 80"/></fragment>'
            '<t id="5" p="100 30"><s>A</s></t>'
            '<arrow id="6" Head3D="200 50 0" Tail3D="120 50 0"/>')
    width, height = get_cdxml_content_size(_write(tmp_path, body), scale=1.0)
    assert width == (200 - 20) * EMU and height == (80 - 30) * EMU


def test_size_is_always_positive_for_generated_drawings(tmp_path):
    body = '<graphic id="2" BoundingBox="96 107 64 91" GraphicType="Rectangle"/>'
    width, height = get_cdxml_content_size(_write(tmp_path, body))
    assert width > 0 and height > 0


def test_page_sized_root_bounding_box_is_not_used_as_content_size(tmp_path):
    # Generated files (draw_molecule, the renderer) copy the page extent into the root
    # BoundingBox; using it embedded a small molecule as a 22 x 30 inch object.
    path = tmp_path / "molecule.cdxml"
    path.write_text(
        '<CDXML BoundingBox="0 0 1620 2160"><page id="1" BoundingBox="0 0 1620 2160">'
        '<fragment id="2"><n id="3" p="200 210"/><n id="4" p="260 250"/></fragment>'
        '</page></CDXML>', encoding="utf-8")
    assert get_cdxml_content_size(path, scale=1.0) == (60 * EMU, 40 * EMU)


def test_conversion_content_box_from_chemdraw_is_preferred(tmp_path):
    path = _write(tmp_path, '<fragment id="2"><n id="3" p="0 0"/></fragment>',
                  ' BoundingBox="0 0 1620 2160"')
    item = {"path": str(path), "content_bbox": (156.0, 173.0, 233.0, 243.0)}
    assert content_size_emu(item, scale=1.0) == (77 * EMU, 70 * EMU)
    assert content_size_emu(item, margin_pt=2, scale=1.0) == (81 * EMU, 74 * EMU)
    # Without a usable native content box, the file itself is measured.
    measured = get_cdxml_content_size(path, scale=1.0)
    assert content_size_emu({"path": str(path)}, scale=1.0) == measured
    assert content_size_emu({"path": str(path), "content_bbox": (5, 5, 5, 9)}, scale=1.0) == measured
