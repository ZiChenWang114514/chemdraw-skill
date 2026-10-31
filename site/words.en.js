// The interface words of the English pages: one JSON object, with the same keys in both languages.
globalThis.ChemWords = {
 "hint": {
  "move": "Drag an atom to move it.",
  "bond": "Click a bond to change its order and an atom to grow a chain. Drag between two atoms to bond them, or click empty space to place a carbon.",
  "atom": "Click an atom to change its element. Shift-click goes back. Click empty space to place a carbon.",
  "ring": "Click an atom to attach a benzene ring, or click empty space to place one.",
  "erase": "Click an atom or a bond to remove it."
 },
 "ask": "“Use ChemDraw Skill to draw {name} as editable CDXML and show me the render.”",
 "names": {
  "aspirin": "aspirin",
  "paracetamol": "paracetamol",
  "caffeine": "caffeine",
  "ibuprofen": "ibuprofen",
  "vanillin": "vanillin"
 },
 "build": "{name}.cdxml, ACS Document 1996",
 "matches": "matches the input",
 "differs": "differs from the input {input}",
 "empty": "nothing drawn",
 "order": [
  "single",
  "double",
  "triple"
 ],
 "setBond": "Bond set to {order}.",
 "grow": "Carbon added.",
 "element": "Atom set to {sym}.",
 "ring": "Benzene ring attached.",
 "noRoom": "No room there. Move the structure first.",
 "erased": "Removed.",
 "moved": "Moved.",
 "undone": "Undone.",
 "reset": "Back to the original.",
 "valence": "{sym} has {n} bonds, more than the usual {v}.",
 "challenge": {
  "title": "Challenge {n} of {total}",
  "hint": "Hint",
  "skip": "Another one",
  "next": "Next",
  "close": "Leave challenges",
  "done": "Solved in {moves} moves.",
  "matches": "matches the target",
  "aim": "target {formula}",
  "tasks": {
   "salicylic": {
    "name": "salicylic acid",
    "task": "As the body does, take the acetyl group off aspirin and keep the phenol OH.",
    "hint": "With the eraser, remove the methyl, the carbonyl carbon and its oxygen on the left: three atoms.",
    "fact": "Aspirin is hydrolysed to salicylic acid in the body, and it is also a common acne-care ingredient."
   },
   "aminophenol": {
    "name": "4-aminophenol",
    "task": "Take paracetamol back to its precursor, 4-aminophenol.",
    "hint": "Erase the three atoms of the acetyl group and keep the NH₂.",
    "fact": "Acetylating it is the usual last step in making paracetamol."
   },
   "acetanilide": {
    "name": "acetanilide",
    "task": "Remove the OH from paracetamol to get acetanilide.",
    "hint": "Erase the OH on the ring.",
    "fact": "Sold as Antifebrin from 1886, it was one of the first synthetic fever remedies."
   },
   "phenylAcetate": {
    "name": "phenyl acetate",
    "task": "Remove the carboxylic acid from aspirin to leave phenyl acetate.",
    "hint": "Erase the COOH on the ring: its carbon and two oxygens, three atoms.",
    "fact": "It is the textbook substrate of the Fries rearrangement, in which the acyl group moves from oxygen to the ring."
   },
   "theophylline": {
    "name": "theophylline",
    "task": "Caffeine minus one methyl is theophylline: remove the methyl on the five-membered ring’s nitrogen.",
    "hint": "The ring nitrogen with a methyl is at the lower left of the five-membered ring. Erase that methyl.",
    "fact": "Tea contains traces of it, and it is prescribed as a bronchodilator for asthma and COPD."
   },
   "theobromine": {
    "name": "theobromine",
    "task": "Now a different methyl: remove the one on the nitrogen between the two carbonyls.",
    "hint": "Find the N between the two C=O groups and erase its methyl.",
    "fact": "The main alkaloid of cocoa and chocolate. The name comes from the genus Theobroma; it contains no bromine."
   },
   "paraxanthine": {
    "name": "paraxanthine",
    "task": "Remove the methyl from the six-ring nitrogen that touches the ring fusion.",
    "hint": "This N has a C=O on one side and a ring-fusion carbon on the other. Erase its methyl.",
    "fact": "Most of the caffeine you drink is turned into paraxanthine in the liver."
   },
   "xanthine": {
    "name": "xanthine",
    "task": "Remove all three methyls to reveal the parent ring system, xanthine.",
    "hint": "Erase the methyl on each of the three nitrogens.",
    "fact": "An intermediate of purine metabolism: xanthine oxidase takes it on to uric acid."
   },
   "ibufenac": {
    "name": "ibufenac",
    "task": "Remove ibuprofen’s alpha methyl to reach its predecessor, ibufenac.",
    "hint": "Find the CH next to the acid and erase the methyl on it.",
    "fact": "Ibuprofen’s predecessor, withdrawn because of liver toxicity. One more methyl made a much safer drug."
   },
   "protocatechuic": {
    "name": "protocatechualdehyde",
    "task": "Remove the methyl from vanillin’s methoxy group to leave two neighbouring OH groups.",
    "hint": "Erase the methyl on the oxygen.",
    "fact": "Methylate one of its OH groups and you get vanillin; methylate the other and you get isovanillin."
   },
   "fluoroacetanilide": {
    "name": "4′-fluoroacetanilide",
    "task": "Swap the OH of paracetamol for fluorine.",
    "hint": "With the atom tool, click the OH oxygen until it reads F. On a keyboard, put the cursor on it and press F.",
    "fact": "Placing fluorine on a ring position that is easily metabolised is a routine move in medicinal chemistry."
   },
   "vanillylAlcohol": {
    "name": "vanillyl alcohol",
    "task": "Reduce the aldehyde of vanillin to an alcohol.",
    "hint": "With the bond tool, click the C=O bond until it is single.",
    "fact": "Reducing vanillin with sodium borohydride gives it, a common undergraduate lab experiment."
   },
   "ibuprofenAmide": {
    "name": "ibuprofen amide",
    "task": "Turn ibuprofen’s acid into a primary amide.",
    "hint": "With the atom tool, click the OH oxygen until it reads N.",
    "fact": "Without the acidic OH, the amide has a different polarity and solubility from the acid."
   },
   "isovanillin": {
    "name": "isovanillin",
    "task": "Move vanillin’s methyl from one oxygen to the neighbouring oxygen.",
    "hint": "Erase the methyl on the oxygen, then with the bond tool click the ring OH oxygen to add a carbon.",
    "fact": "It has the same formula as vanillin with OH and OCH₃ swapped. A matching formula does not prove a structure."
   },
   "wintergreen": {
    "name": "methyl salicylate",
    "task": "Starting from aspirin, make the main component of oil of wintergreen.",
    "hint": "Remove the acetyl group as in the first level, then add a carbon to the acid’s OH.",
    "fact": "It gives oil of wintergreen its smell and is found in many pain-relief rubs."
   },
   "ibuprofenMethyl": {
    "name": "ibuprofen methyl ester",
    "task": "Turn ibuprofen into its methyl ester.",
    "hint": "With the bond tool, click the OH oxygen of the acid to add a carbon.",
    "fact": "Carboxylic acids are often converted to methyl esters like this before gas chromatography."
   },
   "vanillic": {
    "name": "vanillic acid",
    "task": "Oxidise the aldehyde of vanillin to a carboxylic acid.",
    "hint": "With the bond tool, click the aldehyde carbon to add a carbon, then use the atom tool to change it to O.",
    "fact": "Oxidising vanillin gives it, and it is among the flavour compounds of vanilla beans."
   },
   "ethylVanillin": {
    "name": "ethyl vanillin",
    "task": "Extend vanillin’s methoxy group to an ethoxy group.",
    "hint": "With the bond tool, click the methyl to add one more carbon.",
    "fact": "A synthetic flavouring, stronger than vanillin, that does not occur in natural vanilla."
   },
   "veratraldehyde": {
    "name": "veratraldehyde",
    "task": "Turn vanillin’s phenol OH into a second methoxy group.",
    "hint": "With the bond tool, click the ring OH oxygen to add a carbon.",
    "fact": "Vanillin with its phenol methylated, used in fragrances and as a synthetic intermediate."
   },
   "phenacetin": {
    "name": "phenacetin",
    "task": "Put an ethyl group on the OH of paracetamol.",
    "hint": "With the bond tool, click the OH oxygen to add a carbon, then click that carbon to add another.",
    "fact": "Once a popular painkiller, withdrawn because of kidney damage. The body converts it mainly to paracetamol."
   }
  }
 },
 "run": "Run it",
 "progressTop": "Top of the page",
 "faq": {
  "expand": "Expand all",
  "collapse": "Collapse all",
  "count": "{n} found",
  "link": "Copy a link to this question"
 },
 "running": "Running…",
 "rerun": "Run it again",
 "copyAsk": "Copy",
 "copiedAsk": "Copied",
 "lightbox": {
  "open": "Enlarge: {alt}",
  "close": "Close",
  "prev": "Previous",
  "next": "Next",
  "zoomIn": "Zoom in",
  "zoomOut": "Zoom out",
  "fit": "Fit to window",
  "count": "{n} of {total}",
  "hint": "Scroll or double-click to zoom, drag to pan, arrow keys to move between figures, Esc to close."
 },
 "aria": "Structure of {name}, formula {formula}. Edit with the mouse or touch, or focus the canvas, choose with the arrow keys and press Enter to use the current tool.",
 "cleaned": "Cleaned up: bond lengths and angles evened out.",
 "smiles": "SMILES: {smiles}",
 "copied": "SMILES copied: {smiles}",
 "noSmiles": "An atom is over its usual valence. Fix it before exporting SMILES.",
 "download": "Saved {file}. It opens in ChemDraw.",
 "keys": "Tip: rest the pointer on an atom and type C, N, O, S, F or L (Cl) to change it; on a bond, type 1, 2 or 3. Delete removes it.",
 "redone": "Redone.",
 "placed": "Carbon placed.",
 "bonded": "Bond added.",
 "alreadyBonded": "Those two atoms are already bonded.",
 "cursorAtom": "{sym}, {n} bonds",
 "cursorBond": "{order} bond",
 "linkCopied": "Share link copied.",
 "link": "Share link: {url}",
 "tooBig": "This structure is too large for a link.",
 "ringPlaced": "Benzene ring placed.",
 "drawing": "this structure",
 "daily": {
  "button": "Daily molecule",
  "title": "Daily molecule #{n}",
  "streak": "{n}-day streak",
  "shareTitle": "ChemDraw Skill daily molecule #{n}",
  "shareMoves": "{moves} moves",
  "share": "Share result",
  "shared": "Result copied.",
  "shareText": "Result: {text}",
  "lab": "Continue in the Lab",
  "line": "Daily molecule #{n}: start from {mol}.",
  "lineStreak": "Daily molecule #{n}: start from {mol}. {days}-day streak.",
  "solved": "Today’s molecule is done. Come back tomorrow.",
  "again": "Play again"
 },
 "lab": {
  "modes": {
   "daily": "Daily",
   "levels": "Route map",
   "hunt": "Spot the error",
   "isomers": "Isomers",
   "dex": "Collection",
   "free": "Sketchpad"
  },
  "chapters": {
   "take": {
    "title": "Take away",
    "text": "Start from five familiar molecules and remove groups."
   },
   "swap": {
    "title": "Swap",
    "text": "Change one atom, or move one group."
   },
   "add": {
    "title": "Build up",
    "text": "Add new carbons and grow the molecule."
   }
  },
  "stats": {
   "stars": "Stars",
   "streak": "Day streak",
   "compounds": "Compounds",
   "badges": "Badges"
  },
  "moves": "Moves",
  "par": "Fewest moves",
  "target": "Target formula",
  "starsLabel": "{n} of 3 stars",
  "unsolved": "Not solved",
  "lockedName": "Locked",
  "backToRoute": "Back to the route map",
  "restart": "Start over",
  "nextLevel": "Next level",
  "solvedIn": "Solved in {moves} moves.",
  "starsHelp": "Three stars for the fewest moves with no hint, two for no hint, one with a hint.",
  "dexIntro": "Each solved level unlocks a compound. Save any of them as CDXML, or copy a request for your agent.",
  "dexEmpty": "Solve the first level on the route map and its compound appears here.",
  "saveCdxml": "Save .cdxml",
  "copyAsk": "Copy agent request",
  "openBoard": "Open in sketchpad",
  "ask": "Use ChemDraw Skill to draw {name} as editable CDXML, render it in ChemDraw and show me the PNG.",
  "badgesTitle": "Badges",
  "badges": {
   "first": {
    "title": "First molecule",
    "text": "Solve any level."
   },
   "perfect": {
    "title": "Not one move wasted",
    "text": "Earn three stars once."
   },
   "xanthines": {
    "title": "The xanthine family",
    "text": "Solve all four of caffeine’s relatives."
   },
   "complete": {
    "title": "End of the route",
    "text": "Solve all 20 levels."
   },
   "readback": {
    "title": "Perfect readback",
    "text": "Clear all 8 rounds of Spot the error."
   },
   "isomers": {
    "title": "None missed",
    "text": "Find every isomer in a set."
   },
   "streak": {
    "title": "A full week",
    "text": "Solve the daily molecule 7 days running."
   },
   "export": {
    "title": "Back to ChemDraw",
    "text": "Save a .cdxml file."
   }
  },
  "badgeUnlocked": "Badge unlocked: {title}",
  "huntIntro": "The agent’s drawing has one error. Compare it with the correct structure and click the wrong atom or bond. These structures are wrong on purpose, for this game only.",
  "huntStart": "Start a game",
  "huntAgain": "Play again",
  "huntNext": "Next round",
  "huntRound": "Round {n} of {total}",
  "huntLives": "{n} tries left",
  "huntTruth": "Correct structure",
  "huntDrawn": "Agent’s drawing",
  "huntFound": "Found it: {kind}",
  "huntMiss": "Nothing wrong there. Look again.",
  "huntOver": "You cleared {n} rounds. Your best is {best}.",
  "huntClear": "All 8 rounds cleared. That is how a readback catches an error.",
  "huntBest": "Best {n} of 8",
  "huntMirror": "This drawing is mirrored.",
  "huntAtom": "{sym} atom",
  "huntBond": "{order} bond",
  "huntKinds": {
   "element": "The wrong element.",
   "ringN": "A ring carbon was written as nitrogen.",
   "order": "The wrong bond order.",
   "extra": "An extra methyl.",
   "missing": "A missing atom.",
   "valence": "This carbon has more than four bonds."
  },
  "isoIntro": "Start from a blank canvas and draw every constitutional isomer of the formula. Stereoisomers do not count.",
  "isoPick": "Choose a formula",
  "isoProgress": "{n} of {total} found",
  "isoFound": "A new one!",
  "isoSeen": "You already found that one.",
  "isoDone": "You found them all.",
  "isoClear": "Clear the canvas",
  "isoHint": "Current formula {formula}",
  "isoEmpty": "Blank canvas",
  "freeIntro": "Draw anything, then copy its SMILES, save it as CDXML or turn it into a link.",
  "freeLoad": "Start from",
  "freeBlank": "Blank canvas",
  "sharedLoaded": "Opened the shared structure.",
  "sharedBad": "The structure in this link could not be read, so a blank canvas is open.",
  "reset": "Clear progress",
  "resetConfirm": "Click again to clear",
  "resetDone": "Progress cleared.",
  "prog": "Your progress stays in this browser and is never uploaded.",
  "from": "Starting molecule"
 }
};
