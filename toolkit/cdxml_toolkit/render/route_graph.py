"""Shape of a multi-step route, read from which step makes what another step uses.

A route is a set of steps, each with substrates and products. This module
decides whether the steps form a linear chain, a convergent route (arms that
merge) or reactions from one starting material (divergent), and for a
convergent route splits it into rows. Anything else is refused rather than
approximated.
"""
from __future__ import annotations

from .schema import StepDescriptor

_UNSUPPORTED = (
    "The steps are not a linear route, a convergent route (arms that merge) or a set of "
    "reactions from one starting material, so they cannot be laid out."
)


def _graph(steps: list[StepDescriptor]):
    producer: dict[str, int] = {}
    for index, step in enumerate(steps):
        for species in step.products:
            if species in producer:
                raise ValueError(f"Species {species} is produced by more than one step.")
            producer[species] = index
    consumers: dict[str, list[int]] = {}
    for index, step in enumerate(steps):
        for species in step.substrates:
            consumers.setdefault(species, []).append(index)
    feeders = [
        list(dict.fromkeys(producer[s] for s in step.substrates if s in producer and producer[s] != i))
        for i, step in enumerate(steps)
    ]
    return producer, consumers, feeders


def _topological(feeders: list[list[int]]) -> list[int]:
    remaining, order = set(range(len(feeders))), []
    while remaining:
        ready = [i for i in sorted(remaining) if all(f not in remaining for f in feeders[i])]
        if not ready:
            raise ValueError("The steps form a cycle: a product feeds back into its own route.")
        order.append(ready[0])
        remaining.discard(ready[0])
    return order


def classify_route(steps: list[StepDescriptor]) -> tuple[str, list[int]]:
    """Return ``(kind, order)``: kind is linear, convergent or divergent, order the step indices to draw."""
    if not steps:
        raise ValueError("The route has no steps.")
    producer, consumers, feeders = _graph(steps)
    order = _topological(feeders)
    if len(steps) == 1:
        return "linear", [0]

    consumed = {species for species in consumers if species in producer}
    finals = [i for i, step in enumerate(steps) if not any(p in consumed for p in step.products)]
    shared = [species for species, users in consumers.items() if len(users) > 1]

    if not shared and len(finals) == 1:
        chain = all(feeders[order[k]] == ([order[k - 1]] if k else []) for k in range(len(order)))
        return ("linear" if chain else "convergent"), order
    if len(shared) == 1 and len(finals) == len(steps) and all(shared[0] in s.substrates for s in steps):
        return "divergent", list(range(len(steps)))
    raise ValueError(_UNSUPPORTED)


def convergent_sections(steps: list[StepDescriptor]) -> list[list[StepDescriptor]]:
    """Rows of a convergent route: each arm first, then the merge row (with any chain after it)."""
    kind, order = classify_route(steps)
    if kind == "divergent":
        raise ValueError("A route from one starting material is divergent, not convergent.")
    _, _, feeders = _graph(steps)
    sections: list[list[StepDescriptor]] = []

    def build(last: int) -> None:
        chain, current = [last], last
        while len(feeders[current]) == 1:
            current = feeders[current][0]
            chain.insert(0, current)
        for feeder in feeders[current]:
            build(feeder)
        sections.append([steps[i] for i in chain])

    build(order[-1])
    return sections
