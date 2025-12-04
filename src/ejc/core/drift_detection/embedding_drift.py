"""
Embedding-based drift detection for precedent reasoning.

Detects governance drift by analyzing the semantic distribution
of recent decisions compared to historical precedents using
embedding centroids and distance metrics.

This implements Gap #1 Phase 3: Drift Detection via Embedding Distance
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from ..precedent.embeddings import embed_text
from ...utils.logging import get_logger


logger = get_logger("ejc.drift.embedding")


@dataclass
class DriftReport:
    """Report of detected governance drift."""

    drift_detected: bool
    drift_distance: float  # Cosine distance between centroids
    drift_threshold: float
    historical_period_days: int
    recent_period_days: int
    historical_count: int
    recent_count: int
    confidence: float  # Confidence in drift detection (0-1)
    timestamp: str
    explanation: str
    recommendations: List[str]
    details: Dict


class EmbeddingDriftDetector:
    """
    Detects governance drift using embedding distance analysis.

    Compares the semantic distribution of recent decisions against
    historical precedents to identify shifts in reasoning patterns.
    """

    def __init__(
        self,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        drift_threshold: float = 0.15,
        min_sample_size: int = 10
    ):
        """
        Initialize embedding drift detector.

        Args:
            embedding_model: Sentence-transformers model name
            drift_threshold: Threshold for flagging drift (cosine distance)
            min_sample_size: Minimum samples needed for detection
        """
        self.embedding_model = embedding_model
        self.drift_threshold = drift_threshold
        self.min_sample_size = min_sample_size

    def detect_drift(
        self,
        decisions: List[Dict],
        lookback_days: int = 30,
        recent_days: int = 7
    ) -> DriftReport:
        """
        Detect drift by comparing recent vs historical decision patterns.

        Args:
            decisions: List of decision dicts with input_data and timestamps
            lookback_days: Historical period to analyze
            recent_days: Recent period to compare against historical

        Returns:
            DriftReport with analysis results
        """
        # Partition decisions into historical and recent
        historical, recent = self._partition_decisions(
            decisions,
            lookback_days,
            recent_days
        )

        # Check if we have enough data
        if len(historical) < self.min_sample_size:
            return DriftReport(
                drift_detected=False,
                drift_distance=0.0,
                drift_threshold=self.drift_threshold,
                historical_period_days=lookback_days - recent_days,
                recent_period_days=recent_days,
                historical_count=len(historical),
                recent_count=len(recent),
                confidence=0.0,
                timestamp=datetime.utcnow().isoformat(),
                explanation=f"Insufficient historical data ({len(historical)} < {self.min_sample_size})",
                recommendations=["Collect more precedent data before drift detection"],
                details={}
            )

        if len(recent) < self.min_sample_size:
            return DriftReport(
                drift_detected=False,
                drift_distance=0.0,
                drift_threshold=self.drift_threshold,
                historical_period_days=lookback_days - recent_days,
                recent_period_days=recent_days,
                historical_count=len(historical),
                recent_count=len(recent),
                confidence=0.0,
                timestamp=datetime.utcnow().isoformat(),
                explanation=f"Insufficient recent data ({len(recent)} < {self.min_sample_size})",
                recommendations=["Wait for more recent decisions before analysis"],
                details={}
            )

        # Generate embeddings for both periods
        logger.info(f"Generating embeddings for {len(historical)} historical decisions")
        historical_embeddings = self._generate_embeddings(historical)

        logger.info(f"Generating embeddings for {len(recent)} recent decisions")
        recent_embeddings = self._generate_embeddings(recent)

        # Calculate centroids
        historical_centroid = np.mean(historical_embeddings, axis=0)
        recent_centroid = np.mean(recent_embeddings, axis=0)

        # Measure drift as cosine distance
        similarity = cosine_similarity(
            [historical_centroid],
            [recent_centroid]
        )[0][0]
        drift_distance = 1.0 - similarity

        # Calculate confidence based on sample sizes
        confidence = self._calculate_confidence(len(historical), len(recent))

        # Detect drift
        drift_detected = drift_distance > self.drift_threshold

        # Generate explanation and recommendations
        explanation, recommendations = self._generate_analysis(
            drift_detected,
            drift_distance,
            len(historical),
            len(recent),
            historical_embeddings,
            recent_embeddings
        )

        # Additional details
        details = {
            "historical_centroid_norm": float(np.linalg.norm(historical_centroid)),
            "recent_centroid_norm": float(np.linalg.norm(recent_centroid)),
            "similarity_score": float(similarity),
            "variance_historical": float(np.var(historical_embeddings)),
            "variance_recent": float(np.var(recent_embeddings)),
        }

        return DriftReport(
            drift_detected=drift_detected,
            drift_distance=float(drift_distance),
            drift_threshold=self.drift_threshold,
            historical_period_days=lookback_days - recent_days,
            recent_period_days=recent_days,
            historical_count=len(historical),
            recent_count=len(recent),
            confidence=confidence,
            timestamp=datetime.utcnow().isoformat(),
            explanation=explanation,
            recommendations=recommendations,
            details=details
        )

    def _partition_decisions(
        self,
        decisions: List[Dict],
        lookback_days: int,
        recent_days: int
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Partition decisions into historical and recent periods.

        Args:
            decisions: All decisions
            lookback_days: Total lookback period
            recent_days: Recent period size

        Returns:
            (historical_decisions, recent_decisions)
        """
        now = datetime.utcnow()
        recent_cutoff = now - timedelta(days=recent_days)
        historical_cutoff = now - timedelta(days=lookback_days)

        historical = []
        recent = []

        for decision in decisions:
            timestamp_str = decision.get("timestamp", "")
            try:
                # Parse ISO format timestamp
                if timestamp_str:
                    # Handle both with and without 'Z' suffix
                    timestamp_str = timestamp_str.replace('Z', '+00:00')
                    timestamp = datetime.fromisoformat(timestamp_str)

                    if timestamp >= recent_cutoff:
                        recent.append(decision)
                    elif timestamp >= historical_cutoff:
                        historical.append(decision)
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
                continue

        return historical, recent

    def _generate_embeddings(self, decisions: List[Dict]) -> np.ndarray:
        """
        Generate embeddings for a list of decisions.

        Args:
            decisions: List of decision dicts

        Returns:
            Numpy array of embeddings (N x embedding_dim)
        """
        embeddings = []

        for decision in decisions:
            input_data = decision.get("input_data", {})
            input_text = json.dumps(input_data, sort_keys=True)

            embedding = embed_text(input_text, self.embedding_model)
            embeddings.append(embedding)

        return np.array(embeddings)

    def _calculate_confidence(
        self,
        historical_count: int,
        recent_count: int
    ) -> float:
        """
        Calculate confidence in drift detection based on sample sizes.

        Args:
            historical_count: Number of historical samples
            recent_count: Number of recent samples

        Returns:
            Confidence score (0-1)
        """
        # More samples = higher confidence
        # Use sigmoid-like function

        min_count = min(historical_count, recent_count)
        max_confidence = 0.95  # Cap at 95%

        # Target 50% confidence at min_sample_size, 90% at 100 samples
        if min_count < self.min_sample_size:
            return 0.0

        # Logarithmic scale
        confidence = max_confidence * (
            1.0 - np.exp(-0.03 * min_count)
        )

        return min(confidence, max_confidence)

    def _generate_analysis(
        self,
        drift_detected: bool,
        drift_distance: float,
        historical_count: int,
        recent_count: int,
        historical_embeddings: np.ndarray,
        recent_embeddings: np.ndarray
    ) -> Tuple[str, List[str]]:
        """
        Generate human-readable analysis and recommendations.

        Args:
            drift_detected: Whether drift was detected
            drift_distance: Measured drift distance
            historical_count: Historical sample count
            recent_count: Recent sample count
            historical_embeddings: Historical embedding vectors
            recent_embeddings: Recent embedding vectors

        Returns:
            (explanation, recommendations)
        """
        explanation_parts = []
        recommendations = []

        if drift_detected:
            severity = self._classify_drift_severity(drift_distance)
            explanation_parts.append(
                f"🚨 {severity} governance drift detected "
                f"(distance: {drift_distance:.3f}, threshold: {self.drift_threshold:.3f})"
            )

            # Analyze variance changes
            hist_var = np.var(historical_embeddings)
            recent_var = np.var(recent_embeddings)
            var_change = (recent_var - hist_var) / hist_var if hist_var > 0 else 0

            if abs(var_change) > 0.2:
                if var_change > 0:
                    explanation_parts.append(
                        f"Recent decisions show {abs(var_change):.1%} higher variance "
                        "(more diverse cases)"
                    )
                else:
                    explanation_parts.append(
                        f"Recent decisions show {abs(var_change):.1%} lower variance "
                        "(more consistent patterns)"
                    )

            # Recommendations
            recommendations.append(
                "🔍 Review recent decisions for systematic changes in reasoning"
            )
            recommendations.append(
                "📊 Compare critic outputs between historical and recent periods"
            )

            if severity == "CRITICAL":
                recommendations.append(
                    "⚠️ Consider freezing new precedents until drift is investigated"
                )
                recommendations.append(
                    "👥 Schedule human review of recent high-stakes decisions"
                )
            elif severity == "HIGH":
                recommendations.append(
                    "🔄 Consider recalibrating critics with recent feedback"
                )

        else:
            explanation_parts.append(
                f"✅ No significant drift detected "
                f"(distance: {drift_distance:.3f}, threshold: {self.drift_threshold:.3f})"
            )
            explanation_parts.append(
                f"Analyzed {historical_count} historical and {recent_count} recent decisions"
            )

            recommendations.append(
                "✓ Governance patterns remain consistent"
            )
            recommendations.append(
                "📈 Continue monitoring for drift in future periods"
            )

        explanation = " ".join(explanation_parts)
        return explanation, recommendations

    def _classify_drift_severity(self, drift_distance: float) -> str:
        """
        Classify drift severity based on distance.

        Args:
            drift_distance: Measured drift distance

        Returns:
            Severity level: CRITICAL, HIGH, MODERATE
        """
        if drift_distance >= self.drift_threshold * 2:
            return "CRITICAL"
        elif drift_distance >= self.drift_threshold * 1.5:
            return "HIGH"
        else:
            return "MODERATE"

    def compare_periods(
        self,
        decisions: List[Dict],
        period1_start: int,
        period1_end: int,
        period2_start: int,
        period2_end: int
    ) -> Dict:
        """
        Compare two arbitrary time periods for drift.

        Args:
            decisions: All decisions
            period1_start/end: First period (days ago)
            period2_start/end: Second period (days ago)

        Returns:
            Comparison dict with drift metrics
        """
        now = datetime.utcnow()

        period1_start_date = now - timedelta(days=period1_start)
        period1_end_date = now - timedelta(days=period1_end)
        period2_start_date = now - timedelta(days=period2_start)
        period2_end_date = now - timedelta(days=period2_end)

        # Filter decisions for each period
        period1_decisions = []
        period2_decisions = []

        for decision in decisions:
            timestamp_str = decision.get("timestamp", "")
            try:
                timestamp_str = timestamp_str.replace('Z', '+00:00')
                timestamp = datetime.fromisoformat(timestamp_str)

                if period1_end_date <= timestamp <= period1_start_date:
                    period1_decisions.append(decision)
                elif period2_end_date <= timestamp <= period2_start_date:
                    period2_decisions.append(decision)
            except (ValueError, AttributeError):
                continue

        # Generate embeddings
        if len(period1_decisions) < self.min_sample_size or len(period2_decisions) < self.min_sample_size:
            return {
                "error": "Insufficient data for comparison",
                "period1_count": len(period1_decisions),
                "period2_count": len(period2_decisions),
                "min_required": self.min_sample_size
            }

        embeddings1 = self._generate_embeddings(period1_decisions)
        embeddings2 = self._generate_embeddings(period2_decisions)

        centroid1 = np.mean(embeddings1, axis=0)
        centroid2 = np.mean(embeddings2, axis=0)

        similarity = cosine_similarity([centroid1], [centroid2])[0][0]
        drift_distance = 1.0 - similarity

        return {
            "period1": {
                "start_days_ago": period1_start,
                "end_days_ago": period1_end,
                "decision_count": len(period1_decisions)
            },
            "period2": {
                "start_days_ago": period2_start,
                "end_days_ago": period2_end,
                "decision_count": len(period2_decisions)
            },
            "drift_distance": float(drift_distance),
            "similarity": float(similarity),
            "drift_detected": drift_distance > self.drift_threshold,
            "timestamp": datetime.utcnow().isoformat()
        }
