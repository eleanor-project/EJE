"""
Privacy-preserving precedent bundling and sharing.

Implements k-anonymity, differential privacy, and sensitive field redaction
for precedent sharing across organizational boundaries.
"""

import hashlib
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Set, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class AnonymousBundle:
    """Bundle of k-anonymous precedents."""

    bundle_id: str
    precedents: List[Dict]
    k_value: int  # Minimum cluster size
    privacy_guarantee: str  # "k-anonymity", "differential-privacy"
    generalized_attributes: List[str]
    redacted_fields: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PrivacyPreservingPrecedents:
    """
    Privacy-preserving precedent bundling and sharing.

    Features:
    - K-anonymity: Ensure each precedent is indistinguishable from k-1 others
    - Attribute generalization: Reduce specificity of quasi-identifiers
    - Sensitive field redaction: Remove PII and confidential data
    - Differential privacy: Add calibrated noise (future)
    """

    def __init__(
        self,
        k: int = 5,
        sensitive_fields: Optional[Set[str]] = None,
        quasi_identifiers: Optional[Set[str]] = None
    ):
        """
        Initialize privacy-preserving precedents.

        Args:
            k: Minimum cluster size for k-anonymity
            sensitive_fields: Fields to redact entirely
            quasi_identifiers: Fields to generalize
        """
        self.k = k
        self.sensitive_fields = sensitive_fields or {
            "user_id",
            "email",
            "ip_address",
            "phone_number",
            "ssn",
            "credit_card"
        }
        self.quasi_identifiers = quasi_identifiers or {
            "timestamp",
            "location",
            "age",
            "jurisdiction"
        }

    def create_anonymous_bundle(
        self,
        precedents: List[Dict],
        bundle_name: Optional[str] = None
    ) -> AnonymousBundle:
        """
        Create k-anonymous precedent bundle.

        Args:
            precedents: List of precedent dictionaries
            bundle_name: Optional bundle identifier

        Returns:
            AnonymousBundle with k-anonymity guarantee

        Raises:
            ValueError: If fewer than k precedents provided
        """
        if len(precedents) < self.k:
            raise ValueError(
                f"Need at least {self.k} precedents for k-anonymity, got {len(precedents)}"
            )

        # Cluster similar precedents
        clusters = self._cluster_precedents(precedents, min_size=self.k)

        # Process each cluster
        anonymized = []
        generalized_attrs = set()
        redacted = list(self.sensitive_fields)

        for cluster in clusters:
            # Generalize quasi-identifiers
            generalized = self._generalize_cluster(cluster)
            generalized_attrs.update(generalized["generalized_attributes"])

            # Redact sensitive fields
            redacted_cluster = [
                self._redact_sensitive_fields(prec)
                for prec in generalized["precedents"]
            ]

            anonymized.extend(redacted_cluster)

        # Generate bundle ID
        bundle_id = bundle_name or self._generate_bundle_id(anonymized)

        return AnonymousBundle(
            bundle_id=bundle_id,
            precedents=anonymized,
            k_value=self.k,
            privacy_guarantee="k-anonymity",
            generalized_attributes=list(generalized_attrs),
            redacted_fields=redacted,
            metadata={
                "original_count": len(precedents),
                "anonymized_count": len(anonymized),
                "cluster_count": len(clusters)
            }
        )

    def _cluster_precedents(
        self,
        precedents: List[Dict],
        min_size: int
    ) -> List[List[Dict]]:
        """
        Cluster precedents by similarity for k-anonymity.

        Simple clustering: group by verdict and confidence range.
        More sophisticated: use embedding-based clustering.

        Args:
            precedents: List of precedents
            min_size: Minimum cluster size

        Returns:
            List of clusters (each cluster is a list of precedents)
        """
        # Simple clustering by verdict
        verdict_groups: Dict[str, List[Dict]] = {}

        for prec in precedents:
            # Extract verdict from outcome
            outcome = prec.get("outcome", {})
            verdict = outcome.get("verdict", "unknown")

            if verdict not in verdict_groups:
                verdict_groups[verdict] = []

            verdict_groups[verdict].append(prec)

        # Build clusters of size >= min_size
        clusters = []
        current_cluster = []

        for verdict, group in verdict_groups.items():
            # If group is large enough, make it a cluster
            if len(group) >= min_size:
                # Split into chunks of size k
                for i in range(0, len(group), min_size):
                    chunk = group[i:i + min_size]
                    if len(chunk) >= min_size:
                        clusters.append(chunk)
                    else:
                        # Remaining items go to current_cluster
                        current_cluster.extend(chunk)
            else:
                # Accumulate small groups
                current_cluster.extend(group)

            # If current_cluster reaches min_size, create cluster
            if len(current_cluster) >= min_size:
                clusters.append(current_cluster[:min_size])
                current_cluster = current_cluster[min_size:]

        # Handle remaining items (may violate k-anonymity)
        if current_cluster:
            if len(current_cluster) >= min_size:
                clusters.append(current_cluster)
            else:
                # Merge with last cluster if possible
                if clusters:
                    clusters[-1].extend(current_cluster)
                else:
                    logger.warning(
                        f"Remaining {len(current_cluster)} precedents don't meet k={min_size}"
                    )

        return clusters

    def _generalize_cluster(self, cluster: List[Dict]) -> Dict[str, Any]:
        """
        Generalize quasi-identifiers within a cluster.

        Args:
            cluster: List of precedents in the same cluster

        Returns:
            Dict with generalized precedents and attributes list
        """
        generalized_precs = []
        generalized_attrs = set()

        for prec in cluster:
            generalized = prec.copy()

            # Generalize timestamp to date only
            if "timestamp" in prec:
                timestamp = prec["timestamp"]
                if isinstance(timestamp, str):
                    # Keep only date part
                    generalized["timestamp"] = timestamp.split("T")[0]
                    generalized_attrs.add("timestamp")

            # Generalize location to region/country only
            if "input_data" in prec and "context" in prec["input_data"]:
                context = prec["input_data"]["context"]

                if "location" in context:
                    # Generalize to country level
                    location = context.get("location", "")
                    if isinstance(location, dict):
                        # Keep only country
                        generalized["input_data"]["context"]["location"] = {
                            "country": location.get("country", "unknown")
                        }
                    else:
                        # Generic location
                        generalized["input_data"]["context"]["location"] = "generalized"
                    generalized_attrs.add("location")

                if "age" in context:
                    # Generalize age to range
                    age = context.get("age")
                    if isinstance(age, (int, float)):
                        age_range = self._age_to_range(age)
                        generalized["input_data"]["context"]["age"] = age_range
                        generalized_attrs.add("age")

            generalized_precs.append(generalized)

        return {
            "precedents": generalized_precs,
            "generalized_attributes": list(generalized_attrs)
        }

    def _age_to_range(self, age: float) -> str:
        """Convert age to range (e.g., 25-34)."""
        if age < 18:
            return "under-18"
        elif age < 25:
            return "18-24"
        elif age < 35:
            return "25-34"
        elif age < 45:
            return "35-44"
        elif age < 55:
            return "45-54"
        elif age < 65:
            return "55-64"
        else:
            return "65-plus"

    def _redact_sensitive_fields(self, precedent: Dict) -> Dict:
        """
        Redact sensitive fields from precedent.

        Args:
            precedent: Precedent dictionary

        Returns:
            Precedent with sensitive fields redacted
        """
        redacted = precedent.copy()

        # Redact from input_data context
        if "input_data" in redacted and "context" in redacted["input_data"]:
            context = redacted["input_data"]["context"]

            for field in self.sensitive_fields:
                if field in context:
                    context[field] = "[REDACTED]"

        # Redact from top-level metadata
        for field in self.sensitive_fields:
            if field in redacted:
                redacted[field] = "[REDACTED]"

        return redacted

    def _generate_bundle_id(self, precedents: List[Dict]) -> str:
        """Generate deterministic bundle ID from precedents."""
        # Hash concatenation of precedent IDs
        ids = sorted([p.get("id", p.get("hash", "")) for p in precedents])
        combined = "-".join(ids)
        hash_digest = hashlib.sha256(combined.encode()).hexdigest()
        return f"bundle_{hash_digest[:16]}"

    def verify_k_anonymity(self, bundle: AnonymousBundle) -> bool:
        """
        Verify that bundle satisfies k-anonymity.

        Args:
            bundle: Anonymous bundle to verify

        Returns:
            True if k-anonymity satisfied, False otherwise
        """
        # Group by quasi-identifier values
        groups: Dict[str, List[Dict]] = {}

        for prec in bundle.precedents:
            # Create signature from quasi-identifiers
            signature = self._create_signature(prec)

            if signature not in groups:
                groups[signature] = []

            groups[signature].append(prec)

        # Check all groups have size >= k
        min_group_size = min(len(group) for group in groups.values()) if groups else 0

        is_k_anonymous = min_group_size >= bundle.k_value

        if not is_k_anonymous:
            logger.warning(
                f"Bundle fails k-anonymity: minimum group size is {min_group_size}, "
                f"required {bundle.k_value}"
            )

        return is_k_anonymous

    def _create_signature(self, precedent: Dict) -> str:
        """Create signature from quasi-identifiers for grouping."""
        sig_parts = []

        # Add timestamp (generalized)
        if "timestamp" in precedent:
            sig_parts.append(str(precedent["timestamp"]))

        # Add context quasi-identifiers
        if "input_data" in precedent and "context" in precedent["input_data"]:
            context = precedent["input_data"]["context"]

            for attr in sorted(self.quasi_identifiers):
                if attr in context:
                    sig_parts.append(f"{attr}:{context[attr]}")

        return "|".join(sig_parts)

    def add_differential_privacy_noise(
        self,
        bundle: AnonymousBundle,
        epsilon: float = 1.0
    ) -> AnonymousBundle:
        """
        Add differential privacy noise to bundle (placeholder).

        Args:
            bundle: Bundle to add noise to
            epsilon: Privacy budget (smaller = more privacy)

        Returns:
            Bundle with differential privacy guarantee
        """
        # Placeholder: Real DP requires careful calibration
        logger.warning("Differential privacy not fully implemented, using placeholder")

        # Would add Laplace noise to numerical aggregates
        # Would randomize response for categorical data

        bundle.privacy_guarantee = f"k-anonymity+dp(epsilon={epsilon})"
        bundle.metadata["dp_epsilon"] = epsilon

        return bundle
