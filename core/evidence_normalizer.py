"""
Evidence Bundle Normalizer

Converts raw critic outputs into the unified evidence bundle schema.
Handles missing fields gracefully and ensures downstream aggregator compatibility.

Task 1.2: Implement Evidence Normalizer
"""

import hashlib
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger("ejc.core.evidence_normalizer")


class EvidenceNormalizer:
    """
    Normalizes raw critic outputs into the unified evidence bundle schema.

    Handles variations in critic output formats and auto-fills missing fields
    to ensure consistent structure for downstream aggregation.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Evidence Normalizer.

        Args:
            config: Optional configuration dict with default values
        """
        self.config = config or {}
        self.default_version = self.config.get("schema_version", "1.0")
        self.default_config_version = self.config.get("config_version", "1.0")

    def normalize(
        self,
        raw_critic_output: Dict[str, Any],
        input_data: Dict[str, Any],
        metadata_overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Normalize raw critic output into evidence bundle schema.

        Args:
            raw_critic_output: Raw output from critic (may vary in structure)
            input_data: Original input that was evaluated
            metadata_overrides: Optional metadata to override defaults

        Returns:
            Normalized evidence bundle dict that conforms to schema

        Raises:
            ValueError: If required fields are missing and cannot be inferred
        """
        try:
            # Generate bundle ID
            bundle_id = self._generate_bundle_id(raw_critic_output, input_data)

            # Normalize critic output section
            critic_output = self._normalize_critic_output(raw_critic_output)

            # Generate metadata section
            metadata = self._generate_metadata(
                raw_critic_output,
                metadata_overrides or {}
            )

            # Generate input snapshot
            input_snapshot = self._generate_input_snapshot(input_data)

            # Assemble normalized bundle
            bundle = {
                "bundle_id": bundle_id,
                "version": self.default_version,
                "critic_output": critic_output,
                "metadata": metadata,
                "input_snapshot": input_snapshot
            }

            logger.debug(f"Normalized bundle {bundle_id} from {critic_output['critic_name']}")
            return bundle

        except Exception as e:
            logger.error(f"Failed to normalize critic output: {e}")
            raise ValueError(f"Normalization failed: {e}")

    def _normalize_critic_output(
        self,
        raw_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Normalize critic output section.

        Args:
            raw_output: Raw critic output dict

        Returns:
            Normalized critic_output dict

        Raises:
            ValueError: If required fields missing
        """
        # Extract required fields with validation
        critic_name = self._extract_critic_name(raw_output)
        verdict = self._extract_verdict(raw_output)
        confidence = self._extract_confidence(raw_output)
        justification = self._extract_justification(raw_output)

        normalized = {
            "critic_name": critic_name,
            "verdict": verdict,
            "confidence": confidence,
            "justification": justification
        }

        # Add optional fields if present
        if "risk_flags" in raw_output:
            normalized["risk_flags"] = self._normalize_risk_flags(raw_output["risk_flags"])

        if "sub_verdicts" in raw_output:
            normalized["sub_verdicts"] = raw_output["sub_verdicts"]

        if "precedents_referenced" in raw_output:
            precedents = raw_output["precedents_referenced"]
            if isinstance(precedents, list):
                normalized["precedents_referenced"] = precedents

        if "model_info" in raw_output:
            normalized["model_info"] = raw_output["model_info"]

        return normalized

    def _extract_critic_name(self, raw_output: Dict[str, Any]) -> str:
        """Extract critic name from various possible field names."""
        possible_fields = ["critic_name", "name", "critic", "source"]

        for field in possible_fields:
            if field in raw_output and raw_output[field]:
                return str(raw_output[field])

        raise ValueError("critic_name is required but not found in raw output")

    def _extract_verdict(self, raw_output: Dict[str, Any]) -> str:
        """Extract and normalize verdict."""
        possible_fields = ["verdict", "decision", "outcome", "result"]

        for field in possible_fields:
            if field in raw_output and raw_output[field]:
                verdict = str(raw_output[field]).upper()

                # Normalize common variations
                verdict_map = {
                    "APPROVE": "ALLOW",
                    "ACCEPT": "ALLOW",
                    "PASS": "ALLOW",
                    "REJECT": "DENY",
                    "BLOCK": "DENY",
                    "FAIL": "DENY",
                    "REVIEW": "ESCALATE",
                    "MANUAL_REVIEW": "ESCALATE",
                    "HUMAN_REVIEW": "ESCALATE",
                    "SKIP": "ABSTAIN",
                    "PASS_THROUGH": "ABSTAIN",
                    "UNKNOWN": "ABSTAIN"
                }

                normalized_verdict = verdict_map.get(verdict, verdict)

                # Validate against allowed values
                allowed = ["ALLOW", "DENY", "ESCALATE", "ABSTAIN", "ERROR"]
                if normalized_verdict not in allowed:
                    logger.warning(
                        f"Unknown verdict '{verdict}', defaulting to ABSTAIN"
                    )
                    return "ABSTAIN"

                return normalized_verdict

        raise ValueError("verdict is required but not found in raw output")

    def _extract_confidence(self, raw_output: Dict[str, Any]) -> float:
        """Extract and normalize confidence score."""
        possible_fields = ["confidence", "score", "probability", "certainty"]

        for field in possible_fields:
            if field in raw_output:
                try:
                    confidence = float(raw_output[field])

                    # Normalize to 0.0-1.0 range
                    if confidence > 1.0:
                        # Assume it's a percentage (0-100)
                        confidence = confidence / 100.0

                    # Clamp to valid range
                    confidence = max(0.0, min(1.0, confidence))

                    return confidence

                except (ValueError, TypeError):
                    logger.warning(f"Invalid confidence value: {raw_output[field]}")
                    continue

        # Default to medium confidence if missing
        logger.warning("confidence not found, defaulting to 0.5")
        return 0.5

    def _extract_justification(self, raw_output: Dict[str, Any]) -> str:
        """Extract justification/reasoning."""
        possible_fields = [
            "justification",
            "reasoning",
            "explanation",
            "rationale",
            "reason",
            "details"
        ]

        for field in possible_fields:
            if field in raw_output and raw_output[field]:
                justification = str(raw_output[field]).strip()
                if len(justification) >= 10:  # Schema minimum
                    return justification

        # Generate default justification if missing
        critic_name = raw_output.get("critic_name", "Critic")
        verdict = raw_output.get("verdict", "UNKNOWN")
        default = f"{critic_name} evaluated the case and returned verdict: {verdict}"

        logger.warning(f"justification missing or too short, using default")
        return default

    def _normalize_risk_flags(self, raw_flags: Any) -> List[str]:
        """Normalize risk flags to standard values."""
        if not raw_flags:
            return []

        # Handle different input formats
        if isinstance(raw_flags, str):
            raw_flags = [raw_flags]

        if not isinstance(raw_flags, list):
            return []

        # Normalize flag names
        flag_map = {
            "privacy": "privacy_concern",
            "safety": "safety_risk",
            "rights": "rights_violation",
            "novel": "novel_case",
            "high_stakes": "high_stakes",
            "ambiguous": "ambiguous",
            "conflict": "precedent_conflict",
            "jurisdiction": "jurisdiction_issue"
        }

        normalized = []
        for flag in raw_flags:
            flag_str = str(flag).lower().strip()
            normalized_flag = flag_map.get(flag_str, flag_str)
            if normalized_flag:
                normalized.append(normalized_flag)

        return normalized

    def _generate_metadata(
        self,
        raw_output: Dict[str, Any],
        overrides: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate metadata section.

        Args:
            raw_output: Raw critic output
            overrides: Metadata overrides

        Returns:
            Metadata dict
        """
        metadata = {
            "timestamp": overrides.get(
                "timestamp",
                datetime.utcnow().isoformat() + "Z"
            ),
            "critic_name": overrides.get(
                "critic_name",
                raw_output.get("critic_name", "Unknown")
            ),
            "config_version": overrides.get(
                "config_version",
                self.default_config_version
            )
        }

        # Add optional metadata fields if present
        optional_fields = [
            "aggregator_run_id",
            "execution_time_ms",
            "system_info",
            "trace_id",
            "request_id"
        ]

        for field in optional_fields:
            if field in overrides:
                metadata[field] = overrides[field]
            elif field in raw_output:
                metadata[field] = raw_output[field]

        return metadata

    def _generate_input_snapshot(
        self,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate input snapshot section.

        Args:
            input_data: Original input data

        Returns:
            Input snapshot dict
        """
        # Extract prompt
        prompt = self._extract_prompt(input_data)

        snapshot = {
            "prompt": prompt
        }

        # Add context if present
        if "context" in input_data:
            snapshot["context"] = input_data["context"]

        # Add metadata if present
        if "metadata" in input_data:
            snapshot["metadata"] = input_data["metadata"]

        # Generate input hash
        snapshot["input_hash"] = self._calculate_input_hash(input_data)

        return snapshot

    def _extract_prompt(self, input_data: Dict[str, Any]) -> str:
        """Extract prompt from input data."""
        possible_fields = ["prompt", "text", "input", "case", "question", "query"]

        for field in possible_fields:
            if field in input_data and input_data[field]:
                prompt = str(input_data[field]).strip()
                if prompt:
                    return prompt

        # Try to serialize entire input if no prompt field found
        if input_data:
            logger.warning("No prompt field found, using JSON dump of input")
            return json.dumps(input_data, sort_keys=True)

        raise ValueError("Cannot extract prompt from input data")

    def _calculate_input_hash(self, input_data: Dict[str, Any]) -> str:
        """
        Calculate SHA-256 hash of input for deduplication.

        Args:
            input_data: Input data dict

        Returns:
            Hex-encoded SHA-256 hash
        """
        # Create canonical representation
        canonical = json.dumps(input_data, sort_keys=True)

        # Calculate hash
        hash_obj = hashlib.sha256(canonical.encode('utf-8'))
        return hash_obj.hexdigest()

    def _generate_bundle_id(
        self,
        raw_output: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> str:
        """
        Generate unique bundle ID.

        Args:
            raw_output: Raw critic output
            input_data: Input data

        Returns:
            Unique bundle ID string
        """
        # Use existing ID if present
        if "bundle_id" in raw_output:
            return str(raw_output["bundle_id"])

        # Generate new ID
        critic_name = raw_output.get("critic_name", "unknown")
        timestamp = datetime.utcnow().isoformat()
        unique_id = str(uuid.uuid4())[:8]

        bundle_id = f"bundle-{critic_name}-{unique_id}"
        return bundle_id.lower().replace(" ", "-")

    def batch_normalize(
        self,
        raw_outputs: List[Dict[str, Any]],
        input_data: Dict[str, Any],
        metadata_overrides: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Normalize multiple critic outputs for the same input.

        Args:
            raw_outputs: List of raw critic outputs
            input_data: Shared input data
            metadata_overrides: Optional shared metadata overrides

        Returns:
            List of normalized evidence bundles
        """
        normalized_bundles = []

        for raw_output in raw_outputs:
            try:
                bundle = self.normalize(raw_output, input_data, metadata_overrides)
                normalized_bundles.append(bundle)
            except Exception as e:
                logger.error(
                    f"Failed to normalize output from "
                    f"{raw_output.get('critic_name', 'unknown')}: {e}"
                )
                # Continue with other outputs

        return normalized_bundles


def normalize_critic_output(
    raw_output: Dict[str, Any],
    input_data: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function for normalizing a single critic output.

    Args:
        raw_output: Raw critic output dict
        input_data: Original input dict
        config: Optional configuration dict

    Returns:
        Normalized evidence bundle dict
    """
    normalizer = EvidenceNormalizer(config)
    return normalizer.normalize(raw_output, input_data)
