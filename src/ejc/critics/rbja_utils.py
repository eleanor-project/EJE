"""
Shared utilities for RBJA (Rights-Based Jurisprudence Architecture) critics.

Provides common pattern matching, NLP, and detection utilities used across
multiple critic implementations.
"""

import re
from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass


@dataclass
class DetectionResult:
    """Result of a pattern detection check."""
    detected: bool
    confidence: float
    evidence: List[str]
    severity: str = "low"  # low, moderate, high, critical


class PatternMatcher:
    """Sophisticated pattern matching for rights violations and ethical concerns."""

    # Dignity violation patterns
    DIGNITY_PATTERNS = [
        r'\b(treat|use|regard)\s+(as\s+)?(mere\s+)?(\w+\s+)?(object|tool|instrument|means)\b',
        r'\b(exploit|manipulate|coerce|deceive)\s+(\w+\s+)?people\b',
        r'\bwithout\s+(their\s+)?consent\b',
        r'\b(dehumaniz|objectif|commodif)\w+\b',
        r'\binstrumentaliz\w+\b',
        r'\bdegrad(e|ing|ation)\b',
        r'\bhumiliat(e|ing|ion)\b',
    ]

    # Autonomy violation patterns
    AUTONOMY_PATTERNS = [
        r'\b(force|compel|coerce|mandate)\s+(\w+\s+)?(to|into)\b',
        r'\b(remove|eliminate|deny)\s+(\w+\s+)?choice\b',
        r'\b(manipulat|deceiv)\w+\s+into\b',
        r'\bno\s+(real\s+)?alternative\b',
        r'\b(involuntary|unwilling|against\s+will)\b',
        r'\black\s+of\s+agency\b',
        r'\bpaternalistic\s+decision\b',
    ]

    # Discrimination patterns
    DISCRIMINATION_PATTERNS = [
        r'\b(discriminat|bias|prejudic)\w+\s+(against|toward)\b',
        r'\b(unfair|unequal)\s+treatment\s+(of|toward|against)\b',
        r'\bbased\s+on\s+(race|gender|sex|age|religion|disability|orientation)\b',
        r'\b(exclude|deny|restrict)\s+(\w+\s+)?(based\s+on|because\s+of)\b',
        r'\b(stereotype|stigmatiz)\w+\b',
        r'\b(systemic|institutional)\s+(bias|discrimination)\b',
    ]

    # Protected groups keywords
    PROTECTED_GROUPS = {
        'race', 'ethnicity', 'color', 'national origin',
        'gender', 'sex', 'sexual orientation', 'gender identity',
        'religion', 'religious belief', 'creed',
        'age', 'elderly', 'senior',
        'disability', 'disabled', 'handicap',
        'pregnancy', 'familial status',
        'veteran status', 'military service'
    }

    # Safety/harm patterns
    HARM_PHYSICAL = [
        r'\b(injur|harm|hurt|damage)\s+(physical|bodily)\b',
        r'\b(violence|assault|attack)\b',
        r'\b(dangerous|hazard|risk)\s+(to\s+)?(health|safety|life)\b',
        r'\bdeath|fatal|lethal\b',
        r'\btoxic|poison|contamina\w+\b',
    ]

    HARM_PSYCHOLOGICAL = [
        r'\b(mental|psychological|emotional)\s+(harm|damage|abuse|trauma)\b',
        r'\b(anxiety|depression|stress|ptsd)\b',
        r'\b(psychological\s+)?manipulation\b',
        r'\bgaslighting\b',
        r'\btrauma(tic|tiz)\w*\b',
    ]

    HARM_SOCIAL = [
        r'\b(social|reputational)\s+(harm|damage)\b',
        r'\b(ostraciz|exclusion|isolation)\b',
        r'\b(defam|slander|libel)\w+\b',
        r'\breputation(al)?\s+damage\b',
    ]

    # Truth/accuracy patterns
    MISINFORMATION_PATTERNS = [
        r'\b(false|misleading|deceptive)\s+(information|claim|statement)\b',
        r'\b(misinformation|disinformation|fake\s+news)\b',
        r'\b(fabricat|manufactur)\w+\s+(evidence|fact|data)\b',
        r'\bdeliberate(ly)?\s+(false|misleading)\b',
        r'\bwithout\s+evidence\b',
        r'\bunverified\s+claim\b',
    ]

    # Fairness patterns
    UNFAIRNESS_PATTERNS = [
        r'\b(unfair|inequitable|unjust)\b',
        r'\bdisparate\s+(impact|treatment)\b',
        r'\bunequal\s+(access|opportunity|treatment)\b',
        r'\badvantage\s+(some|certain)\s+over\s+(others|rest)\b',
        r'\b(privilege|favor)\s+(one|some)\s+group\b',
    ]

    @classmethod
    def detect_patterns(
        cls,
        text: str,
        patterns: List[str],
        case_sensitive: bool = False
    ) -> DetectionResult:
        """
        Detect if any patterns match in the text.

        Args:
            text: Text to search
            patterns: List of regex patterns
            case_sensitive: Whether to do case-sensitive matching

        Returns:
            DetectionResult with detection status, confidence, and evidence
        """
        flags = 0 if case_sensitive else re.IGNORECASE
        evidence = []
        matches = 0

        for pattern in patterns:
            compiled = re.compile(pattern, flags)
            for match in compiled.finditer(text):
                evidence.append(match.group(0))
                matches += 1

        detected = len(evidence) > 0
        confidence = min(1.0, len(evidence) * 0.3)  # More matches = higher confidence

        return DetectionResult(
            detected=detected,
            confidence=confidence,
            evidence=evidence[:5],  # Limit evidence to top 5
            severity=cls._calculate_severity(matches)
        )

    @classmethod
    def _calculate_severity(cls, match_count: int) -> str:
        """Calculate severity based on number of matches."""
        if match_count >= 5:
            return "critical"
        elif match_count >= 3:
            return "high"
        elif match_count >= 2:
            return "moderate"
        elif match_count >= 1:
            return "low"
        return "none"

    @classmethod
    def detect_protected_group_mention(cls, text: str) -> Tuple[bool, Set[str]]:
        """
        Detect if text mentions protected groups.

        Returns:
            (found, set of mentioned groups)
        """
        text_lower = text.lower()
        mentioned = {group for group in cls.PROTECTED_GROUPS if group in text_lower}
        return len(mentioned) > 0, mentioned

    @classmethod
    def extract_key_phrases(cls, text: str, max_phrases: int = 10) -> List[str]:
        """Extract key phrases from text (simple implementation)."""
        # Remove common words and extract important phrases
        sentences = re.split(r'[.!?]+', text)
        phrases = []

        for sentence in sentences[:max_phrases]:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Skip very short fragments
                phrases.append(sentence)

        return phrases


class ConfidenceCalculator:
    """Calculate confidence scores based on multiple signals."""

    @staticmethod
    def combine_signals(
        pattern_confidence: float,
        context_confidence: float,
        match_count: int,
        text_length: int
    ) -> float:
        """
        Combine multiple confidence signals into final score.

        Args:
            pattern_confidence: Confidence from pattern matching
            context_confidence: Confidence from context analysis
            match_count: Number of pattern matches
            text_length: Length of text analyzed

        Returns:
            Combined confidence score (0.0-1.0)
        """
        # Weight pattern matching heavily
        base_confidence = pattern_confidence * 0.6 + context_confidence * 0.4

        # Boost for multiple matches
        match_boost = min(0.2, match_count * 0.05)

        # Penalize very short texts (less reliable)
        length_penalty = 0 if text_length > 100 else (100 - text_length) / 200

        final = base_confidence + match_boost - length_penalty
        return max(0.0, min(1.0, final))

    @staticmethod
    def aggregate_multi_check(results: List[DetectionResult]) -> float:
        """
        Aggregate confidence from multiple detection checks.

        Args:
            results: List of DetectionResult objects

        Returns:
            Aggregated confidence (0.0-1.0)
        """
        if not results:
            return 0.0

        detected_results = [r for r in results if r.detected]
        if not detected_results:
            return 0.0

        # Average confidence of detected items
        avg_confidence = sum(r.confidence for r in detected_results) / len(detected_results)

        # Boost for multiple detections
        detection_boost = min(0.3, len(detected_results) * 0.1)

        return min(1.0, avg_confidence + detection_boost)


class EvidenceBuilder:
    """Build structured evidence for critic justifications."""

    @staticmethod
    def build_justification(
        verdict: str,
        primary_reason: str,
        evidence: List[str],
        severity: str,
        confidence: float
    ) -> str:
        """
        Build a structured justification message.

        Args:
            verdict: The verdict (ALLOW, BLOCK, REVIEW)
            primary_reason: Main reason for verdict
            evidence: List of evidence strings
            severity: Severity level
            confidence: Confidence score

        Returns:
            Formatted justification string
        """
        parts = [
            f"Verdict: {verdict}",
            f"Reason: {primary_reason}",
            f"Severity: {severity}",
            f"Confidence: {confidence:.2f}"
        ]

        if evidence:
            evidence_str = "; ".join(evidence[:3])  # Top 3 pieces of evidence
            parts.append(f"Evidence: {evidence_str}")

        return " | ".join(parts)

    @staticmethod
    def build_multi_violation_justification(
        violations: List[Dict[str, Any]],
        verdict: str
    ) -> str:
        """
        Build justification for multiple violations.

        Args:
            violations: List of violation dicts with 'right', 'severity', 'evidence'
            verdict: Final verdict

        Returns:
            Formatted justification
        """
        if not violations:
            return f"{verdict}: No violations detected"

        critical_violations = [v for v in violations if v.get('severity') == 'critical']

        if critical_violations:
            violation = critical_violations[0]
            return f"{verdict}: Critical {violation['right']} violation detected - {violation.get('evidence', [''])[0]}"

        # Multiple non-critical violations
        violation_summary = ", ".join([v['right'] for v in violations])
        return f"{verdict}: Multiple concerns detected ({violation_summary})"
