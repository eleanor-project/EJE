"""
Comprehensive Unit Tests for Evidence Bundle System

Tests cover:
- Evidence bundle schema validation
- Evidence normalizer functionality
- Metadata enrichment
- Serialization/deserialization
- Edge cases and error handling

Related Issues: #42, #49
"""

import json
import pytest
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any
from pydantic import ValidationError

from src.ejc.core.evidence_normalizer import (
    EvidenceNormalizer,
    CriticOutput,
    EvidenceBundle,
    InputSnapshot,
    BundleMetadata,
    EvidenceSource
)
from src.ejc.core.evidence_serialization import EvidenceBundleSerializer
from src.ejc.core.metadata_enrichment import MetadataEnricher


# ==============================================================================
# Test Fixtures
# ==============================================================================

@pytest.fixture
def sample_critic_output():
    """Sample valid critic output for testing"""
    return {
        "critic": "bias_critic",
        "verdict": "ALLOW",
        "confidence": 0.85,
        "justification": "No significant bias detected in the content.",
        "weight": 1.0,
        "evidence_sources": [
            {
                "type": "policy",
                "reference": "POLICY-001",
                "relevance_score": 0.9
            }
        ]
    }


@pytest.fixture
def sample_input_context():
    """Sample input context for testing"""
    return {
        "text": "Sample decision text requiring evaluation",
        "context": {
            "domain": "healthcare",
            "priority": "high"
        },
        "metadata": {
            "source": "api",
            "user_id": "user123"
        }
    }


@pytest.fixture
def malformed_critic_output():
    """Malformed critic output for testing error handling"""
    return {
        "critic": "test_critic",
        # Missing required fields
        "confidence": 1.5,  # Invalid: > 1.0
        "verdict": "INVALID_VERDICT"  # Invalid enum value
    }


@pytest.fixture
def normalizer():
    """Evidence normalizer instance"""
    return EvidenceNormalizer()


@pytest.fixture
def serializer():
    """Evidence bundle serializer instance"""
    return EvidenceBundleSerializer()


@pytest.fixture
def metadata_enricher():
    """Metadata enricher instance"""
    return MetadataEnricher(
        system_version="7.0.0",
        environment="test"
    )


# ==============================================================================
# Schema Validation Tests
# ==============================================================================

class TestSchemaValidation:
    """Test evidence bundle schema validation"""

    def test_valid_critic_output(self, sample_critic_output):
        """Test that valid critic output passes validation"""
        critic_output = CriticOutput(**sample_critic_output)

        assert critic_output.critic == "bias_critic"
        assert critic_output.verdict == "ALLOW"
        assert critic_output.confidence == 0.85
        assert len(critic_output.evidence_sources) == 1

    def test_invalid_confidence_rejected(self):
        """Test that invalid confidence values are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            CriticOutput(
                critic="test",
                verdict="ALLOW",
                confidence=1.5,  # Invalid
                justification="test"
            )

        assert "confidence" in str(exc_info.value)

    def test_invalid_verdict_rejected(self):
        """Test that invalid verdict values are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            CriticOutput(
                critic="test",
                verdict="INVALID",  # Not in enum
                confidence=0.5,
                justification="test"
            )

        assert "verdict" in str(exc_info.value)

    def test_missing_required_fields_rejected(self):
        """Test that missing required fields are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            CriticOutput(
                critic="test",
                # Missing verdict, confidence, justification
            )

        errors = str(exc_info.value)
        assert "verdict" in errors
        assert "confidence" in errors
        assert "justification" in errors

    def test_evidence_source_validation(self):
        """Test evidence source validation"""
        # Valid source
        source = EvidenceSource(
            type="precedent",
            reference="PREC-001",
            relevance_score=0.8
        )
        assert source.type == "precedent"

        # Invalid type
        with pytest.raises(ValidationError):
            EvidenceSource(
                type="invalid_type",
                reference="REF-001"
            )

    def test_optional_fields_have_defaults(self, sample_critic_output):
        """Test that optional fields have sensible defaults"""
        # Remove optional fields
        minimal_output = {
            "critic": "test_critic",
            "verdict": "ALLOW",
            "confidence": 0.7,
            "justification": "Test justification"
        }

        critic_output = CriticOutput(**minimal_output)

        assert critic_output.weight == 1.0  # Default
        assert critic_output.priority is None  # Default
        assert critic_output.timestamp is not None  # Auto-generated
        assert len(critic_output.evidence_sources) == 0  # Default empty list


# ==============================================================================
# Evidence Normalizer Tests
# ==============================================================================

class TestEvidenceNormalizer:
    """Test evidence normalizer functionality"""

    def test_normalize_single_critic(self, normalizer, sample_critic_output, sample_input_context):
        """Test normalizing a single critic output"""
        bundle = normalizer.normalize(
            critic_outputs=[sample_critic_output],
            input_context=sample_input_context
        )

        assert bundle.bundle_id is not None
        assert len(bundle.critic_outputs) == 1
        assert bundle.critic_outputs[0].critic == "bias_critic"
        assert bundle.input_snapshot.text == sample_input_context["text"]

    def test_normalize_multiple_critics(self, normalizer, sample_input_context):
        """Test normalizing multiple critic outputs"""
        critic_outputs = [
            {
                "critic": "bias_critic",
                "verdict": "ALLOW",
                "confidence": 0.85,
                "justification": "No bias detected"
            },
            {
                "critic": "safety_critic",
                "verdict": "DENY",
                "confidence": 0.92,
                "justification": "Safety concerns identified"
            },
            {
                "critic": "legal_critic",
                "verdict": "REVIEW",
                "confidence": 0.6,
                "justification": "Requires legal review"
            }
        ]

        bundle = normalizer.normalize(
            critic_outputs=critic_outputs,
            input_context=sample_input_context
        )

        assert len(bundle.critic_outputs) == 3
        assert {c.critic for c in bundle.critic_outputs} == {
            "bias_critic", "safety_critic", "legal_critic"
        }

    def test_auto_fill_missing_fields(self, normalizer, sample_input_context):
        """Test that normalizer auto-fills missing optional fields"""
        minimal_output = {
            "critic": "minimal_critic",
            "verdict": "ALLOW",
            "confidence": 0.5,
            "justification": "Minimal test"
        }

        bundle = normalizer.normalize(
            critic_outputs=[minimal_output],
            input_context=sample_input_context
        )

        critic = bundle.critic_outputs[0]
        assert critic.weight == 1.0
        assert critic.timestamp is not None

    def test_invalid_critic_outputs_record_validation_errors(self, normalizer, sample_input_context):
        """Malformed critic outputs should be captured as validation warnings."""
        critic_outputs = [
            {
                "critic": "valid",
                "verdict": "ALLOW",
                "confidence": 0.9,
                "justification": "ok",
            },
            {
                "critic": "invalid",
                "verdict": "ALLOW",
                "confidence": "not-a-number",
                "justification": "broken",
            },
        ]

        bundle = normalizer.normalize(
            input_text=sample_input_context["text"],
            critic_outputs=critic_outputs,
            input_context=sample_input_context,
        )

        assert len(bundle.critic_outputs) == 1
        assert bundle.critic_outputs[0].critic == "valid"
        assert any(err.field == "critic_outputs[1]" for err in bundle.validation_errors)
        assert isinstance(bundle.critic_outputs[0].evidence_sources, list)

    def test_context_hash_generation(self, normalizer, sample_critic_output, sample_input_context):
        """Test that context hash is properly generated"""
        bundle = normalizer.normalize(
            critic_outputs=[sample_critic_output],
            input_context=sample_input_context
        )

        # Hash should be 64 character hex string (SHA-256)
        assert len(bundle.input_snapshot.context_hash) == 64
        assert all(c in '0123456789abcdef' for c in bundle.input_snapshot.context_hash)

        # Same input should produce same hash
        bundle2 = normalizer.normalize(
            critic_outputs=[sample_critic_output],
            input_context=sample_input_context
        )
        assert bundle.input_snapshot.context_hash == bundle2.input_snapshot.context_hash

    def test_handle_empty_critic_list(self, normalizer, sample_input_context):
        """Test handling of empty critic outputs list"""
        with pytest.raises(ValueError, match="at least one critic output"):
            normalizer.normalize(
                critic_outputs=[],
                input_context=sample_input_context
            )

    def test_handle_malformed_critic_output(self, normalizer, malformed_critic_output, sample_input_context):
        """Test handling of malformed critic output"""
        with pytest.raises((ValidationError, ValueError)):
            normalizer.normalize(
                critic_outputs=[malformed_critic_output],
                input_context=sample_input_context
            )

    def test_preserve_evidence_sources(self, normalizer, sample_critic_output, sample_input_context):
        """Test that evidence sources are preserved during normalization"""
        bundle = normalizer.normalize(
            critic_outputs=[sample_critic_output],
            input_context=sample_input_context
        )

        critic = bundle.critic_outputs[0]
        assert len(critic.evidence_sources) == 1
        assert critic.evidence_sources[0].type == "policy"
        assert critic.evidence_sources[0].reference == "POLICY-001"


# ==============================================================================
# Metadata Enrichment Tests
# ==============================================================================

class TestMetadataEnrichment:
    """Test metadata enrichment functionality"""

    def test_add_system_metadata(self, metadata_enricher, normalizer, sample_critic_output, sample_input_context):
        """Test adding system metadata to evidence bundle"""
        bundle = normalizer.normalize(
            critic_outputs=[sample_critic_output],
            input_context=sample_input_context
        )

        enriched_bundle = metadata_enricher.enrich(bundle)

        assert enriched_bundle.metadata.system_version == "7.0.0"
        assert enriched_bundle.metadata.environment == "test"
        assert enriched_bundle.metadata.created_at is not None

    def test_add_timing_information(self, metadata_enricher, normalizer, sample_critic_output, sample_input_context):
        """Test that timing information is added"""
        import time
        start_time = time.time()

        bundle = normalizer.normalize(
            critic_outputs=[sample_critic_output],
            input_context=sample_input_context
        )

        time.sleep(0.01)  # Small delay
        enriched_bundle = metadata_enricher.enrich(bundle, start_time=start_time)

        assert enriched_bundle.metadata.processing_time_ms > 0

    def test_add_correlation_id(self, metadata_enricher, normalizer, sample_critic_output, sample_input_context):
        """Test adding correlation ID for tracing"""
        bundle = normalizer.normalize(
            critic_outputs=[sample_critic_output],
            input_context=sample_input_context
        )

        correlation_id = "test-correlation-123"
        enriched_bundle = metadata_enricher.enrich(bundle, correlation_id=correlation_id)

        assert enriched_bundle.metadata.correlation_id == correlation_id

    def test_add_critic_config_versions(self, metadata_enricher, normalizer, sample_input_context):
        """Test adding critic configuration versions"""
        critic_outputs = [
            {
                "critic": "critic_1",
                "verdict": "ALLOW",
                "confidence": 0.8,
                "justification": "Test",
                "config_version": "1.2.3"
            },
            {
                "critic": "critic_2",
                "verdict": "ALLOW",
                "confidence": 0.7,
                "justification": "Test",
                "config_version": "2.0.1"
            }
        ]

        bundle = normalizer.normalize(
            critic_outputs=critic_outputs,
            input_context=sample_input_context
        )

        enriched_bundle = metadata_enricher.enrich(bundle)

        assert "critic_1" in enriched_bundle.metadata.critic_config_versions
        assert enriched_bundle.metadata.critic_config_versions["critic_1"] == "1.2.3"
        assert enriched_bundle.metadata.critic_config_versions["critic_2"] == "2.0.1"


# ==============================================================================
# Serialization/Deserialization Tests
# ==============================================================================

class TestSerialization:
    """Test evidence bundle serialization and deserialization"""

    def test_serialize_to_json(self, serializer, normalizer, sample_critic_output, sample_input_context):
        """Test serializing evidence bundle to JSON"""
        bundle = normalizer.normalize(
            critic_outputs=[sample_critic_output],
            input_context=sample_input_context
        )

        json_str = serializer.to_json(bundle)

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert "bundle_id" in parsed
        assert "critic_outputs" in parsed
        assert "input_snapshot" in parsed

    def test_deserialize_from_json(self, serializer, normalizer, sample_critic_output, sample_input_context):
        """Test deserializing evidence bundle from JSON"""
        bundle = normalizer.normalize(
            critic_outputs=[sample_critic_output],
            input_context=sample_input_context
        )

        json_str = serializer.to_json(bundle)
        deserialized_bundle = serializer.from_json(json_str)

        assert deserialized_bundle.bundle_id == bundle.bundle_id
        assert len(deserialized_bundle.critic_outputs) == len(bundle.critic_outputs)
        assert deserialized_bundle.input_snapshot.text == bundle.input_snapshot.text

    def test_roundtrip_preserves_data(self, serializer, normalizer, sample_critic_output, sample_input_context):
        """Test that serialization roundtrip preserves all data"""
        bundle = normalizer.normalize(
            critic_outputs=[sample_critic_output],
            input_context=sample_input_context
        )

        json_str = serializer.to_json(bundle)
        restored_bundle = serializer.from_json(json_str)

        # Check key fields preserved
        assert restored_bundle.bundle_id == bundle.bundle_id
        assert restored_bundle.version == bundle.version

        # Check critic outputs
        orig_critic = bundle.critic_outputs[0]
        rest_critic = restored_bundle.critic_outputs[0]
        assert rest_critic.critic == orig_critic.critic
        assert rest_critic.verdict == orig_critic.verdict
        assert rest_critic.confidence == orig_critic.confidence
        assert rest_critic.justification == orig_critic.justification

    def test_serialize_with_validation(self, serializer, normalizer, sample_critic_output, sample_input_context):
        """Test that serialization validates against schema"""
        bundle = normalizer.normalize(
            critic_outputs=[sample_critic_output],
            input_context=sample_input_context
        )

        json_str = serializer.to_json(bundle, validate=True)
        parsed = json.loads(json_str)

        # Check schema compliance
        assert parsed["version"].count('.') == 2  # Version format: X.Y.Z
        assert len(parsed["input_snapshot"]["context_hash"]) == 64  # SHA-256

    def test_handle_invalid_json(self, serializer):
        """Test handling of invalid JSON during deserialization"""
        invalid_json = '{"invalid": json structure'

        with pytest.raises((json.JSONDecodeError, ValueError)):
            serializer.from_json(invalid_json)

    def test_handle_schema_mismatch(self, serializer):
        """Test handling of JSON that doesn't match schema"""
        invalid_bundle = json.dumps({
            "bundle_id": "test-123",
            # Missing required fields
        })

        with pytest.raises((ValidationError, KeyError)):
            serializer.from_json(invalid_bundle)

    def test_batch_serialization(self, serializer, normalizer, sample_critic_output, sample_input_context):
        """Test batch serialization of multiple bundles"""
        bundles = []
        for i in range(3):
            bundle = normalizer.normalize(
                critic_outputs=[sample_critic_output],
                input_context=sample_input_context
            )
            bundles.append(bundle)

        json_array = serializer.serialize_batch(bundles)
        parsed = json.loads(json_array)

        assert len(parsed) == 3
        assert all("bundle_id" in b for b in parsed)


# ==============================================================================
# Edge Cases and Error Handling Tests
# ==============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_very_long_justification(self, normalizer, sample_input_context):
        """Test handling of very long justification text"""
        long_justification = "A" * 10000  # 10k characters

        critic_output = {
            "critic": "test_critic",
            "verdict": "ALLOW",
            "confidence": 0.8,
            "justification": long_justification
        }

        bundle = normalizer.normalize(
            critic_outputs=[critic_output],
            input_context=sample_input_context
        )

        assert len(bundle.critic_outputs[0].justification) == 10000

    def test_unicode_in_text(self, normalizer, sample_critic_output):
        """Test handling of Unicode characters in input"""
        unicode_context = {
            "text": "Test with émojis 🎉 and spëcial çharacters",
            "context": {}
        }

        bundle = normalizer.normalize(
            critic_outputs=[sample_critic_output],
            input_context=unicode_context
        )

        assert "🎉" in bundle.input_snapshot.text
        assert "émojis" in bundle.input_snapshot.text

    def test_extreme_confidence_values(self, normalizer, sample_input_context):
        """Test boundary values for confidence"""
        # Test minimum confidence (0.0)
        min_critic = {
            "critic": "min_critic",
            "verdict": "ABSTAIN",
            "confidence": 0.0,
            "justification": "No confidence"
        }

        bundle = normalizer.normalize(
            critic_outputs=[min_critic],
            input_context=sample_input_context
        )
        assert bundle.critic_outputs[0].confidence == 0.0

        # Test maximum confidence (1.0)
        max_critic = {
            "critic": "max_critic",
            "verdict": "ALLOW",
            "confidence": 1.0,
            "justification": "Absolute confidence"
        }

        bundle = normalizer.normalize(
            critic_outputs=[max_critic],
            input_context=sample_input_context
        )
        assert bundle.critic_outputs[0].confidence == 1.0

    def test_all_verdict_types(self, normalizer, sample_input_context):
        """Test all possible verdict values"""
        verdicts = ["ALLOW", "DENY", "REVIEW", "ERROR", "ABSTAIN"]

        for verdict in verdicts:
            critic_output = {
                "critic": f"{verdict.lower()}_critic",
                "verdict": verdict,
                "confidence": 0.5,
                "justification": f"Test {verdict}"
            }

            bundle = normalizer.normalize(
                critic_outputs=[critic_output],
                input_context=sample_input_context
            )

            assert bundle.critic_outputs[0].verdict == verdict

    def test_empty_input_text_rejected(self, normalizer, sample_critic_output):
        """Test that empty input text is rejected"""
        empty_context = {
            "text": "",
            "context": {}
        }

        with pytest.raises(ValidationError):
            normalizer.normalize(
                critic_outputs=[sample_critic_output],
                input_context=empty_context
            )

    def test_concurrent_normalization(self, normalizer, sample_critic_output, sample_input_context):
        """Test thread-safe concurrent normalization"""
        import threading

        results = []
        errors = []

        def normalize_concurrent():
            try:
                bundle = normalizer.normalize(
                    critic_outputs=[sample_critic_output],
                    input_context=sample_input_context
                )
                results.append(bundle)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=normalize_concurrent) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 10
        assert len(errors) == 0
        # Each should have unique bundle_id
        bundle_ids = {b.bundle_id for b in results}
        assert len(bundle_ids) == 10


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestIntegration:
    """Integration tests for complete evidence bundle workflow"""

    def test_full_workflow(self, normalizer, metadata_enricher, serializer, sample_critic_output, sample_input_context):
        """Test complete workflow: normalize → enrich → serialize → deserialize"""
        # Step 1: Normalize
        bundle = normalizer.normalize(
            critic_outputs=[sample_critic_output],
            input_context=sample_input_context
        )
        assert bundle is not None

        # Step 2: Enrich with metadata
        enriched_bundle = metadata_enricher.enrich(bundle)
        assert enriched_bundle.metadata.system_version == "7.0.0"

        # Step 3: Serialize to JSON
        json_str = serializer.to_json(enriched_bundle)
        assert len(json_str) > 0

        # Step 4: Deserialize back
        restored_bundle = serializer.from_json(json_str)
        assert restored_bundle.bundle_id == enriched_bundle.bundle_id

        # Verify data integrity through full pipeline
        assert restored_bundle.critic_outputs[0].critic == sample_critic_output["critic"]
        assert restored_bundle.metadata.system_version == "7.0.0"

    def test_multiple_critics_with_conflicts(self, normalizer, metadata_enricher, sample_input_context):
        """Test workflow with conflicting critic outputs"""
        conflicting_outputs = [
            {
                "critic": "permissive_critic",
                "verdict": "ALLOW",
                "confidence": 0.9,
                "justification": "No issues found"
            },
            {
                "critic": "strict_critic",
                "verdict": "DENY",
                "confidence": 0.95,
                "justification": "Multiple violations detected"
            },
            {
                "critic": "neutral_critic",
                "verdict": "REVIEW",
                "confidence": 0.6,
                "justification": "Ambiguous case requiring review"
            }
        ]

        bundle = normalizer.normalize(
            critic_outputs=conflicting_outputs,
            input_context=sample_input_context
        )

        enriched_bundle = metadata_enricher.enrich(bundle)

        # Should handle conflicting verdicts gracefully
        assert len(enriched_bundle.critic_outputs) == 3
        verdicts = {c.verdict for c in enriched_bundle.critic_outputs}
        assert verdicts == {"ALLOW", "DENY", "REVIEW"}


# ==============================================================================
# Run Tests
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
