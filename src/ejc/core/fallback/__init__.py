"""
Fallback Engine Module

Provides fallback logic, evidence bundles, and explanation generation
for error scenarios and graceful degradation.
"""

from .fallback_engine import FallbackEngine, FallbackStrategy, FallbackTrigger
from .fallback_bundle import create_fallback_evidence_bundle
from .fallback_explainer import FallbackExplainer

__all__ = [
    'FallbackEngine',
    'FallbackStrategy',
    'FallbackTrigger',
    'create_fallback_evidence_bundle',
    'FallbackExplainer'
]
