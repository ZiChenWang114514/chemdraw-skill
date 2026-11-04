"""Match each sample of a parsed OpenLynx .rpt to the product its platemap row expects.

Usage (runtime Python, after `cdx.py call parse_analysis_file --json '{"pdf_path": "plate.rpt", "output_path": "parsed.json"}'`):
    cdx.py py match_plate.py parsed.json platemap.csv out.json

Sample N of the report is platemap row N. For each peak the expected [M+H]+ / [M-H]- is looked for among the
peak's strongest ions (with the +1 to +4 isotope steps of Cl, Br and 13C), then the Boc-type fragments
[M+H-C4H8]+ and [M+H-Boc]+. An intact molecular ion wins over a fragment; ties go to the larger peak.
"""
import csv
import json
import sys

from rdkit import Chem
from rdkit.Chem.Descriptors import ExactMolWt

PROTON = 1.00728
KINDS = [("[M+H]+", PROTON, "ES+"), ("[M-H]-", -PROTON, "ES-"),
         ("[M+H-C4H8]+", PROTON - 56.0626, "ES+"), ("[M+H-Boc]+", PROTON - 100.0524, "ES+")]


def match(sample, mono):
    found = {}
    for peak in sample["peaks"]:
        for rank, (label, shift, mode) in enumerate(KINDS):
            for spectrum in peak["ms_spectra"]:
                if not spectrum["mode"].startswith(mode):
                    continue
                for ion in spectrum["top_ions"]:
                    if any(abs(ion - (mono + shift + step * 1.0034)) < 0.6 for step in range(5)):
                        if peak["peak_num"] not in found or rank < found[peak["peak_num"]][2]:
                            found[peak["peak_num"]] = (peak, (spectrum["mode"], ion, label), rank)
    return min(found.values(), key=lambda c: (c[2], -c[0]["area_pct"]), default=None)


def main(parsed, platemap, output):
    samples = json.load(open(parsed, encoding="utf-8"))["data"]["samples"]
    plate = list(csv.DictReader(open(platemap, encoding="utf-8-sig")))
    rows = []
    for sample, well in zip(samples, plate):
        mono = ExactMolWt(Chem.MolFromSmiles(well["Desired Product Smiles"]))
        row = {"well": well["Well"], "smiles": well["Desired Product Smiles"], "expected_MH": round(mono + PROTON, 2),
               "peaks_in_sample": len(sample["peaks"])}
        best = match(sample, mono)
        if best:
            peak, (mode, ion, label), _ = best
            row.update(found=True, rt_min=peak["rt"], area_pct=peak["area_pct"], ion=ion, mode=mode, assigned_as=label)
        else:
            row["found"] = False
        rows.append(row)
    json.dump(rows, open(output, "w", encoding="utf-8"), indent=1)
    return rows


if __name__ == "__main__":
    main(*sys.argv[1:4])
