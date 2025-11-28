"""
Tests for XAI Pipeline - Phase 5A

Tests explainability functionality including SHAP, LIME, and multi-level explanations.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ejc.core.explainability.xai_pipeline import (
    XAIPipeline,
    ExplanationLevel,
    XAIMethod
)


class TestXAIPipeline:
    """Test suite for XAI Pipeline."""

    @pytest.fixture
    def pipeline(self):
        """Create an XAIPipeline instance."""
        return XAIPipeline()

    def test_pipeline_initialization(self, pipeline):
        """Test pipeline initializes and checks available methods."""
        assert isinstance(pipeline.available_methods, dict)
        # Check that it checked for various libraries
        assert 'shap' in pipeline.available_methods
        assert 'lime' in pipeline.available_methods
        assert 'alibi' in pipeline.available_methods
        assert 'matplotlib' in pipeline.available_methods

    def test_explanation_level_enum(self):
        """Test ExplanationLevel enum values."""
        assert ExplanationLevel.EXECUTIVE.value == "executive"
        assert ExplanationLevel.NARRATIVE.value == "narrative"
        assert ExplanationLevel.TECHNICAL.value == "technical"
        assert ExplanationLevel.VISUAL.value == "visual"

    def test_xai_method_enum(self):
        """Test XAIMethod enum values."""
        assert XAIMethod.SHAP.value == "shap"
        assert XAIMethod.LIME.value == "lime"
        assert XAIMethod.COUNTERFACTUAL.value == "counterfactual"
        assert XAIMethod.PDP.value == "pdp"
        assert XAIMethod.SALIENCY.value == "saliency"
        assert XAIMethod.ATTENTION.value == "attention"

    def test_generate_explanation_basic(self, pipeline):
        """Test basic explanation generation."""
        # Mock model and instance (will fail gracefully if libraries not available)
        mock_model = None
        mock_instance = None

        result = pipeline.generate_explanation(
            model=mock_model,
            instance=mock_instance,
            method=XAIMethod.SHAP,
            level=ExplanationLevel.NARRATIVE
        )

        # Should return a structured response even if libraries unavailable
        assert 'explanation' in result
        assert 'method' in result
        assert 'level' in result
        assert 'confidence' in result
        assert 'visualizations' in result

        assert result['method'] == 'shap'
        assert result['level'] == 'narrative'

    def test_method_string_conversion(self, pipeline):
        """Test that string method names are converted to enums."""
        mock_model = None
        mock_instance = None

        result = pipeline.generate_explanation(
            model=mock_model,
            instance=mock_instance,
            method="lime",  # String instead of enum
            level="executive"  # String instead of enum
        )

        assert result['method'] == 'lime'
        assert result['level'] == 'executive'

    def test_executive_summary_format(self, pipeline):
        """Test executive summary formatting."""
        raw_explanation = {
            'method': 'SHAP',
            'confidence': 0.85,
            'feature_impacts': [0.5, 0.3, 0.2]
        }

        summary = pipeline._format_explanation(raw_explanation, ExplanationLevel.EXECUTIVE)

        # Should be concise
        assert len(summary) < 200
        assert 'SHAP' in summary
        assert '85%' in summary or '0.85' in summary

    def test_narrative_explanation_format(self, pipeline):
        """Test narrative explanation formatting."""
        raw_explanation = {
            'method': 'LIME',
            'confidence': 0.9
        }

        narrative = pipeline._format_explanation(raw_explanation, ExplanationLevel.NARRATIVE)

        # Should be plain language
        assert len(narrative) > 50
        assert 'LIME' in narrative
        # Should explain what LIME does
        assert 'local' in narrative.lower() or 'interpretable' in narrative.lower()

    def test_technical_explanation_format(self, pipeline):
        """Test technical explanation formatting."""
        raw_explanation = {
            'method': 'SHAP',
            'confidence': 0.92,
            'feature_impacts': [0.5, -0.3, 0.2, 0.1]
        }

        technical = pipeline._format_explanation(raw_explanation, ExplanationLevel.TECHNICAL)

        # Should include technical details
        assert 'Method:' in technical
        assert 'Confidence:' in technical
        assert 'Feature' in technical
        # Should include impact values
        assert '0.5' in technical or '0.500' in technical

    def test_visual_description_format(self, pipeline):
        """Test visual description formatting."""
        raw_explanation = {
            'method': 'SHAP',
            'visualizations': ['waterfall', 'force']
        }

        visual_desc = pipeline._format_explanation(raw_explanation, ExplanationLevel.VISUAL)

        assert 'waterfall' in visual_desc
        assert 'force' in visual_desc

        # Test with no visualizations
        raw_explanation_no_viz = {
            'method': 'TEST',
            'visualizations': []
        }

        visual_desc_empty = pipeline._format_explanation(raw_explanation_no_viz, ExplanationLevel.VISUAL)
        assert 'No visualizations' in visual_desc_empty

    def test_error_handling(self, pipeline):
        """Test error handling when libraries are unavailable."""
        # Force unavailable method
        pipeline.available_methods['shap'] = False

        mock_model = None
        mock_instance = None

        result = pipeline.generate_explanation(
            model=mock_model,
            instance=mock_instance,
            method=XAIMethod.SHAP,
            level=ExplanationLevel.NARRATIVE
        )

        # Should return error message instead of crashing
        assert isinstance(result['explanation'], str)
        if 'error' in result['explanation'].lower() or 'not available' in result['explanation'].lower():
            assert result['confidence'] <= 0.5

    @pytest.mark.skipif(True, reason="Requires sklearn and actual data")
    def test_shap_with_real_model(self, pipeline):
        """Test SHAP explanation with a real model (integration test)."""
        # This would require actual sklearn models and data
        # Skipped by default, can be enabled for integration testing
        pass

    @pytest.mark.skipif(True, reason="Requires LIME library and actual data")
    def test_lime_with_real_model(self, pipeline):
        """Test LIME explanation with a real model (integration test)."""
        # This would require LIME library, models, and data
        # Skipped by default, can be enabled for integration testing
        pass


def test_counterfactual_method(pipeline=None):
    """Test counterfactual explanation generation."""
    if pipeline is None:
        pipeline = XAIPipeline()

    result = pipeline._generate_counterfactual(None, None)

    # Should handle gracefully even without full implementation
    assert 'method' in result
    assert result['method'] == 'COUNTERFACTUAL'


def test_pdp_method(pipeline=None):
    """Test PDP explanation generation."""
    if pipeline is None:
        pipeline = XAIPipeline()

    # Without real model, should handle error
    result = pipeline._generate_pdp(None, None)

    # Should return structured response
    assert isinstance(result, dict)
    # Either successful or error response
    assert 'method' in result or 'error' in result


def test_saliency_method(pipeline=None):
    """Test saliency map generation."""
    if pipeline is None:
        pipeline = XAIPipeline()

    result = pipeline._generate_saliency(None, None)

    # Should return info about neural network requirement
    assert 'method' in result
    assert result['method'] == 'SALIENCY'
    assert 'visualizations' in result
