"""Optional prediction engines (OCSR, reaction, retrosynthesis, NMR), each in its own environment.

The runtime never imports an engine's packages. Every engine runs in a separate interpreter under
``env.home()`` and is driven through a JSON pipe by ``worker.py``; Java engines run as a jar.
Results are model predictions: they carry ``provenance: "model_prediction"`` and are never merged
or picked silently.
"""


def __getattr__(name: str):
    if name in ("compare_shifts", "predict_shifts", "predict"):
        from . import nmr

        return getattr(nmr, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

