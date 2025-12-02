"""
EJC Explainability Module

Multi-modal explainability pipeline implementing World Bank AI Governance
recommendations for transparency and interpretability.
"""

from .xai_pipeline import XAIPipeline, ExplanationLevel, XAIMethod
from .counterfactual_generator import CounterfactualGenerator, CounterfactualMode, Counterfactual
from .shap_explainer import SHAPExplainer, SHAPExplanation

__all__ = [
    'XAIPipeline',
    'ExplanationLevel',
    'XAIMethod',
    'CounterfactualGenerator',
    'CounterfactualMode',
    'Counterfactual',
    'SHAPExplainer',
    'SHAPExplanation'
]
