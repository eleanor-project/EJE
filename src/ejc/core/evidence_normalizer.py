"""
Evidence Bundle Normalizer

Converts raw critic outputs into the unified evidence bundle schema,
handling normalization, validation, and metadata enrichment.
"""

import hashlib
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# Evidence Source Models
class EvidenceSource(BaseModel):
    """Reference to an evidence source used by a critic"""
    type: str = Field(..., pattern="^(policy|precedent|rule|constitutional_principle)$")
    reference: str = Field(..., min_length=1)
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0)


# Critic Output Models
class CriticOutput(BaseModel):
    """Individual critic evaluation output"""
    critic: str = Field(..., min_length=1)
    verdict: str = Field(..., pattern="^(ALLOW|DENY|REVIEW|ERROR|ABSTAIN)$")
    confidence: float = Field(..., ge=0.0, le=1.0)
    justification: str = Field(..., min_length=1)
    weight: float = Field(default=1.0, ge=0.0)
    priority: Optional[str] = Field(default=None, pattern="^(override|veto)$")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    config_version: Optional[str] = Field(None, pattern="^\\d+\\.\\d+\\.\\d+$")
    evidence_sources: List[EvidenceSource] = Field(default_factory=list)

    @field_validator('timestamp', mode='before')
    @classmethod
    def ensure_timestamp(cls, v: Any) -> str:
        """Ensure timestamp is in ISO 8601 format"""
        if v is None:
            return datetime.utcnow().isoformat() + "Z"
        if isinstance(v, datetime):
            return v.isoformat() + "Z"
        return str(v)


# Input Snapshot Models
class InputMetadata(BaseModel):
    """Input-level metadata"""
    source: Optional[str] = None
    domain: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class InputSnapshot(BaseModel):
    """Snapshot of input context at evaluation time"""
    text: str = Field(..., min_length=1)
    context: Dict[str, Any] = Field(default_factory=dict)
    metadata: InputMetadata = Field(default_factory=InputMetadata)
    context_hash: str = Field(...)

    @model_validator(mode='before')
    @classmethod
    def compute_hash_if_missing(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Auto-compute context hash if not provided"""
        if 'context_hash' not in values or not values['context_hash']:
            text = values.get('text', '')
            context = str(values.get('context', {}))
            combined = f"{text}::{context}".encode('utf-8')
            values['context_hash'] = hashlib.sha256(combined).hexdigest()
        return values


# Justification Synthesis Models
class ConflictingEvidence(BaseModel):
    """Description of conflicting evidence between critics"""
    critics: List[str]
    description: str


class ConfidenceAssessment(BaseModel):
    """Overall confidence metrics"""
    average_confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_variance: float = Field(..., ge=0.0)
    consensus_level: str = Field(..., pattern="^(unanimous|strong|moderate|weak|conflicted)$")


class JustificationSynthesis(BaseModel):
    """Aggregated justification structure"""
    summary: Optional[str] = None
    supporting_evidence: List[str] = Field(default_factory=list)
    conflicting_evidence: List[ConflictingEvidence] = Field(default_factory=list)
    confidence_assessment: Optional[ConfidenceAssessment] = None


# Metadata Models
class PrecedentReference(BaseModel):
    """Reference to a precedent case"""
    precedent_id: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    influence_weight: float = Field(..., ge=0.0, le=1.0)


class Flags(BaseModel):
    """Operational flags and markers"""
    requires_human_review: bool = False
    is_override: bool = False
    is_fallback: bool = False
    is_test: bool = False


class BundleMetadata(BaseModel):
    """Evidence bundle metadata for tracking and auditing"""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: Optional[str] = None
    system_version: str = Field(..., pattern="^\\d+\\.\\d+\\.\\d+$")
    critic_config_versions: Dict[str, str] = Field(default_factory=dict)
    processing_time_ms: Optional[float] = Field(None, ge=0.0)
    environment: str = Field(default="development", pattern="^(production|staging|development|test)$")
    correlation_id: Optional[str] = None
    precedent_refs: List[PrecedentReference] = Field(default_factory=list)
    flags: Flags = Field(default_factory=Flags)


# Validation Error Models
class ValidationError(BaseModel):
    """Validation error entry"""
    field: str
    error: str
    severity: str = Field(..., pattern="^(error|warning|info)$")


# Main Evidence Bundle Model
class EvidenceBundle(BaseModel):
    """
    Atomic unit of reasoning across critics containing evaluation evidence,
    metadata, and context.
    """
    bundle_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    version: str = Field(default="1.0.0", pattern="^\\d+\\.\\d+\\.\\d+$")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    input_snapshot: InputSnapshot
    critic_outputs: List[CriticOutput] = Field(..., min_length=1)
    justification_synthesis: Optional[JustificationSynthesis] = None
    metadata: BundleMetadata
    validation_errors: List[ValidationError] = Field(default_factory=list)


# Evidence Normalizer Class
class EvidenceNormalizer:
    """
    Normalizes raw critic outputs into unified evidence bundles.

    Handles:
    - Schema conversion and validation
    - Missing field normalization
    - Metadata enrichment
    - Error tracking
    """

    def __init__(self, system_version: str = "1.0.0", environment: str = "development"):
        """
        Initialize the evidence normalizer.

        Args:
            system_version: Version of the EJE system
            environment: Deployment environment (production, staging, development, test)
        """
        self.system_version = system_version
        self.environment = environment

    def normalize(
        self,
        input_text: Optional[str] = None,
        critic_outputs: Optional[List[Dict[str, Any]]] = None,
        input_context: Optional[Dict[str, Any]] = None,
        input_metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        precedent_refs: Optional[List[Dict[str, Any]]] = None,
        processing_time_ms: Optional[float] = None
    ) -> EvidenceBundle:
        """
        Normalize raw critic outputs into an evidence bundle.

        Args:
            input_text: Explicit text to evaluate (preferred if provided)
            critic_outputs: List of raw critic output dictionaries
            input_context: Optional block containing `text`, `context`, and `metadata`
                           If both input_text and input_context['text'] are supplied, they
                           must match.
            input_metadata: Input-level metadata (overrides metadata in input_context)
            correlation_id: Correlation ID for distributed tracing
            precedent_refs: References to precedent cases
            processing_time_ms: Total processing time in milliseconds

        Returns:
            Normalized and validated EvidenceBundle

        Raises:
            ValueError: If normalization fails critically
        """
        validation_errors = []

        if not critic_outputs:
            raise ValueError("No valid critic outputs provided")

        # Resolve input text and supporting context/metadata
        context_block = input_context if isinstance(input_context, dict) else {}
        context_from_block: Dict[str, Any] = {}
        metadata_from_block: Optional[Dict[str, Any]] = None
        text_from_block: Optional[str] = None

        if context_block:
            if any(key in context_block for key in ("text", "context", "metadata")):
                text_from_block = context_block.get("text")
                context_from_block = context_block.get("context", {})
                metadata_from_block = context_block.get("metadata")
            else:
                context_from_block = context_block

        if input_text and text_from_block and text_from_block != input_text:
            raise ValueError("Input text conflict between input_text and input_context['text']")

        text = input_text or text_from_block
        if text is None:
            raise ValueError("Input text is required for normalization")

        context = context_from_block
        metadata = input_metadata or metadata_from_block or {}

        # Normalize input snapshot
        try:
            input_snapshot = self._normalize_input_snapshot(
                text,
                context,
                metadata
            )
        except Exception as e:
            validation_errors.append(
                ValidationError(
                    field="input_snapshot",
                    error=f"Failed to normalize input snapshot: {str(e)}",
                    severity="error"
                )
            )
            # Create minimal input snapshot as fallback
            input_snapshot = InputSnapshot(
                text=text,
                context=context,
                metadata=InputMetadata(**metadata),
                context_hash=""  # Will be auto-computed
            )

        # Normalize critic outputs
        normalized_critics = []
        for idx, raw_output in enumerate(critic_outputs):
            try:
                normalized = self._normalize_critic_output(raw_output)
                normalized_critics.append(normalized)
            except Exception as e:
                validation_errors.append(
                    ValidationError(
                        field=f"critic_outputs[{idx}]",
                        error=f"Failed to normalize critic output: {str(e)}",
                        severity="warning"
                    )
                )

        if not normalized_critics:
            raise ValueError("No valid critic outputs after normalization")

        # Build metadata
        metadata = self._build_metadata(
            normalized_critics,
            correlation_id,
            precedent_refs,
            processing_time_ms
        )

        # Create evidence bundle
        try:
            bundle = EvidenceBundle(
                input_snapshot=input_snapshot,
                critic_outputs=normalized_critics,
                metadata=metadata,
                validation_errors=validation_errors
            )
        except Exception as e:
            raise ValueError(f"Failed to create evidence bundle: {str(e)}") from e

        return bundle

    def _normalize_input_snapshot(
        self,
        text: str,
        context: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> InputSnapshot:
        """Normalize input snapshot with auto-generated hash"""
        input_metadata = InputMetadata(**metadata)

        return InputSnapshot(
            text=text,
            context=context,
            metadata=input_metadata,
            context_hash=""  # Will be auto-computed by validator
        )

    def _normalize_critic_output(self, raw_output: Dict[str, Any]) -> CriticOutput:
        """
        Normalize a single critic output, filling in missing fields.

        Args:
            raw_output: Raw critic output dictionary

        Returns:
            Normalized CriticOutput
        """
        required_fields = ["verdict", "confidence"]
        missing_fields = [field for field in required_fields if field not in raw_output]

        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Ensure required fields have defaults
        normalized = {
            'critic': raw_output.get('critic', 'unknown'),
            'verdict': raw_output.get('verdict', 'ERROR').upper(),
            'confidence': float(raw_output.get('confidence', 0.0)),
            'justification': raw_output.get('justification', 'No justification provided'),
            'weight': float(raw_output.get('weight', 1.0)),
            'priority': raw_output.get('priority'),
            'timestamp': raw_output.get('timestamp'),  # Will use default if None
            'config_version': raw_output.get('config_version'),
            'evidence_sources': []
        }

        # Normalize evidence sources if present
        if 'evidence_sources' in raw_output:
            for source in raw_output['evidence_sources']:
                try:
                    normalized['evidence_sources'].append(EvidenceSource(**source))
                except Exception:
                    # Skip invalid evidence sources
                    continue

        return CriticOutput(**normalized)

    def _build_metadata(
        self,
        critic_outputs: List[CriticOutput],
        correlation_id: Optional[str],
        precedent_refs: Optional[List[Dict[str, Any]]],
        processing_time_ms: Optional[float]
    ) -> BundleMetadata:
        """Build bundle metadata from critic outputs and additional info"""
        # Extract critic config versions
        critic_config_versions = {}
        for output in critic_outputs:
            if output.config_version:
                critic_config_versions[output.critic] = output.config_version

        # Normalize precedent references
        normalized_precedents = []
        if precedent_refs:
            for ref in precedent_refs:
                try:
                    normalized_precedents.append(PrecedentReference(**ref))
                except Exception:
                    # Skip invalid precedent references
                    continue

        # Determine if human review is required
        requires_review = any(
            output.verdict in ['REVIEW', 'ERROR'] for output in critic_outputs
        )

        return BundleMetadata(
            system_version=self.system_version,
            critic_config_versions=critic_config_versions,
            processing_time_ms=processing_time_ms,
            environment=self.environment,
            correlation_id=correlation_id,
            precedent_refs=normalized_precedents,
            flags=Flags(requires_human_review=requires_review)
        )

    def normalize_batch(
        self,
        inputs: List[Dict[str, Any]]
    ) -> List[EvidenceBundle]:
        """
        Normalize a batch of inputs into evidence bundles.

        Args:
            inputs: List of dictionaries containing input_text and critic_outputs

        Returns:
            List of normalized evidence bundles
        """
        bundles = []
        for input_data in inputs:
            try:
                bundle = self.normalize(
                    critic_outputs=input_data.get('critic_outputs', []),
                    input_context=input_data.get('input_context'),
                    input_text=input_data.get('input_text'),
                    input_metadata=input_data.get('input_metadata'),
                    correlation_id=input_data.get('correlation_id'),
                    precedent_refs=input_data.get('precedent_refs'),
                    processing_time_ms=input_data.get('processing_time_ms')
                )
                bundles.append(bundle)
            except Exception as e:
                # Log error but continue processing batch
                print(f"Error normalizing input: {str(e)}")
                continue

        return bundles
