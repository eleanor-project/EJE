"""
EJC Ethical Trade-Off Engine

Detects and resolves ethical value tensions in AI decision-making.
Implements World Bank AI Governance Report recommendations for
managing conflicts between fairness, transparency, privacy, and accountability.
"""

from .tradeoff_engine import (
    TradeOffEngine,
    EthicalPrinciple,
    TradeOffType,
    TradeOffDetection,
    TradeOffResolution
)

__all__ = [
    'TradeOffEngine',
    'EthicalPrinciple',
    'TradeOffType',
    'TradeOffDetection',
    'TradeOffResolution'
]
