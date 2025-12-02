"""
EJC Explainability Module

Multi-modal explainability pipeline implementing World Bank AI Governance
recommendations for transparency and interpretability.
"""

from .xai_pipeline import XAIPipeline, ExplanationLevel, XAIMethod
from .counterfactual_generator import CounterfactualGenerator, CounterfactualMode, Counterfactual

__all__ = [
    'XAIPipeline',
    'ExplanationLevel',
    'XAIMethod',
    'CounterfactualGenerator',
    'CounterfactualMode',
    'Counterfactual'
]
