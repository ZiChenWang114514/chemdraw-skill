// Names, tasks, hints and facts of the molecules that are only ever the daily one, and the names of the
// starting skeletons, in English. Same keys as daily.zh.js; merged into ChemWords after words.en.js.

{
  const daily = {
 "names": {
  "benzene": "benzene",
  "pyridine": "pyridine",
  "pyrimidine": "pyrimidine",
  "imidazole": "imidazole",
  "indole": "indole",
  "naphthalene": "naphthalene",
  "cyclohexane": "cyclohexane",
  "thiophene": "thiophene",
  "furan": "furan",
  "purine": "purine",
  "aceticAcid": "acetic acid",
  "hexane": "hexane"
 },
 "tasks": {
  "alanine": {
   "name": "alanine",
   "task": "Turn acetic acid into alanine: the methyl carbon gets an amino group and a methyl of its own.",
   "hint": "With the bond tool, click the CH₃ carbon twice to add two carbons. Then with the atom tool, click one of the new atoms until it reads N.",
   "fact": "Its side chain is a single methyl group, which makes it a non-polar amino acid used to build proteins."
  },
  "threonine": {
   "name": "threonine",
   "task": "Build threonine from acetic acid: an amino group, plus a carbon that carries both a methyl and an OH.",
   "hint": "With the bond tool, click the CH₃ carbon to add a carbon, click that new carbon twice, then click the CH₃ carbon again for a separate branch. With the atom tool, turn one of the two end atoms into O and the separate branch into N.",
   "fact": "A hydroxyl-bearing amino acid that humans cannot make themselves, so it has to come from food."
  },
  "methylimidazole": {
   "name": "4-methylimidazole",
   "task": "Put a methyl on the imidazole ring carbon next to the NH.",
   "hint": "With the bond tool, click the ring carbon beside the N–H to add a carbon.",
   "fact": "It can form when foods brown, and is found in roasted foods, grilled meats, coffee and some caramel colourings."
  },
  "gaba": {
   "name": "γ-aminobutyric acid",
   "task": "Extend acetic acid by two carbons and finish the chain with an amino group.",
   "hint": "With the bond tool, click the CH₃ carbon, then keep clicking the new end atom until the chain has three atoms beyond it. With the atom tool, turn the last atom into N.",
   "fact": "The chief inhibitory neurotransmitter of the mature mammalian central nervous system."
  },
  "glycine": {
   "name": "glycine",
   "task": "Put an amino group on the methyl carbon of acetic acid to make the simplest amino acid.",
   "hint": "With the bond tool, click the CH₃ carbon to add a carbon. Then with the atom tool, click that new atom until it reads N.",
   "fact": "The simplest stable amino acid: its side chain is a single hydrogen atom."
  },
  "serine": {
   "name": "serine",
   "task": "Build serine from acetic acid: the carbon next to the acid carries an amino group and a CH₂OH group.",
   "hint": "With the bond tool, click the CH₃ carbon to add a carbon, click that carbon to add a second atom, then click the CH₃ carbon again for a separate branch. With the atom tool, turn the tip of the two-atom branch into O and the single branch into N.",
   "fact": "The side chain is a hydroxymethyl group, which makes serine a polar amino acid. The body can make it itself."
  },
  "methylMethacrylate": {
   "name": "methyl methacrylate",
   "task": "Make the methyl ester of methacrylic acid from acetic acid.",
   "hint": "With the bond tool, click the CH₃ carbon twice and click one of the new bonds until it is double. Then click the OH oxygen to add a methyl.",
   "fact": "The monomer that is made on a large scale into poly(methyl methacrylate), PMMA."
  },
  "triazole": {
   "name": "1,2,4-triazole",
   "task": "Change one carbon of imidazole to nitrogen so that two N atoms sit side by side.",
   "hint": "With the atom tool, click the ring carbon beside the N–H until it reads N.",
   "fact": "One of two isomeric triazoles, with a five-membered ring of two carbons and three nitrogens."
  },
  "cysteine": {
   "name": "cysteine",
   "task": "Build cysteine from acetic acid: the carbon next to the acid carries an amino group and a CH₂SH group.",
   "hint": "With the bond tool, click the CH₃ carbon to add a carbon, click that carbon to add a second atom, then click the CH₃ carbon again for a separate branch. With the atom tool, turn the tip of the two-atom branch into S and the single branch into N.",
   "fact": "The thiol group in its side chain lets two cysteines link into a disulfide bond."
  },
  "glycolicAcid": {
   "name": "glycolic acid",
   "task": "Put an OH on the methyl carbon of acetic acid.",
   "hint": "With the bond tool, click the CH₃ carbon to add a carbon. Then with the atom tool, click that new atom until it reads O.",
   "fact": "A colourless crystalline solid that dissolves readily in water and is used in skin-care products."
  },
  "diallylDisulfide": {
   "name": "diallyl disulfide",
   "task": "Make the garlic molecule: S–S in the middle of the chain, with a vinyl end on each side.",
   "hint": "With the atom tool, turn the 4th and 5th carbons of the chain into S. With the bond tool, click the last carbon twice in turn to add two carbons at that end, so each side of S–S has three carbons. Then click the outermost bond on each side until it is double.",
   "fact": "A main component of garlic oil, formed as allicin breaks down when garlic is crushed."
  },
  "lacticAcid": {
   "name": "lactic acid",
   "task": "Give the methyl carbon of acetic acid a methyl and an OH to make lactic acid.",
   "hint": "With the bond tool, click the CH₃ carbon twice to add two carbons. Then with the atom tool, click one of them until it reads O.",
   "fact": "An alpha-hydroxy acid: the hydroxyl sits on the carbon right next to the carboxyl group."
  },
  "methacrylicAcid": {
   "name": "methacrylic acid",
   "task": "Give the methyl carbon of acetic acid a methylene and a methyl: acrylic acid with one more methyl.",
   "hint": "With the bond tool, click the CH₃ carbon twice to add two carbons, then click one of the two new bonds until it is double.",
   "fact": "Made on a large scale as the precursor of methyl methacrylate and so of the plastic PMMA."
  },
  "thymol": {
   "name": "thymol",
   "task": "Build the phenol of thyme: OH next to an isopropyl, with a methyl opposite the isopropyl.",
   "hint": "With the bond tool, click a ring carbon to add a methyl. Click the ring carbon opposite it to add a carbon, then click that carbon twice for an isopropyl. Click the ring carbon next to the isopropyl to add a carbon and turn it into O with the atom tool.",
   "fact": "It occurs naturally in oil of thyme, and is a phenol related to p-cymene and isomeric with carvacrol."
  },
  "skatole": {
   "name": "3-methylindole",
   "task": "Put a methyl on the carbon of indole's five-membered ring that is not next to the nitrogen.",
   "hint": "With the bond tool, click the five-ring carbon that is not beside the NH to add a carbon.",
   "fact": "In tiny amounts it smells flowery and turns up in several flowers and essential oils, though it is also the main source of faecal smell."
  },
  "leafAldehyde": {
   "name": "trans-2-hexenal",
   "task": "Turn one end of hexane into an aldehyde and put a double bond next to it.",
   "hint": "With the bond tool, click the last carbon to add a carbon. With the atom tool, turn it into O, then click the C–O bond with the bond tool until it is double. Finally click the second bond from that end until it is double.",
   "fact": "It has a green, leafy smell and occurs in many plants, fruits, vegetables and spices."
  },
  "acrylicAcid": {
   "name": "acrylic acid",
   "task": "Extend the methyl of acetic acid by one carbon and make the new bond a C=C.",
   "hint": "With the bond tool, click the CH₃ carbon to add a carbon, then click the new bond until it is double.",
   "fact": "The simplest unsaturated carboxylic acid; more than a million tonnes are made every year."
  },
  "valine": {
   "name": "valine",
   "task": "Build valine from acetic acid: the carbon next to the acid carries an amino group and an isopropyl group.",
   "hint": "With the bond tool, click the CH₃ carbon to add a carbon, click that new carbon twice to give it two methyls, then click the CH₃ carbon again for a separate branch. With the atom tool, turn the separate branch into N.",
   "fact": "Its side chain is an isopropyl group, and humans cannot make it, so it has to come from food."
  },
  "dimethylDisulfide": {
   "name": "dimethyl disulfide",
   "task": "Cut hexane down to four carbons and make the two in the middle sulfur.",
   "hint": "With the eraser, remove the first two carbons of the chain. With the atom tool, turn the two middle carbons into S.",
   "fact": "A flammable liquid whose garlic-like smell resembles leaking gas."
  },
  "benzimidazole": {
   "name": "benzimidazole",
   "task": "Change one carbon of indole's five-membered ring to nitrogen.",
   "hint": "With the atom tool, click the five-ring carbon that is not beside the NH until it reads N.",
   "fact": "A benzene ring fused to an imidazole ring; it forms white tabular crystals."
  },
  "isoamylAcetate": {
   "name": "isoamyl acetate",
   "task": "Esterify acetic acid with isoamyl alcohol: grow a 3-methylbutyl chain on the OH oxygen.",
   "hint": "With the bond tool, click the OH oxygen and keep clicking the new end atom until three carbons are in a row. Then click the last carbon twice to give it two methyls.",
   "fact": "Its strong smell is like banana and pear."
  },
  "butyricAcid": {
   "name": "butyric acid",
   "task": "Grow a two-carbon chain from the methyl of acetic acid.",
   "hint": "With the bond tool, click the CH₃ carbon to add a carbon, then click that new carbon to add one more.",
   "fact": "Its esters are widespread in nature, but the acid itself has an unpleasant smell."
  },
  "carvacrol": {
   "name": "carvacrol",
   "task": "Build the phenol of oregano: OH next to a methyl, with an isopropyl opposite the methyl.",
   "hint": "With the bond tool, click a ring carbon to add a methyl. Click the ring carbon opposite it to add a carbon, then click that carbon twice for an isopropyl. Click the ring carbon next to the methyl to add a carbon and turn it into O with the atom tool.",
   "fact": "A phenol with the warm, pungent smell of oregano, isomeric with thymol."
  },
  "vinylAcetate": {
   "name": "vinyl acetate",
   "task": "Turn the OH of acetic acid into an O–CH=CH₂ group.",
   "hint": "With the bond tool, click the OH oxygen to add a carbon, click that carbon to add a second, then click the bond between the two new carbons until it is double.",
   "fact": "The precursor of polyvinyl acetate and several other important polymers."
  },
  "dimethylacetamide": {
   "name": "N,N-dimethylacetamide",
   "task": "Swap the OH of acetic acid for a dimethylamino group.",
   "hint": "With the atom tool, click the OH oxygen until it reads N. Then with the bond tool, click that N twice to add two methyls.",
   "fact": "A colourless, water-miscible, high-boiling liquid that is widely used as a polar solvent in synthesis."
  },
  "cinnamylAlcohol": {
   "name": "cinnamyl alcohol",
   "task": "Hang a three-carbon allylic alcohol on benzene.",
   "hint": "With the bond tool, click a ring carbon, then keep clicking the new end atom until four atoms hang off the ring. With the atom tool, turn the last one into O, then click the bond between the first and second new carbons until it is double.",
   "fact": "Found as esters in storax, balsam of Peru and cinnamon leaves."
  },
  "benzofuran": {
   "name": "benzofuran",
   "task": "Swap the NH of indole for oxygen.",
   "hint": "With the atom tool, click the ring N until it reads O.",
   "fact": "A colourless liquid found in coal tar; psoralen, a benzofuran derivative, occurs in several plants."
  },
  "heptanone": {
   "name": "2-heptanone",
   "task": "Put a ketone near the end of a seven-carbon chain, starting from hexane.",
   "hint": "With the bond tool, click the last carbon twice to add two carbons. With the atom tool, turn one of them into O, then click the C–O bond with the bond tool until it is double.",
   "fact": "Its smell is banana-like and fruity."
  },
  "pyrazine": {
   "name": "pyrazine",
   "task": "Slide one nitrogen of pyrimidine round the ring until the two N atoms face each other.",
   "hint": "With the atom tool, turn one ring N into C, then turn the ring carbon beside it (not the one between the two N) into N.",
   "fact": "A symmetrical ring with a sweet, corn-like, nutty smell, less basic than pyridine."
  },
  "isoprene": {
   "name": "isoprene",
   "task": "Trim hexane to four carbons, add a methyl branch and make two double bonds.",
   "hint": "With the eraser, remove the first two carbons. With the bond tool, click the second remaining carbon to add a carbon, then click the new bond and the last bond of the chain until each is double.",
   "fact": "Plants and animals, humans included, make it, and its polymers are the main component of natural rubber."
  },
  "benzaldehyde": {
   "name": "benzaldehyde",
   "task": "Hang a CHO group on benzene.",
   "hint": "With the bond tool, click a ring carbon to add a carbon, click that carbon to add another. With the atom tool, turn the last one into O, then click the C–O bond with the bond tool until it is double.",
   "fact": "One of the simplest aromatic aldehydes, and one of the most useful ones in industry."
  },
  "quinoline": {
   "name": "quinoline",
   "task": "Change one carbon of naphthalene, right beside a ring-fusion carbon, to nitrogen.",
   "hint": "With the atom tool, click a ring carbon next to a fusion carbon until it reads N.",
   "fact": "A colourless liquid with a strong smell that turns yellow and then brown in light."
  },
  "acetophenone": {
   "name": "acetophenone",
   "task": "Hang an acetyl group on benzene.",
   "hint": "With the bond tool, click a ring carbon to add a carbon, then click that carbon twice to add two more. With the atom tool, turn one of them into O, then click the C–O bond with the bond tool until it is double.",
   "fact": "The simplest aromatic ketone, and a precursor of resins and fragrances."
  },
  "chlorobenzene": {
   "name": "chlorobenzene",
   "task": "Swap one hydrogen of benzene for chlorine.",
   "hint": "With the bond tool, click a ring carbon to add a carbon, then with the atom tool click it until it reads Cl.",
   "fact": "The simplest chlorinated benzene: a common solvent and an intermediate in making other chemicals."
  },
  "nicotinamide": {
   "name": "nicotinamide",
   "task": "Hang a carboxamide group on pyridine, two bonds away from the nitrogen.",
   "hint": "With the bond tool, click a ring carbon two bonds from the ring N, then click the new carbon twice for two more atoms. With the atom tool, turn one into O and the other into N, then click the C–O bond until it is double.",
   "fact": "A form of vitamin B3 found in food and used as a dietary supplement."
  },
  "leafAlcohol": {
   "name": "cis-3-hexen-1-ol",
   "task": "Put an OH on the end of hexane and a double bond in the middle of the chain.",
   "hint": "With the bond tool, click the last carbon to add a carbon, then click the middle bond of the original chain until it is double. With the atom tool, turn the new end atom into O.",
   "fact": "It smells of freshly cut grass, and most plants make small amounts of it."
  },
  "styrene": {
   "name": "styrene",
   "task": "Hang a vinyl group on benzene.",
   "hint": "With the bond tool, click a ring carbon to add a carbon, click that carbon to add another, then click the bond between the two new carbons until it is double.",
   "fact": "The precursor of polystyrene and several copolymers; it has a sweet smell."
  },
  "niacin": {
   "name": "nicotinic acid",
   "task": "Hang a carboxylic acid group on pyridine, two bonds away from the nitrogen.",
   "hint": "With the bond tool, click a ring carbon two bonds from the ring N, then click the new carbon twice for two more atoms. With the atom tool, turn both into O, then click one C–O bond until it is double.",
   "fact": "Also called niacin, a form of vitamin B3; the human body can make some of it from the amino acid tryptophan."
  },
  "isoquinoline": {
   "name": "isoquinoline",
   "task": "Change one carbon of naphthalene, second from a ring-fusion carbon, to nitrogen.",
   "hint": "With the atom tool, click a ring carbon that is two bonds from a fusion carbon until it reads N.",
   "fact": "The name also covers a family of many thousands of natural plant alkaloids."
  },
  "phenylethanol": {
   "name": "2-phenylethanol",
   "task": "Hang a CH₂CH₂OH chain on benzene.",
   "hint": "With the bond tool, click a ring carbon, then keep clicking the new end atom until three atoms hang off the ring. With the atom tool, turn the last one into O.",
   "fact": "It smells of flowers and is found in many essential oils."
  },
  "pyrazole": {
   "name": "pyrazole",
   "task": "Move one nitrogen of imidazole so the two N atoms sit side by side.",
   "hint": "With the atom tool, turn the ring N without an H into C, then turn the carbon between the two former N atoms into N.",
   "fact": "Notable drugs with a pyrazole ring include celecoxib."
  },
  "tetramethylpyrazine": {
   "name": "tetramethylpyrazine",
   "task": "Turn pyridine into a pyrazine and put a methyl on every carbon.",
   "hint": "With the atom tool, turn the ring carbon opposite the ring N into N. With the bond tool, click each of the four remaining ring carbons to add a methyl.",
   "fact": "Also called ligustrazine, it is found in nattō and in fermented cocoa beans."
  },
  "hydroquinone": {
   "name": "hydroquinone",
   "task": "Put an OH on benzene at each of two opposite carbons.",
   "hint": "With the bond tool, click two ring carbons that face each other across the ring, one carbon each. With the atom tool, turn both new atoms into O.",
   "fact": "Two OH groups sit opposite each other on a benzene ring; the compound is also known as quinol."
  },
  "cyclohexene": {
   "name": "cyclohexene",
   "task": "Put one double bond in cyclohexane.",
   "hint": "With the bond tool, click any ring bond until it is double.",
   "fact": "An intermediate in the commercial synthesis of nylon."
  },
  "acetylpyridine": {
   "name": "2-acetylpyridine",
   "task": "Hang an acetyl group on the carbon of pyridine next to the nitrogen.",
   "hint": "With the bond tool, click a ring carbon beside the ring N, then click the new carbon twice for two more atoms. With the atom tool, turn one into O, then click the C–O bond until it is double.",
   "fact": "A flavouring found in malt that adds to the taste of corn tortillas, popcorn and beer."
  },
  "benzothiazole": {
   "name": "benzothiazole",
   "task": "Swap the NH of indole for sulfur and the carbon beside it for nitrogen.",
   "hint": "With the atom tool, turn the five-ring carbon that is not beside the NH into N, and turn the NH into S.",
   "fact": "Firefly luciferin, the light-making molecule of fireflies, is a benzothiazole derivative."
  },
  "serotonin": {
   "name": "serotonin",
   "task": "Give indole an OH on its benzene ring and an aminoethyl chain on its five-ring.",
   "hint": "With the bond tool, click the benzene-ring carbon that is second from the fusion carbon on the CH side, and turn the new atom into O. Click the five-ring carbon away from the NH, then keep clicking the new end atom until three atoms hang off it, and turn the last into N.",
   "fact": "A monoamine neurotransmitter involved in mood, appetite and sleep."
  },
  "benzylAlcohol": {
   "name": "benzyl alcohol",
   "task": "Hang a CH₂OH group on benzene.",
   "hint": "With the bond tool, click a ring carbon to add a carbon, click that carbon to add another, then with the atom tool turn the last one into O.",
   "fact": "A solvent with a mild, pleasant smell, low toxicity and low vapour pressure."
  },
  "anisole": {
   "name": "anisole",
   "task": "Put a methoxy group on benzene.",
   "hint": "With the bond tool, click a ring carbon to add a carbon, then click that carbon to add a methyl. With the atom tool, turn the atom between the ring and the methyl into O.",
   "fact": "It smells of aniseed, and many of its derivatives are found in natural and artificial fragrances."
  },
  "menthol": {
   "name": "menthol",
   "task": "Build the peppermint alcohol on cyclohexane: a methyl, an isopropyl opposite it, and an OH next to the isopropyl.",
   "hint": "With the bond tool, click a ring carbon to add a methyl. Click the ring carbon opposite it, then click the new carbon twice for an isopropyl. Click a ring carbon beside the isopropyl to add a carbon and turn it into O with the atom tool.",
   "fact": "It occurs naturally in mint oils such as peppermint and corn mint."
  },
  "tetrahydropyran": {
   "name": "tetrahydropyran",
   "task": "Replace one ring carbon of cyclohexane with oxygen.",
   "hint": "With the atom tool, click one ring carbon until it reads O.",
   "fact": "Its preferred IUPAC name is oxane."
  },
  "catechol": {
   "name": "catechol",
   "task": "Put an OH on benzene at each of two neighbouring carbons.",
   "hint": "With the bond tool, click two neighbouring ring carbons, one carbon each. With the atom tool, turn both new atoms into O.",
   "fact": "First found by heating the plant extract catechin until it broke down; it is the ortho isomer of the three benzenediols."
  },
  "tetralin": {
   "name": "tetralin",
   "task": "Saturate one ring of naphthalene and leave the other aromatic.",
   "hint": "With the bond tool, click two double bonds of one ring (the ones away from the fusion) until each is single.",
   "fact": "A partially hydrogenated naphthalene used as a hydrogen-donor solvent."
  },
  "coumarin": {
   "name": "coumarin",
   "task": "Turn one ring of naphthalene into a lactone: a ring oxygen and a C=O beside it.",
   "hint": "With the bond tool, click the double bond between the fusion-adjacent carbon and its neighbour until it is single. With the atom tool, turn the fusion-adjacent carbon into O. Click its neighbour with the bond tool to add a carbon, turn that into O, and click its bond until it is double.",
   "fact": "A colourless crystalline solid with a sweet odour resembling vanilla, found in many plants."
  },
  "cymene": {
   "name": "p-cymene",
   "task": "Put a methyl and an isopropyl on opposite carbons of benzene.",
   "hint": "With the bond tool, click a ring carbon to add a methyl. Click the ring carbon opposite it to add a carbon, then click that new carbon twice more to give it two methyls.",
   "fact": "A naturally occurring aromatic hydrocarbon related to the monoterpenes."
  },
  "thiazole": {
   "name": "thiazole",
   "task": "Change one carbon of thiophene to nitrogen, two bonds from the sulfur.",
   "hint": "With the atom tool, click the ring carbon that is next to the carbon beside S until it reads N.",
   "fact": "The thiazole ring is part of vitamin B1 (thiamine)."
  },
  "hypoxanthine": {
   "name": "hypoxanthine",
   "task": "Strip caffeine of its methyls and one carbonyl oxygen, and move a double bond.",
   "hint": "With the eraser, remove all three methyls and the carbonyl O on the carbon between the two six-ring nitrogens. With the bond tool, click the bond from that carbon to the N–H until it is double.",
   "fact": "A naturally occurring purine; as part of the nucleoside inosine it sits in the anticodon of some tRNAs."
  },
  "naphthol2": {
   "name": "2-naphthol",
   "task": "Put an OH on naphthalene at a position away from the ring fusion.",
   "hint": "With the bond tool, click a ring carbon that is two bonds from a fusion carbon to add a carbon, then with the atom tool turn it into O.",
   "fact": "A fluorescent crystalline solid; it differs from its isomer 1-naphthol only in where the OH sits."
  },
  "limonene": {
   "name": "limonene",
   "task": "Put a methyl and an isopropenyl on opposite carbons of cyclohexane, and a double bond in the ring.",
   "hint": "With the bond tool, click a ring carbon to add a methyl. Click the ring carbon opposite it, click the new carbon twice, then click one of those new bonds until it is double. Finally click the ring bond that leaves the methyl carbon until it is double.",
   "fact": "The major component of the oil of citrus peel, named after the Italian limone, lemon."
  },
  "dimethylpyrazine": {
   "name": "2,5-dimethylpyrazine",
   "task": "Turn pyridine into a pyrazine with a methyl on each side.",
   "hint": "With the atom tool, turn the ring carbon opposite the ring N into N. With the bond tool, click two ring carbons that face each other across the ring to add a methyl to each.",
   "fact": "It belongs to the alkylpyrazines, strongly aromatic compounds that also form during cooking through Maillard reactions."
  },
  "indoleCarbinol": {
   "name": "indole-3-carbinol",
   "task": "Hang a CH₂OH group on the five-ring carbon of indole that is not next to the nitrogen.",
   "hint": "With the bond tool, click that five-ring carbon, then click the new carbon to add another. With the atom tool, turn the last atom into O.",
   "fact": "Formed when glucobrassicin breaks down in cruciferous vegetables such as broccoli and cabbage."
  },
  "terpinene": {
   "name": "γ-terpinene",
   "task": "Put a methyl and an isopropyl on opposite carbons of cyclohexane, and make both of those ring carbons part of a double bond.",
   "hint": "With the bond tool, click a ring carbon to add a methyl. Click the ring carbon opposite it, then click the new carbon twice for an isopropyl. Then click one ring bond leaving each of those two carbons until both are double.",
   "fact": "One of the terpinenes, a group of isomeric monoterpenes that differ in where their double bonds sit."
  },
  "pyrrole": {
   "name": "pyrrole",
   "task": "Swap the oxygen of furan for NH.",
   "hint": "With the atom tool, click the ring O until it reads N.",
   "fact": "Substituted pyrroles are building blocks of natural products; porphobilinogen is the biosynthetic precursor of many, including heme."
  },
  "dmap": {
   "name": "4-dimethylaminopyridine",
   "task": "Put a dimethylamino group on the carbon of pyridine opposite the nitrogen.",
   "hint": "With the bond tool, click the ring carbon opposite the ring N to add a carbon, then with the atom tool turn it into N. Click that N twice with the bond tool to add two methyls.",
   "fact": "More basic than pyridine, because the NMe₂ group stabilises the protonated form through resonance."
  },
  "naphthol1": {
   "name": "1-naphthol",
   "task": "Put an OH on naphthalene at a carbon next to the ring fusion.",
   "hint": "With the bond tool, click a ring carbon right beside a fusion carbon to add a carbon, then with the atom tool turn it into O.",
   "fact": "A fluorescent white solid and a precursor of many useful compounds."
  },
  "isobutylbenzene": {
   "name": "isobutylbenzene",
   "task": "Cut the whole propionic acid side off ibuprofen.",
   "hint": "With the eraser, remove the five atoms of the CH(CH₃)COOH group.",
   "fact": "It is used in synthesis, for instance to make ibuprofen."
  },
  "histamine": {
   "name": "histamine",
   "task": "Hang an aminoethyl chain on the imidazole ring.",
   "hint": "With the bond tool, click the ring carbon beside the N–H, then keep clicking the new end atom until three atoms hang off the ring. With the atom tool, turn the last one into N.",
   "fact": "Found in mammals and in many vegetables, fruits and foods: an imidazole ring with an ethylamine chain."
  },
  "vinylguaiacol": {
   "name": "2-methoxy-4-vinylphenol",
   "task": "Turn vanillin's aldehyde into a vinyl group.",
   "hint": "With the atom tool, click the aldehyde O until it reads C.",
   "fact": "A flavouring agent and one of the compounds behind the natural aroma of buckwheat."
  },
  "acetovanillone": {
   "name": "acetovanillone",
   "task": "Turn vanillin's aldehyde into a methyl ketone.",
   "hint": "With the bond tool, click the aldehyde carbon to add a carbon.",
   "fact": "Also called apocynin, a natural compound related to vanillin and isolated from several plants."
  },
  "cyclohexanol": {
   "name": "cyclohexanol",
   "task": "Put an OH on cyclohexane.",
   "hint": "With the bond tool, click a ring carbon to add a carbon, then with the atom tool click it until it reads O.",
   "fact": "It has a camphor-like smell; millions of tonnes are made each year, mainly as a precursor of nylon."
  },
  "furoicAcid": {
   "name": "2-furoic acid",
   "task": "Hang a carboxylic acid group on the furan carbon next to oxygen.",
   "hint": "With the bond tool, click a ring carbon beside O, then click the new carbon twice for two more atoms. With the atom tool, turn both into O, then click one C–O bond until it is double.",
   "fact": "Its name comes from the Latin furfur, bran; it is found in food as a preservative and a flavour."
  },
  "hydroxyquinoline": {
   "name": "8-hydroxyquinoline",
   "task": "Make quinoline with an OH on the neighbouring ring, beside the nitrogen's fusion carbon.",
   "hint": "With the atom tool, turn a ring carbon beside a fusion carbon into N. With the bond tool, click the carbon in the other ring beside that same fusion carbon to add a carbon, and turn it into O.",
   "fact": "Its aluminium complex is a common component of organic light-emitting diodes (OLEDs)."
  },
  "furfurylAlcohol": {
   "name": "furfuryl alcohol",
   "task": "Hang a CH₂OH group on the furan carbon next to oxygen.",
   "hint": "With the bond tool, click a ring carbon beside O, then click the new carbon to add another. With the atom tool, turn the last one into O.",
   "fact": "A colourless liquid with a faint odour of burning and a bitter taste."
  },
  "mercaptopurine": {
   "name": "6-mercaptopurine",
   "task": "Put a C=S at the 6-position of purine, shifting the ring bonds to make room.",
   "hint": "With the bond tool, click the C=C at the lower left of the six-ring and the C=N at its upper left until both are single. Click the lowest carbon of the six-ring to add a carbon, then click the bond between the two fusion carbons until it is double. Turn the new carbon into S with the atom tool and click its bond until it is double.",
   "fact": "A medicine for some leukaemias and autoimmune diseases."
  },
  "morpholine": {
   "name": "morpholine",
   "task": "Put an oxygen and a nitrogen on opposite sides of a six-membered ring.",
   "hint": "With the atom tool, turn one ring carbon into O and the ring carbon opposite it into N.",
   "fact": "One ring holds both an amine and an ether group."
  },
  "tryptophol": {
   "name": "tryptophol",
   "task": "Hang a CH₂CH₂OH chain on the five-ring carbon of indole that is not next to the nitrogen.",
   "hint": "With the bond tool, click that five-ring carbon, then keep clicking the new end atom until three atoms hang off it. With the atom tool, turn the last one into O.",
   "fact": "An aromatic alcohol found in wine as a by-product of fermentation."
  },
  "piperazine": {
   "name": "piperazine",
   "task": "Replace two opposite ring carbons of cyclohexane with nitrogen.",
   "hint": "With the atom tool, turn two ring carbons that face each other across the ring into N.",
   "fact": "Cyclohexane with two opposite CH₂ groups replaced by NH."
  },
  "tetrahydrothiophene": {
   "name": "tetrahydrothiophene",
   "task": "Saturate the ring of thiophene.",
   "hint": "With the bond tool, click each of the two ring double bonds until it is single.",
   "fact": "A volatile liquid with an intensely unpleasant odour; the sulfur analogue of THF."
  },
  "menthane": {
   "name": "p-menthane",
   "task": "Put a methyl and an isopropyl on opposite carbons of cyclohexane.",
   "hint": "With the bond tool, click a ring carbon to add a methyl. Click the ring carbon opposite it, then click the new carbon twice for an isopropyl.",
   "fact": "Hydrogenating p-cymene, limonene and other terpenoids gives it, and it smells of fennel."
  },
  "dimethylfuran": {
   "name": "2,5-dimethylfuran",
   "task": "Put a methyl on each carbon of furan that is next to oxygen.",
   "hint": "With the bond tool, click each of the two ring carbons beside O to add a methyl.",
   "fact": "A potential biofuel that can be made from cellulose."
  },
  "thf": {
   "name": "tetrahydrofuran",
   "task": "Saturate the ring of furan.",
   "hint": "With the bond tool, click each of the two ring double bonds until it is single.",
   "fact": "Mostly used as a precursor of polymers, and a versatile solvent."
  },
  "adenine": {
   "name": "adenine",
   "task": "Put an amino group on the six-membered ring carbon of purine that sits next to the fusion.",
   "hint": "With the bond tool, click the six-ring carbon beside the fusion carbon (not the one between two N) to add a carbon, then with the atom tool turn it into N.",
   "fact": "A purine base found in DNA, RNA and ATP; it pairs with thymine in DNA and uracil in RNA."
  },
  "guanine": {
   "name": "guanine",
   "task": "Strip caffeine of its methyls and turn the carbonyl between the two ring nitrogens into an amino group.",
   "hint": "With the eraser, remove all three methyls. Click the C=O bond between the two six-ring nitrogens until it is single, turn that O into N with the atom tool, then click the bond from that carbon to the N–H until it is double.",
   "fact": "One of the four main bases of DNA and RNA, pairing with cytosine in DNA."
  },
  "furfurylThiol": {
   "name": "furfuryl mercaptan",
   "task": "Hang a CH₂SH group on the furan carbon next to oxygen.",
   "hint": "With the bond tool, click a ring carbon beside O, then click the new carbon to add another. With the atom tool, click the last one until it reads S.",
   "fact": "Its strong odour is that of roasted coffee, and it is a key part of coffee's aroma."
  },
  "cumene": {
   "name": "cumene",
   "task": "Hang an isopropyl group on benzene.",
   "hint": "With the bond tool, click a ring carbon to add a carbon, then click that carbon twice to give it two methyls.",
   "fact": "A constituent of crude oil and refined fuels; nearly all industrial cumene is converted to cumene hydroperoxide."
  },
  "methylxanthine7": {
   "name": "7-methylxanthine",
   "task": "Keep only the methyl on the five-membered ring of caffeine.",
   "hint": "With the eraser, remove the two methyls on the nitrogens of the six-membered ring.",
   "fact": "An active metabolite of caffeine and theobromine, and a non-selective blocker of adenosine receptors."
  },
  "guaiacol": {
   "name": "guaiacol",
   "task": "Take the aldehyde off vanillin.",
   "hint": "With the eraser, remove the aldehyde O and its carbon.",
   "fact": "A phenol with a methoxy group; it occurs widely in nature and is a common product of heating wood."
  },
  "thiophenecarbaldehyde": {
   "name": "thiophene-2-carbaldehyde",
   "task": "Hang a CHO group on the thiophene carbon next to sulfur.",
   "hint": "With the bond tool, click a ring carbon beside S, then click the new carbon to add another. With the atom tool, turn it into O, then click the C–O bond until it is double.",
   "fact": "A versatile precursor of drugs including eprosartan, azosemide and teniposide."
  },
  "isoeugenol": {
   "name": "isoeugenol",
   "task": "Turn vanillin's aldehyde into a propenyl group.",
   "hint": "With the atom tool, click the aldehyde O until it reads C. With the bond tool, click that carbon to add one more.",
   "fact": "A propenyl-substituted guaiacol found in ylang-ylang oil and wood smoke; it has been used to make vanillin."
  },
  "syringaldehyde": {
   "name": "syringaldehyde",
   "task": "Give vanillin a second methoxy group on the other side of the OH.",
   "hint": "With the bond tool, click the ring carbon on the other side of the OH from the OCH₃, then click the new carbon to add another. With the atom tool, turn the first new atom into O.",
   "fact": "It occurs in trace amounts widely in nature; the beetle Scolytus multistriatus uses it as a signal to find a host tree."
  },
  "furfural": {
   "name": "furfural",
   "task": "Hang a CHO group on the furan carbon next to oxygen.",
   "hint": "With the bond tool, click a ring carbon beside O, then click the new carbon to add another. With the atom tool, turn it into O, then click the C–O bond until it is double.",
   "fact": "Made by dehydrating sugars in farm by-products such as corncobs, oat and wheat bran."
  },
  "anisaldehyde": {
   "name": "4-anisaldehyde",
   "task": "Move vanillin's methoxy: drop the one beside the OH and put a methyl on the OH.",
   "hint": "With the eraser, remove the OCH₃ oxygen and its methyl. With the bond tool, click the ring OH oxygen to add a methyl.",
   "fact": "It has a sweet, floral aniseed smell."
  },
  "phenetidine": {
   "name": "p-phenetidine",
   "task": "Rearrange paracetamol: the amide becomes an ethoxy group and the OH becomes an amino group.",
   "hint": "With the eraser, remove the carbonyl oxygen. With the atom tool, turn the amide N into O and the ring OH oxygen into N.",
   "fact": "An intermediate in making drugs, dyes and the sweetener dulcin."
  },
  "diaminopurine": {
   "name": "2,6-diaminopurine",
   "task": "Put an amino group on both six-ring carbons of purine that have a free spot.",
   "hint": "With the bond tool, click the six-ring carbon beside the fusion and the carbon between the two six-ring N atoms to add a carbon to each, then turn both new atoms into N.",
   "fact": "Once used in the treatment of leukaemia; some bacteriophage viruses have it instead of adenine in their genetic material."
  },
  "enprofylline": {
   "name": "enprofylline",
   "task": "Turn caffeine into a xanthine whose only substituent is a propyl on the N beside the ring fusion.",
   "hint": "With the eraser, remove the methyl on the five-ring N and the methyl on the N between the two C=O. With the bond tool, click the remaining methyl, then click the new carbon, to grow a propyl.",
   "fact": "A xanthine used in asthma treatment as a bronchodilator."
  },
  "eugenol": {
   "name": "eugenol",
   "task": "Turn vanillin's aldehyde into an allyl group.",
   "hint": "With the bond tool, click the aldehyde C=O bond until it is single. With the atom tool, turn the O into C. Click that carbon with the bond tool to add one more, then click the new bond until it is double.",
   "fact": "Extracted from clove, nutmeg, cinnamon, basil and bay leaf; clove bud oil is 80 to 90% eugenol."
  },
  "aniline": {
   "name": "aniline",
   "task": "Strip paracetamol down to a bare amino group on benzene.",
   "hint": "With the eraser, remove the ring OH, then the acetyl group's three atoms.",
   "fact": "The simplest aromatic amine, used mainly to make precursors of polyurethane, dyes and other chemicals."
  },
  "salicylamide": {
   "name": "salicylamide",
   "task": "Take the acetyl group off aspirin and turn its acid into an amide.",
   "hint": "With the eraser, remove the three atoms of the acetyl group. With the atom tool, click the acid's OH oxygen until it reads N.",
   "fact": "A non-prescription drug with pain-relieving and fever-reducing properties similar to aspirin."
  },
  "benzoicAcid": {
   "name": "benzoic acid",
   "task": "Take the whole acetoxy group off aspirin.",
   "hint": "With the eraser, remove the ester oxygen and the three atoms of the acetyl group, four atoms in all.",
   "fact": "The simplest aromatic carboxylic acid; its name comes from gum benzoin, once its only source."
  },
  "salicylaldehyde": {
   "name": "salicylaldehyde",
   "task": "Take the acetyl group off aspirin and the OH off its acid, leaving an aldehyde.",
   "hint": "With the eraser, remove the three atoms of the acetyl group and the OH oxygen of the acid.",
   "fact": "It smells of bitter almond at higher concentration and is a precursor of coumarin."
  }
 }
};
  Object.assign(globalThis.ChemWords.names, daily.names);
  Object.assign(globalThis.ChemWords.challenge.tasks, daily.tasks);
}
