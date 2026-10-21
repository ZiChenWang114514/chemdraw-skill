#!/usr/bin/env python3
"""
NMR Data Extractor — standalone CLI wrapper.

Extracts reported NMR data strings (1H, 13C, 19F, etc.) from MestReNova
PDF exports.  Delegates to procedure_writer.extract_nmr_data().

Usage:
    python extract_nmr.py path/to/nmr.pdf [path/to/nmr2.pdf ...]
"""

import argparse
import sys

from .procedure_writer import extract_nmr_data


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Extract NMR data from PDFs")
    parser.add_argument('files', nargs='+', help='NMR PDF files')
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='Output file (default: stdout)')
    args = parser.parse_args(argv)

    seen = set()
    results = []
    for pdf in args.files:
        for line in extract_nmr_data(pdf):
            if line not in seen:
                seen.add(line)
                results.append(line)

    output = "\n".join(results)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output + "\n")
        print(f"Wrote {len(results)} NMR entries to {args.output}",
              file=sys.stderr)
    else:
        if output:
            print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
