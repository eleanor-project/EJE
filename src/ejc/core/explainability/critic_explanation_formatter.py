"""
Critic Explanation Formatter

Task 5.1: Per-Critic Explanation Formatter

Defines standardized explanation format for each critic output.
Enforces consistent style, extracts key information, and conveys
confidence and reasoning in a clear, interpretable format.

Features:
- Standardized explanation structure
- Style enforcement and validation
- Key information extraction
- Confidence and reasoning presentation
- Support for multiple output formats (verbose, compact, structured)
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ...utils.logging import get_logger


logger = get_logger("ejc.explainability.critic_formatter")


class ExplanationStyle(Enum):
    """Output style for critic explanations"""
    VERBOSE = "verbose"      # Detailed, human-readable explanation
    COMPACT = "compact"      # Brief, essential information only
    STRUCTURED = "structured"  # Full structured data for programmatic use
    NARRATIVE = "narrative"  # Natural language paragraph form


class ConfidenceLevel(Enum):
    """Semantic confidence levels"""
    VERY_HIGH = "very_high"  # 0.9 - 1.0
    HIGH = "high"            # 0.7 - 0.9
    MEDIUM = "medium"        # 0.5 - 0.7
    LOW = "low"              # 0.3 - 0.5
    VERY_LOW = "very_low"    # 0.0 - 0.3


@dataclass
class CriticExplanation:
    """
    Standardized explanation structure for critic output.

    This provides a consistent interface for explaining critic decisions
    regardless of the underlying critic implementation.
    """
    critic_name: str
    verdict: str  # ALLOW, DENY, ESCALATE, etc.
    confidence: float  # 0.0 to 1.0
    confidence_level: ConfidenceLevel

    # Core reasoning
    primary_reason: str  # Main reason for the verdict
    supporting_reasons: List[str] = field(default_factory=list)

    # Evidence and factors
    key_factors: Dict[str, Any] = field(default_factory=dict)
    evidence_summary: Optional[str] = None

    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    processing_time_ms: Optional[float] = None
    critic_priority: Optional[str] = None
    critic_weight: Optional[float] = None

    # Additional context
    warnings: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'critic_name': self.critic_name,
            'verdict': self.verdict,
            'confidence': self.confidence,
            'confidence_level': self.confidence_level.value,
            'primary_reason': self.primary_reason,
            'supporting_reasons': self.supporting_reasons,
            'key_factors': self.key_factors,
            'evidence_summary': self.evidence_summary,
            'timestamp': self.timestamp.isoformat(),
            'processing_time_ms': self.processing_time_ms,
            'critic_priority': self.critic_priority,
            'critic_weight': self.critic_weight,
            'warnings': self.warnings,
            'limitations': self.limitations
        }


class CriticExplanationFormatter:
    """
    Formats critic outputs into standardized explanations.

    Ensures consistent style, extracts key information, and provides
    clear presentation of confidence and reasoning.
    """

    def __init__(
        self,
        default_style: ExplanationStyle = ExplanationStyle.VERBOSE,
        enforce_style: bool = True,
        include_metadata: bool = True
    ):
        """
        Initialize critic explanation formatter.

        Args:
            default_style: Default explanation style
            enforce_style: Whether to enforce style guidelines
            include_metadata: Whether to include metadata in formatted output
        """
        self.default_style = default_style
        self.enforce_style = enforce_style
        self.include_metadata = include_metadata

    def format_critic_output(
        self,
        critic_output: Dict[str, Any],
        style: Optional[ExplanationStyle] = None
    ) -> CriticExplanation:
        """
        Format raw critic output into standardized explanation.

        Args:
            critic_output: Raw output from critic
            style: Output style (uses default if None)

        Returns:
            Formatted CriticExplanation object
        """
        style = style or self.default_style

        # Extract core information
        critic_name = critic_output.get('critic_name', 'UnknownCritic')
        verdict = critic_output.get('verdict') or 'UNKNOWN'

        # Handle None or invalid confidence values
        confidence_raw = critic_output.get('confidence', 0.5)
        if confidence_raw is None:
            confidence = 0.5
        else:
            try:
                confidence = float(confidence_raw)
            except (TypeError, ValueError):
                confidence = 0.5

        # Classify confidence level
        confidence_level = self._classify_confidence(confidence)

        # Extract reasoning
        justification = critic_output.get('justification', '')
        reasoning = critic_output.get('reasoning', '')
        primary_reason, supporting_reasons = self._extract_reasoning(
            justification, reasoning
        )

        # Extract key factors
        key_factors = self._extract_key_factors(critic_output)

        # Generate evidence summary
        evidence_summary = self._generate_evidence_summary(critic_output)

        # Extract metadata
        metadata = critic_output.get('metadata', {})
        timestamp = metadata.get('timestamp')
        if timestamp and isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif not timestamp:
            timestamp = datetime.utcnow()

        processing_time = metadata.get('processing_time_ms')
        priority = metadata.get('priority')
        weight = metadata.get('weight')

        # Extract warnings and limitations
        warnings = self._extract_warnings(critic_output)
        limitations = self._extract_limitations(critic_output)

        # Create explanation object
        explanation = CriticExplanation(
            critic_name=critic_name,
            verdict=verdict,
            confidence=confidence,
            confidence_level=confidence_level,
            primary_reason=primary_reason,
            supporting_reasons=supporting_reasons,
            key_factors=key_factors,
            evidence_summary=evidence_summary,
            timestamp=timestamp,
            processing_time_ms=processing_time,
            critic_priority=priority,
            critic_weight=weight,
            warnings=warnings,
            limitations=limitations
        )

        # Enforce style if enabled
        if self.enforce_style:
            explanation = self._enforce_style_guidelines(explanation)

        logger.debug(f"Formatted explanation for {critic_name} in {style.value} style")

        return explanation

    def format_to_text(
        self,
        explanation: CriticExplanation,
        style: Optional[ExplanationStyle] = None
    ) -> str:
        """
        Format explanation as human-readable text.

        Args:
            explanation: Formatted explanation object
            style: Output style (uses default if None)

        Returns:
            Human-readable text explanation
        """
        style = style or self.default_style

        if style == ExplanationStyle.VERBOSE:
            return self._format_verbose(explanation)
        elif style == ExplanationStyle.COMPACT:
            return self._format_compact(explanation)
        elif style == ExplanationStyle.NARRATIVE:
            return self._format_narrative(explanation)
        else:  # STRUCTURED
            import json
            return json.dumps(explanation.to_dict(), indent=2)

    def _classify_confidence(self, confidence: float) -> ConfidenceLevel:
        """Classify numeric confidence into semantic level"""
        if confidence >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif confidence >= 0.7:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif confidence >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def _extract_reasoning(
        self,
        justification: str,
        reasoning: str
    ) -> tuple[str, List[str]]:
        """
        Extract primary and supporting reasons from justification text.

        Returns:
            Tuple of (primary_reason, supporting_reasons)
        """
        # Combine justification and reasoning
        full_text = f"{justification}\n{reasoning}".strip()

        if not full_text:
            return "No justification provided", []

        # Split into lines and extract reasons
        lines = [line.strip() for line in full_text.split('\n') if line.strip()]

        if not lines:
            return full_text, []

        # First substantive line is primary reason
        primary_reason = lines[0]

        # Remaining lines are supporting reasons
        supporting_reasons = lines[1:] if len(lines) > 1 else []

        return primary_reason, supporting_reasons

    def _extract_key_factors(self, critic_output: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key factors that influenced the decision"""
        factors = {}

        # Extract from metadata
        metadata = critic_output.get('metadata', {})

        # Common factor fields
        factor_fields = [
            'violations', 'flags', 'patterns_matched', 'rules_triggered',
            'risk_level', 'severity', 'impact', 'probability'
        ]

        for field in factor_fields:
            if field in metadata:
                factors[field] = metadata[field]
            elif field in critic_output:
                factors[field] = critic_output[field]

        # Extract any *_score fields
        for key, value in critic_output.items():
            if key.endswith('_score') and isinstance(value, (int, float)):
                factors[key] = value

        return factors

    def _generate_evidence_summary(self, critic_output: Dict[str, Any]) -> Optional[str]:
        """Generate a summary of the evidence used"""
        evidence = critic_output.get('evidence', [])

        if not evidence:
            return None

        if isinstance(evidence, list):
            if not evidence:
                return None
            count = len(evidence)
            return f"Based on {count} piece{'s' if count != 1 else ''} of evidence"
        elif isinstance(evidence, dict):
            return f"Evidence includes: {', '.join(evidence.keys())}"
        else:
            return str(evidence)

    def _extract_warnings(self, critic_output: Dict[str, Any]) -> List[str]:
        """Extract any warnings from critic output"""
        warnings = []

        # Check for explicit warnings field
        if 'warnings' in critic_output:
            warnings_data = critic_output['warnings']
            if isinstance(warnings_data, list):
                warnings.extend(warnings_data)
            elif isinstance(warnings_data, str):
                warnings.append(warnings_data)

        # Check metadata
        metadata = critic_output.get('metadata', {})
        if 'warnings' in metadata:
            metadata_warnings = metadata['warnings']
            if isinstance(metadata_warnings, list):
                warnings.extend(metadata_warnings)
            elif isinstance(metadata_warnings, str):
                warnings.append(metadata_warnings)

        return warnings

    def _extract_limitations(self, critic_output: Dict[str, Any]) -> List[str]:
        """Extract any stated limitations"""
        limitations = []

        # Check for explicit limitations field
        if 'limitations' in critic_output:
            lim_data = critic_output['limitations']
            if isinstance(lim_data, list):
                limitations.extend(lim_data)
            elif isinstance(lim_data, str):
                limitations.append(lim_data)

        # Infer limitations from metadata
        metadata = critic_output.get('metadata', {})

        # Low confidence is a limitation
        confidence = critic_output.get('confidence', 1.0)
        if confidence is not None:
            try:
                confidence_val = float(confidence)
                if confidence_val < 0.5:
                    limitations.append(f"Low confidence ({confidence_val:.2f}) may indicate incomplete analysis")
            except (TypeError, ValueError):
                pass  # Invalid confidence value, skip

        # Missing data is a limitation
        if metadata.get('data_incomplete'):
            limitations.append("Analysis based on incomplete data")

        return limitations

    def _enforce_style_guidelines(self, explanation: CriticExplanation) -> CriticExplanation:
        """Enforce style guidelines on explanation"""
        # Ensure primary reason is not empty
        if not explanation.primary_reason or explanation.primary_reason.strip() == "":
            explanation.primary_reason = f"Critic {explanation.critic_name} returned {explanation.verdict}"

        # Ensure primary reason ends with period
        if not explanation.primary_reason.endswith('.'):
            explanation.primary_reason += '.'

        # Capitalize first letter
        if explanation.primary_reason:
            explanation.primary_reason = explanation.primary_reason[0].upper() + explanation.primary_reason[1:]

        # Limit primary reason length (for compact style)
        max_length = 200
        if len(explanation.primary_reason) > max_length:
            explanation.primary_reason = explanation.primary_reason[:max_length-3] + '...'

        return explanation

    def _format_verbose(self, explanation: CriticExplanation) -> str:
        """Format as verbose, detailed explanation"""
        lines = []

        # Header
        lines.append(f"=== {explanation.critic_name} Explanation ===")
        lines.append("")

        # Verdict and Confidence
        lines.append(f"Verdict: {explanation.verdict}")
        lines.append(
            f"Confidence: {explanation.confidence:.2f} ({explanation.confidence_level.value.replace('_', ' ').title()})"
        )
        lines.append("")

        # Primary Reason
        lines.append("Primary Reason:")
        lines.append(f"  {explanation.primary_reason}")
        lines.append("")

        # Supporting Reasons
        if explanation.supporting_reasons:
            lines.append("Supporting Analysis:")
            for i, reason in enumerate(explanation.supporting_reasons, 1):
                lines.append(f"  {i}. {reason}")
            lines.append("")

        # Key Factors
        if explanation.key_factors:
            lines.append("Key Factors:")
            for key, value in explanation.key_factors.items():
                lines.append(f"  - {key}: {value}")
            lines.append("")

        # Evidence
        if explanation.evidence_summary:
            lines.append(f"Evidence: {explanation.evidence_summary}")
            lines.append("")

        # Warnings
        if explanation.warnings:
            lines.append("Warnings:")
            for warning in explanation.warnings:
                lines.append(f"  ⚠ {warning}")
            lines.append("")

        # Limitations
        if explanation.limitations:
            lines.append("Limitations:")
            for limitation in explanation.limitations:
                lines.append(f"  ℹ {limitation}")
            lines.append("")

        # Metadata
        if self.include_metadata:
            lines.append("Metadata:")
            if explanation.processing_time_ms:
                lines.append(f"  Processing Time: {explanation.processing_time_ms:.2f}ms")
            if explanation.critic_priority:
                lines.append(f"  Priority: {explanation.critic_priority}")
            if explanation.critic_weight:
                lines.append(f"  Weight: {explanation.critic_weight}")
            lines.append(f"  Timestamp: {explanation.timestamp.isoformat()}")

        return "\n".join(lines)

    def _format_compact(self, explanation: CriticExplanation) -> str:
        """Format as compact, essential information only"""
        parts = [
            f"{explanation.critic_name}:",
            f"{explanation.verdict}",
            f"({explanation.confidence:.2f})",
            f"- {explanation.primary_reason}"
        ]

        return " ".join(parts)

    def _format_narrative(self, explanation: CriticExplanation) -> str:
        """Format as natural language narrative"""
        # Build narrative
        narrative_parts = []

        # Introduction
        confidence_desc = explanation.confidence_level.value.replace('_', ' ')
        narrative_parts.append(
            f"The {explanation.critic_name} has determined a verdict of {explanation.verdict} "
            f"with {confidence_desc} confidence ({explanation.confidence:.2f})."
        )

        # Reasoning
        narrative_parts.append(explanation.primary_reason)

        # Supporting reasons
        if explanation.supporting_reasons:
            if len(explanation.supporting_reasons) == 1:
                narrative_parts.append(f"Additionally, {explanation.supporting_reasons[0]}")
            else:
                narrative_parts.append(
                    "This decision is further supported by several factors: " +
                    "; ".join(explanation.supporting_reasons) + "."
                )

        # Warnings
        if explanation.warnings:
            narrative_parts.append(
                f"However, please note the following: {'; '.join(explanation.warnings)}."
            )

        return " ".join(narrative_parts)


def format_critic_output(
    critic_output: Dict[str, Any],
    style: ExplanationStyle = ExplanationStyle.VERBOSE
) -> str:
    """
    Convenience function to format critic output as text.

    Args:
        critic_output: Raw critic output dictionary
        style: Desired explanation style

    Returns:
        Formatted text explanation
    """
    formatter = CriticExplanationFormatter(default_style=style)
    explanation = formatter.format_critic_output(critic_output)
    return formatter.format_to_text(explanation, style)


def format_multiple_critics(
    critic_outputs: List[Dict[str, Any]],
    style: ExplanationStyle = ExplanationStyle.COMPACT
) -> str:
    """
    Format multiple critic outputs into a combined view.

    Args:
        critic_outputs: List of critic output dictionaries
        style: Desired explanation style

    Returns:
        Combined formatted text
    """
    formatter = CriticExplanationFormatter(default_style=style)

    lines = []
    lines.append("=== Critic Explanations ===")
    lines.append("")

    for i, output in enumerate(critic_outputs, 1):
        explanation = formatter.format_critic_output(output)
        text = formatter.format_to_text(explanation, style)

        if style != ExplanationStyle.COMPACT:
            lines.append(f"--- Critic {i} ---")
        lines.append(text)
        lines.append("")

    return "\n".join(lines)
