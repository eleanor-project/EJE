"""
Privacy-preserving precedent bundling for federated sharing.

Implements k-anonymity bundling to enable precedent sharing across nodes
while protecting individual case privacy. Uses clustering to group similar
cases and generalize sensitive attributes.

This implements Gap #1 Phase 3: K-Anonymity Bundling
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
import json
import hashlib

import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity

from .embeddings import embed_text
from ...utils.logging import get_logger


logger = get_logger("ejc.precedent.privacy")


@dataclass
class AnonymousBundle:
    """
    K-anonymous precedent bundle safe for federated sharing.

    Contains aggregated statistics and generalized patterns from
    at least k similar precedents to prevent re-identification.
    """

    bundle_id: str
    k_value: int  # Anonymity level (minimum precedents in bundle)
    precedent_count: int
    created_at: str

    # Aggregated statistics
    verdict_distribution: Dict[str, int]  # {"ALLOW": 5, "DENY": 2}
    avg_confidence: float
    confidence_range: tuple  # (min, max)

    # Generalized themes (most common keywords/concepts)
    common_themes: List[str]
    context_patterns: Dict[str, Any]

    # Temporal info (generalized)
    time_period: str  # e.g., "2025-Q4"

    # Privacy guarantees
    privacy_guarantee: str  # "k-anonymity", "differential-privacy"
    suppressed_fields: List[str]  # Fields removed for privacy

    # Metadata
    source_node: Optional[str] = None
    consent_given: bool = True


@dataclass
class PrivacyConfig:
    """Configuration for privacy-preserving operations."""

    min_k: int = 5  # Minimum k for k-anonymity
    max_k: int = 20  # Maximum bundle size
    similarity_threshold: float = 0.75  # For clustering
    suppress_pii: bool = True
    differential_privacy: bool = False
    noise_scale: float = 0.1


class KAnonymityBundler:
    """
    Creates k-anonymous precedent bundles for privacy-preserving sharing.

    Groups similar precedents into bundles where each bundle contains
    at least k similar cases, making individual case re-identification
    infeasible.
    """

    def __init__(
        self,
        config: Optional[PrivacyConfig] = None,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize K-anonymity bundler.

        Args:
            config: Privacy configuration
            embedding_model: Model for semantic similarity
        """
        self.config = config or PrivacyConfig()
        self.embedding_model = embedding_model

    def create_bundles(
        self,
        precedents: List[Dict[str, Any]],
        k: Optional[int] = None
    ) -> List[AnonymousBundle]:
        """
        Create k-anonymous bundles from precedents.

        Args:
            precedents: List of precedent dicts with input_data, outcome, etc.
            k: Override default k value (min precedents per bundle)

        Returns:
            List of AnonymousBundle objects

        Raises:
            ValueError: If insufficient precedents for even one bundle
        """
        k_value = k or self.config.min_k

        if len(precedents) < k_value:
            raise ValueError(
                f"Need at least {k_value} precedents for k-anonymity, "
                f"got {len(precedents)}"
            )

        logger.info(f"Creating k-anonymous bundles (k={k_value}) from {len(precedents)} precedents")

        # Cluster similar precedents
        clusters = self._cluster_precedents(precedents, k_value)

        logger.info(f"Created {len(clusters)} clusters")

        # Create bundles from clusters
        bundles = []
        for cluster_precedents in clusters:
            if len(cluster_precedents) >= k_value:
                bundle = self._create_bundle(cluster_precedents, k_value)
                bundles.append(bundle)
            else:
                logger.warning(
                    f"Skipping cluster with {len(cluster_precedents)} precedents "
                    f"(below k={k_value})"
                )

        logger.info(f"Created {len(bundles)} k-anonymous bundles")
        return bundles

    def _cluster_precedents(
        self,
        precedents: List[Dict],
        min_k: int
    ) -> List[List[Dict]]:
        """
        Cluster precedents by semantic similarity.

        Args:
            precedents: List of precedent dicts
            min_k: Minimum cluster size

        Returns:
            List of clusters (each cluster is a list of precedents)
        """
        if len(precedents) == 0:
            return []

        # Generate embeddings
        embeddings = []
        for prec in precedents:
            input_data = prec.get("input_data", {})
            input_text = json.dumps(input_data, sort_keys=True)
            embedding = embed_text(input_text, self.embedding_model)
            embeddings.append(embedding)

        embeddings_array = np.array(embeddings)

        # Use DBSCAN for density-based clustering
        # eps = 1 - similarity_threshold for cosine distance
        eps = 1.0 - self.config.similarity_threshold

        clusterer = DBSCAN(
            eps=eps,
            min_samples=min_k,
            metric='cosine'
        )

        labels = clusterer.fit_predict(embeddings_array)

        # Group precedents by cluster label
        clusters_dict: Dict[int, List[Dict]] = {}
        for idx, label in enumerate(labels):
            if label == -1:
                # Noise point - create singleton cluster
                continue

            if label not in clusters_dict:
                clusters_dict[label] = []
            clusters_dict[label].append(precedents[idx])

        # Convert to list of clusters
        clusters = list(clusters_dict.values())

        # Handle noise points by merging small clusters
        noise_precedents = [
            precedents[idx] for idx, label in enumerate(labels) if label == -1
        ]

        if noise_precedents and len(noise_precedents) >= min_k:
            clusters.append(noise_precedents)

        return clusters

    def _create_bundle(
        self,
        precedents: List[Dict],
        k_value: int
    ) -> AnonymousBundle:
        """
        Create an anonymous bundle from a cluster of precedents.

        Args:
            precedents: List of similar precedents
            k_value: K-anonymity level

        Returns:
            AnonymousBundle with aggregated data
        """
        # Generate bundle ID
        bundle_id = self._generate_bundle_id(precedents)

        # Aggregate verdicts
        verdict_counts: Dict[str, int] = {}
        confidences = []

        for prec in precedents:
            outcome = prec.get("outcome", {})
            verdict = outcome.get("verdict", "UNKNOWN")
            confidence = outcome.get("confidence", 0.5)

            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
            confidences.append(confidence)

        avg_confidence = np.mean(confidences) if confidences else 0.5
        confidence_range = (float(np.min(confidences)), float(np.max(confidences))) if confidences else (0.0, 1.0)

        # Extract common themes
        common_themes = self._extract_common_themes(precedents)

        # Generalize context patterns
        context_patterns = self._generalize_context(precedents)

        # Determine time period (generalized)
        time_period = self._generalize_time_period(precedents)

        # Identify suppressed fields
        suppressed_fields = self._identify_suppressed_fields()

        return AnonymousBundle(
            bundle_id=bundle_id,
            k_value=k_value,
            precedent_count=len(precedents),
            created_at=datetime.utcnow().isoformat(),
            verdict_distribution=verdict_counts,
            avg_confidence=float(avg_confidence),
            confidence_range=confidence_range,
            common_themes=common_themes,
            context_patterns=context_patterns,
            time_period=time_period,
            privacy_guarantee="k-anonymity",
            suppressed_fields=suppressed_fields,
            consent_given=True
        )

    def _generate_bundle_id(self, precedents: List[Dict]) -> str:
        """Generate unique bundle ID from precedent hashes."""
        # Sort decision IDs for deterministic hashing
        decision_ids = sorted([
            prec.get("decision_id", str(i))
            for i, prec in enumerate(precedents)
        ])

        combined = "".join(decision_ids)
        hash_val = hashlib.sha256(combined.encode()).hexdigest()

        return f"bundle-{hash_val[:16]}"

    def _extract_common_themes(
        self,
        precedents: List[Dict],
        top_n: int = 5
    ) -> List[str]:
        """
        Extract common themes/keywords from precedents.

        Args:
            precedents: List of precedents
            top_n: Number of themes to return

        Returns:
            List of common theme strings
        """
        # Simple word frequency analysis
        word_counts: Dict[str, int] = {}

        for prec in precedents:
            input_data = prec.get("input_data", {})
            prompt = input_data.get("prompt", "")

            # Tokenize (simple approach)
            words = prompt.lower().split()

            # Count significant words (filter common stopwords)
            stopwords = {"the", "a", "an", "is", "are", "was", "were", "to", "of", "and", "or"}
            for word in words:
                word = word.strip(".,!?;:")
                if word and len(word) > 3 and word not in stopwords:
                    word_counts[word] = word_counts.get(word, 0) + 1

        # Get top N most common
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        common_themes = [word for word, count in sorted_words[:top_n]]

        return common_themes

    def _generalize_context(self, precedents: List[Dict]) -> Dict[str, Any]:
        """
        Generalize context patterns from precedents.

        Args:
            precedents: List of precedents

        Returns:
            Generalized context dict
        """
        # Count context field occurrences
        field_counts: Dict[str, int] = {}
        field_values: Dict[str, Set[Any]] = {}

        for prec in precedents:
            context = prec.get("input_data", {}).get("context", {})

            for key, value in context.items():
                field_counts[key] = field_counts.get(key, 0) + 1

                if key not in field_values:
                    field_values[key] = set()

                # Store value types, not actual values (for privacy)
                field_values[key].add(type(value).__name__)

        # Create generalized pattern
        patterns = {}
        for key, count in field_counts.items():
            frequency = count / len(precedents)
            patterns[key] = {
                "present_in": f"{frequency:.0%}",
                "types": list(field_values.get(key, set()))
            }

        return patterns

    def _generalize_time_period(self, precedents: List[Dict]) -> str:
        """
        Generalize timestamps to quarter/year for privacy.

        Args:
            precedents: List of precedents

        Returns:
            Generalized time period string (e.g., "2025-Q4")
        """
        timestamps = []

        for prec in precedents:
            timestamp_str = prec.get("timestamp", "")
            try:
                timestamp_str = timestamp_str.replace('Z', '+00:00')
                timestamp = datetime.fromisoformat(timestamp_str)
                timestamps.append(timestamp)
            except (ValueError, AttributeError):
                continue

        if not timestamps:
            return "unknown"

        # Use most recent timestamp
        most_recent = max(timestamps)

        # Determine quarter
        quarter = (most_recent.month - 1) // 3 + 1

        return f"{most_recent.year}-Q{quarter}"

    def _identify_suppressed_fields(self) -> List[str]:
        """
        Identify fields suppressed for privacy.

        Returns:
            List of suppressed field names
        """
        suppressed = [
            "user_id",
            "session_id",
            "ip_address",
            "email",
            "phone",
            "exact_timestamp",
            "precise_location",
            "device_id"
        ]

        if self.config.suppress_pii:
            suppressed.extend([
                "name",
                "address",
                "ssn",
                "credit_card",
                "medical_record"
            ])

        return suppressed

    def verify_k_anonymity(
        self,
        bundle: AnonymousBundle,
        required_k: Optional[int] = None
    ) -> bool:
        """
        Verify that a bundle meets k-anonymity requirements.

        Args:
            bundle: Bundle to verify
            required_k: Required k value (default: use config)

        Returns:
            True if bundle is k-anonymous
        """
        required = required_k or self.config.min_k

        if bundle.precedent_count < required:
            logger.warning(
                f"Bundle {bundle.bundle_id} has {bundle.precedent_count} precedents "
                f"(required: {required})"
            )
            return False

        if bundle.k_value < required:
            logger.warning(
                f"Bundle {bundle.bundle_id} k_value={bundle.k_value} "
                f"(required: {required})"
            )
            return False

        return True

    def bundle_to_dict(self, bundle: AnonymousBundle) -> Dict[str, Any]:
        """
        Convert bundle to dictionary for serialization.

        Args:
            bundle: AnonymousBundle instance

        Returns:
            Dictionary representation
        """
        return asdict(bundle)

    def bundle_from_dict(self, data: Dict[str, Any]) -> AnonymousBundle:
        """
        Create bundle from dictionary.

        Args:
            data: Dictionary with bundle data

        Returns:
            AnonymousBundle instance
        """
        return AnonymousBundle(**data)

    def export_bundles(
        self,
        bundles: List[AnonymousBundle],
        filepath: str
    ):
        """
        Export bundles to JSON file.

        Args:
            bundles: List of bundles to export
            filepath: Output file path
        """
        bundles_data = [self.bundle_to_dict(b) for b in bundles]

        with open(filepath, 'w') as f:
            json.dump({
                "export_timestamp": datetime.utcnow().isoformat(),
                "bundle_count": len(bundles),
                "privacy_guarantee": "k-anonymity",
                "bundles": bundles_data
            }, f, indent=2)

        logger.info(f"Exported {len(bundles)} bundles to {filepath}")

    def import_bundles(self, filepath: str) -> List[AnonymousBundle]:
        """
        Import bundles from JSON file.

        Args:
            filepath: Input file path

        Returns:
            List of AnonymousBundle objects
        """
        with open(filepath, 'r') as f:
            data = json.load(f)

        bundles = [
            self.bundle_from_dict(b) for b in data.get("bundles", [])
        ]

        logger.info(f"Imported {len(bundles)} bundles from {filepath}")
        return bundles
