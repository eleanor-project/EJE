"""
XAI Pipeline - Multimodal Explainability Pack (Phase 5A)

Implements explainability technologies aligned with World Bank AI Governance Report (Section 5.1).

Features:
- SHAP (SHapley Additive exPlanations)
- LIME (Local Interpretable Model-agnostic Explanations)
- Counterfactual Explanations
- Partial Dependence Plots (PDPs)
- Saliency Maps
- Multi-level explanations (executive, narrative, technical, visual)

References:
- World Bank Report Section 4.1: "Explainability"
- World Bank Report Section 5.1: "Explainability Technologies"
- Gunning (2017): DARPA XAI Program
"""

from typing import Dict, Any, Optional, List, Union
from enum import Enum
import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import counterfactual generator and SHAP explainer
from .counterfactual_generator import CounterfactualGenerator, CounterfactualMode
from .shap_explainer import SHAPExplainer, SHAPExplanation


class ExplanationLevel(Enum):
    """Explanation detail levels per World Bank recommendations."""
    EXECUTIVE = "executive"       # One-sentence summary
    NARRATIVE = "narrative"        # Plain language explanation
    TECHNICAL = "technical"        # Technical XAI output
    VISUAL = "visual"              # Visual explanations


class XAIMethod(Enum):
    """Supported XAI methods."""
    SHAP = "shap"
    LIME = "lime"
    COUNTERFACTUAL = "counterfactual"
    PDP = "pdp"
    SALIENCY = "saliency"
    ATTENTION = "attention"


class XAIPipeline:
    """
    Multimodal Explainability Pipeline.

    Provides model-agnostic and model-specific explanations at multiple
    levels of detail for different audiences.
    """

    def __init__(self):
        """Initialize XAI Pipeline with available methods."""
        self.available_methods = self._check_available_methods()
        self.counterfactual_generator = CounterfactualGenerator()
        self.shap_explainer = SHAPExplainer(enable_caching=True)

    def _check_available_methods(self) -> Dict[str, bool]:
        """Check which XAI libraries are available."""
        methods = {
            'shap': False,
            'lime': False,
            'alibi': False,
            'matplotlib': False
        }

        try:
            import shap
            methods['shap'] = True
        except ImportError:
            pass

        try:
            import lime
            methods['lime'] = True
        except ImportError:
            pass

        try:
            import alibi
            methods['alibi'] = True
        except ImportError:
            pass

        try:
            import matplotlib
            methods['matplotlib'] = True
        except ImportError:
            pass

        return methods

    def generate_explanation(
        self,
        model: Any,
        instance: Any,
        method: Union[XAIMethod, str] = XAIMethod.SHAP,
        level: Union[ExplanationLevel, str] = ExplanationLevel.NARRATIVE,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate explanation for a model prediction.

        Args:
            model: The model to explain (can be any sklearn-compatible model)
            instance: The instance to explain
            method: XAI method to use
            level: Explanation detail level
            **kwargs: Additional method-specific parameters

        Returns:
            Dictionary containing:
                - explanation: The generated explanation
                - method: Method used
                - level: Detail level
                - confidence: Confidence in explanation quality
                - visualizations: Optional visual outputs
        """
        # Convert to enums if strings provided
        if isinstance(method, str):
            method = XAIMethod(method.lower())
        if isinstance(level, str):
            level = ExplanationLevel(level.lower())

        # Generate explanation based on method
        if method == XAIMethod.SHAP:
            raw_explanation = self._generate_shap_explanation(model, instance, **kwargs)
        elif method == XAIMethod.LIME:
            raw_explanation = self._generate_lime_explanation(model, instance, **kwargs)
        elif method == XAIMethod.COUNTERFACTUAL:
            raw_explanation = self._generate_counterfactual(model, instance, **kwargs)
        elif method == XAIMethod.PDP:
            raw_explanation = self._generate_pdp(model, instance, **kwargs)
        elif method == XAIMethod.SALIENCY:
            raw_explanation = self._generate_saliency(model, instance, **kwargs)
        else:
            raw_explanation = {'error': f'Method {method} not yet implemented'}

        # Format explanation based on level
        formatted_explanation = self._format_explanation(raw_explanation, level)

        return {
            'explanation': formatted_explanation,
            'method': method.value,
            'level': level.value,
            'confidence': raw_explanation.get('confidence', 0.8),
            'visualizations': raw_explanation.get('visualizations', [])
        }

    def _generate_shap_explanation(
        self,
        model: Any,
        instance: Any,
        background_data: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate SHAP explanation.

        SHAP (SHapley Additive exPlanations) uses game theory to assign
        importance scores to features.

        For EJE decisions, instance should be a Decision dict.
        """
        # Check if instance is an EJE decision
        if isinstance(instance, dict) and 'critic_reports' in instance:
            # Use EJE-specific SHAP explainer
            try:
                explanation = self.shap_explainer.explain_decision(
                    decision=instance,
                    explanation_type=kwargs.get('explanation_type', 'local'),
                    background_data=background_data
                )

                if not explanation.get('available', False):
                    return {
                        'error': explanation.get('error', 'SHAP not available'),
                        'confidence': 0.0
                    }

                return {
                    'method': 'SHAP',
                    'critic_explanations': explanation['critic_explanations'],
                    'aggregate_explanation': explanation['aggregate_explanation'],
                    'features': explanation['features'],
                    'computation_time': explanation['computation_time'],
                    'cached_count': explanation.get('cached_count', 0),
                    'confidence': 0.9,
                    'visualizations': ['waterfall', 'bar', 'force']
                }

            except Exception as e:
                return {
                    'error': f'SHAP generation failed: {str(e)}',
                    'confidence': 0.0
                }

        # Fallback for non-EJE models
        if not self.available_methods['shap']:
            return {
                'error': 'SHAP not available. Install with: pip install shap',
                'confidence': 0.0
            }

        try:
            import shap
            import numpy as np

            # Create explainer based on model type
            if hasattr(model, 'predict_proba'):
                # Tree-based or probabilistic models
                if background_data is not None:
                    explainer = shap.Explainer(model, background_data)
                else:
                    explainer = shap.Explainer(model)
            else:
                # Linear or other models
                explainer = shap.LinearExplainer(model, background_data)

            # Generate SHAP values
            shap_values = explainer(instance)

            # Extract feature importances
            if hasattr(shap_values, 'values'):
                feature_impacts = shap_values.values
            else:
                feature_impacts = shap_values

            # Convert to interpretable format
            if isinstance(feature_impacts, np.ndarray):
                if len(feature_impacts.shape) > 1:
                    feature_impacts = feature_impacts[0]  # Get first instance

            return {
                'method': 'SHAP',
                'feature_impacts': feature_impacts.tolist() if hasattr(feature_impacts, 'tolist') else [],
                'shap_values': shap_values,
                'confidence': 0.9,
                'visualizations': ['waterfall', 'force']
            }

        except Exception as e:
            return {
                'error': f'SHAP generation failed: {str(e)}',
                'confidence': 0.0
            }

    def _generate_lime_explanation(
        self,
        model: Any,
        instance: Any,
        training_data: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate LIME explanation.

        LIME (Local Interpretable Model-agnostic Explanations) creates
        local linear approximations of the model's behavior.
        """
        if not self.available_methods['lime']:
            return {
                'error': 'LIME not available. Install with: pip install lime',
                'confidence': 0.0
            }

        try:
            import lime
            import lime.lime_tabular
            import numpy as np

            # LIME requires training data for tabular explainer
            if training_data is None:
                return {
                    'error': 'LIME requires training_data parameter',
                    'confidence': 0.0
                }

            # Create LIME explainer
            explainer = lime.lime_tabular.LimeTabularExplainer(
                training_data,
                mode='classification' if hasattr(model, 'predict_proba') else 'regression'
            )

            # Generate explanation
            if hasattr(model, 'predict_proba'):
                exp = explainer.explain_instance(
                    instance[0] if isinstance(instance, np.ndarray) else instance,
                    model.predict_proba
                )
            else:
                exp = explainer.explain_instance(
                    instance[0] if isinstance(instance, np.ndarray) else instance,
                    model.predict
                )

            # Extract feature importances
            feature_impacts = dict(exp.as_list())

            return {
                'method': 'LIME',
                'feature_impacts': feature_impacts,
                'lime_explanation': exp,
                'confidence': 0.85,
                'visualizations': ['feature_importance']
            }

        except Exception as e:
            return {
                'error': f'LIME generation failed: {str(e)}',
                'confidence': 0.0
            }

    def _generate_counterfactual(
        self,
        model: Any,
        instance: Any,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate counterfactual explanation.

        Counterfactuals answer: "What would need to change for a different outcome?"

        For EJE decisions, instance should be a Decision dict.
        """
        try:
            # Check if instance is an EJE decision
            if isinstance(instance, dict) and 'critic_reports' in instance:
                # Use EJE-specific counterfactual generator
                mode = kwargs.get('mode', CounterfactualMode.NEAREST)
                if isinstance(mode, str):
                    mode = CounterfactualMode(mode.lower())

                result = self.counterfactual_generator.generate(
                    decision=instance,
                    mode=mode,
                    target_verdict=kwargs.get('target_verdict'),
                )

                return {
                    'method': 'COUNTERFACTUAL',
                    'counterfactuals': result['counterfactuals'],
                    'key_factors': result['key_factors'],
                    'generation_time': result['generation_time'],
                    'within_timeout': result['within_timeout'],
                    'confidence': 0.9 if result['within_timeout'] else 0.7,
                    'visualizations': ['factor_changes', 'decision_tree']
                }
            else:
                # Fallback for non-EJE models
                if not self.available_methods['alibi']:
                    return {
                        'error': 'Alibi not available for counterfactuals. Install with: pip install alibi',
                        'confidence': 0.0
                    }

                return {
                    'method': 'COUNTERFACTUAL',
                    'counterfactuals': [],
                    'message': 'Counterfactual generation requires EJE Decision format or Alibi library',
                    'confidence': 0.5,
                    'visualizations': []
                }

        except Exception as e:
            return {
                'error': f'Counterfactual generation failed: {str(e)}',
                'confidence': 0.0
            }

    def _generate_pdp(
        self,
        model: Any,
        instance: Any,
        feature_idx: int = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate Partial Dependence Plot data.

        PDPs show the marginal effect of a feature on predictions.
        """
        try:
            from sklearn.inspection import partial_dependence

            # Generate PDP for specified feature
            pd_result = partial_dependence(
                model,
                instance,
                features=[feature_idx]
            )

            return {
                'method': 'PDP',
                'pd_values': pd_result['average'].tolist(),
                'feature_values': pd_result['values'][0].tolist(),
                'confidence': 0.8,
                'visualizations': ['line_plot']
            }

        except Exception as e:
            return {
                'error': f'PDP generation failed: {str(e)}',
                'confidence': 0.0
            }

    def _generate_saliency(
        self,
        model: Any,
        instance: Any,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate saliency map (for neural networks).

        Saliency maps show which input features the model is most sensitive to.
        """
        return {
            'method': 'SALIENCY',
            'message': 'Saliency maps require neural network models',
            'confidence': 0.5,
            'visualizations': []
        }

    def _format_explanation(
        self,
        raw_explanation: Dict[str, Any],
        level: ExplanationLevel
    ) -> str:
        """
        Format explanation based on detail level.

        Args:
            raw_explanation: Raw XAI output
            level: Desired explanation level

        Returns:
            Formatted explanation string
        """
        if 'error' in raw_explanation:
            return raw_explanation['error']

        method = raw_explanation.get('method', 'Unknown')

        if level == ExplanationLevel.EXECUTIVE:
            # One-sentence summary
            return self._generate_executive_summary(raw_explanation)

        elif level == ExplanationLevel.NARRATIVE:
            # Plain language explanation
            return self._generate_narrative_explanation(raw_explanation)

        elif level == ExplanationLevel.TECHNICAL:
            # Technical details
            return self._generate_technical_explanation(raw_explanation)

        elif level == ExplanationLevel.VISUAL:
            # Visual explanation description
            return self._generate_visual_description(raw_explanation)

        else:
            return f"{method} explanation generated"

    def _generate_executive_summary(self, raw_explanation: Dict[str, Any]) -> str:
        """Generate one-sentence executive summary."""
        method = raw_explanation.get('method', 'XAI')
        confidence = raw_explanation.get('confidence', 0.5)

        return f"{method} analysis (confidence: {confidence:.0%}) identifies key factors influencing this decision."

    def _generate_narrative_explanation(self, raw_explanation: Dict[str, Any]) -> str:
        """Generate plain language narrative explanation."""
        method = raw_explanation.get('method', 'Unknown')

        narrative = f"This explanation was generated using {method}, which analyzes "

        if method == 'SHAP':
            narrative += "how each feature contributes to the prediction using game theory principles. "
            narrative += "Features with higher SHAP values have stronger influence on the outcome."

        elif method == 'LIME':
            narrative += "the model's behavior locally around this specific instance. "
            narrative += "It creates a simpler, interpretable model that approximates the complex model's decisions."

        elif method == 'PDP':
            narrative += "how changing this feature affects the prediction while keeping others constant. "
            narrative += "This shows the average marginal effect of the feature."

        else:
            narrative += "the factors that led to this particular decision."

        return narrative

    def _generate_technical_explanation(self, raw_explanation: Dict[str, Any]) -> str:
        """Generate technical explanation with details."""
        import json
        method = raw_explanation.get('method', 'Unknown')

        # Include technical details
        technical = f"Method: {method}\n"
        technical += f"Confidence: {raw_explanation.get('confidence', 0.0):.3f}\n"

        if 'feature_impacts' in raw_explanation:
            technical += f"\nFeature Impacts:\n"
            impacts = raw_explanation['feature_impacts']
            if isinstance(impacts, dict):
                for feat, impact in list(impacts.items())[:5]:  # Top 5
                    technical += f"  {feat}: {impact:.4f}\n"
            elif isinstance(impacts, list):
                for i, impact in enumerate(impacts[:5]):
                    technical += f"  Feature {i}: {impact:.4f}\n"

        return technical

    def _generate_visual_description(self, raw_explanation: Dict[str, Any]) -> str:
        """Generate description of available visualizations."""
        viz_types = raw_explanation.get('visualizations', [])

        if not viz_types:
            return "No visualizations available for this explanation."

        desc = "Available visualizations: " + ", ".join(viz_types)
        return desc


# Export
__all__ = ['XAIPipeline', 'ExplanationLevel', 'XAIMethod']
