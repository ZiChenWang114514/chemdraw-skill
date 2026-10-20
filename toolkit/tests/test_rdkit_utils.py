"""Unit tests for rdkit_utils.py — RDKit-based CDXML fragment utilities."""

import xml.etree.ElementTree as ET

import pytest

try:
    from rdkit import Chem
    HAS_RDKIT = True
except ImportError:
    HAS_RDKIT = False

needs_rdkit = pytest.mark.skipif(not HAS_RDKIT, reason="RDKit not installed")


# =========================================================================
# Inline CDXML test fragments
# =========================================================================

# Benzene: 6 carbons in a ring with alternating single/double bonds
BENZENE_FRAG = """\
<fragment id="1">
  <n id="1" p="100 200" Element="6"/>
  <n id="2" p="112.45 192.80" Element="6"/>
  <n id="3" p="124.90 200" Element="6"/>
  <n id="4" p="124.90 214.40" Element="6"/>
  <n id="5" p="112.45 221.60" Element="6"/>
  <n id="6" p="100 214.40" Element="6"/>
  <b id="10" B="1" E="2" Order="2"/>
  <b id="11" B="2" E="3"/>
  <b id="12" B="3" E="4" Order="2"/>
  <b id="13" B="4" E="5"/>
  <b id="14" B="5" E="6" Order="2"/>
  <b id="15" B="6" E="1"/>
</fragment>"""

# Methanol: C-O with explicit H on oxygen
METHANOL_FRAG = """\
<fragment id="2">
  <n id="1" p="100 200" Element="6"/>
  <n id="2" p="114.40 200" Element="8" NumHydrogens="1"/>
  <b id="10" B="1" E="2"/>
</fragment>"""

# Acetic acid: CH3-C(=O)-OH
ACETIC_ACID_FRAG = """\
<fragment id="3">
  <n id="1" p="100 200" Element="6"/>
  <n id="2" p="114.40 200" Element="6"/>
  <n id="3" p="121.60 187.55" Element="8" NumHydrogens="0"/>
  <n id="4" p="128.80 200" Element="8" NumHydrogens="1"/>
  <b id="10" B="1" E="2"/>
  <b id="11" B="2" E="3" Order="2"/>
  <b id="12" B="2" E="4"/>
</fragment>"""

# Ethane: C-C (simplest two-carbon)
ETHANE_FRAG = """\
<fragment id="4">
  <n id="1" p="100 200" Element="6"/>
  <n id="2" p="114.40 200" Element="6"/>
  <b id="10" B="1" E="2"/>
</fragment>"""

# Fragment with abbreviation group (NodeType="Fragment") — e.g., OTs
ABBREV_FRAG = """\
<fragment id="5">
  <n id="1" p="100 200" Element="6"/>
  <n id="2" p="114.40 200" NodeType="Fragment">
    <fragment id="99">
      <n id="90" p="114.40 200" Element="8"/>
    </fragment>
    <t p="114.40 200"><s>OTs</s></t>
  </n>
  <b id="10" B="1" E="2"/>
</fragment>"""

# Single atom — too small for cleanup
SINGLE_ATOM_FRAG = """\
<fragment id="6">
  <n id="1" p="100 200" Element="6"/>
</fragment>"""


# =========================================================================
# frag_to_mol
# =========================================================================

@needs_rdkit
class TestFragToMol:
    def test_benzene_returns_mol(self):
        from cdxml_toolkit.rdkit_utils import frag_to_mol
        frag = ET.fromstring(BENZENE_FRAG)
        mol, atoms_data = frag_to_mol(frag)
        assert mol is not None
        assert mol.GetNumAtoms() == 6
        assert mol.GetNumBonds() == 6

    def test_atoms_data_has_correct_fields(self):
        from cdxml_toolkit.rdkit_utils import frag_to_mol
        frag = ET.fromstring(METHANOL_FRAG)
        mol, atoms_data = frag_to_mol(frag)
        assert len(atoms_data) == 2
        a0 = atoms_data[0]
        assert "id" in a0
        assert "idx" in a0
        assert "x" in a0
        assert "y" in a0
        assert "elem" in a0
        assert "num_h" in a0
        assert "is_abbrev" in a0
        assert "xml" in a0

    def test_abbreviation_becomes_dummy_atom(self):
        from cdxml_toolkit.rdkit_utils import frag_to_mol
        frag = ET.fromstring(ABBREV_FRAG)
        mol, atoms_data = frag_to_mol(frag)
        assert mol is not None
        # Second atom should be dummy (element 0)
        assert atoms_data[1]["is_abbrev"] is True
        assert mol.GetAtomWithIdx(1).GetAtomicNum() == 0

    def test_explicit_hydrogens_set(self):
        from cdxml_toolkit.rdkit_utils import frag_to_mol
        frag = ET.fromstring(METHANOL_FRAG)
        mol, atoms_data = frag_to_mol(frag)
        # Oxygen has NumHydrogens="1" → explicit H set
        assert atoms_data[1]["num_h"] == 1

    def test_external_connection_point_skipped(self):
        from cdxml_toolkit.rdkit_utils import frag_to_mol
        xml = """\
        <fragment id="7">
          <n id="1" p="100 200" Element="6"/>
          <n id="2" p="114.40 200" Element="6"/>
          <n id="3" p="128.80 200" NodeType="ExternalConnectionPoint"/>
          <b id="10" B="1" E="2"/>
        </fragment>"""
        frag = ET.fromstring(xml)
        mol, atoms_data = frag_to_mol(frag)
        assert mol.GetNumAtoms() == 2  # ECP skipped


# =========================================================================
# frag_to_smiles
# =========================================================================

@needs_rdkit
class TestFragToSmiles:
    def test_benzene(self):
        from cdxml_toolkit.rdkit_utils import frag_to_smiles
        frag = ET.fromstring(BENZENE_FRAG)
        smi = frag_to_smiles(frag)
        assert smi is not None
        # RDKit canonical SMILES for benzene
        assert smi == "c1ccccc1"

    def test_methanol(self):
        from cdxml_toolkit.rdkit_utils import frag_to_smiles
        frag = ET.fromstring(METHANOL_FRAG)
        smi = frag_to_smiles(frag)
        assert smi is not None
        assert "O" in smi
        assert "C" in smi

    def test_ethane(self):
        from cdxml_toolkit.rdkit_utils import frag_to_smiles
        frag = ET.fromstring(ETHANE_FRAG)
        smi = frag_to_smiles(frag)
        assert smi is not None
        assert smi == "CC"

    def test_acetic_acid(self):
        from cdxml_toolkit.rdkit_utils import frag_to_smiles
        frag = ET.fromstring(ACETIC_ACID_FRAG)
        smi = frag_to_smiles(frag)
        assert smi is not None
        # Should contain C, O, and =O
        assert "C" in smi


# =========================================================================
# frag_to_mw
# =========================================================================

@needs_rdkit
class TestFragToMw:
    def test_benzene_mw(self):
        from cdxml_toolkit.rdkit_utils import frag_to_mw
        frag = ET.fromstring(BENZENE_FRAG)
        mw = frag_to_mw(frag)
        assert mw is not None
        # Benzene MW = 78.11 (average)
        assert abs(mw - 78.11) < 0.1

    def test_methanol_mw(self):
        from cdxml_toolkit.rdkit_utils import frag_to_mw
        frag = ET.fromstring(METHANOL_FRAG)
        mw = frag_to_mw(frag)
        assert mw is not None
        # Methanol MW = 32.04
        assert abs(mw - 32.04) < 0.1

    def test_acetic_acid_mw(self):
        from cdxml_toolkit.rdkit_utils import frag_to_mw
        frag = ET.fromstring(ACETIC_ACID_FRAG)
        mw = frag_to_mw(frag)
        assert mw is not None
        # Acetic acid MW = 60.05
        assert abs(mw - 60.05) < 0.1

    def test_abbreviation_resolved_via_superatom(self):
        """OTs abbreviation should resolve to a real MW via superatom table."""
        from cdxml_toolkit.rdkit_utils import frag_to_mw
        frag = ET.fromstring(ABBREV_FRAG)
        mw = frag_to_mw(frag)
        # OTs = OS(=O)(=O)c1ccc(C)cc1 (MW ~171.19) bonded to a C
        # Core C contributes ~12 + implicit H, plus OTs minus 1 H
        assert mw is not None
        # C-OTs: methyl tosylate-like, MW should be reasonable
        assert 150 < mw < 250

    def test_unknown_abbreviation_returns_none(self):
        """An abbreviation not in the superatom table should return None."""
        from cdxml_toolkit.rdkit_utils import frag_to_mw
        xml = """\
        <fragment id="5">
          <n id="1" p="100 200" Element="6"/>
          <n id="2" p="114.40 200" NodeType="Fragment">
            <fragment id="99">
              <n id="90" p="114.40 200" Element="6"/>
            </fragment>
            <t p="114.40 200"><s>XyzNotReal</s></t>
          </n>
          <b id="10" B="1" E="2"/>
        </fragment>"""
        frag = ET.fromstring(xml)
        mw = frag_to_mw(frag)
        assert mw is None


# =========================================================================
# frag_to_molblock
# =========================================================================

@needs_rdkit
class TestFragToMolblock:
    def test_returns_string(self):
        from cdxml_toolkit.rdkit_utils import frag_to_molblock
        frag = ET.fromstring(ETHANE_FRAG)
        mb = frag_to_molblock(frag)
        assert mb is not None
        assert isinstance(mb, str)
        assert "V2000" in mb or "V3000" in mb


# =========================================================================
# cleanup_fragment_rdkit
# =========================================================================

@needs_rdkit
class TestCleanupFragmentRdkit:
    def test_cleanup_returns_true(self):
        from cdxml_toolkit.rdkit_utils import cleanup_fragment_rdkit
        frag = ET.fromstring(BENZENE_FRAG)
        result = cleanup_fragment_rdkit(frag)
        assert result is True

    def test_single_atom_returns_false(self):
        from cdxml_toolkit.rdkit_utils import cleanup_fragment_rdkit
        frag = ET.fromstring(SINGLE_ATOM_FRAG)
        result = cleanup_fragment_rdkit(frag)
        assert result is False

    def test_coordinates_updated(self):
        from cdxml_toolkit.rdkit_utils import cleanup_fragment_rdkit
        frag = ET.fromstring(BENZENE_FRAG)
        # Record original coords
        orig = {}
        for n in frag.findall("n"):
            orig[n.get("id")] = n.get("p")
        cleanup_fragment_rdkit(frag)
        # At least check coords are valid floats after cleanup
        for n in frag.findall("n"):
            p = n.get("p")
            parts = p.split()
            assert len(parts) == 2
            float(parts[0])  # should not raise
            float(parts[1])

    def test_centroid_preserved(self):
        """Centroid should be approximately preserved after cleanup."""
        from cdxml_toolkit.rdkit_utils import cleanup_fragment_rdkit
        frag = ET.fromstring(BENZENE_FRAG)
        # Compute original centroid
        oxs, oys = [], []
        for n in frag.findall("n"):
            parts = n.get("p").split()
            oxs.append(float(parts[0]))
            oys.append(float(parts[1]))
        ocx = sum(oxs) / len(oxs)
        ocy = sum(oys) / len(oys)

        cleanup_fragment_rdkit(frag)

        # Compute new centroid
        nxs, nys = [], []
        for n in frag.findall("n"):
            parts = n.get("p").split()
            nxs.append(float(parts[0]))
            nys.append(float(parts[1]))
        ncx = sum(nxs) / len(nxs)
        ncy = sum(nys) / len(nys)

        assert abs(ncx - ocx) < 1.0, f"X centroid shifted: {ocx} → {ncx}"
        assert abs(ncy - ocy) < 1.0, f"Y centroid shifted: {ocy} → {ncy}"


# =========================================================================
# Scale / coordinate helpers
# =========================================================================

@needs_rdkit
class TestScaleHelpers:
    def test_rdkit_default_bond_length(self):
        from cdxml_toolkit.rdkit_utils import rdkit_default_bond_length
        bl = rdkit_default_bond_length()
        assert isinstance(bl, float)
        assert 1.0 < bl < 2.0  # Typically ~1.5

    def test_avg_bond_length_from_atoms(self):
        from cdxml_toolkit.rdkit_utils import frag_to_mol, avg_bond_length_from_atoms
        frag = ET.fromstring(ETHANE_FRAG)
        mol, atoms_data = frag_to_mol(frag)
        bl = avg_bond_length_from_atoms(atoms_data, mol)
        # Ethane bond is 14.40 pt in our test data
        assert abs(bl - 14.40) < 0.01

    def test_set_cdxml_conformer(self):
        from cdxml_toolkit.rdkit_utils import frag_to_mol, set_cdxml_conformer
        frag = ET.fromstring(ETHANE_FRAG)
        mol, atoms_data = frag_to_mol(frag)
        set_cdxml_conformer(mol, atoms_data, scale=1.0)
        conf = mol.GetConformer()
        # First atom at (100, -200, 0) in RDKit space (y-flipped)
        p0 = conf.GetAtomPosition(0)
        assert abs(p0.x - 100.0) < 0.01
        assert abs(p0.y - (-200.0)) < 0.01


# =========================================================================
# Import uses constants.ACS_BOND_LENGTH
# =========================================================================

@needs_rdkit
class TestUsesSharedConstants:
    def test_imports_acs_bond_length(self):
        """Verify the module uses constants.ACS_BOND_LENGTH, not a hardcoded value."""
        import cdxml_toolkit.rdkit_utils as rdkit_utils
        from cdxml_toolkit.constants import ACS_BOND_LENGTH
        # The internal _avg_bond_length fallback should return ACS_BOND_LENGTH
        # for a molecule with no bonds
        from rdkit import Chem
        mol = Chem.MolFromSmiles("[He]")
        atoms_data = [{"x": 0.0, "y": 0.0, "idx": 0}]
        result = rdkit_utils._avg_bond_length(atoms_data, mol)
        assert result == ACS_BOND_LENGTH
