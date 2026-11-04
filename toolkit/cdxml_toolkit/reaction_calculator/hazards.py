"""Hazard reminders for common solvents and reagents: GHS pictograms, H-statements, boiling and flash point.

A built-in table, nothing is looked up or uploaded. Values are the usual classification of the pure
substance as supplier safety data sheets give it (EU CLP wording); suppliers differ in detail, and a
species that is not in the table is reported as not listed instead of being guessed. The table is a
reminder, not a replacement for the supplier's SDS.
"""

from __future__ import annotations

from functools import lru_cache

from rdkit import Chem

DISCLAIMER = 'from a built-in table of common reagents; a reminder, not a substitute for the supplier SDS'

GHS_NAME = {
    'GHS01': 'explosive', 'GHS02': 'flammable', 'GHS03': 'oxidising', 'GHS04': 'gas under pressure',
    'GHS05': 'corrosive', 'GHS06': 'acutely toxic', 'GHS07': 'harmful or irritant', 'GHS08': 'health hazard',
    'GHS09': 'hazardous to the environment',
}

H_TEXT = {
    'H200': 'unstable explosive', 'H201': 'explosive; mass explosion hazard',
    'H220': 'extremely flammable gas', 'H222': 'extremely flammable aerosol',
    'H224': 'extremely flammable liquid and vapour', 'H225': 'highly flammable liquid and vapour',
    'H226': 'flammable liquid and vapour', 'H228': 'flammable solid',
    'H240': 'heating may cause an explosion', 'H241': 'heating may cause a fire or explosion',
    'H242': 'heating may cause a fire',
    'H250': 'catches fire spontaneously if exposed to air', 'H251': 'self-heating; may catch fire',
    'H260': 'in contact with water releases flammable gases which may ignite spontaneously',
    'H261': 'in contact with water releases flammable gases',
    'H270': 'may cause or intensify fire; oxidiser',
    'H271': 'may cause fire or explosion; strong oxidiser',
    'H272': 'may intensify fire; oxidiser',
    'H280': 'contains gas under pressure; may explode if heated',
    'H290': 'may be corrosive to metals',
    'H300': 'fatal if swallowed', 'H301': 'toxic if swallowed', 'H302': 'harmful if swallowed',
    'H304': 'may be fatal if swallowed and enters airways',
    'H310': 'fatal in contact with skin', 'H311': 'toxic in contact with skin', 'H312': 'harmful in contact with skin',
    'H314': 'causes severe skin burns and eye damage', 'H315': 'causes skin irritation',
    'H317': 'may cause an allergic skin reaction', 'H318': 'causes serious eye damage',
    'H319': 'causes serious eye irritation',
    'H330': 'fatal if inhaled', 'H331': 'toxic if inhaled', 'H332': 'harmful if inhaled',
    'H334': 'may cause allergy or asthma symptoms or breathing difficulties if inhaled',
    'H335': 'may cause respiratory irritation', 'H336': 'may cause drowsiness or dizziness',
    'H340': 'may cause genetic defects', 'H341': 'suspected of causing genetic defects',
    'H350': 'may cause cancer', 'H351': 'suspected of causing cancer',
    'H360': 'may damage fertility or the unborn child',
    'H360D': 'may damage the unborn child', 'H360F': 'may damage fertility',
    'H360FD': 'may damage fertility; may damage the unborn child',
    'H361': 'suspected of damaging fertility or the unborn child',
    'H361d': 'suspected of damaging the unborn child', 'H361f': 'suspected of damaging fertility',
    'H370': 'causes damage to organs', 'H371': 'may cause damage to organs',
    'H372': 'causes damage to organs through prolonged or repeated exposure',
    'H373': 'may cause damage to organs through prolonged or repeated exposure',
    'H400': 'very toxic to aquatic life',
    'H410': 'very toxic to aquatic life with long lasting effects',
    'H411': 'toxic to aquatic life with long lasting effects',
    'H412': 'harmful to aquatic life with long lasting effects',
    'H413': 'may cause long lasting harmful effects to aquatic life',
}

# Statements that carry the signal word "Danger"; any other statement gives "Warning".
_DANGER = frozenset({
    'H200', 'H201', 'H220', 'H222', 'H224', 'H225', 'H228', 'H240', 'H241', 'H242',
    'H250', 'H251', 'H260', 'H270', 'H271', 'H300', 'H301', 'H304', 'H310', 'H311',
    'H314', 'H318', 'H330', 'H331', 'H334', 'H340', 'H350', 'H360', 'H360D', 'H360F',
    'H360FD', 'H370', 'H372',
})
_NO_SIGNAL = frozenset({'H412', 'H413'})

# smiles, name, bp (C), flash point (C), pictograms, H-statements, note
_PEROXIDES = 'forms explosive peroxides on storage'
_PYROPHORIC = 'pyrophoric: catches fire spontaneously in air and reacts violently with water'
_MOISTURE = 'reacts violently with water, releasing corrosive fumes'

_ENTRIES = (
    # solvents (33)
    ('C1CCOC1', 'tetrahydrofuran', 66, -14, 'GHS02 GHS07 GHS08', 'H225 H302 H319 H335 H351', _PEROXIDES),
    ('ClCCl', 'dichloromethane', 40, None, 'GHS07 GHS08', 'H315 H319 H335 H336 H351 H373', None),
    ('ClC(Cl)Cl', 'chloroform', 61, None, 'GHS06 GHS07 GHS08', 'H302 H315 H319 H331 H336 H351 H361d H372', None),
    ('ClCCCl', '1,2-dichloroethane', 83, 13, 'GHS02 GHS06 GHS07 GHS08', 'H225 H302 H315 H319 H331 H335 H350', None),
    ('ClC(Cl)(Cl)Cl', 'carbon tetrachloride', 77, None, 'GHS06 GHS08 GHS09', 'H301 H311 H331 H351 H372 H412', 'hepatotoxic and ozone-depleting'),
    ('CN(C)C=O', 'N,N-dimethylformamide', 153, 58, 'GHS02 GHS07 GHS08', 'H226 H312 H319 H332 H360D', None),
    ('CC(=O)N(C)C', 'N,N-dimethylacetamide', 165, 63, 'GHS07 GHS08', 'H312 H319 H332 H360D', None),
    ('CS(C)=O', 'dimethyl sulfoxide', 189, 87, '', '', 'carries dissolved substances through the skin'),
    ('CC#N', 'acetonitrile', 82, 2, 'GHS02 GHS07', 'H225 H302 H312 H319 H332', None),
    ('Cc1ccccc1', 'toluene', 111, 4, 'GHS02 GHS07 GHS08', 'H225 H304 H315 H336 H361d H373', None),
    ('Cc1ccccc1C', 'o-xylene', 144, 32, 'GHS02 GHS07 GHS08', 'H226 H304 H312 H315 H319 H332 H335 H373', None),
    ('c1ccccc1', 'benzene', 80, -11, 'GHS02 GHS07 GHS08', 'H225 H304 H315 H319 H340 H350 H372', 'carcinogen; use a substitute where one will do'),
    ('Clc1ccccc1', 'chlorobenzene', 132, 27, 'GHS02 GHS07 GHS09', 'H226 H315 H332 H411', None),
    ('CCO', 'ethanol', 78, 13, 'GHS02 GHS07', 'H225 H319', None),
    ('CO', 'methanol', 65, 11, 'GHS02 GHS06 GHS08', 'H225 H301 H311 H331 H370', 'poisonous by skin contact and inhalation as well'),
    ('CC(C)O', 'isopropanol', 82, 12, 'GHS02 GHS07', 'H225 H319 H336', None),
    ('CCCCO', '1-butanol', 118, 35, 'GHS02 GHS05 GHS07', 'H226 H302 H315 H318 H335 H336', None),
    ('CC(C)(C)O', 'tert-butanol', 82, 11, 'GHS02 GHS07', 'H225 H319 H332 H335', None),
    ('OCC(F)(F)F', '2,2,2-trifluoroethanol', 74, 29, 'GHS02 GHS05 GHS06 GHS08', 'H226 H301 H318 H331 H360F H373', None),
    ('O', 'water', 100, None, '', '', None),
    ('CCOC(C)=O', 'ethyl acetate', 77, -4, 'GHS02 GHS07', 'H225 H319 H336', None),
    ('CC(C)OC(C)=O', 'isopropyl acetate', 89, 2, 'GHS02 GHS07', 'H225 H319 H336', None),
    ('CCOCC', 'diethyl ether', 35, -45, 'GHS02 GHS07', 'H224 H302 H336', _PEROXIDES),
    ('COCCOC', '1,2-dimethoxyethane', 85, -2, 'GHS02 GHS07 GHS08', 'H225 H315 H332 H360FD', _PEROXIDES),
    ('COCCOCCOC', 'diglyme', 162, 57, 'GHS02 GHS08', 'H226 H360FD', _PEROXIDES),
    ('COC(C)(C)C', 'tert-butyl methyl ether', 55, -28, 'GHS02 GHS07', 'H225 H315', None),
    ('C1COCCO1', '1,4-dioxane', 101, 12, 'GHS02 GHS07 GHS08', 'H225 H319 H335 H350', _PEROXIDES),
    ('CC(C)=O', 'acetone', 56, -17, 'GHS02 GHS07', 'H225 H319 H336', None),
    ('CCC(C)=O', '2-butanone', 80, -9, 'GHS02 GHS07', 'H225 H319 H336', None),
    ('CN1CCCC1=O', 'N-methyl-2-pyrrolidone', 202, 91, 'GHS07 GHS08', 'H315 H319 H335 H360D', None),
    ('CN(C)P(=O)(N(C)C)N(C)C', 'hexamethylphosphoramide', 235, 105, 'GHS08', 'H340 H350', 'potent carcinogen and mutagen; substitute with DMPU or DMI'),
    ('CN1CCCN(C)C1=O', '1,3-dimethyl-3,4,5,6-tetrahydro-2(1H)-pyrimidinone', 246, 121, 'GHS05 GHS07 GHS08', 'H302 H318 H361f', None),
    ('CC1CCCO1', '2-methyltetrahydrofuran', 80, -11, 'GHS02 GHS05 GHS07', 'H225 H302 H315 H318', _PEROXIDES),
    ('CCCCC', 'pentane', 36, -49, 'GHS02 GHS07 GHS08 GHS09', 'H225 H304 H336 H411', None),
    ('CCCCCC', 'hexane', 69, -22, 'GHS02 GHS07 GHS08 GHS09', 'H225 H304 H315 H336 H361f H373 H411', None),
    ('CCCCCCC', 'heptane', 98, -4, 'GHS02 GHS07 GHS08 GHS09', 'H225 H304 H315 H336 H410', None),
    ('C1CCCCC1', 'cyclohexane', 81, -18, 'GHS02 GHS07 GHS08 GHS09', 'H225 H304 H315 H336 H410', None),
    ('C[N+](=O)[O-]', 'nitromethane', 101, 35, 'GHS02 GHS07 GHS08', 'H226 H302 H332 H351', 'can detonate if sensitised by amines, bases or acids under confinement'),
    ('O=S1(=O)CCCC1', 'sulfolane', 285, 165, 'GHS07 GHS08', 'H302 H360FD', None),

    # organolithium, Grignard and pyrophoric / water-reactive hydride reagents (13)
    ('[Li]CCCC', 'n-butyllithium', None, -17, 'GHS02 GHS05 GHS07 GHS08 GHS09', 'H225 H250 H260 H304 H314 H336 H361f H373 H410', _PYROPHORIC),
    ('[Li]C(C)CC', 'sec-butyllithium', None, -15, 'GHS02 GHS05 GHS07 GHS08 GHS09', 'H225 H250 H260 H304 H314 H336 H410', _PYROPHORIC),
    ('[Li]C(C)(C)C', 'tert-butyllithium', None, -30, 'GHS02 GHS05 GHS07 GHS08', 'H224 H250 H260 H304 H314 H336', _PYROPHORIC),
    ('[Li]C', 'methyllithium', None, -20, 'GHS02 GHS05 GHS07', 'H225 H250 H260 H314 H336', _PYROPHORIC),
    ('[Li]c1ccccc1', 'phenyllithium', None, -4, 'GHS02 GHS05 GHS07 GHS08', 'H225 H250 H260 H314 H336 H361f', _PYROPHORIC),
    ('[H-].[Na+]', 'sodium hydride', None, None, 'GHS02 GHS05', 'H228 H260 H314', 'releases flammable hydrogen with water; mineral-oil dispersion ignites on moisture contact'),
    ('[H-].[K+]', 'potassium hydride', None, None, 'GHS02 GHS05', 'H228 H260 H314', _PYROPHORIC),
    ('[H-].[H-].[Ca+2]', 'calcium hydride', None, None, 'GHS02 GHS07', 'H260 H315 H319 H335', 'releases flammable hydrogen with water'),
    ('[BH4-].[Na+]', 'sodium borohydride', None, None, 'GHS02 GHS05 GHS06', 'H260 H301 H314', 'releases flammable hydrogen with water'),
    ('[BH4-].[Li+]', 'lithium borohydride', None, None, 'GHS02 GHS05', 'H260 H314', 'reacts violently with water, releasing hydrogen'),
    ('[AlH4-].[Li+]', 'lithium aluminium hydride', None, None, 'GHS02 GHS05', 'H260 H314', 'reacts violently with water, releasing hydrogen'),
    ('CC(C)C[AlH]CC(C)C', 'diisobutylaluminium hydride', None, -18, 'GHS02 GHS05 GHS07 GHS08', 'H225 H250 H260 H304 H314 H336', _PYROPHORIC),
    ('B', 'borane', None, -20, 'GHS02 GHS05 GHS06', 'H224 H260 H301 H314 H331', 'flammable and moisture-sensitive'),

    # chlorinating, brominating, acylating, sulfonylating and silylating reagents (20)
    ('O=C(Cl)C(=O)Cl', 'oxalyl chloride', 63, None, 'GHS05 GHS06', 'H290 H302 H314 H330', 'reacts violently with water and DMF, releasing CO, CO2 and HCl'),
    ('ClS(Cl)=O', 'thionyl chloride', 76, None, 'GHS05 GHS06', 'H302 H314 H331', 'reacts violently with water, releasing HCl and SO2'),
    ('O=P(Cl)(Cl)Cl', 'phosphoryl chloride', 106, None, 'GHS05 GHS06 GHS08', 'H290 H302 H311 H314 H330 H372', _MOISTURE),
    ('ClP(Cl)Cl', 'phosphorus trichloride', 76, None, 'GHS05 GHS06 GHS08', 'H300 H314 H330 H373', _MOISTURE),
    ('BrP(Br)Br', 'phosphorus tribromide', 173, None, 'GHS05 GHS07', 'H314 H335', 'reacts violently with water, releasing HBr'),
    ('ClP(Cl)(Cl)(Cl)Cl', 'phosphorus pentachloride', None, None, 'GHS05 GHS06 GHS08', 'H302 H314 H330 H373', _MOISTURE),
    ('CC(=O)Cl', 'acetyl chloride', 51, 4, 'GHS02 GHS05', 'H225 H314', 'reacts violently with water, releasing HCl'),
    ('O=C(Cl)c1ccccc1', 'benzoyl chloride', 197, 72, 'GHS05 GHS06 GHS07', 'H302 H311 H314 H317 H331', 'corrosive lachrymator'),
    ('CS(=O)(=O)Cl', 'methanesulfonyl chloride', 161, 110, 'GHS05 GHS06', 'H290 H300 H310 H314 H330', 'acutely toxic lachrymator'),
    ('Cc1ccc(S(=O)(=O)Cl)cc1', 'p-toluenesulfonyl chloride', None, 128, 'GHS05 GHS07', 'H290 H314 H317', 'corrosive and moisture-sensitive'),
    ('O=S(=O)(OS(=O)(=O)C(F)(F)F)C(F)(F)F', 'trifluoromethanesulfonic anhydride', 82, None, 'GHS05 GHS07', 'H290 H302 H314', 'fuming and violently reactive with water'),
    ('O=C(OC(=O)C(F)(F)F)C(F)(F)F', 'trifluoroacetic anhydride', 40, None, 'GHS05 GHS07', 'H314 H332 H412', 'volatile and reacts exothermically with water'),
    ('CC(=O)OC(C)=O', 'acetic anhydride', 140, 49, 'GHS02 GHS05 GHS06', 'H226 H302 H314 H330', 'reacts with water'),
    ('CC(C)(C)OC(=O)OC(=O)OC(C)(C)C', 'di-tert-butyl dicarbonate', None, 37, 'GHS02 GHS05 GHS06 GHS07', 'H226 H315 H317 H318 H330', 'fatal if inhaled; evolves CO2 with acids'),
    ('C[Si](C)(C)Cl', 'trimethylsilyl chloride', 57, -28, 'GHS02 GHS05 GHS06', 'H225 H301 H312 H314 H331', 'flammable and releases HCl with moisture'),
    ('CC(C)(C)[Si](C)(C)Cl', 'tert-butyldimethylsilyl chloride', None, 22, 'GHS02 GHS05 GHS09', 'H228 H290 H314 H411', 'moisture-sensitive and corrosive'),
    ('C[Si](C)(C)OS(=O)(=O)C(F)(F)F', 'trimethylsilyl trifluoromethanesulfonate', 140, 25, 'GHS02 GHS05', 'H226 H314', 'fumes strongly in moist air'),
    ('BrCc1ccccc1', 'benzyl bromide', 198, 86, 'GHS07', 'H315 H319 H335', 'potent lachrymator'),
    ('CI', 'iodomethane', 42, None, 'GHS06 GHS07 GHS08', 'H301 H312 H315 H331 H335 H351', 'volatile alkylating agent'),
    ('COS(=O)(=O)OC', 'dimethyl sulfate', 188, 83, 'GHS05 GHS06 GHS08', 'H301 H311 H314 H317 H330 H341 H350', 'potent carcinogen and delayed pulmonary toxin; no odour warning'),

    # acids and bases (20)
    ('CCN(CC)CC', 'triethylamine', 89, -11, 'GHS02 GHS05 GHS06', 'H225 H302 H311 H314 H331 H335', None),
    ('CCN(C(C)C)C(C)C', 'N,N-diisopropylethylamine', 127, 10, 'GHS02 GHS05 GHS06', 'H225 H302 H314 H331 H412', None),
    ('c1ccncc1', 'pyridine', 115, 20, 'GHS02 GHS07', 'H225 H302 H312 H315 H319 H332', None),
    ('Cc1cccc(C)n1', '2,6-lutidine', 144, 37, 'GHS02 GHS07', 'H226 H302 H315 H319', None),
    ('CN(C)c1ccncc1', '4-(dimethylamino)pyridine', None, 110, 'GHS05 GHS06 GHS08', 'H301 H310 H315 H318 H331 H370', 'acutely toxic through skin absorption'),
    ('C1CCNCC1', 'piperidine', 106, 16, 'GHS02 GHS05 GHS06', 'H225 H302 H311 H314 H331', None),
    ('C1COCCN1', 'morpholine', 129, 31, 'GHS02 GHS05 GHS06', 'H226 H302 H311 H314 H331', None),
    ('C1CN2CCN1CC2', '1,4-diazabicyclo[2.2.2]octane', None, 62, 'GHS02 GHS05 GHS07', 'H228 H302 H315 H318', None),
    ('N1=C2CCCCCN2CCC1', '1,8-diazabicyclo[5.4.0]undec-7-ene', 261, 116, 'GHS05 GHS06', 'H290 H301 H314', None),
    ('c1c[nH]cn1', 'imidazole', 256, 145, 'GHS05 GHS07 GHS08', 'H302 H314 H360D', None),
    ('CC(=O)O', 'acetic acid', 118, 39, 'GHS02 GHS05', 'H226 H314', None),
    ('OC=O', 'formic acid', 101, 49, 'GHS02 GHS05 GHS06', 'H226 H302 H314 H331', None),
    ('OC(=O)C(F)(F)F', 'trifluoroacetic acid', 72, None, 'GHS05 GHS07', 'H290 H314 H332 H412', 'volatile and strongly corrosive'),
    ('CS(=O)(=O)O', 'methanesulfonic acid', 167, 189, 'GHS05 GHS07', 'H290 H302 H312 H314 H335', None),
    ('Cc1ccc(S(=O)(=O)O)cc1', 'p-toluenesulfonic acid', None, 180, 'GHS05 GHS07', 'H315 H318 H335', None),
    ('OS(=O)(=O)C(F)(F)F', 'trifluoromethanesulfonic acid', 162, None, 'GHS05 GHS07', 'H290 H302 H314 H335', 'superacid; fumes in air and chars organic matter'),
    ('OS(=O)(=O)O', 'sulfuric acid', 337, None, 'GHS05', 'H290 H314', 'add acid to water slowly; strongly exothermic dilution'),
    ('Cl', 'hydrochloric acid', -85, None, 'GHS05 GHS07', 'H290 H314 H335', None),
    ('[K+].[K+].[O-]C([O-])=O', 'potassium carbonate', None, None, 'GHS07', 'H315 H319 H335', None),
    ('[Cs+].[Cs+].[O-]C([O-])=O', 'caesium carbonate', None, None, 'GHS07', 'H315 H319 H335', None),
    ('[Na+].[OH-]', 'sodium hydroxide', None, None, 'GHS05', 'H290 H314', None),
    ('[K+].[OH-]', 'potassium hydroxide', None, None, 'GHS05 GHS07', 'H290 H302 H314', None),
    ('CC(C)(C)[O-].[K+]', 'potassium tert-butoxide', None, None, 'GHS02 GHS05', 'H228 H251 H314', 'moisture-sensitive strong base'),
    ('[F-].[Cs+]', 'caesium fluoride', None, None, 'GHS05 GHS06 GHS08', 'H301 H315 H318 H332 H361f', 'hygroscopic'),
    ('CCCC[N+](CCCC)(CCCC)CCCC.[F-]', 'tetrabutylammonium fluoride', None, None, 'GHS05 GHS07', 'H302 H314', None),

    # coupling reagents, azides and cyanides (12)
    ('C1CCC(CC1)N=C=NC1CCCCC1', 'N,N\'-dicyclohexylcarbodiimide', None, None, 'GHS05 GHS06', 'H302 H311 H317 H318', 'strong skin sensitiser'),
    ('CC(C)N=C=NC(C)C', 'N,N\'-diisopropylcarbodiimide', 146, 33, 'GHS02 GHS05 GHS06 GHS08', 'H226 H315 H317 H318 H330 H334', 'fatal if inhaled; potent sensitiser'),
    ('CCN=C=NCCCN(C)C', '1-ethyl-3-(3-dimethylaminopropyl)carbodiimide', 195, 79, 'GHS05 GHS06 GHS08 GHS09', 'H302 H311 H315 H317 H318 H373 H400 H410', 'contact sensitiser'),
    ('CCN=C=NCCCN(C)C.Cl', 'EDC hydrochloride', None, None, 'GHS05 GHS06 GHS08 GHS09', 'H302 H311 H315 H317 H318 H373 H400 H410', 'contact sensitiser'),
    ('On1nnc2ccccc21', '1-hydroxybenzotriazole', None, None, 'GHS01', 'H201', 'desensitised explosive when dry; keep hydrated'),
    ('CN(C)C(=[N+](C)C)On1nnc2cccnc21.F[P-](F)(F)(F)(F)F', 'HATU', None, None, 'GHS02 GHS07 GHS08', 'H228 H315 H317 H319 H334 H335', 'peptide coupling reagent; sensitiser and energetic benzotriazole derivative'),
    ('CN(C)C(=[N+](C)C)On1nnc2ccccc21.F[P-](F)(F)(F)(F)F', 'HBTU', None, None, 'GHS02 GHS07 GHS08', 'H228 H315 H317 H319 H334 H335', 'peptide coupling reagent; respiratory and skin sensitiser'),
    ('[N-]=[N+]=[N-].[Na+]', 'sodium azide', None, None, 'GHS06 GHS08 GHS09', 'H300 H310 H373 H410', 'forms explosive azides with heavy metals and toxic HN3 with acids'),
    ('C[Si](C)(C)N=[N+]=[N-]', 'trimethylsilyl azide', 95, 6, 'GHS02 GHS06 GHS08', 'H225 H300 H310 H330 H373', 'hydrolyses to toxic and explosive hydrazoic acid; never mix with acid'),
    ('O=P(N=[N+]=[N-])(Oc1ccccc1)Oc1ccccc1', 'diphenylphosphoryl azide', 157, 112, 'GHS06 GHS08', 'H300 H310 H330 H373', 'acutely toxic; thermal decomposition above 150 °C can be explosive'),
    ('[C-]#[N+].[K+]', 'potassium cyanide', None, None, 'GHS05 GHS06 GHS08 GHS09', 'H290 H300 H310 H330 H372 H410', 'liberates lethal HCN gas on contact with acid'),
    ('[C-]#[N+].[Na+]', 'sodium cyanide', None, None, 'GHS05 GHS06 GHS08 GHS09', 'H290 H300 H310 H330 H372 H410', 'liberates lethal HCN gas on contact with acid'),
    ('C[Si](C)(C)C#N', 'trimethylsilyl cyanide', 118, 1, 'GHS02 GHS06 GHS09', 'H225 H300 H310 H330 H410', 'volatile HCN equivalent; hydrolyses rapidly with moisture'),

    # oxidants, peroxides, halogens and fluorinating agents (15)
    ('OOC(=O)c1cccc(Cl)c1', '3-chloroperoxybenzoic acid', None, None, 'GHS02 GHS07', 'H242 H315 H319 H335', 'organic peroxide: keep cool, heating can cause a fire'),
    ('OO', 'hydrogen peroxide', 150, None, 'GHS03 GHS05 GHS07', 'H271 H302 H314 H332 H335', 'strong oxidiser; decomposes violently with transition metals'),
    ('CC(C)(C)OO', 'tert-butyl hydroperoxide', 89, 43, 'GHS02 GHS03 GHS05 GHS06 GHS08 GHS09', 'H226 H242 H302 H311 H314 H317 H330 H341 H411', 'organic peroxide: shock and heat sensitive'),
    ('CC(C)(C)OOC(C)(C)C', 'di-tert-butyl peroxide', 110, 6, 'GHS02 GHS08 GHS09', 'H225 H242 H341 H412', 'organic peroxide: thermal decomposition hazard'),
    ('O=[Os](=O)(=O)=O', 'osmium tetroxide', 130, None, 'GHS05 GHS06', 'H300 H310 H314 H330', 'volatile and fixes corneal tissue on vapour contact; use in a fume hood'),
    ('BrBr', 'bromine', 59, None, 'GHS05 GHS06 GHS09', 'H314 H330 H400', 'dense corrosive vapour; keep sodium thiosulfate on hand'),
    ('II', 'iodine', 184, None, 'GHS07 GHS08 GHS09', 'H302 H312 H315 H319 H332 H335 H372 H400', None),
    ('O=C1CCC(=O)N1Br', 'N-bromosuccinimide', None, None, 'GHS03 GHS05 GHS07 GHS08 GHS09', 'H272 H290 H302 H314 H317 H341 H400', None),
    ('O=C1CCC(=O)N1Cl', 'N-chlorosuccinimide', None, None, 'GHS05 GHS07 GHS09', 'H290 H302 H314 H335 H400', None),
    ('O=C1CCC(=O)N1I', 'N-iodosuccinimide', None, None, 'GHS05 GHS07', 'H302 H315 H318 H335', 'light- and moisture-sensitive'),
    ('CCN(CC)S(F)(F)F', 'diethylaminosulfur trifluoride', 122, 23, 'GHS02 GHS05 GHS06', 'H226 H301 H314 H330', 'explodes on heating above 90 °C and releases HF with water'),
    ('C[N+]12CC[N+](F)(CC1)CC2.F[B-](F)(F)F.F[B-](F)(F)F', 'Selectfluor', None, None, 'GHS03 GHS05 GHS06', 'H272 H301 H317 H318', 'electrophilic fluorinating agent'),
    ('O=[Mn](=O)(=O)[O-].[K+]', 'potassium permanganate', None, None, 'GHS03 GHS05 GHS07 GHS08 GHS09', 'H272 H302 H314 H361d H373 H410', 'strong oxidiser'),
    ('O=[Cr](=O)=O', 'chromium(VI) oxide', None, None, 'GHS03 GHS05 GHS06 GHS08 GHS09', 'H271 H301 H311 H314 H317 H330 H334 H340 H350 H361f H372 H410', 'carcinogenic strong oxidiser'),
    ('[O-]Cl.[Na+]', 'sodium hypochlorite', None, None, 'GHS05 GHS09', 'H290 H314 H400 H410', 'releases toxic chlorine gas with acids'),

    # phosphines, catalysts and common substrates (12)
    ('c1ccc(cc1)P(c1ccccc1)c1ccccc1', 'triphenylphosphine', None, None, 'GHS07 GHS08', 'H302 H317 H373 H413', None),
    ('CCCCP(CCCC)CCCC', 'tributylphosphine', 240, 37, 'GHS02 GHS05 GHS06 GHS09', 'H226 H250 H302 H312 H314 H411', 'air-sensitive and pyrophoric in finely divided form'),
    ('CCOC(=O)N=NC(=O)OCC', 'diethyl azodicarboxylate', 211, 90, 'GHS01 GHS05 GHS06 GHS08', 'H240 H242 H311 H315 H317 H318 H330 H334 H335', 'shock- and heat-sensitive Mitsunobu reagent'),
    ('CC(C)OC(=O)N=NC(=O)OC(C)C', 'diisopropyl azodicarboxylate', 235, 106, 'GHS02 GHS07 GHS08 GHS09', 'H242 H315 H317 H319 H335 H351 H373 H411', None),
    ('CC(=O)[O-].CC(=O)[O-].[Pd+2]', 'palladium(II) acetate', None, None, 'GHS05 GHS07 GHS09', 'H317 H318 H400 H410', None),
    ('[Cu]I', 'copper(I) iodide', None, None, 'GHS05 GHS07 GHS08 GHS09', 'H302 H315 H317 H318 H373 H410', None),
    ('Nc1ccccc1', 'aniline', 184, 70, 'GHS05 GHS06 GHS08 GHS09', 'H301 H311 H317 H318 H331 H341 H351 H372 H410', 'absorbed through the skin'),
    ('O=Cc1ccccc1', 'benzaldehyde', 179, 64, 'GHS07', 'H302 H412', None),
    ('OCc1ccccc1', 'benzyl alcohol', 205, 93, 'GHS07', 'H302 H319 H332', None),
    ('COC(=O)C=C', 'methyl acrylate', 80, -3, 'GHS02 GHS07', 'H225 H302 H312 H315 H317 H319 H332 H335', 'can polymerise exothermically'),
    ('Brc1ccccc1', 'bromobenzene', 156, 51, 'GHS02 GHS07 GHS09', 'H226 H315 H411', None),
    ('C=[N+]=[N-]', 'diazomethane', -23, -50, 'GHS01 GHS06 GHS08', 'H200 H330 H350', 'explosive and fatally toxic gas; use smooth glass and blast shield'),
)


# SMARTS structural class hazard alerts for compounds not explicitly in _ENTRIES.
_CLASS_ALERT_SPECS = (
    ('azide', 'Azide functional group', '[$(*-[N-]=[N+]=[N-]),$(*-N=[N+]=[N-]),$(*-N=N#N),$([N-]=[N+]=[N-])]',
     ['GHS01', 'GHS06'], 'shock/heat-sensitive energetic group; forms toxic and explosive HN3 with acids'),
    ('peroxide', 'Peroxide (O-O) group', '[OX2,OX1-][OX2,OX1-]',
     ['GHS02', 'GHS03'], 'peroxide O-O bond: thermal and radical decomposition hazard'),
    ('acyl_halide', 'Acyl halide', '[CX3](=[OX1])[F,Cl,Br,I]',
     ['GHS05'], 'corrosive acylating agent; hydrolyses exothermically with water releasing HX'),
    ('sulfonyl_halide', 'Sulfonyl halide', '[SX4](=[OX1])(=[OX1])[F,Cl,Br,I]',
     ['GHS05'], 'corrosive sulfonylating agent; moisture-sensitive'),
    ('diazo', 'Diazo functional group', '[$([#6]=[N+]=[N-]),$([#6-]-[N+]#[N]),$([#6]=N#N)]',
     ['GHS01', 'GHS06'], 'diazo compound: thermal/explosion hazard and acute toxicity'),
    ('isocyanate', 'Isocyanate (-N=C=O)', '[#6]-N=C=O',
     ['GHS06', 'GHS08'], 'isocyanate: potent respiratory sensitiser and lachrymator'),
    ('nitrile_inorganic_cyanide', 'Nitrile / inorganic cyanide', '[$([C-]#[N+]),$([*][C]#[N])]',
     ['GHS06'], 'nitrile / cyanide group: acute toxicity or HCN release hazard with strong acid'),
)


@lru_cache(maxsize=1)
def _compiled_alerts():
    compiled = []
    for key, label, smarts, ghs, warning in _CLASS_ALERT_SPECS:
        pat = Chem.MolFromSmarts(smarts)
        if pat is not None:
            compiled.append((key, label, pat, ghs, warning))
    return tuple(compiled)


@lru_cache(maxsize=1)
def _table() -> dict:
    table = {}
    for smiles, name, bp, flash, ghs, h, note in _ENTRIES:
        mol = Chem.MolFromSmiles(smiles)
        codes = h.split()
        signal = None if not set(codes) - _NO_SIGNAL else ('Danger' if set(codes) & _DANGER else 'Warning')
        entry = {'name': name, 'smiles': Chem.MolToSmiles(mol), 'bp_c': bp, 'flash_c': flash, 'ghs': ghs.split(),
                 'h': codes, 'signal': signal, 'note': note}
        table[entry['smiles']] = entry
    return table


HAZARDS = _table()


def _neutralize_frag(mol):
    """Neutralize simple protonated amines / deprotonated acids for salt-stripped parent lookup."""
    rw = Chem.RWMol(mol)
    changed = False
    for atom in rw.GetAtoms():
        chg = atom.GetFormalCharge()
        if chg > 0 and atom.GetTotalNumHs() >= chg and atom.GetAtomicNum() in (7, 15):
            atom.SetFormalCharge(0)
            atom.SetNumExplicitHs(max(0, atom.GetNumExplicitHs() - chg))
            changed = True
        elif chg == -1 and atom.GetAtomicNum() in (8, 16) and atom.GetTotalValence() == 1:
            atom.SetFormalCharge(0)
            atom.SetNumExplicitHs(atom.GetNumExplicitHs() + 1)
            changed = True
    if not changed:
        return None
    try:
        Chem.SanitizeMol(rw)
        return Chem.MolToSmiles(rw)
    except Exception:
        return None


def lookup(smiles: str) -> dict | None:
    """The entry for a structure (stereo and drawing coordinates ignored), or None when it is not listed.

    For multi-component salts/adducts not listed as the full salt, falls back to the largest
    listed parent fragment (>= 2 heavy atoms).
    """
    mol = Chem.MolFromSmiles(smiles) if smiles else None
    if mol is None:
        return None
    flat = Chem.Mol(mol)
    Chem.RemoveStereochemistry(flat)
    table = _table()
    entry = table.get(Chem.MolToSmiles(flat))
    if entry is not None:
        return {**entry, 'ghs': list(entry['ghs']), 'h': list(entry['h'])}

    frags = Chem.GetMolFrags(flat, asMols=True)
    if len(frags) > 1:
        for frag in sorted(frags, key=lambda m: m.GetNumHeavyAtoms(), reverse=True):
            if frag.GetNumHeavyAtoms() < 2:
                continue
            frag_smi = Chem.MolToSmiles(frag)
            parent = table.get(frag_smi)
            if parent is None:
                neut_smi = _neutralize_frag(frag)
                if neut_smi:
                    parent = table.get(neut_smi)
            if parent is not None:
                parent_note = f"parent compound ({parent['name']}); check salt/solvate SDS"
                merged_note = f"{parent['note']}; {parent_note}" if parent.get('note') else parent_note
                return {**parent, 'ghs': list(parent['ghs']), 'h': list(parent['h']), 'note': merged_note}
    return None


def class_alerts(smiles: str) -> list[dict]:
    """Return SMARTS structural hazard class alerts matched by ``smiles``."""
    mol = Chem.MolFromSmiles(smiles) if smiles else None
    if mol is None:
        return []
    alerts = []
    for key, label, pat, ghs, warning in _compiled_alerts():
        if mol.HasSubstructMatch(pat):
            alerts.append({'class': key, 'label': label, 'ghs': list(ghs), 'warning': warning})
    return alerts


def assess(smiles: str) -> dict:
    """Inspect ``smiles`` against the table and structural class alerts."""
    found = lookup(smiles)
    alerts = class_alerts(smiles)
    if found is not None:
        return {**found, 'listed': True, 'class_alerts': alerts}
    return {'listed': False, 'class_alerts': alerts}


def entries() -> list[dict]:
    return [lookup(smiles) for smiles in _table()]


def summary(entry: dict) -> str:
    """One line: signal word, pictograms, statements, boiling and flash point, note."""
    parts = [entry['signal'] or 'no GHS classification']
    if entry['ghs']:
        parts.append(' '.join(entry['ghs']))
    if entry['h']:
        parts.append(' '.join(entry['h']))
    if entry['bp_c'] is not None:
        parts.append(f"bp {entry['bp_c']} °C")
    if entry['flash_c'] is not None:
        parts.append(f"flash point {entry['flash_c']} °C")
    if entry.get('note'):
        parts.append(entry['note'])
    return '; '.join(parts)


def for_rows(rows: list[dict]) -> list[dict]:
    """A safety item per reactant, reagent, catalyst and solvent row: the entry, or ``listed: False``."""
    items = []
    for row in rows:
        if row['role'] == 'product':
            continue
        smi = row.get('smiles') or ''
        found = lookup(smi)
        item = {'id': row['id'], 'name': row['name'], 'role': row['role']}
        if found is None:
            alerts = class_alerts(smi)
            unlisted_item = {**item, 'listed': False}
            if alerts:
                unlisted_item['class_alerts'] = alerts
            items.append(unlisted_item)
        else:
            items.append({**item, 'listed': True, **{k: found[k] for k in ('signal', 'ghs', 'h', 'bp_c', 'flash_c', 'note')}})
    return items


def lines(items: list[dict]) -> list[str]:
    """Text lines for a table footer: the heading, one line per listed species, the species not listed."""
    if not items:
        return []
    out = [f'Safety reminders ({DISCLAIMER}):']
    out += [f"{item['name']}: {summary(item)}." for item in items if item['listed']]
    for item in items:
        if not item['listed'] and item.get('class_alerts'):
            classes = ', '.join(f"{a['class']} ({a['warning']})" for a in item['class_alerts'])
            out.append(f"{item['name']} (not listed; structural class alert): {classes}.")
    missing = [item['name'] for item in items if not item['listed']]
    if missing:
        out.append(f"Species not listed in the safety table (check the supplier SDS): {', '.join(missing)}.")
    return out
