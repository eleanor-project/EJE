"""EJC Core Module containing ethical reasoning components."""

from typing import TYPE_CHECKING

__all__ = [
    "EthicalReasoningEngine",
    "Decision",
    "adjudicate",
    "adjudicate_simple",
    "Aggregator",
    "load_global_config",
]


if TYPE_CHECKING:  # pragma: no cover - imported for type checkers only
    from .ethical_reasoning_engine import EthicalReasoningEngine
    from .decision import Decision
    from .adjudicate import adjudicate, adjudicate_simple
    from .aggregator import Aggregator
    from .config_loader import load_global_config


def __getattr__(name: str):
    if name == "EthicalReasoningEngine":
        from .ethical_reasoning_engine import EthicalReasoningEngine

        return EthicalReasoningEngine

    if name == "Decision":
        from .decision import Decision

        return Decision

    if name == "adjudicate":
        from .adjudicate import adjudicate

        return adjudicate

    if name == "adjudicate_simple":
        from .adjudicate import adjudicate_simple

        return adjudicate_simple

    if name == "Aggregator":
        from .aggregator import Aggregator

        return Aggregator

    if name == "load_global_config":
        from .config_loader import load_global_config

        return load_global_config

    raise AttributeError(f"module 'ejc.core' has no attribute {name!r}")
