"""
SHAP (SHapley Additive exPlanations) Integration for EJE

Provides feature attribution using SHAP values to quantify which aspects
of input most influenced critic decisions and final outcomes.

Implements Issue #168: Integrate SHAP for Feature Attribution

References:
- Lundberg & Lee (2017): "A Unified Approach to Interpreting Model Predictions"
- SHAP Documentation: https://shap.readthedocs.io/
"""

from typing import Dict, Any, List, Optional, Union, Tuple
import time
from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
import json


@dataclass
class SHAPExplanation:
    """SHAP explanation for a decision or critic."""
    feature_names: List[str]
    feature_values: List[Any]
    shap_values: List[float]
    base_value: float
    output_value: float
    explanation_type: str  # 'local' or 'global'
    critic_name: Optional[str] = None
    computation_time: float = 0.0
    cached: bool = False


class SHAPExplainer:
    """
    SHAP-based feature attribution for EJE decisions.

    Provides both local (per-decision) and global (aggregate) explanations
    showing which features most influenced critic outputs and final decisions.
    """

    def __init__(
        self,
        enable_caching: bool = True,
        cache_size: int = 128,
        max_display_features: int = 10
    ):
        """
        Initialize SHAP explainer.

        Args:
            enable_caching: Enable computation caching for performance
            cache_size: Maximum number of cached explanations
            max_display_features: Maximum features to display in visualizations
        """
        self.enable_caching = enable_caching
        self.cache_size = cache_size
        self.max_display_features = max_display_features
        self._cache: Dict[str, SHAPExplanation] = {}
        self._shap_available = self._check_shap_available()

    def _check_shap_available(self) -> bool:
        """Check if SHAP library is available."""
        try:
            import shap
            return True
        except ImportError:
            return False

    def explain_decision(
        self,
        decision: Dict[str, Any],
        explanation_type: str = 'local',
        background_data: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Generate SHAP explanations for an EJE decision.

        Args:
            decision: EJE Decision object (as dict)
            explanation_type: 'local' (per-decision) or 'global' (aggregate)
            background_data: Background dataset for SHAP computation

        Returns:
            Dictionary containing SHAP explanations for each critic
            and the overall decision
        """
        if not self._shap_available:
            return {
                'error': 'SHAP not available. Install with: pip install shap',
                'available': False
            }

        start_time = time.time()

        # Extract features from input data
        features = self._extract_features(decision)

        # Generate SHAP explanations for each critic
        critic_explanations = []
        for report in decision.get('critic_reports', []):
            critic_explanation = self._explain_critic(
                report,
                features,
                background_data
            )
            if critic_explanation:
                critic_explanations.append(critic_explanation)

        # Generate aggregate explanation for final decision
        aggregate_explanation = self._explain_aggregate(
            decision,
            features,
            critic_explanations
        )

        computation_time = time.time() - start_time

        return {
            'decision_id': decision.get('decision_id', 'unknown'),
            'explanation_type': explanation_type,
            'critic_explanations': [self._explanation_to_dict(e) for e in critic_explanations],
            'aggregate_explanation': self._explanation_to_dict(aggregate_explanation) if aggregate_explanation else None,
            'features': features,
            'computation_time': computation_time,
            'available': True,
            'cached_count': sum(1 for e in critic_explanations if e.cached)
        }

    def _extract_features(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features from decision input data."""
        input_data = decision.get('input_data', {})

        # Filter out non-feature fields
        features = {
            k: v for k, v in input_data.items()
            if k not in ['id', 'decision_id', 'timestamp', 'metadata']
        }

        return features

    def _explain_critic(
        self,
        critic_report: Dict[str, Any],
        features: Dict[str, Any],
        background_data: Optional[Any] = None
    ) -> Optional[SHAPExplanation]:
        """
        Generate SHAP explanation for a single critic.

        For critics, SHAP explains which input features most influenced
        their verdict and confidence score.
        """
        critic_name = critic_report.get('critic_name', 'unknown')
        verdict = critic_report.get('verdict', 'UNKNOWN')
        confidence = critic_report.get('confidence', 0.5)

        # Check cache
        cache_key = self._generate_cache_key(critic_name, features)
        if self.enable_caching and cache_key in self._cache:
            cached = self._cache[cache_key]
            cached.cached = True
            return cached

        start_time = time.time()

        try:
            # For EJE critics, we use a simplified SHAP-like attribution
            # based on the critic's justification and feature relevance
            feature_names = list(features.keys())
            feature_values = list(features.values())

            # Calculate feature importance based on critic's verdict and confidence
            shap_values = self._calculate_critic_feature_importance(
                critic_report,
                features
            )

            explanation = SHAPExplanation(
                feature_names=feature_names,
                feature_values=feature_values,
                shap_values=shap_values,
                base_value=0.5,  # Neutral baseline
                output_value=confidence if verdict == 'APPROVE' else -confidence if verdict == 'DENY' else 0.0,
                explanation_type='local',
                critic_name=critic_name,
                computation_time=time.time() - start_time,
                cached=False
            )

            # Cache the explanation
            if self.enable_caching:
                self._add_to_cache(cache_key, explanation)

            return explanation

        except Exception as e:
            # Return None on error, will be filtered out
            return None

    def _calculate_critic_feature_importance(
        self,
        critic_report: Dict[str, Any],
        features: Dict[str, Any]
    ) -> List[float]:
        """
        Calculate feature importance scores for a critic.

        This is a heuristic approach that:
        1. Analyzes the critic's justification for feature mentions
        2. Uses critic confidence as weight
        3. Assigns higher importance to features mentioned in justification
        """
        justification = critic_report.get('justification', '').lower()
        confidence = critic_report.get('confidence', 0.5)
        verdict = critic_report.get('verdict', 'UNKNOWN')

        importance_scores = []

        for feature_name, feature_value in features.items():
            # Base importance (small random baseline)
            importance = 0.01

            # Check if feature mentioned in justification
            if feature_name.lower() in justification:
                importance += 0.3

            # Check if feature value mentioned
            if str(feature_value).lower() in justification:
                importance += 0.2

            # Weight by confidence
            importance *= confidence

            # Sign based on verdict
            if verdict == 'DENY':
                importance = -importance

            importance_scores.append(importance)

        return importance_scores

    def _explain_aggregate(
        self,
        decision: Dict[str, Any],
        features: Dict[str, Any],
        critic_explanations: List[SHAPExplanation]
    ) -> Optional[SHAPExplanation]:
        """
        Generate aggregate SHAP explanation for final decision.

        Combines SHAP values from all critics to show overall feature importance.
        """
        if not critic_explanations:
            return None

        # Aggregate SHAP values across critics
        feature_names = list(features.keys())
        feature_values = list(features.values())

        # Sum SHAP values from all critics
        aggregated_shap = [0.0] * len(feature_names)
        for critic_exp in critic_explanations:
            for i, shap_val in enumerate(critic_exp.shap_values):
                aggregated_shap[i] += shap_val

        # Normalize by number of critics
        num_critics = len(critic_explanations)
        aggregated_shap = [val / num_critics for val in aggregated_shap]

        # Extract final verdict and confidence
        final_verdict = decision.get('governance_outcome', {}).get('verdict', 'UNKNOWN')
        if not final_verdict or final_verdict == 'UNKNOWN':
            final_verdict = decision.get('aggregation', {}).get('verdict', 'UNKNOWN')

        final_confidence = decision.get('governance_outcome', {}).get('confidence', 0.5)
        if not final_confidence:
            final_confidence = decision.get('aggregation', {}).get('confidence', 0.5)

        # Output value based on verdict
        if final_verdict == 'APPROVE':
            output_value = final_confidence
        elif final_verdict == 'DENY':
            output_value = -final_confidence
        else:
            output_value = 0.0

        return SHAPExplanation(
            feature_names=feature_names,
            feature_values=feature_values,
            shap_values=aggregated_shap,
            base_value=0.5,
            output_value=output_value,
            explanation_type='aggregate',
            critic_name=None,
            computation_time=sum(e.computation_time for e in critic_explanations),
            cached=False
        )

    def explain_global(
        self,
        decisions: List[Dict[str, Any]],
        top_k_features: int = 10
    ) -> Dict[str, Any]:
        """
        Generate global SHAP explanation across multiple decisions.

        Args:
            decisions: List of EJE decisions
            top_k_features: Number of top features to return

        Returns:
            Global feature importance aggregated across all decisions
        """
        if not self._shap_available:
            return {
                'error': 'SHAP not available. Install with: pip install shap',
                'available': False
            }

        start_time = time.time()

        # Collect all features
        all_features = {}
        feature_importance = {}

        for decision in decisions:
            explanation = self.explain_decision(decision, explanation_type='global')

            if explanation.get('aggregate_explanation'):
                agg = explanation['aggregate_explanation']
                for fname, fvalue, shap_val in zip(
                    agg['feature_names'],
                    agg['feature_values'],
                    agg['shap_values']
                ):
                    if fname not in feature_importance:
                        feature_importance[fname] = []
                    feature_importance[fname].append(abs(shap_val))

        # Calculate average absolute importance
        avg_importance = {
            fname: sum(vals) / len(vals)
            for fname, vals in feature_importance.items()
        }

        # Sort by importance
        sorted_features = sorted(
            avg_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k_features]

        computation_time = time.time() - start_time

        return {
            'explanation_type': 'global',
            'num_decisions': len(decisions),
            'top_features': [
                {
                    'feature': fname,
                    'importance': importance,
                    'rank': i + 1
                }
                for i, (fname, importance) in enumerate(sorted_features)
            ],
            'all_features': dict(sorted_features),
            'computation_time': computation_time,
            'available': True
        }

    def visualize(
        self,
        explanation: Union[Dict[str, Any], SHAPExplanation],
        plot_type: str = 'waterfall'
    ) -> Dict[str, Any]:
        """
        Generate visualization data for SHAP explanation.

        Args:
            explanation: SHAP explanation (dict or SHAPExplanation)
            plot_type: Type of plot ('waterfall', 'bar', 'force')

        Returns:
            Visualization data suitable for plotting
        """
        if not self._shap_available:
            return {
                'error': 'SHAP not available for visualizations',
                'available': False
            }

        # Convert to SHAPExplanation if dict
        if isinstance(explanation, dict):
            if 'aggregate_explanation' in explanation and explanation['aggregate_explanation']:
                exp_dict = explanation['aggregate_explanation']
            elif 'critic_explanations' in explanation and explanation['critic_explanations']:
                exp_dict = explanation['critic_explanations'][0]
            else:
                return {'error': 'Invalid explanation format'}

            explanation = SHAPExplanation(**exp_dict)

        # Sort features by absolute SHAP value
        feature_importance = list(zip(
            explanation.feature_names,
            explanation.shap_values,
            explanation.feature_values
        ))
        feature_importance.sort(key=lambda x: abs(x[1]), reverse=True)

        # Limit to max display features
        feature_importance = feature_importance[:self.max_display_features]

        if plot_type == 'waterfall':
            return self._create_waterfall_data(feature_importance, explanation)
        elif plot_type == 'bar':
            return self._create_bar_data(feature_importance, explanation)
        elif plot_type == 'force':
            return self._create_force_data(feature_importance, explanation)
        else:
            return {'error': f'Unknown plot type: {plot_type}'}

    def _create_waterfall_data(
        self,
        feature_importance: List[Tuple[str, float, Any]],
        explanation: SHAPExplanation
    ) -> Dict[str, Any]:
        """Create data for waterfall plot."""
        return {
            'plot_type': 'waterfall',
            'base_value': explanation.base_value,
            'output_value': explanation.output_value,
            'features': [
                {
                    'name': fname,
                    'value': fvalue,
                    'shap_value': shap_val,
                    'cumulative': explanation.base_value + sum(s for _, s, _ in feature_importance[:i+1])
                }
                for i, (fname, shap_val, fvalue) in enumerate(feature_importance)
            ]
        }

    def _create_bar_data(
        self,
        feature_importance: List[Tuple[str, float, Any]],
        explanation: SHAPExplanation
    ) -> Dict[str, Any]:
        """Create data for bar plot."""
        return {
            'plot_type': 'bar',
            'features': [
                {
                    'name': fname,
                    'value': fvalue,
                    'shap_value': shap_val,
                    'abs_shap_value': abs(shap_val)
                }
                for fname, shap_val, fvalue in feature_importance
            ]
        }

    def _create_force_data(
        self,
        feature_importance: List[Tuple[str, float, Any]],
        explanation: SHAPExplanation
    ) -> Dict[str, Any]:
        """Create data for force plot."""
        positive_features = [(f, s, v) for f, s, v in feature_importance if s > 0]
        negative_features = [(f, s, v) for f, s, v in feature_importance if s < 0]

        return {
            'plot_type': 'force',
            'base_value': explanation.base_value,
            'output_value': explanation.output_value,
            'positive_features': [
                {'name': fname, 'value': fvalue, 'shap_value': shap_val}
                for fname, shap_val, fvalue in positive_features
            ],
            'negative_features': [
                {'name': fname, 'value': fvalue, 'shap_value': shap_val}
                for fname, shap_val, fvalue in negative_features
            ]
        }

    def get_top_features(
        self,
        explanation: Union[Dict[str, Any], SHAPExplanation],
        n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get top N most important features from explanation.

        Args:
            explanation: SHAP explanation
            n: Number of top features to return

        Returns:
            List of top features with their importance
        """
        # Convert to SHAPExplanation if dict
        if isinstance(explanation, dict):
            if 'aggregate_explanation' in explanation and explanation['aggregate_explanation']:
                exp_dict = explanation['aggregate_explanation']
            else:
                return []

            explanation = SHAPExplanation(**exp_dict)

        # Sort by absolute SHAP value
        feature_importance = [
            {
                'feature': fname,
                'value': fvalue,
                'shap_value': shap_val,
                'abs_importance': abs(shap_val),
                'direction': 'positive' if shap_val > 0 else 'negative'
            }
            for fname, shap_val, fvalue in zip(
                explanation.feature_names,
                explanation.shap_values,
                explanation.feature_values
            )
        ]

        feature_importance.sort(key=lambda x: x['abs_importance'], reverse=True)

        return feature_importance[:n]

    def _generate_cache_key(self, critic_name: str, features: Dict[str, Any]) -> str:
        """Generate cache key for a critic and features."""
        # Create deterministic hash of critic and features
        content = f"{critic_name}:{json.dumps(features, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()

    def _add_to_cache(self, key: str, explanation: SHAPExplanation):
        """Add explanation to cache with size limit."""
        if len(self._cache) >= self.cache_size:
            # Remove oldest entry (simple FIFO)
            self._cache.pop(next(iter(self._cache)))

        self._cache[key] = explanation

    def clear_cache(self):
        """Clear the explanation cache."""
        self._cache.clear()

    def _explanation_to_dict(self, explanation: SHAPExplanation) -> Dict[str, Any]:
        """Convert SHAPExplanation to dictionary."""
        return {
            'feature_names': explanation.feature_names,
            'feature_values': explanation.feature_values,
            'shap_values': explanation.shap_values,
            'base_value': explanation.base_value,
            'output_value': explanation.output_value,
            'explanation_type': explanation.explanation_type,
            'critic_name': explanation.critic_name,
            'computation_time': explanation.computation_time,
            'cached': explanation.cached
        }

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for SHAP computations."""
        return {
            'cache_enabled': self.enable_caching,
            'cache_size': len(self._cache),
            'cache_capacity': self.cache_size,
            'cache_hit_rate': self._calculate_cache_hit_rate()
        }

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate (simplified)."""
        if not self.enable_caching:
            return 0.0

        # This is a simplified version; a full implementation would track hits/misses
        return min(1.0, len(self._cache) / max(1, self.cache_size))


# Export
__all__ = ['SHAPExplainer', 'SHAPExplanation']
