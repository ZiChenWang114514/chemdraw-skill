"""Skill helpers (cdx, acs_builder, image_review_workspace, ...) live in scripts/."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
