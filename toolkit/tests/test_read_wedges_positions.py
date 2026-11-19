"""read_wedges takes atom positions as they arrive from JSON (string keys)."""

import json

import pytest

pytest.importorskip("rdkit")

from cdxml_toolkit.vision.stereo_audit import read_wedges

SMILES = "CC(N)C(=O)O"
# Atom 1 is the centre; 0 = CH3, 2 = N, 3 = C(=O)O.  Image y grows downward.
POSITIONS = {0: (-1.0, 0.0), 1: (0.0, 0.0), 2: (0.0, -1.0), 3: (1.0, 0.5)}
WEDGES = [{"atom": 1, "neighbor": 2, "kind": "wedge"}]


def test_string_keys_from_json_match_int_keys():
    as_json = json.loads(json.dumps(POSITIONS))
    assert set(as_json) == {"0", "1", "2", "3"}
    expected = read_wedges(SMILES, WEDGES, POSITIONS)["smiles"]
    assert read_wedges(SMILES, WEDGES, as_json)["smiles"] == expected
    assert read_wedges(SMILES, WEDGES, [as_json])["smiles"] == expected


@pytest.mark.parametrize("positions", [{}, [], [{}]])
def test_no_coordinates_is_a_failure(positions):
    with pytest.raises(ValueError, match="coordinates"):
        read_wedges(SMILES, WEDGES, positions)


def test_no_wedges_is_a_failure():
    with pytest.raises(ValueError, match="wedge"):
        read_wedges(SMILES, [], POSITIONS)
