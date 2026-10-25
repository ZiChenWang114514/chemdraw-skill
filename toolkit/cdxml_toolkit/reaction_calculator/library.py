"""Common solvents and liquid reagents: name, usual role and bench density.

Densities are typical values near 20-25 degrees C in g/mL; they turn a mass into a volume that
can be pipetted, so check the bottle when it matters. A structure is recognised by its canonical
SMILES, a name typed into the calculator by any of the aliases.
"""

from __future__ import annotations

from functools import lru_cache

from rdkit import Chem

# smiles, name, aliases, role, density g/mL
_ENTRIES = (
    # solvents
    ('C1CCOC1', 'tetrahydrofuran', ('THF',), 'solvent', 0.889),
    ('ClCCl', 'dichloromethane', ('DCM', 'CH2Cl2', 'methylene chloride'), 'solvent', 1.325),
    ('ClC(Cl)Cl', 'chloroform', ('CHCl3',), 'solvent', 1.489),
    ('ClCCCl', '1,2-dichloroethane', ('DCE',), 'solvent', 1.253),
    ('CN(C)C=O', 'N,N-dimethylformamide', ('DMF',), 'solvent', 0.944),
    ('CS(C)=O', 'dimethyl sulfoxide', ('DMSO',), 'solvent', 1.100),
    ('CC#N', 'acetonitrile', ('MeCN', 'ACN', 'CH3CN'), 'solvent', 0.786),
    ('Cc1ccccc1', 'toluene', ('PhMe',), 'solvent', 0.867),
    ('c1ccccc1', 'benzene', ('PhH',), 'solvent', 0.877),
    ('CCO', 'ethanol', ('EtOH',), 'solvent', 0.789),
    ('CO', 'methanol', ('MeOH',), 'solvent', 0.792),
    ('CC(C)O', 'isopropanol', ('iPrOH', 'IPA', '2-propanol'), 'solvent', 0.786),
    ('O', 'water', ('H2O',), 'solvent', 0.997),
    ('CCOC(C)=O', 'ethyl acetate', ('EtOAc', 'EA'), 'solvent', 0.902),
    ('CCOCC', 'diethyl ether', ('Et2O', 'ether'), 'solvent', 0.713),
    ('COC(C)(C)C', 'tert-butyl methyl ether', ('MTBE',), 'solvent', 0.740),
    ('C1COCCO1', '1,4-dioxane', ('dioxane',), 'solvent', 1.033),
    ('CC(C)=O', 'acetone', (), 'solvent', 0.791),
    ('CN1CCCC1=O', 'N-methyl-2-pyrrolidone', ('NMP',), 'solvent', 1.028),
    ('CC1CCCO1', '2-methyltetrahydrofuran', ('2-MeTHF', 'MeTHF'), 'solvent', 0.854),
    ('CCCCC', 'pentane', (), 'solvent', 0.626),
    ('CCCCCC', 'hexane', (), 'solvent', 0.659),
    ('CCCCCCC', 'heptane', (), 'solvent', 0.684),
    ('C1CCCCC1', 'cyclohexane', ('CyH',), 'solvent', 0.779),
    # liquid reagents and bases
    ('CCN(CC)CC', 'triethylamine', ('Et3N', 'TEA', 'NEt3'), 'reagent', 0.726),
    ('CCN(C(C)C)C(C)C', 'N,N-diisopropylethylamine', ('DIPEA', 'DIEA', 'Hunig base', 'iPr2NEt'), 'reagent', 0.742),
    ('c1ccncc1', 'pyridine', ('py',), 'reagent', 0.982),
    ('C1CCC2=NCCCN2CC1', '1,8-diazabicyclo[5.4.0]undec-7-ene', ('DBU',), 'reagent', 1.018),
    ('C1CCNCC1', 'piperidine', (), 'reagent', 0.862),
    ('C1COCCN1', 'morpholine', (), 'reagent', 1.007),
    ('CC(=O)OC(C)=O', 'acetic anhydride', ('Ac2O',), 'reagent', 1.082),
    ('CC(=O)O', 'acetic acid', ('AcOH', 'HOAc'), 'reagent', 1.049),
    ('OC=O', 'formic acid', (), 'reagent', 1.220),
    ('OC(=O)C(F)(F)F', 'trifluoroacetic acid', ('TFA',), 'reagent', 1.489),
    ('CC(=O)Cl', 'acetyl chloride', ('AcCl',), 'reagent', 1.104),
    ('O=C(Cl)c1ccccc1', 'benzoyl chloride', ('BzCl',), 'reagent', 1.211),
    ('ClS(Cl)=O', 'thionyl chloride', ('SOCl2',), 'reagent', 1.638),
    ('O=C(Cl)C(=O)Cl', 'oxalyl chloride', (), 'reagent', 1.478),
    ('C[Si](C)(C)Cl', 'chlorotrimethylsilane', ('TMSCl',), 'reagent', 0.856),
    ('CC[SiH](CC)CC', 'triethylsilane', ('Et3SiH',), 'reagent', 0.728),
    ('CI', 'iodomethane', ('MeI',), 'reagent', 2.280),
    ('BrCc1ccccc1', 'benzyl bromide', ('BnBr',), 'reagent', 1.438),
    ('C=CCBr', 'allyl bromide', (), 'reagent', 1.398),
    ('CCOC(=O)CBr', 'ethyl bromoacetate', (), 'reagent', 1.506),
    ('COC(=O)C=C', 'methyl acrylate', (), 'reagent', 0.956),
    ('C=Cc1ccccc1', 'styrene', (), 'reagent', 0.906),
    ('C#Cc1ccccc1', 'phenylacetylene', (), 'reagent', 0.930),
    ('Ic1ccccc1', 'iodobenzene', ('PhI',), 'reagent', 1.831),
    ('Brc1ccccc1', 'bromobenzene', ('PhBr',), 'reagent', 1.495),
    ('Nc1ccccc1', 'aniline', (), 'reagent', 1.022),
    ('O=Cc1ccccc1', 'benzaldehyde', ('PhCHO',), 'reagent', 1.044),
    ('OCc1ccccc1', 'benzyl alcohol', ('BnOH',), 'reagent', 1.044),
    ('O=C1CCCCC1', 'cyclohexanone', (), 'reagent', 0.947),
)

TRANSITION_METALS = frozenset({'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ru', 'Rh', 'Pd', 'Ag',
                               'Ir', 'Pt', 'Au', 'Os', 'Re', 'W', 'Mo', 'Zr', 'Hf', 'Cd'})


@lru_cache(maxsize=1)
def _table():
    by_smiles, by_name = {}, {}
    for smiles, name, aliases, role, density in _ENTRIES:
        mol = Chem.MolFromSmiles(smiles)
        entry = {'name': name, 'aliases': list(aliases), 'role': role, 'density': density,
                 'smiles': Chem.MolToSmiles(mol)}
        by_smiles[entry['smiles']] = entry
        for alias in (name, *aliases):
            by_name.setdefault(alias.lower(), entry)
    return by_smiles, by_name


def by_smiles(smiles: str) -> dict | None:
    """The library entry for a structure, matched on canonical SMILES (stereo and isotopes ignored)."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    flat = Chem.Mol(mol)
    Chem.RemoveStereochemistry(flat)
    return _table()[0].get(Chem.MolToSmiles(flat))


def by_name(text: str) -> dict | None:
    """The library entry for a name or common abbreviation (case-insensitive)."""
    return _table()[1].get(text.strip().lower())


def entries() -> list[dict]:
    """Every entry once, for pages that resolve typed names offline."""
    return list({e['smiles']: e for e in _table()[0].values()}.values())
