"""compact_parser.py — Parse compact reaction scheme syntax into SchemeDescriptor.

Transforms a concise text notation (see COMPACT_SYNTAX.md) into the same
SchemeDescriptor dataclasses produced by the YAML parser.

Grammar highlights:
    ArBr{BrC1=CC=CC=C1} --> product{c1ccc(N2CCCCC2)cc1} (94%)
      above: piperidine{C1CCNCC1}, "Pd-RuPhos (0.5 mol%)"
      below: "NaOtBu, THF", "85 deg C, 6 hrs"
"""

from __future__ import annotations

import re
from typing import Optional

from .schema import (
    StructureRef,
    ArrowContent,
    StepDescriptor,
    RunArrowEntry,
    StepRunArrows,
    SchemeDescriptor,
    VALID_LAYOUTS,
    VALID_WRAPS,
    VALID_ARROW_STYLES,
)


# ── Error type ────────────────────────────────────────────────────────

class ParseError(Exception):
    """Syntax or semantic error with optional line number."""

    def __init__(self, message: str, line: int | None = None):
        self.line = line
        if line is not None:
            super().__init__(f"Line {line}: {message}")
        else:
            super().__init__(message)


# ── Low-level helpers ─────────────────────────────────────────────────

def _split_respecting(text: str, delimiter: str) -> list[str]:
    """Split *text* on *delimiter*, skipping occurrences inside ``{}`` or ``\"\"``."""
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    in_quote = False
    i = 0
    dlen = len(delimiter)
    while i < len(text):
        ch = text[i]
        if ch == '"' and depth == 0:
            in_quote = not in_quote
            current.append(ch)
        elif ch == '{' and not in_quote:
            depth += 1
            current.append(ch)
        elif ch == '}' and not in_quote:
            depth = max(depth - 1, 0)
            current.append(ch)
        elif (
            not in_quote
            and depth == 0
            and text[i : i + dlen] == delimiter
        ):
            parts.append("".join(current))
            current = []
            i += dlen
            continue
        else:
            current.append(ch)
        i += 1
    parts.append("".join(current))
    return parts


# Arrow regex fragments (compiled once)
_ARROW_PATTERNS = [
    # order matters: longer/more-specific first
    (re.compile(r"==>"), "solid"),       # parallel (arrow style is solid; layout implies parallel)
    (re.compile(r"\.\.>"), "dashed"),
    (re.compile(r"-->"), "solid"),
    (re.compile(r"[Xx]>"), "failed"),
]


def _find_arrows(line: str) -> list[tuple[int, int, str, str | None]]:
    """Return ``[(start, end, arrow_style, label_or_None), ...]`` for every
    arrow token in *line* that is outside ``{}`` and ``\"\"``."""
    arrows: list[tuple[int, int, str, str | None]] = []
    depth = 0
    in_quote = False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '"' and depth == 0:
            in_quote = not in_quote
            i += 1
            continue
        if ch == '{' and not in_quote:
            depth += 1
            i += 1
            continue
        if ch == '}' and not in_quote:
            depth = max(depth - 1, 0)
            i += 1
            continue
        if depth > 0 or in_quote:
            i += 1
            continue
        # Try each arrow pattern at position i
        for pat, style in _ARROW_PATTERNS:
            m = pat.match(line, i)
            if m:
                end = m.end()
                # Check for |label| immediately after
                label: str | None = None
                if end < len(line) and line[end] == '|':
                    pipe_close = line.find('|', end + 1)
                    if pipe_close > end:
                        label = line[end + 1 : pipe_close]
                        end = pipe_close + 1
                arrows.append((m.start(), end, style, label))
                i = end
                break
        else:
            i += 1
    return arrows


def _strip_trailing_yield(line: str) -> tuple[str, str | None]:
    """Remove a trailing ``(N%)`` yield annotation that is outside ``{}``.

    Returns ``(cleaned_line, yield_string_or_None)``.
    """
    depth = 0
    in_quote = False
    last_close = -1
    for i, ch in enumerate(line):
        if ch == '"' and depth == 0:
            in_quote = not in_quote
        elif ch == '{' and not in_quote:
            depth += 1
        elif ch == '}' and not in_quote:
            depth = max(depth - 1, 0)
        elif ch == ')' and depth == 0 and not in_quote:
            last_close = i
    if last_close < 1:
        return line, None
    # Walk backwards from last_close to find matching '('
    depth = 0
    in_quote = False
    open_pos = -1
    for i in range(last_close, -1, -1):
        ch = line[i]
        if ch == ')':
            depth += 1
        elif ch == '(':
            depth -= 1
            if depth == 0:
                open_pos = i
                break
    if open_pos < 0:
        return line, None
    content = line[open_pos + 1 : last_close]
    if '%' in content:
        return line[:open_pos].rstrip(), content
    return line, None


# ── Species token parsing ─────────────────────────────────────────────

_ID_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_-]*$')


def _parse_species_token(
    token: str, lineno: int | None = None
) -> tuple[str, str | None, str | None]:
    """Parse a single species token into ``(id, smiles_or_None, label_or_None)``.

    Accepted forms::

        ArBr                     → ("ArBr",  None,    None)
        ArBr{BrC1=CC=CC=C1}     → ("ArBr",  "BrC1…", None)
        "1"{BrC1=CC=CC=C1}      → ("1",     "BrC1…", "1")
        "1"                      → ("1",     None,    "1")
    """
    token = token.strip()
    if not token:
        raise ParseError("Empty species token", lineno)

    smiles: str | None = None
    label: str | None = None

    # Extract {SMILES}
    brace_open = -1
    depth = 0
    in_q = False
    for i, ch in enumerate(token):
        if ch == '"':
            in_q = not in_q
        elif ch == '{' and not in_q and depth == 0:
            brace_open = i
            depth += 1
        elif ch == '{' and not in_q:
            depth += 1
        elif ch == '}' and not in_q:
            depth -= 1

    if brace_open >= 0:
        brace_close = token.rfind('}')
        if brace_close <= brace_open:
            raise ParseError(f"Unclosed '{{' in species: {token}", lineno)
        smiles = token[brace_open + 1 : brace_close]
        id_part = token[:brace_open].strip()
    else:
        id_part = token

    # Quoted ID → also becomes label
    if id_part.startswith('"') and id_part.endswith('"') and len(id_part) >= 2:
        id_str = id_part[1:-1]
        label = id_str
    elif id_part.startswith('"'):
        raise ParseError(f"Unclosed quote in species ID: {token}", lineno)
    else:
        id_str = id_part

    if not id_str:
        raise ParseError(f"Empty species ID: {token}", lineno)

    return id_str, smiles, label


# ── Condition items parsing ───────────────────────────────────────────

def _parse_condition_items(
    text: str,
    structures: dict[str, StructureRef],
    lineno: int | None = None,
) -> ArrowContent:
    """Parse a comma-separated list of condition items into :class:`ArrowContent`.

    Rules:
    - ``"quoted text"`` → text label
    - ``bare_id`` → structure reference
    - ``bare_id{SMILES}`` → define structure inline + reference it
    """
    ac = ArrowContent()
    items = _split_respecting(text.strip(), ",")
    for raw in items:
        item = raw.strip()
        if not item:
            continue
        if item.startswith('"') and item.endswith('"') and len(item) >= 2:
            # Text label
            ac.text.append(item[1:-1])
        elif '{' in item:
            # Inline structure definition
            sid, smi, lbl = _parse_species_token(item, lineno)
            if sid not in structures:
                structures[sid] = StructureRef(id=sid, smiles=smi, label=lbl)
            elif smi and structures[sid].smiles is None:
                structures[sid].smiles = smi
            ac.structures.append(sid)
        else:
            # Bare structure reference
            ac.structures.append(item)
    return ac


# ── Run arrow parsing ─────────────────────────────────────────────────

def _parse_run_arrow(text: str, lineno: int | None = None) -> RunArrowEntry:
    """Parse ``"input" -> "output"`` into a :class:`RunArrowEntry`."""
    parts = text.split('->')
    if len(parts) != 2:
        raise ParseError(
            f"Run arrow must have exactly one '->': {text!r}", lineno
        )
    inp = parts[0].strip().strip('"')
    out = parts[1].strip().strip('"')
    if not inp or not out:
        raise ParseError(f"Empty input or output in run arrow: {text!r}", lineno)
    return RunArrowEntry(input_label=inp, output_label=out)


# ── Main parser ───────────────────────────────────────────────────────

def parse_compact(text: str) -> SchemeDescriptor:
    """Parse compact syntax text into a :class:`SchemeDescriptor`."""
    lines = text.split('\n')

    # Collected state
    directives: dict[str, str] = {}
    structures: dict[str, StructureRef] = {}
    reaction_chain_line: str | None = None
    reaction_chain_lineno: int | None = None
    # Conditions collected per step-number (1-indexed); 0 = implicit single-step
    step_above: dict[int, list[tuple[str, int]]] = {}   # step → [(raw_text, lineno)]
    step_below: dict[int, list[tuple[str, int]]] = {}
    step_runs: dict[int, list[tuple[str, int]]] = {}
    condition_key_entries: dict[str, str] = {}
    is_parallel = False

    current_step: int = 0  # 0 = implicit single-step context
    in_conditions_block = False

    for raw_lineno, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()

        # Blank line
        if not line or line.isspace():
            continue

        # Comment
        if line.lstrip().startswith('#'):
            continue

        # Row separator — not supported in compact syntax
        if line.strip() == '---':
            raise ParseError(
                "Row separators (---) are not supported in compact syntax. "
                "Use YAML format for stacked-rows layout.",
                raw_lineno,
            )

        # Directive
        if line.startswith('@'):
            in_conditions_block = False
            rest = line[1:].strip()
            if rest.startswith('conditions'):
                in_conditions_block = True
                continue
            parts = rest.split(None, 1)
            if not parts:
                raise ParseError("Empty directive", raw_lineno)
            key = parts[0]
            val = parts[1].strip('"') if len(parts) > 1 else ""
            directives[key] = val
            continue

        # Condition key entry: (a) "..."
        if in_conditions_block:
            m = re.match(r'^\(([a-zA-Z0-9,]+)\)\s*"(.*)"', line.strip())
            if m:
                condition_key_entries[m.group(1)] = m.group(2)
                continue
            else:
                in_conditions_block = False
                # fall through to other parsing

        # Step block header: "step N:"
        m_step = re.match(r'^step\s+(\d+)\s*:', line)
        if m_step:
            current_step = int(m_step.group(1))
            continue

        # Definition line: "id: {SMILES}" or "id: name ..." or "id: file ..."
        m_def = re.match(
            r'^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)', line
        )
        if m_def and not line.lstrip().startswith(('above', 'below', 'run')):
            sid = m_def.group(1)
            spec = m_def.group(2).strip()
            sref = StructureRef(id=sid)

            if spec.startswith('{'):
                close = spec.rfind('}')
                if close < 0:
                    raise ParseError(f"Unclosed '{{' in definition of {sid}", raw_lineno)
                sref.smiles = spec[1:close]
                remainder = spec[close + 1 :].strip()
                # Check for label "..."
                lm = re.match(r'label\s+"([^"]*)"', remainder)
                if lm:
                    sref.label = lm.group(1)
            elif spec.startswith('name'):
                nm = re.match(r'name\s+"([^"]*)"', spec)
                if nm:
                    sref.name = nm.group(1)
                else:
                    raise ParseError(f"Invalid name spec for {sid}", raw_lineno)
            elif spec.startswith('file'):
                fm = re.match(r'file\s+"([^"]*)"', spec)
                if fm:
                    sref.file = fm.group(1)
                else:
                    raise ParseError(f"Invalid file spec for {sid}", raw_lineno)
            else:
                raise ParseError(f"Unknown definition spec for {sid}: {spec}", raw_lineno)

            if sid in structures:
                raise ParseError(f"Duplicate structure definition: {sid}", raw_lineno)
            structures[sid] = sref
            continue

        # Indented condition/run line
        if line.startswith((' ', '\t')):
            stripped = line.strip()

            # Step-indexed: [N] above: ... or [N] below: ...
            m_idx = re.match(r'^\[(\d+)\]\s*(above|below)\s*:\s*(.*)', stripped)
            if m_idx:
                step_num = int(m_idx.group(1))
                position = m_idx.group(2)
                content = m_idx.group(3)
                target = step_above if position == 'above' else step_below
                target.setdefault(step_num, []).append((content, raw_lineno))
                continue

            # above: / below:
            if stripped.startswith('above:') or stripped.startswith('below:'):
                position = 'above' if stripped.startswith('above') else 'below'
                content = stripped.split(':', 1)[1].strip()
                target = step_above if position == 'above' else step_below
                target.setdefault(current_step, []).append((content, raw_lineno))
                continue

            # run: "in" -> "out"  or  run[N]: "in" -> "out"
            m_run = re.match(r'^run(?:\[(\d+)\])?\s*:\s*(.*)', stripped)
            if m_run:
                step_num = int(m_run.group(1)) if m_run.group(1) else current_step
                step_runs.setdefault(step_num, []).append(
                    (m_run.group(2), raw_lineno)
                )
                continue

        # If none of the above matched, try reaction chain
        # A reaction chain must contain at least one arrow
        arrows = _find_arrows(line)
        if arrows:
            if reaction_chain_line is not None:
                raise ParseError(
                    "Multiple reaction chains found (only one per scheme)",
                    raw_lineno,
                )
            reaction_chain_line = line
            reaction_chain_lineno = raw_lineno
            # Detect parallel arrow
            for _, _, style, _ in arrows:
                if style == "solid" and '==>' in line:
                    is_parallel = True
            continue

        # Before giving up, check for common syntax errors
        if '{' in line and line.count('{') != line.count('}'):
            raise ParseError(
                "Unclosed '{' in line (mismatched braces)", raw_lineno
            )
        if line.count('"') % 2 != 0:
            raise ParseError(
                "Unclosed quote in line (odd number of '\"')", raw_lineno
            )
        raise ParseError(f"Unrecognized line: {line!r}", raw_lineno)

    # ── Require a reaction chain ──────────────────────────────────
    if reaction_chain_line is None:
        raise ParseError("No reaction chain found (missing --> arrow)")

    # ── Parse reaction chain ──────────────────────────────────────
    chain = reaction_chain_line
    chain, yield_str = _strip_trailing_yield(chain)
    arrows = _find_arrows(chain)
    if not arrows:
        raise ParseError(
            "No arrow found in reaction chain", reaction_chain_lineno
        )

    # Extract segments between arrows
    segments: list[str] = []
    arrow_styles: list[str] = []
    arrow_labels: list[str | None] = []
    prev_end = 0
    for start, end, style, label in arrows:
        segments.append(chain[prev_end:start])
        arrow_styles.append(style)
        arrow_labels.append(label)
        prev_end = end
    segments.append(chain[prev_end:])  # last segment (products of last step)

    # Parse each segment into species
    segment_species: list[list[tuple[str, str | None, str | None]]] = []
    for seg in segments:
        species_tokens = _split_respecting(seg.strip(), '+')
        species_list: list[tuple[str, str | None, str | None]] = []
        for tok in species_tokens:
            tok = tok.strip()
            if not tok:
                continue
            species_list.append(
                _parse_species_token(tok, reaction_chain_lineno)
            )
        segment_species.append(species_list)

    # Validate: no empty segments
    for idx, seg in enumerate(segment_species):
        if not seg:
            if idx == 0:
                raise ParseError(
                    "Missing substrates before first arrow",
                    reaction_chain_lineno,
                )
            else:
                raise ParseError(
                    f"Missing species after arrow {idx}",
                    reaction_chain_lineno,
                )

    # Register all species as StructureRefs
    for seg in segment_species:
        for sid, smi, lbl in seg:
            if sid not in structures:
                structures[sid] = StructureRef(id=sid, smiles=smi, label=lbl)
            else:
                # Update SMILES / label if provided inline and not yet set
                if smi and structures[sid].smiles is None:
                    structures[sid].smiles = smi
                if lbl and structures[sid].label is None:
                    structures[sid].label = lbl

    # ── Build steps ───────────────────────────────────────────────
    num_steps = len(arrows)
    steps: list[StepDescriptor] = []

    for i in range(num_steps):
        substrates = [sid for sid, _, _ in segment_species[i]]
        products = [sid for sid, _, _ in segment_species[i + 1]]
        step_num = i + 1  # 1-indexed

        # Determine above/below content
        # Try step-indexed first, then fall back to implicit (key=0) for single-step
        above_key = step_num if step_num in step_above else (0 if num_steps == 1 else step_num)
        below_key = step_num if step_num in step_below else (0 if num_steps == 1 else step_num)

        above = ArrowContent()
        for raw_text, ln in step_above.get(above_key, []):
            ac = _parse_condition_items(raw_text, structures, ln)
            above.structures.extend(ac.structures)
            above.text.extend(ac.text)

        below = ArrowContent()
        for raw_text, ln in step_below.get(below_key, []):
            ac = _parse_condition_items(raw_text, structures, ln)
            below.structures.extend(ac.structures)
            below.text.extend(ac.text)

        # Arrow label → populate conditions from letter key if available
        lbl = arrow_labels[i]
        if lbl and condition_key_entries:
            # Letter conditions mode — put the full text below the arrow
            for letter in re.split(r'[,\s]+', lbl):
                letter = letter.strip()
                if letter in condition_key_entries:
                    below.text.append(condition_key_entries[letter])

        step = StepDescriptor(
            substrates=substrates,
            products=products,
            above_arrow=above if (above.structures or above.text) else None,
            below_arrow=below if (below.structures or below.text) else None,
            yield_=(yield_str if i == num_steps - 1 else None),
            number=step_num if num_steps > 1 else None,
            arrow_style=arrow_styles[i],
        )
        steps.append(step)

    # ── Build run arrows ──────────────────────────────────────────
    run_arrows: list[StepRunArrows] = []
    for step_key, run_lines in sorted(step_runs.items()):
        # Map key 0 → step 1
        step_num = step_key if step_key > 0 else 1
        entries: list[RunArrowEntry] = []
        for raw_text, ln in run_lines:
            entries.append(_parse_run_arrow(raw_text, ln))
        run_arrows.append(StepRunArrows(step=step_num, runs=entries))

    # ── Determine layout ──────────────────────────────────────────
    explicit_layout = 'layout' in directives
    layout = directives.get('layout', 'linear')
    if not explicit_layout:
        if is_parallel:
            layout = 'numbered-parallel'
        elif num_steps > 1:
            layout = 'sequential'
    if layout not in VALID_LAYOUTS:
        raise ParseError(f"Unknown layout: {layout!r}")

    wrap = directives.get('wrap', 'repeat')
    if wrap not in VALID_WRAPS:
        raise ParseError(f"Unknown wrap: {wrap!r}")

    steps_per_row: int | None = None
    if 'steps_per_row' in directives:
        try:
            steps_per_row = int(directives['steps_per_row'])
        except ValueError:
            raise ParseError(f"steps_per_row must be integer: {directives['steps_per_row']!r}")

    title = directives.get('title')

    cond_key = condition_key_entries if condition_key_entries else None

    # ── Validate references ───────────────────────────────────────
    for step in steps:
        for sid in step.substrates + step.products:
            if sid not in structures:
                raise ParseError(f"Undefined structure reference: {sid!r}")
        for ac in (step.above_arrow, step.below_arrow):
            if ac:
                for sid in ac.structures:
                    if sid not in structures:
                        raise ParseError(f"Undefined structure reference in conditions: {sid!r}")

    return SchemeDescriptor(
        structures=structures,
        steps=steps,
        layout=layout,
        wrap=wrap,
        steps_per_row=steps_per_row,
        title=title,
        run_arrows=run_arrows,
        condition_key=cond_key,
    )


def parse_compact_file(path: str) -> SchemeDescriptor:
    """Read a file and parse it as compact syntax."""
    with open(path, 'r', encoding='utf-8') as f:
        return parse_compact(f.read())
