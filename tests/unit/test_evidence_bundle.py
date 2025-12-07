"""
Unit tests for Evidence Bundle functionality.

Tests cover:
- Evidence bundle normalization
- Serialization/deserialization
- Schema validation
- Metadata enrichment
- Edge cases and error handling
"""

import hashlib
import json
import time
from datetime import datetime

import pytest

from ejc.core.evidence_normalizer import (
    CriticOutput,
    EvidenceBundle,
    EvidenceNormalizer,
    EvidenceSource,
    InputSnapshot,
)
from ejc.core.evidence_serialization import (
    DeserializationError,
    EvidenceBundleSerializer,
    SerializationError,
    bundle_from_dict,
    bundle_from_json,
    bundle_to_dict,
    bundle_to_json,
    validate_bundle_dict,
    validate_bundle_json,
)
from ejc.core.metadata_enrichment import (
    MetadataEnricher,
    create_enricher_from_config,
    enrich_with_timing,
)


class TestEvidenceBundleNormalization:
    """Tests for evidence bundle normalization"""

    def test_normalize_valid_input(self):
        """Test normalizing valid critic outputs into evidence bundle"""
        normalizer = EvidenceNormalizer(system_version="1.0.0", environment="test")

        critic_outputs = [
            {
                "critic": "bias_critic",
                "verdict": "ALLOW",
                "confidence": 0.95,
                "justification": "No bias detected in the input text.",
                "weight": 1.0,
            },
            {
                "critic": "harm_critic",
                "verdict": "DENY",
                "confidence": 0.88,
                "justification": "Potential harmful content detected.",
                "weight": 1.5,
            },
        ]

        bundle = normalizer.normalize(
            input_text="Sample input text for evaluation",
            critic_outputs=critic_outputs,
            correlation_id="test-correlation-123",
        )

        assert bundle.bundle_id is not None
        assert bundle.version == "1.0.0"
        assert len(bundle.critic_outputs) == 2
        assert bundle.input_snapshot.text == "Sample input text for evaluation"
        assert bundle.metadata.system_version == "1.0.0"
        assert bundle.metadata.environment == "test"
        assert bundle.metadata.correlation_id == "test-correlation-123"

    def test_normalize_with_missing_fields(self):
        """Test normalization with missing optional fields"""
        normalizer = EvidenceNormalizer()

        critic_outputs = [
            {
                "critic": "test_critic",
                "verdict": "REVIEW",
                "confidence": 0.5,
                # Missing justification - should use default
            }
        ]

        bundle = normalizer.normalize(
            input_text="Test input",
            critic_outputs=critic_outputs,
        )

        assert bundle.critic_outputs[0].justification == "No justification provided"
        assert bundle.critic_outputs[0].weight == 1.0
        assert bundle.critic_outputs[0].priority is None

    def test_normalize_with_invalid_critic_output(self):
        """Test normalization handles invalid critic outputs gracefully"""
        normalizer = EvidenceNormalizer()

        critic_outputs = [
            {
                "critic": "valid_critic",
                "verdict": "ALLOW",
                "confidence": 0.9,
                "justification": "Valid output",
            },
            {
                # Invalid: missing required fields
                "critic": "invalid_critic",
            },
        ]

        bundle = normalizer.normalize(
            input_text="Test input",
            critic_outputs=critic_outputs,
        )

        # Should have validation errors
        assert len(bundle.validation_errors) > 0
        # Should still have valid critic output
        assert len(bundle.critic_outputs) >= 1

    def test_conflicting_input_text_sources(self):
        """Ensure conflicting text inputs raise a clear error"""
        normalizer = EvidenceNormalizer()

        critic_output = {
            "critic": "test_critic",
            "verdict": "ALLOW",
            "confidence": 0.8,
            "justification": "Valid",
        }

        with pytest.raises(ValueError, match="Input text conflict"):
            normalizer.normalize(
                input_text="explicit text",
                critic_outputs=[critic_output],
                input_context={
                    "text": "different text",
                    "context": {},
                },
            )

    def test_normalize_batch(self):
        """Test batch normalization"""
        normalizer = EvidenceNormalizer()

        inputs = [
            {
                "input_text": "First input",
                "critic_outputs": [
                    {
                        "critic": "test_critic",
                        "verdict": "ALLOW",
                        "confidence": 0.9,
                        "justification": "First justification",
                    }
                ],
            },
            {
                "input_text": "Second input",
                "critic_outputs": [
                    {
                        "critic": "test_critic",
                        "verdict": "DENY",
                        "confidence": 0.8,
                        "justification": "Second justification",
                    }
                ],
            },
        ]

        bundles = normalizer.normalize_batch(inputs)

        assert len(bundles) == 2
        assert bundles[0].input_snapshot.text == "First input"
        assert bundles[1].input_snapshot.text == "Second input"

    def test_normalize_with_evidence_sources(self):
        """Test normalization with evidence sources"""
        normalizer = EvidenceNormalizer()

        critic_outputs = [
            {
                "critic": "policy_critic",
                "verdict": "DENY",
                "confidence": 0.92,
                "justification": "Violates policy XYZ",
                "evidence_sources": [
                    {
                        "type": "policy",
                        "reference": "policy-xyz-v1",
                        "relevance_score": 0.95,
                    },
                    {
                        "type": "precedent",
                        "reference": "case-abc-123",
                        "relevance_score": 0.87,
                    },
                ],
            }
        ]

        bundle = normalizer.normalize(
            input_text="Test input",
            critic_outputs=critic_outputs,
        )

        assert len(bundle.critic_outputs[0].evidence_sources) == 2
        assert bundle.critic_outputs[0].evidence_sources[0].type == "policy"
        assert bundle.critic_outputs[0].evidence_sources[1].type == "precedent"

    def test_context_hash_generation(self):
        """Test automatic context hash generation"""
        normalizer = EvidenceNormalizer()

        text = "Test input text"
        context = {"key": "value"}

        bundle = normalizer.normalize(
            input_text=text,
            critic_outputs=[
                {
                    "critic": "test",
                    "verdict": "ALLOW",
                    "confidence": 0.9,
                    "justification": "Test",
                }
            ],
            input_context=context,
        )

        # Verify hash was generated
        assert bundle.input_snapshot.context_hash is not None
        assert len(bundle.input_snapshot.context_hash) == 64  # SHA-256 hex length

        # Verify hash is consistent
        combined = f"{text}::{context}".encode("utf-8")
        expected_hash = hashlib.sha256(combined).hexdigest()
        assert bundle.input_snapshot.context_hash == expected_hash

    def test_requires_human_review_flag(self):
        """Test automatic requires_human_review flag setting"""
        normalizer = EvidenceNormalizer()

        # Case 1: REVIEW verdict should trigger flag
        bundle1 = normalizer.normalize(
            input_text="Test",
            critic_outputs=[
                {
                    "critic": "test",
                    "verdict": "REVIEW",
                    "confidence": 0.5,
                    "justification": "Uncertain",
                }
            ],
        )
        assert bundle1.metadata.flags.requires_human_review is True

        # Case 2: ERROR verdict should trigger flag
        bundle2 = normalizer.normalize(
            input_text="Test",
            critic_outputs=[
                {
                    "critic": "test",
                    "verdict": "ERROR",
                    "confidence": 0.0,
                    "justification": "Error occurred",
                }
            ],
        )
        assert bundle2.metadata.flags.requires_human_review is True

        # Case 3: ALLOW verdict should not trigger flag
        bundle3 = normalizer.normalize(
            input_text="Test",
            critic_outputs=[
                {
                    "critic": "test",
                    "verdict": "ALLOW",
                    "confidence": 0.9,
                    "justification": "All good",
                }
            ],
        )
        assert bundle3.metadata.flags.requires_human_review is False


class TestEvidenceBundleSerialization:
    """Tests for evidence bundle serialization/deserialization"""

    def test_serialize_to_json(self):
        """Test serializing evidence bundle to JSON"""
        normalizer = EvidenceNormalizer()
        bundle = normalizer.normalize(
            input_text="Test input",
            critic_outputs=[
                {
                    "critic": "test_critic",
                    "verdict": "ALLOW",
                    "confidence": 0.9,
                    "justification": "Test justification",
                }
            ],
        )

        json_str = bundle_to_json(bundle)

        assert isinstance(json_str, str)
        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert parsed["input_snapshot"]["text"] == "Test input"
        assert len(parsed["critic_outputs"]) == 1

    def test_serialize_to_json_pretty(self):
        """Test pretty-printing JSON serialization"""
        normalizer = EvidenceNormalizer()
        bundle = normalizer.normalize(
            input_text="Test input",
            critic_outputs=[
                {
                    "critic": "test",
                    "verdict": "ALLOW",
                    "confidence": 0.9,
                    "justification": "Test",
                }
            ],
        )

        json_str = bundle_to_json(bundle, pretty=True)

        # Pretty-printed JSON should have newlines
        assert "\n" in json_str
        # Should still be valid JSON
        parsed = json.loads(json_str)
        assert "input_snapshot" in parsed

    def test_deserialize_from_json(self):
        """Test deserializing evidence bundle from JSON"""
        normalizer = EvidenceNormalizer()
        original_bundle = normalizer.normalize(
            input_text="Test input",
            critic_outputs=[
                {
                    "critic": "test_critic",
                    "verdict": "DENY",
                    "confidence": 0.85,
                    "justification": "Test justification",
                }
            ],
        )

        # Serialize then deserialize
        json_str = bundle_to_json(original_bundle)
        restored_bundle = bundle_from_json(json_str)

        # Verify data is preserved
        assert restored_bundle.input_snapshot.text == original_bundle.input_snapshot.text
        assert len(restored_bundle.critic_outputs) == len(original_bundle.critic_outputs)
        assert restored_bundle.critic_outputs[0].critic == "test_critic"
        assert restored_bundle.critic_outputs[0].verdict == "DENY"

    def test_deserialize_invalid_json(self):
        """Test deserializing invalid JSON raises error"""
        invalid_json = "{invalid json"

        with pytest.raises(DeserializationError) as exc_info:
            bundle_from_json(invalid_json)

        assert "Invalid JSON format" in str(exc_info.value)

    def test_deserialize_invalid_schema(self):
        """Test deserializing JSON with invalid schema raises error"""
        invalid_data = json.dumps(
            {
                "bundle_id": "123",
                # Missing required fields
                "version": "1.0.0",
            }
        )

        with pytest.raises(DeserializationError) as exc_info:
            bundle_from_json(invalid_data)

        assert "validation failed" in str(exc_info.value)

    def test_to_dict_and_from_dict(self):
        """Test converting to/from dictionary"""
        normalizer = EvidenceNormalizer()
        original_bundle = normalizer.normalize(
            input_text="Test input",
            critic_outputs=[
                {
                    "critic": "test",
                    "verdict": "ALLOW",
                    "confidence": 0.9,
                    "justification": "Test",
                }
            ],
        )

        # Convert to dict and back
        bundle_dict = bundle_to_dict(original_bundle)
        restored_bundle = bundle_from_dict(bundle_dict)

        assert isinstance(bundle_dict, dict)
        assert restored_bundle.input_snapshot.text == original_bundle.input_snapshot.text

    def test_validate_valid_json(self):
        """Test validation of valid JSON"""
        normalizer = EvidenceNormalizer()
        bundle = normalizer.normalize(
            input_text="Test",
            critic_outputs=[
                {
                    "critic": "test",
                    "verdict": "ALLOW",
                    "confidence": 0.9,
                    "justification": "Test",
                }
            ],
        )

        json_str = bundle_to_json(bundle)
        is_valid, error = validate_bundle_json(json_str)

        assert is_valid is True
        assert error is None

    def test_validate_invalid_json(self):
        """Test validation of invalid JSON"""
        invalid_json = json.dumps({"invalid": "structure"})
        is_valid, error = validate_bundle_json(invalid_json)

        assert is_valid is False
        assert error is not None
        assert "validation failed" in error.lower()

    def test_batch_serialization(self):
        """Test batch serialization"""
        normalizer = EvidenceNormalizer()
        bundles = [
            normalizer.normalize(
                input_text=f"Input {i}",
                critic_outputs=[
                    {
                        "critic": "test",
                        "verdict": "ALLOW",
                        "confidence": 0.9,
                        "justification": f"Justification {i}",
                    }
                ],
            )
            for i in range(3)
        ]

        json_str = EvidenceBundleSerializer.to_json_batch(bundles)
        restored_bundles = EvidenceBundleSerializer.from_json_batch(json_str)

        assert len(restored_bundles) == 3
        for i, bundle in enumerate(restored_bundles):
            assert bundle.input_snapshot.text == f"Input {i}"


class TestMetadataEnrichment:
    """Tests for metadata enrichment"""

    def test_create_enricher(self):
        """Test creating metadata enricher"""
        enricher = MetadataEnricher(
            system_version="1.2.3",
            config_version="2.0.0",
            environment="production",
        )

        assert enricher.system_version == "1.2.3"
        assert enricher.config_version == "2.0.0"
        assert enricher.environment == "production"
        assert enricher.deployment_id is not None

    def test_generate_correlation_id(self):
        """Test correlation ID generation"""
        enricher = MetadataEnricher()
        correlation_id = enricher.generate_correlation_id()

        assert isinstance(correlation_id, str)
        assert len(correlation_id) > 0

    def test_enrich_bundle_metadata(self):
        """Test enriching bundle with metadata"""
        enricher = MetadataEnricher(
            system_version="1.0.0", config_version="1.0.0", environment="test"
        )

        bundle_data = {"metadata": {}}

        enriched = enricher.enrich_bundle_metadata(
            bundle_data, correlation_id="test-correlation"
        )

        assert enriched["metadata"]["system_version"] == "1.0.0"
        assert enriched["metadata"]["environment"] == "test"
        assert enriched["metadata"]["correlation_id"] == "test-correlation"
        assert "created_at" in enriched["metadata"]
        assert "updated_at" in enriched["metadata"]
        assert "system" in enriched["metadata"]

    def test_track_critic_execution(self):
        """Test critic execution tracking"""
        enricher = MetadataEnricher()

        with enricher.track_critic_execution("test_critic") as tracker:
            time.sleep(0.01)  # Simulate some work

        stats = tracker.get_stats()

        assert stats.critic_name == "test_critic"
        assert stats.success is True
        assert stats.duration_ms > 0
        assert stats.error_message is None

    def test_track_critic_execution_with_error(self):
        """Test critic execution tracking with error"""
        enricher = MetadataEnricher()

        try:
            with enricher.track_critic_execution("failing_critic") as tracker:
                raise ValueError("Test error")
        except ValueError:
            pass

        stats = tracker.get_stats()

        assert stats.critic_name == "failing_critic"
        assert stats.success is False
        assert stats.error_message == "Test error"

    def test_enrich_with_timing(self):
        """Test enriching bundle with timing information"""
        bundle_data = {}
        start_time = time.time()
        time.sleep(0.01)
        end_time = time.time()

        enriched = enrich_with_timing(bundle_data, start_time, end_time)

        assert "metadata" in enriched
        assert "processing_time_ms" in enriched["metadata"]
        assert enriched["metadata"]["processing_time_ms"] > 0

    def test_set_flags(self):
        """Test setting operational flags"""
        enricher = MetadataEnricher()
        bundle_data = {}

        enriched = enricher.set_flags(
            bundle_data,
            requires_human_review=True,
            is_override=False,
            is_fallback=True,
            is_test=True,
        )

        flags = enriched["metadata"]["flags"]
        assert flags["requires_human_review"] is True
        assert flags["is_override"] is False
        assert flags["is_fallback"] is True
        assert flags["is_test"] is True

    def test_add_audit_trail_entry(self):
        """Test adding audit trail entries"""
        enricher = MetadataEnricher()
        bundle_data = {}

        enriched = enricher.add_audit_trail_entry(
            bundle_data, action="reviewed", actor="admin", details={"notes": "Looks good"}
        )

        assert "audit_trail" in enriched["metadata"]
        assert len(enriched["metadata"]["audit_trail"]) == 1
        entry = enriched["metadata"]["audit_trail"][0]
        assert entry["action"] == "reviewed"
        assert entry["actor"] == "admin"
        assert entry["details"]["notes"] == "Looks good"

    def test_create_enricher_from_config(self):
        """Test creating enricher from configuration"""
        config = {
            "system_version": "2.0.0",
            "config_version": "1.5.0",
            "environment": "staging",
            "deployment_id": "test-deployment-123",
        }

        enricher = create_enricher_from_config(config)

        assert enricher.system_version == "2.0.0"
        assert enricher.config_version == "1.5.0"
        assert enricher.environment == "staging"
        assert enricher.deployment_id == "test-deployment-123"


class TestEvidenceBundleEdgeCases:
    """Tests for edge cases and error handling"""

    def test_empty_critic_outputs_raises_error(self):
        """Test that empty critic outputs raises error"""
        normalizer = EvidenceNormalizer()

        with pytest.raises(ValueError) as exc_info:
            normalizer.normalize(input_text="Test", critic_outputs=[])

        assert "No valid critic outputs" in str(exc_info.value)

    def test_very_long_text_input(self):
        """Test handling of very long text input"""
        normalizer = EvidenceNormalizer()
        long_text = "A" * 100000  # 100k characters

        bundle = normalizer.normalize(
            input_text=long_text,
            critic_outputs=[
                {
                    "critic": "test",
                    "verdict": "ALLOW",
                    "confidence": 0.9,
                    "justification": "Test",
                }
            ],
        )

        assert len(bundle.input_snapshot.text) == 100000
        assert bundle.input_snapshot.context_hash is not None

    def test_special_characters_in_text(self):
        """Test handling of special characters in input"""
        normalizer = EvidenceNormalizer()
        special_text = "Test with special chars: \n\t\r\"'{}[]<>&"

        bundle = normalizer.normalize(
            input_text=special_text,
            critic_outputs=[
                {
                    "critic": "test",
                    "verdict": "ALLOW",
                    "confidence": 0.9,
                    "justification": "Test",
                }
            ],
        )

        # Should serialize/deserialize correctly
        json_str = bundle_to_json(bundle)
        restored = bundle_from_json(json_str)
        assert restored.input_snapshot.text == special_text

    def test_verdict_case_normalization(self):
        """Test that verdicts are normalized to uppercase"""
        normalizer = EvidenceNormalizer()

        bundle = normalizer.normalize(
            input_text="Test",
            critic_outputs=[
                {
                    "critic": "test",
                    "verdict": "allow",  # lowercase
                    "confidence": 0.9,
                    "justification": "Test",
                }
            ],
        )

        assert bundle.critic_outputs[0].verdict == "ALLOW"

    def test_confidence_bounds(self):
        """Test confidence value bounds validation"""
        normalizer = EvidenceNormalizer()

        # Valid confidence
        bundle = normalizer.normalize(
            input_text="Test",
            critic_outputs=[
                {
                    "critic": "test",
                    "verdict": "ALLOW",
                    "confidence": 0.5,
                    "justification": "Test",
                }
            ],
        )
        assert 0.0 <= bundle.critic_outputs[0].confidence <= 1.0

        # Confidence outside bounds should fail validation
        with pytest.raises(Exception):  # Pydantic validation error
            CriticOutput(
                critic="test",
                verdict="ALLOW",
                confidence=1.5,  # > 1.0
                justification="Test",
            )

    def test_unicode_text_handling(self):
        """Test handling of unicode characters"""
        normalizer = EvidenceNormalizer()
        unicode_text = "Test with unicode: 你好 мир 🌍"

        bundle = normalizer.normalize(
            input_text=unicode_text,
            critic_outputs=[
                {
                    "critic": "test",
                    "verdict": "ALLOW",
                    "confidence": 0.9,
                    "justification": "Unicode test: 你好",
                }
            ],
        )

        # Should serialize/deserialize correctly
        json_str = bundle_to_json(bundle)
        restored = bundle_from_json(json_str)
        assert restored.input_snapshot.text == unicode_text
        assert "你好" in restored.critic_outputs[0].justification
