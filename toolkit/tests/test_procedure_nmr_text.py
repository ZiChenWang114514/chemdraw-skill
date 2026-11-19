"""Reported NMR lines are taken whole from the PDF text, for every nucleus."""

from cdxml_toolkit.analysis.deterministic import procedure_writer

PAGE = (
    "Compound 7\n"
    "1H NMR (400 MHz, CDCl3) \u03b4 7.26 (d, J = 8.0 Hz, 2H), 6.88 (d, J = 8.0\n"
    "Hz, 2H), 3.80 (s, 3H).\n"
    "13C NMR (101 MHz, CDCl3) \u03b4 170.1, 159.2, 130.4,\n"
    "114.0, 55.3.\n"
    "19F NMR (376 MHz, CDCl3) \u03b4 -62.5\n"
    "Page 1 of 2\n"
)


def lines(monkeypatch, text):
    monkeypatch.setattr(procedure_writer, "extract_all_text", lambda path: text)
    return procedure_writer.extract_nmr_data("report.pdf")


def test_every_nucleus_keeps_its_shifts(monkeypatch):
    proton, carbon, fluorine = lines(monkeypatch, PAGE)
    assert proton == ("1H NMR (400 MHz, CDCl3) \u03b4 7.26 (d, J = 8.0 Hz, 2H), "
                      "6.88 (d, J = 8.0 Hz, 2H), 3.80 (s, 3H).")
    assert carbon == "13C NMR (101 MHz, CDCl3) \u03b4 170.1, 159.2, 130.4, 114.0, 55.3."
    assert fluorine == "19F NMR (376 MHz, CDCl3) \u03b4 -62.5."


def test_a_line_repeated_on_each_page_is_reported_once(monkeypatch):
    assert len(lines(monkeypatch, PAGE + PAGE)) == 3


def test_text_without_nmr_lines_gives_nothing(monkeypatch):
    assert lines(monkeypatch, "LC-MS report, no spectra.") == []
