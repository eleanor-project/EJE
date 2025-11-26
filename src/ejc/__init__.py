"""
Eleanor Ethical Jurisprudence Core (EJC)

Constitutional AI governance framework implementing RBJA principles.
"""

__version__ = "1.5.0"

from .core.ethical_reasoning_engine import EthicalReasoningEngine
from .core.decision import Decision
from .core.adjudicate import adjudicate

__all__ = [
    "EthicalReasoningEngine",
    "Decision",
    "adjudicate",
    "__version__"
]
