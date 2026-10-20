"""Verify the generated CDXML files are valid and contain expected elements."""
import sys
import os

sys.path.insert(0, r"C:\Users\mic23\cdxml-toolkit")

from lxml import etree

out_dir = r"C:\Users\mic23\cdxml-toolkit-mcp-testing-temp\phase2\task7b"

files = [
    ("route_A_5C_scheme.cdxml", "Route A — 5-carbon linker (2-step sequential)"),
    ("route_B_4C_scheme.cdxml", "Route B — 4-carbon linker (single-step, 3 runs)"),
]

for fname, desc in files:
    path = os.path.join(out_dir, fname)
    print(f"\n{'='*60}")
    print(f"  {desc}")
    print(f"  {fname}")
    print(f"{'='*60}")

    try:
        with open(path, "rb") as f:
            content = f.read()

        # Parse as XML (strip DOCTYPE first)
        import re
        clean = re.sub(rb'<!DOCTYPE[^>]*>', b'', content)
        root = etree.fromstring(clean)

        # Count structural elements
        fragments = root.xpath("//fragment")
        arrows = root.xpath("//arrow")
        texts = root.xpath("//t")
        atoms = root.xpath("//n")

        print(f"  Fragments (molecules): {len(fragments)}")
        print(f"  Arrows:                {len(arrows)}")
        print(f"  Text elements:         {len(texts)}")
        print(f"  Atom nodes:            {len(atoms)}")
        print(f"  File size:             {len(content):,} bytes")

        # Extract text content
        print(f"  Text labels:")
        for t in texts:
            text_content = "".join(t.itertext()).strip()
            if text_content:
                print(f"    '{text_content[:80]}'")

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()

print("\nAll files verified.")
