"""
EJC Explainability Module

Multi-modal explainability pipeline implementing World Bank AI Governance
recommendations for transparency and interpretability.
"""

from .xai_pipeline import XAIPipeline, ExplanationLevel, XAIMethod
from .counterfactual_generator import CounterfactualGenerator, CounterfactualMode, Counterfactual
from .shap_explainer import SHAPExplainer, SHAPExplanation
from .decision_visualizer import DecisionVisualizer, VisualizationType, ExportFormat
from .multi_level_explainer import MultiLevelExplainer, AudienceLevel, MultiLevelExplanation
from .precedent_analyzer import PrecedentAnalyzer, ComparisonType, PrecedentComparison
from .xai_performance import (
    XAIPerformanceOptimizer,
    ExplanationMode,
    PerformanceMetrics,
    BenchmarkResults,
    LazyExplanation,
    XAIBenchmarkSuite,
    get_optimizer
)

__all__ = [
    'XAIPipeline',
    'ExplanationLevel',
    'XAIMethod',
    'CounterfactualGenerator',
    'CounterfactualMode',
    'Counterfactual',
    'SHAPExplainer',
    'SHAPExplanation',
    'DecisionVisualizer',
    'VisualizationType',
    'ExportFormat',
    'MultiLevelExplainer',
    'AudienceLevel',
    'MultiLevelExplanation',
    'PrecedentAnalyzer',
    'ComparisonType',
    'PrecedentComparison',
    'XAIPerformanceOptimizer',
    'ExplanationMode',
    'PerformanceMetrics',
    'BenchmarkResults',
    'LazyExplanation',
    'XAIBenchmarkSuite',
    'get_optimizer'
]
