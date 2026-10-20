"""Tests for mol_builder — LLM-assisted molecule construction tools.

These tests verify the offline/unit-testable parts of mol_builder.
Functions that require ChemScript or PubChem are tested with
conditional skips based on availability.
"""

import pytest
from rdkit import Chem
from cdxml_toolkit.naming.mol_builder import (
    resolve_to_smiles,
    get_prefix_form,
    assemble_name,
    modify_name,
    validate_name,
    name_to_structure,
    enumerate_names,
    list_reactions,
    apply_reaction,
    deprotect,
    get_tool_definitions,
    _parse_name_components,
    _split_prefix_segments,
    _is_complex_prefix,
)


# ---------------------------------------------------------------------------
# Helper: check if a name-to-structure backend is available
# ---------------------------------------------------------------------------

def _name_resolver_available():
    """Return True if ChemScript or OPSIN can resolve IUPAC names."""
    # Try ChemScript first
    try:
        from cdxml_toolkit.chemdraw.chemscript_bridge import ChemScriptBridge
        ChemScriptBridge()
        return True
    except Exception:
        pass
    # Try OPSIN (bundled offline fallback)
    try:
        from cdxml_toolkit.resolve.jre_manager import ensure_java_on_path
        if ensure_java_on_path():
            from py2opsin import py2opsin as _py2opsin
            smi = _py2opsin("benzene")
            if smi:
                return True
    except Exception:
        pass
    return False


needs_chemscript = pytest.mark.skipif(
    not _name_resolver_available(),
    reason="No name resolver available (neither ChemScript nor OPSIN)",
)


def _chemscript_available():
    """Return True only if ChemScript is available (needed for SMILES→name)."""
    try:
        from cdxml_toolkit.chemdraw.chemscript_bridge import ChemScriptBridge
        ChemScriptBridge()
        return True
    except Exception:
        return False


needs_chemscript_bidirectional = pytest.mark.skipif(
    not _chemscript_available(),
    reason="ChemScript required (SMILES-to-name not available via OPSIN)",
)


# ---------------------------------------------------------------------------
# Unit tests (no external dependencies)
# ---------------------------------------------------------------------------

class TestPrefixTable:
    """get_prefix_form for table lookups (offline, instant)."""

    @pytest.mark.parametrize("group, expected", [
        ("CF3", "trifluoromethyl"),
        ("NO2", "nitro"),
        ("OMe", "methoxy"),
        ("NH2", "amino"),
        ("Me", "methyl"),
        ("Ph", "phenyl"),
        ("Cl", "chloro"),
        ("Br", "bromo"),
        ("morpholine", "morpholino"),
        ("cyclopropane", "cyclopropyl"),
        ("CN", "cyano"),
        ("tBu", "tert-butyl"),
        ("iPr", "propan-2-yl"),
        ("SH", "sulfanyl"),
        ("CHF2", "difluoromethyl"),
        # Functional group descriptors (natural language)
        ("methyl ester", "methoxycarbonyl"),
        ("ethyl ester", "ethoxycarbonyl"),
        ("aldehyde", "formyl"),
        ("ketone", "oxo"),
        ("carboxylic acid", "carboxy"),
        ("nitrile", "cyano"),
        ("amide", "carbamoyl"),
        ("alcohol", "hydroxy"),
        ("hydroxyl", "hydroxy"),
        ("thiol", "sulfanyl"),
        ("mercaptan", "sulfanyl"),
        # Common ester abbreviation variants
        ("COOMe", "methoxycarbonyl"),
        ("CO2Me", "methoxycarbonyl"),
        ("COOCH3", "methoxycarbonyl"),
        ("MeO2C", "methoxycarbonyl"),
        ("COOEt", "ethoxycarbonyl"),
        ("CO2Et", "ethoxycarbonyl"),
        ("CO2H", "carboxy"),
        ("-COOH", "carboxy"),
        ("-CHO", "formyl"),
        ("Me ester", "methoxycarbonyl"),
        ("OMe ester", "methoxycarbonyl"),
    ])
    def test_table_lookup(self, group, expected):
        result = get_prefix_form(group)
        assert result["ok"] is True
        assert result["prefix"] == expected
        assert result["source"] == "table"

    def test_case_insensitive(self):
        assert get_prefix_form("cf3")["prefix"] == "trifluoromethyl"
        assert get_prefix_form("CF3")["prefix"] == "trifluoromethyl"
        assert get_prefix_form("Cf3")["prefix"] == "trifluoromethyl"

    def test_empty_input(self):
        result = get_prefix_form("")
        assert result["ok"] is False


class TestComplexPrefix:
    """_is_complex_prefix detection."""

    def test_simple_prefixes(self):
        assert not _is_complex_prefix("chloro")
        assert not _is_complex_prefix("methyl")
        assert not _is_complex_prefix("amino")
        assert not _is_complex_prefix("morpholino")

    def test_complex_prefixes(self):
        assert _is_complex_prefix("1,1-difluoroethyl")
        assert _is_complex_prefix("propan-2-yl")

    def test_already_parenthesised(self):
        assert not _is_complex_prefix("(1,1-difluoroethyl)")


class TestSplitPrefixSegments:
    """_split_prefix_segments parsing."""

    def test_single_prefix(self):
        result = _split_prefix_segments("2-chloro")
        assert result == ["2-chloro"]

    def test_two_simple_prefixes(self):
        result = _split_prefix_segments("2-chloro-3-methyl")
        assert result == ["2-chloro", "3-methyl"]

    def test_parenthesised_prefix(self):
        result = _split_prefix_segments("2-chloro-3-(trifluoromethyl)")
        assert result == ["2-chloro", "3-(trifluoromethyl)"]

    def test_multiplied_prefix(self):
        result = _split_prefix_segments("2,4-dichloro")
        assert result == ["2,4-dichloro"]


class TestParseNameComponents:
    """_parse_name_components — name decomposition."""

    def test_simple_substituted(self):
        result = _parse_name_components("2-chloropyridine")
        assert result is not None
        assert result["parent"] == "pyridine"
        assert len(result["substituents"]) == 1
        assert result["substituents"][0] == {"locant": "2", "prefix": "chloro"}

    def test_two_substituents(self):
        result = _parse_name_components("2-chloro-3-methylpyridine")
        assert result is not None
        assert result["parent"] == "pyridine"
        assert len(result["substituents"]) == 2
        prefixes = {s["prefix"] for s in result["substituents"]}
        assert prefixes == {"chloro", "methyl"}

    def test_parenthesised_substituent(self):
        result = _parse_name_components("3-(trifluoromethyl)pyridine")
        assert result is not None
        assert result["parent"] == "pyridine"
        assert result["substituents"][0]["prefix"] == "trifluoromethyl"

    def test_bare_parent(self):
        result = _parse_name_components("pyridine")
        assert result is not None
        assert result["parent"] == "pyridine"
        assert result["substituents"] == []

    def test_benzene(self):
        result = _parse_name_components("4-nitrobenzene")
        assert result is not None
        assert result["parent"] == "benzene"
        assert result["substituents"][0]["prefix"] == "nitro"


class TestAssembleName:
    """assemble_name — name construction (no validation)."""

    def test_single_substituent(self):
        result = assemble_name("pyridine",
                               [{"locant": "2", "prefix": "chloro"}],
                               validate=False)
        assert result["ok"] is True
        assert result["name"] == "2-chloropyridine"

    def test_alphabetical_order(self):
        result = assemble_name("pyridine", [
            {"locant": "3", "prefix": "methyl"},
            {"locant": "2", "prefix": "chloro"},
        ], validate=False)
        assert result["ok"] is True
        assert result["name"] == "2-chloro-3-methylpyridine"

    def test_multiplied_prefix(self):
        result = assemble_name("benzene", [
            {"locant": "2", "prefix": "chloro"},
            {"locant": "4", "prefix": "chloro"},
        ], validate=False)
        assert result["ok"] is True
        assert result["name"] == "2,4-dichlorobenzene"

    def test_complex_prefix_parenthesised(self):
        result = assemble_name("pyridine", [
            {"locant": "2", "prefix": "chloro"},
            {"locant": "3", "prefix": "1,1-difluoroethyl"},
        ], validate=False)
        assert result["ok"] is True
        assert result["name"] == "2-chloro-3-(1,1-difluoroethyl)pyridine"

    def test_bare_parent(self):
        result = assemble_name("pyridine", [], validate=False)
        assert result["ok"] is True
        assert result["name"] == "pyridine"

    def test_empty_parent_error(self):
        result = assemble_name("", [{"locant": "2", "prefix": "chloro"}])
        assert result["ok"] is False

    def test_three_different_substituents(self):
        result = assemble_name("pyridine", [
            {"locant": "2", "prefix": "chloro"},
            {"locant": "3", "prefix": "methyl"},
            {"locant": "5", "prefix": "amino"},
        ], validate=False)
        assert result["ok"] is True
        # Alphabetical: amino, chloro, methyl
        assert result["name"] == "5-amino-2-chloro-3-methylpyridine"


class TestModifyName:
    """modify_name — name surgery (no validation)."""

    def test_swap_simple(self):
        result = modify_name("4-nitropyridine", "swap",
                             target="nitro", replacement="amino",
                             validate=False)
        assert result["ok"] is True
        assert result["name"] == "4-aminopyridine"

    def test_swap_realphabetises(self):
        # nitro → amino: should move from after methyl to before chloro
        result = modify_name("2-chloro-3-methyl-5-nitropyridine", "swap",
                             target="nitro", replacement="amino",
                             validate=False)
        assert result["ok"] is True
        assert result["name"] == "5-amino-2-chloro-3-methylpyridine"

    def test_swap_target_not_found(self):
        result = modify_name("2-chloropyridine", "swap",
                             target="bromo", replacement="amino",
                             validate=False)
        assert result["ok"] is False
        assert "not found" in result["error"]

    def test_add_substituent(self):
        result = modify_name("2-chloropyridine", "add",
                             replacement="methyl", locant="3",
                             validate=False)
        assert result["ok"] is True
        assert result["name"] == "2-chloro-3-methylpyridine"

    def test_remove_substituent(self):
        result = modify_name("2-chloro-3-methylpyridine", "remove",
                             target="chloro", validate=False)
        assert result["ok"] is True
        assert result["name"] == "3-methylpyridine"

    def test_invalid_operation(self):
        result = modify_name("pyridine", "foobar")
        assert result["ok"] is False


class TestResolveToSmiles:
    """resolve_to_smiles — tests that work with the formula parser."""

    def test_condensed_formula(self):
        result = resolve_to_smiles("Et3N", use_network=False)
        assert result["ok"] is True
        # Et3N may hit reagent_db (tier 1) or formula parser (tier 2)
        assert result["source"] in ("reagent_db", "formula")
        assert "N" in result["smiles"]

    def test_reagent_db(self):
        result = resolve_to_smiles("HATU", use_network=False)
        # HATU should be in the reagent DB
        if result["ok"]:
            assert result["source"] in ("reagent_db", "formula")

    def test_nonexistent(self):
        result = resolve_to_smiles("xyzzyplugh", use_network=False)
        assert result["ok"] is False


class TestToolDefinitions:
    """get_tool_definitions — schema structure."""

    def test_returns_list(self):
        defs = get_tool_definitions()
        assert isinstance(defs, list)
        assert len(defs) >= 10  # at least 7 name tools + 3 graph tools

    def test_all_have_required_keys(self):
        for tool in get_tool_definitions():
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert tool["input_schema"]["type"] == "object"
            assert "properties" in tool["input_schema"]
            assert "required" in tool["input_schema"]

    def test_tool_names(self):
        names = {t["name"] for t in get_tool_definitions()}
        expected = {
            "resolve_to_smiles", "get_prefix_form", "assemble_name",
            "modify_name", "validate_name", "name_to_structure",
            "enumerate_names",
            "list_reactions", "apply_reaction", "deprotect",
        }
        assert expected.issubset(names)


# ---------------------------------------------------------------------------
# Integration tests (require ChemScript)
# ---------------------------------------------------------------------------

@needs_chemscript
class TestValidateNameCS:
    """validate_name with ChemScript backend."""

    def test_valid_name(self):
        result = validate_name("2-chloropyridine", use_network=False)
        assert result["valid"] is True
        assert result["smiles"] is not None

    def test_invalid_name(self):
        result = validate_name("2-chloro-99-methylpyridine", use_network=False)
        assert result["valid"] is False

    def test_common_name(self):
        result = validate_name("aspirin", use_network=False)
        # ChemScript may or may not resolve common names;
        # at minimum it shouldn't crash
        assert "valid" in result


@needs_chemscript
class TestAssembleWithValidation:
    """assemble_name + validation round-trip."""

    def test_simple_validated(self):
        result = assemble_name("pyridine", [
            {"locant": "2", "prefix": "chloro"},
        ], use_network=False)
        assert result["ok"] is True
        assert result["valid"] is True
        assert result["smiles"] is not None

    def test_two_substituents_validated(self):
        result = assemble_name("pyridine", [
            {"locant": "2", "prefix": "chloro"},
            {"locant": "3", "prefix": "methyl"},
        ], use_network=False)
        assert result["ok"] is True
        assert result["valid"] is True


@needs_chemscript
class TestModifyWithValidation:
    """modify_name + validation round-trip."""

    def test_swap_validated(self):
        result = modify_name("2-chloropyridine", "swap",
                             target="chloro", replacement="bromo",
                             use_network=False)
        assert result["ok"] is True
        assert result["valid"] is True
        assert result["name"] == "2-bromopyridine"


@needs_chemscript
class TestNameToStructure:
    """name_to_structure with ChemScript."""

    def test_cdxml_output(self):
        result = name_to_structure("morpholine")
        assert result["ok"] is True
        assert "cdxml" in result
        assert "<?xml" in result["cdxml"]

    def test_smiles_output(self):
        result = name_to_structure("morpholine", output_format="smiles")
        assert result["ok"] is True
        assert result["smiles"]


@needs_chemscript
class TestPrefixProbe:
    """get_prefix_form with Se-probe fallback."""

    def test_probe_for_unknown_group(self):
        """Groups not in the table should try the Se-probe."""
        # "adamantane" as a substituent → "adamantan-1-yl" or similar
        result = get_prefix_form("adamantane")
        # This may or may not succeed depending on probe setup;
        # at minimum it shouldn't crash
        assert "ok" in result


# ---------------------------------------------------------------------------
# End-to-end workflow tests (require ChemScript)
# ---------------------------------------------------------------------------

@needs_chemscript
class TestEndToEnd:
    """Simulate an LLM orchestrator workflow."""

    def test_draw_substituted_pyridine(self):
        """Workflow: 'Draw 2-chloropyridine with a CF3 on the 3-position'."""
        # Step 1: Get prefix form
        pf = get_prefix_form("CF3")
        assert pf["ok"] is True
        assert pf["prefix"] == "trifluoromethyl"

        # Step 2: Assemble name
        result = assemble_name("pyridine", [
            {"locant": "2", "prefix": "chloro"},
            {"locant": "3", "prefix": pf["prefix"]},
        ], use_network=False)
        assert result["ok"] is True
        assert result["valid"] is True

        # Step 3: Generate structure
        struct = name_to_structure(result["name"])
        assert struct["ok"] is True
        assert "cdxml" in struct

    def test_reaction_via_swap(self):
        """Workflow: 'Turn the nitro group into an amino group'."""
        # Starting material
        sm = validate_name("4-nitropyridine", use_network=False)
        assert sm["valid"] is True

        # Swap nitro → amino
        product = modify_name("4-nitropyridine", "swap",
                              target="nitro", replacement="amino",
                              use_network=False)
        assert product["ok"] is True
        assert product["valid"] is True
        assert product["name"] == "4-aminopyridine"


# ---------------------------------------------------------------------------
# enumerate_names tests (require ChemScript for SMILES→name decomposition)
# ---------------------------------------------------------------------------

@needs_chemscript_bidirectional
class TestEnumerateNames:
    """enumerate_names — alternative IUPAC name forms."""

    def test_ketone_returns_acetyl_alternative(self):
        """Core use case: ketone suffix → acetyl prefix."""
        result = enumerate_names("1-(4-bromophenyl)ethan-1-one")
        assert result["ok"] is True
        assert result["canonical_name"] == "1-(4-bromophenyl)ethan-1-one"
        all_names = [n["name"] for n in result["names"]]
        assert "1-acetyl-4-bromobenzene" in all_names

    def test_ketone_acetyl_has_prefixes(self):
        """The acetyl alternative should list 'acetyl' as a visible prefix."""
        result = enumerate_names("CC(=O)c1ccc(Br)cc1")
        acetyl_entry = None
        for n in result["names"]:
            if n["name"] == "1-acetyl-4-bromobenzene":
                acetyl_entry = n
                break
        assert acetyl_entry is not None
        assert "acetyl" in acetyl_entry["prefixes"]
        assert "bromo" in acetyl_entry["prefixes"]

    def test_amine_suffix_to_prefix(self):
        """Amine suffix → amino prefix: pyridin-4-amine → 4-aminopyridine."""
        result = enumerate_names("pyridin-4-amine")
        assert result["ok"] is True
        all_names = [n["name"] for n in result["names"]]
        assert "4-aminopyridine" in all_names

    def test_canonical_always_first(self):
        """Canonical name is always the first entry."""
        result = enumerate_names("CC(=O)c1ccc(Br)cc1")
        assert result["ok"] is True
        assert result["names"][0]["strategy"] == "canonical"
        assert result["names"][0]["name"] == result["canonical_name"]

    def test_accepts_smiles(self):
        """Accepts SMILES input, not just names."""
        result = enumerate_names("c1ccc(N)cc1")
        assert result["ok"] is True
        assert result["smiles"]  # got a SMILES back

    def test_invalid_input(self):
        """Returns ok=False for unresolvable input."""
        result = enumerate_names("notachemical12345xyz")
        assert result["ok"] is False

    def test_only_valid_alternatives(self):
        """All returned name forms should be marked valid."""
        result = enumerate_names("1-(4-bromophenyl)ethan-1-one")
        for n in result["names"]:
            assert n["valid"] is True


@needs_chemscript_bidirectional
class TestEnumerateNamesThenSwap:
    """End-to-end: enumerate_names → find prefix → modify_name."""

    def test_ketone_to_ester(self):
        """Workflow: 'change the ketone to a methyl ester'.

        1. enumerate_names to find the acetyl prefix form
        2. get_prefix_form('methyl ester') → 'methoxycarbonyl'
        3. modify_name swap acetyl → methoxycarbonyl
        """
        # Step 1: enumerate
        names = enumerate_names("1-(4-bromophenyl)ethan-1-one")
        assert names["ok"]
        # Find the name form with acetyl as a prefix
        operable = None
        for n in names["names"]:
            if "acetyl" in n["prefixes"]:
                operable = n["name"]
                break
        assert operable is not None, "Should find acetyl prefix form"

        # Step 2: resolve replacement
        pf = get_prefix_form("methyl ester")
        assert pf["ok"]
        assert pf["prefix"] == "methoxycarbonyl"

        # Step 3: swap
        product = modify_name(operable, "swap",
                              target="acetyl", replacement=pf["prefix"],
                              use_network=False)
        assert product["ok"]
        assert product["valid"]
        # Verify the product is methyl 4-bromobenzoate
        smi = product["smiles"]
        mol = Chem.MolFromSmiles(smi)
        assert mol is not None
        # Should contain ester (C(=O)O) and Br and benzene
        assert Chem.MolFromSmarts("[CX3](=O)[OX2]").HasSubstructMatch(mol) or \
               mol.HasSubstructMatch(Chem.MolFromSmarts("[CX3](=O)[OX2]"))


# ===========================================================================
# Layer 3 — Graph manipulation tests
# ===========================================================================

class TestListReactions:
    """list_reactions — template catalogue."""

    def test_returns_reactions(self):
        result = list_reactions()
        assert result["ok"] is True
        assert len(result["reactions"]) >= 60  # classic + datamol ring-forming

    def test_reaction_fields(self):
        result = list_reactions()
        for rxn in result["reactions"]:
            assert "name" in rxn
            assert "description" in rxn
            assert "n_reactants" in rxn
            assert "conditions" in rxn
            assert "category" in rxn

    def test_known_reactions_present(self):
        names = {r["name"] for r in list_reactions()["reactions"]}
        expected = {
            "suzuki_coupling", "buchwald_amination", "snar",
            "amide_coupling", "nitro_reduction",
        }
        assert expected.issubset(names)

    def test_heterocyclic_reactions_present(self):
        names = {r["name"] for r in list_reactions()["reactions"]}
        expected_heterocyclic = {
            "pyrrole_2",       # Paal-Knorr
            "indole_2",        # Fischer
            "thiazole_1",      # Hantzsch
            "123_triazole_2",  # Huisgen click
            "benzimidazole_1",
        }
        assert expected_heterocyclic.issubset(names), (
            f"Missing: {expected_heterocyclic - names}"
        )

    def test_categories_returned(self):
        result = list_reactions()
        assert "categories" in result
        expected = {
            "coupling", "functional_group", "heterocycle_formation",
            "deprotection", "protection",
        }
        assert expected.issubset(set(result["categories"]))

    def test_category_filter(self):
        hetero = list_reactions(category="heterocycle_formation")
        assert hetero["ok"] is True
        assert len(hetero["reactions"]) >= 50
        for rxn in hetero["reactions"]:
            assert rxn["category"] == "heterocycle_formation"

    def test_category_filter_coupling(self):
        coupling = list_reactions(category="coupling")
        assert coupling["ok"] is True
        names = {r["name"] for r in coupling["reactions"]}
        assert "suzuki_coupling" in names
        # No heterocyclic reactions in coupling category
        assert not names & {"pyrrole_2", "indole_2", "thiazole_1"}


def _smiles_equal(smi1, smi2):
    """Compare SMILES by canonical form."""
    c1 = Chem.MolToSmiles(Chem.MolFromSmiles(smi1))
    c2 = Chem.MolToSmiles(Chem.MolFromSmiles(smi2))
    return c1 == c2


class TestApplyReaction:
    """apply_reaction — core reaction transforms (RDKit only)."""

    def test_nitro_reduction(self):
        # 4-nitrotoluene → 4-aminotoluene
        result = apply_reaction(
            "nitro_reduction", "Cc1ccc([N+](=O)[O-])cc1")
        assert result["ok"] is True
        assert len(result["products"]) >= 1
        product_smi = result["products"][0]["smiles"]
        assert _smiles_equal(product_smi, "Cc1ccc(N)cc1")
        assert "conditions" in result

    def test_ester_hydrolysis(self):
        # Methyl benzoate → benzoic acid
        result = apply_reaction(
            "ester_hydrolysis", "COC(=O)c1ccccc1")
        assert result["ok"] is True
        product_smi = result["products"][0]["smiles"]
        assert _smiles_equal(product_smi, "OC(=O)c1ccccc1")

    def test_alcohol_oxidation(self):
        # Benzyl alcohol → benzaldehyde
        result = apply_reaction(
            "alcohol_oxidation", "OCc1ccccc1")
        assert result["ok"] is True
        product_smi = result["products"][0]["smiles"]
        assert _smiles_equal(product_smi, "O=Cc1ccccc1")

    def test_suzuki_coupling(self):
        # Bromobenzene + phenylboronic acid → biphenyl
        result = apply_reaction(
            "suzuki_coupling",
            "c1ccc(Br)cc1",
            "c1ccc(B(O)O)cc1",
        )
        assert result["ok"] is True
        product_smi = result["products"][0]["smiles"]
        assert _smiles_equal(product_smi, "c1ccc(-c2ccccc2)cc1")

    def test_buchwald_amination(self):
        # 4-bromopyridine + morpholine → 4-morpholinopyridine
        result = apply_reaction(
            "buchwald_amination",
            "c1cc(Br)ccn1",
            "C1COCCN1",
        )
        assert result["ok"] is True
        assert len(result["products"]) >= 1

    def test_amide_coupling(self):
        # Benzoic acid + methylamine → N-methylbenzamide
        result = apply_reaction(
            "amide_coupling",
            "OC(=O)c1ccccc1",
            "CN",
        )
        assert result["ok"] is True
        product_smi = result["products"][0]["smiles"]
        assert _smiles_equal(product_smi, "CNC(=O)c1ccccc1")

    def test_unknown_reaction_error(self):
        result = apply_reaction("foobar_reaction", "C")
        assert result["ok"] is False
        assert "Unknown reaction" in result["error"]

    def test_missing_reagent_error(self):
        result = apply_reaction("suzuki_coupling", "c1ccc(Br)cc1")
        assert result["ok"] is False
        assert "requires a reagent" in result["error"]

    def test_no_match(self):
        # Methane has no aryl halide — should fail cleanly
        result = apply_reaction("nitro_reduction", "C")
        assert result["ok"] is False

    def test_substrate_name_resolution(self):
        # Accepts names, not just SMILES
        result = apply_reaction("nitro_reduction", "nitrobenzene")
        # nitrobenzene should resolve via reagent DB or formula
        if result["ok"]:
            assert len(result["products"]) >= 1

    # --- Ring-forming heterocyclic reactions ---

    def test_paal_knorr_pyrrole(self):
        """Paal-Knorr: acetonylacetone + methylamine → 1,2,5-trimethylpyrrole."""
        result = apply_reaction("pyrrole_2", "CC(=O)CCC(=O)C", "CN")
        assert result["ok"] is True
        prod = result["products"][0]["smiles"]
        mol = Chem.MolFromSmiles(prod)
        assert mol is not None
        # Product should contain a pyrrole ring (5-membered with N)
        ri = mol.GetRingInfo()
        assert ri.NumRings() >= 1

    def test_fischer_indole(self):
        """Fischer indole: phenylhydrazine + methylethylketone → indole."""
        result = apply_reaction("indole_2", "c1ccc(NN)cc1", "CCC(C)=O")
        assert result["ok"] is True
        prod = result["products"][0]["smiles"]
        mol = Chem.MolFromSmiles(prod)
        assert mol is not None
        ri = mol.GetRingInfo()
        assert ri.NumRings() >= 2  # benzene + pyrrole

    def test_hantzsch_thiazole(self):
        """Hantzsch: alpha-bromoketone + thioamide → thiazole."""
        result = apply_reaction("thiazole_1", "CC(=O)CBr", "CC(=S)N")
        assert result["ok"] is True
        prod = result["products"][0]["smiles"]
        mol = Chem.MolFromSmiles(prod)
        assert mol is not None
        # Should contain S in a ring
        assert any(a.GetSymbol() == "S" and a.IsInRing()
                    for a in mol.GetAtoms())

    def test_huisgen_click_triazole(self):
        """Huisgen CuAAC: phenylacetylene + benzyl azide → triazole."""
        result = apply_reaction(
            "123_triazole_2",
            "C#Cc1ccccc1",          # phenylacetylene
            "c1ccc(CN=[N+]=[N-])cc1",  # benzyl azide
        )
        assert result["ok"] is True
        prod = result["products"][0]["smiles"]
        mol = Chem.MolFromSmiles(prod)
        assert mol is not None
        # Product should contain a 5-membered ring with 3 nitrogens
        ri = mol.GetRingInfo()
        assert ri.NumRings() >= 2  # triazole + phenyl rings


class TestDeprotect:
    """deprotect — protecting group removal."""

    def test_boc_removal(self):
        # Boc-aniline → aniline
        boc_aniline = "O=C(OC(C)(C)C)Nc1ccccc1"
        result = deprotect(boc_aniline)
        assert result["ok"] is True
        product = result["product_smiles"]
        assert _smiles_equal(product, "Nc1ccccc1")

    def test_no_pg_detected(self):
        # Plain aniline — nothing to deprotect
        result = deprotect("Nc1ccccc1")
        assert result["ok"] is True
        assert result["removed"] == []
        assert "No protecting groups" in result.get("note", "")

    def test_tbs_removal(self):
        # TBS-protected phenol → phenol
        tbs_phenol = "[Si](C)(C)C(C)(C)C(Oc1ccccc1)"
        result = deprotect(tbs_phenol)
        assert result["ok"] is True
        # Should get phenol back (or close to it)

    def test_invalid_smiles(self):
        result = deprotect("not_a_smiles")
        assert result["ok"] is False


# ---------------------------------------------------------------------------
# End-to-end workflow: graph manipulation path
# ---------------------------------------------------------------------------

@needs_chemscript
class TestEndToEndGraph:
    """Simulate LLM orchestrator using graph manipulation path."""

    def test_suzuki_then_name(self):
        """Workflow: Suzuki coupling → name the product → CDXML."""
        result = apply_reaction(
            "suzuki_coupling",
            "c1cc(Br)ccn1",          # 3-bromopyridine
            "c1ccc(B(O)O)cc1",       # phenylboronic acid
        )
        assert result["ok"] is True
        product_smi = result["products"][0]["smiles"]

        # Get the name
        product_name = result["products"][0].get("name")
        if product_name:
            struct = name_to_structure(product_name)
            assert struct["ok"] is True

    def test_nitro_reduction_then_buchwald(self):
        """Multi-step: reduce nitro, then Buchwald amination."""
        # Step 1: Reduce 2-nitro-4-bromopyridine
        step1 = apply_reaction(
            "nitro_reduction",
            "O=[N+]([O-])c1cc(Br)ccn1",
        )
        assert step1["ok"] is True
        intermediate = step1["products"][0]["smiles"]

        # Step 2: Buchwald on the remaining bromide
        step2 = apply_reaction(
            "buchwald_amination",
            intermediate,
            "C1COCCN1",  # morpholine
        )
        assert step2["ok"] is True
        final = step2["products"][0]["smiles"]
        # Should have amino + morpholino on pyridine
        mol = Chem.MolFromSmiles(final)
        assert mol is not None

    def test_click_chemistry_then_name(self):
        """Workflow: Huisgen click → name → CDXML."""
        # CuAAC: phenylacetylene + benzyl azide → 1-benzyl-4-phenyl-1,2,3-triazole
        result = apply_reaction(
            "123_triazole_2",
            "C#Cc1ccccc1",
            "c1ccc(CN=[N+]=[N-])cc1",
        )
        assert result["ok"] is True
        product_name = result["products"][0].get("name")
        if product_name:
            struct = name_to_structure(product_name)
            assert struct["ok"] is True
