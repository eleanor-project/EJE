"""
EJC Core Module

Core ethical reasoning components.
"""

from .ethical_reasoning_engine import EthicalReasoningEngine
from .decision import Decision
from .adjudicate import adjudicate, adjudicate_simple
from .aggregator import Aggregator
from .config_loader import load_global_config

__all__ = [
    "EthicalReasoningEngine",
    "Decision",
    "adjudicate",
    "adjudicate_simple",
    "Aggregator",
    "load_global_config"
]
