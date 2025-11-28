"""
Advanced context system for jurisdiction-aware, culturally-sensitive decision making.

Provides:
- Jurisdiction-aware reasoning (legal/regulatory context)
- Cultural norm adaptation
- Domain-specific ethics tuning
"""

from .context_manager import ContextManager
from .jurisdiction import JurisdictionContext, JurisdictionRegistry
from .cultural import CulturalContext, CulturalNormAdapter
from .domain import DomainContext, DomainSpecialization

__all__ = [
    "ContextManager",
    "JurisdictionContext",
    "JurisdictionRegistry",
    "CulturalContext",
    "CulturalNormAdapter",
    "DomainContext",
    "DomainSpecialization",
]
