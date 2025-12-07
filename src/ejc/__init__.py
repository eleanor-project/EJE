"""Eleanor Ethical Jurisprudence Core (EJC).

Constitutional AI governance framework implementing RBJA principles.
"""

from typing import TYPE_CHECKING

__version__ = "1.5.0"

__all__ = [
    "EthicalReasoningEngine",
    "Decision",
    "adjudicate",
    "__version__",
]


if TYPE_CHECKING:  # pragma: no cover - imported for type checkers only
    from .core.ethical_reasoning_engine import EthicalReasoningEngine
    from .core.decision import Decision
    from .core.adjudicate import adjudicate


def __getattr__(name: str):
    if name == "EthicalReasoningEngine":
        from .core.ethical_reasoning_engine import EthicalReasoningEngine

        return EthicalReasoningEngine

    if name == "Decision":
        from .core.decision import Decision

        return Decision

    if name == "adjudicate":
        from .core.adjudicate import adjudicate

        return adjudicate

    raise AttributeError(f"module 'ejc' has no attribute {name!r}")
