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
from .critic_explanation_formatter import (
    CriticExplanationFormatter,
    CriticExplanation,
    ExplanationStyle,
    ConfidenceLevel,
    format_critic_output,
    format_multiple_critics
)
from .aggregated_explanation_builder import (
    AggregatedExplanationBuilder,
    AggregatedExplanation,
    AggregationMode,
    ConsensusLevel,
    VerdictAnalysis,
    ConsistencyAnalysis,
    aggregate_explanations
)
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
    'CriticExplanationFormatter',
    'CriticExplanation',
    'ExplanationStyle',
    'ConfidenceLevel',
    'format_critic_output',
    'format_multiple_critics',
    'AggregatedExplanationBuilder',
    'AggregatedExplanation',
    'AggregationMode',
    'ConsensusLevel',
    'VerdictAnalysis',
    'ConsistencyAnalysis',
    'aggregate_explanations',
    'XAIPerformanceOptimizer',
    'ExplanationMode',
    'PerformanceMetrics',
    'BenchmarkResults',
    'LazyExplanation',
    'XAIBenchmarkSuite',
    'get_optimizer'
]
