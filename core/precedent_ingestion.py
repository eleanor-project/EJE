"""
Precedent Ingestion Pipeline

Task 3.2: Create Precedent Ingestion Pipeline

Automatically stores completed decisions into precedent storage for future retrieval.
Triggers after aggregator and policy stages, capturing evidence bundles and final decisions.
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass

from core.precedent_storage import PrecedentStorage
from core.critic_aggregator import AggregationResult

logger = logging.getLogger("ejc.core.precedent_ingestion")


@dataclass
class IngestionConfig:
    """Configuration for precedent ingestion."""

    enabled: bool = True  # Whether ingestion is enabled
    min_confidence: Optional[float] = None  # Only ingest if confidence >= threshold
    allowed_verdicts: Optional[List[str]] = None  # Only ingest these verdicts
    skip_escalations: bool = False  # Skip ESCALATE verdicts
    skip_abstentions: bool = True  # Skip ABSTAIN verdicts by default
    require_evidence: bool = True  # Require at least one evidence bundle


class PrecedentIngestionPipeline:
    """
    Pipeline for automatic precedent ingestion.

    Captures completed decisions and stores them as precedents for
    similarity-based retrieval. Integrates with aggregator output.
    """

    def __init__(
        self,
        storage: PrecedentStorage,
        config: Optional[IngestionConfig] = None
    ):
        """
        Initialize ingestion pipeline.

        Args:
            storage: Precedent storage backend
            config: Optional configuration
        """
        self.storage = storage
        self.config = config or IngestionConfig()
        self._ingestion_hooks: List[Callable] = []

    def ingest_decision(
        self,
        query: str,
        evidence_bundles: List[Dict[str, Any]],
        aggregation_result: AggregationResult,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Ingest a completed decision as a precedent.

        Args:
            query: The input query/prompt
            evidence_bundles: List of evidence bundles from critics
            aggregation_result: Final aggregation result
            additional_metadata: Optional additional metadata

        Returns:
            Precedent ID if stored, None if skipped

        Raises:
            ValueError: If ingestion requirements not met
        """
        # Check if ingestion is enabled
        if not self.config.enabled:
            logger.debug("Ingestion disabled, skipping")
            return None

        # Validate inputs
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if self.config.require_evidence and not evidence_bundles:
            logger.warning("No evidence bundles provided, skipping ingestion")
            return None

        # Apply filters
        if not self._should_ingest(aggregation_result):
            logger.debug(
                f"Skipping ingestion: {aggregation_result.final_verdict} "
                f"({aggregation_result.confidence:.2f})"
            )
            return None

        # Build composite evidence bundle
        composite_bundle = self._build_composite_bundle(
            evidence_bundles,
            aggregation_result
        )

        # Build metadata
        metadata = self._build_metadata(
            aggregation_result,
            additional_metadata
        )

        # Store precedent
        try:
            precedent_id = self.storage.store_precedent(
                query=query,
                evidence_bundle=composite_bundle,
                decision=aggregation_result.final_verdict,
                confidence=aggregation_result.confidence,
                metadata=metadata
            )

            logger.info(
                f"Ingested precedent {precedent_id}: "
                f"{aggregation_result.final_verdict} ({aggregation_result.confidence:.2f})"
            )

            # Trigger hooks
            self._trigger_hooks(precedent_id, query, aggregation_result)

            return precedent_id

        except Exception as e:
            logger.error(f"Failed to ingest precedent: {e}")
            raise

    def ingest_batch(
        self,
        decisions: List[Dict[str, Any]]
    ) -> List[Optional[str]]:
        """
        Ingest a batch of decisions.

        Args:
            decisions: List of decision dicts with keys:
                      'query', 'evidence_bundles', 'aggregation_result', 'metadata'

        Returns:
            List of precedent IDs (None for skipped)
        """
        precedent_ids = []

        for decision in decisions:
            try:
                precedent_id = self.ingest_decision(
                    query=decision["query"],
                    evidence_bundles=decision["evidence_bundles"],
                    aggregation_result=decision["aggregation_result"],
                    additional_metadata=decision.get("metadata")
                )
                precedent_ids.append(precedent_id)

            except Exception as e:
                logger.error(f"Failed to ingest decision: {e}")
                precedent_ids.append(None)

        logger.info(
            f"Batch ingestion: {sum(1 for x in precedent_ids if x)} / {len(decisions)} stored"
        )

        return precedent_ids

    def _should_ingest(self, result: AggregationResult) -> bool:
        """
        Check if decision should be ingested based on filters.

        Args:
            result: Aggregation result

        Returns:
            True if should ingest, False otherwise
        """
        # Check confidence threshold
        if self.config.min_confidence is not None:
            if result.confidence < self.config.min_confidence:
                return False

        # Check verdict filters
        verdict = result.final_verdict

        if self.config.skip_escalations and verdict == "ESCALATE":
            return False

        if self.config.skip_abstentions and verdict == "ABSTAIN":
            return False

        if self.config.allowed_verdicts:
            if verdict not in self.config.allowed_verdicts:
                return False

        return True

    def _build_composite_bundle(
        self,
        evidence_bundles: List[Dict[str, Any]],
        aggregation_result: AggregationResult
    ) -> Dict[str, Any]:
        """
        Build composite evidence bundle from individual bundles and aggregation.

        Args:
            evidence_bundles: Individual critic evidence bundles
            aggregation_result: Final aggregation result

        Returns:
            Composite bundle dict
        """
        # Take first bundle as template (if available)
        if evidence_bundles:
            base_bundle = evidence_bundles[0].copy()
        else:
            base_bundle = {
                "bundle_id": "composite-precedent",
                "version": "1.0",
                "input_snapshot": {"prompt": ""},
                "metadata": {}
            }

        # Build composite critic output
        composite_output = {
            "critic_name": "AggregatedCritics",
            "verdict": aggregation_result.final_verdict,
            "confidence": aggregation_result.confidence,
            "justification": self._synthesize_justification(
                evidence_bundles,
                aggregation_result
            ),
            "aggregation_metadata": {
                "contributing_critics": aggregation_result.contributing_critics,
                "weighted_scores": aggregation_result.weighted_scores,
                "total_weight": aggregation_result.total_weight,
                "conflicts_detected": len(aggregation_result.conflicts_detected),
                "individual_bundles": [
                    {
                        "critic": b.get("critic_output", {}).get("critic_name", "Unknown"),
                        "verdict": b.get("critic_output", {}).get("verdict", "UNKNOWN"),
                        "confidence": b.get("critic_output", {}).get("confidence", 0.0)
                    }
                    for b in evidence_bundles
                ]
            }
        }

        # Update bundle
        base_bundle["critic_output"] = composite_output

        return base_bundle

    def _synthesize_justification(
        self,
        evidence_bundles: List[Dict[str, Any]],
        aggregation_result: AggregationResult
    ) -> str:
        """
        Synthesize justification from multiple critics.

        Args:
            evidence_bundles: Evidence bundles
            aggregation_result: Aggregation result

        Returns:
            Synthesized justification string
        """
        parts = [
            f"Final decision: {aggregation_result.final_verdict} "
            f"(confidence: {aggregation_result.confidence:.2f})"
        ]

        # Add critic breakdown
        if evidence_bundles:
            critic_summaries = []
            for bundle in evidence_bundles:
                critic_output = bundle.get("critic_output", {})
                critic_name = critic_output.get("critic_name", "Unknown")
                verdict = critic_output.get("verdict", "UNKNOWN")
                confidence = critic_output.get("confidence", 0.0)

                critic_summaries.append(
                    f"{critic_name}: {verdict} ({confidence:.2f})"
                )

            parts.append(f"Critics: {', '.join(critic_summaries)}")

        # Add conflict info
        if aggregation_result.conflicts_detected:
            parts.append(
                f"Conflicts detected: {len(aggregation_result.conflicts_detected)}"
            )

        return ". ".join(parts) + "."

    def _build_metadata(
        self,
        aggregation_result: AggregationResult,
        additional_metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build metadata dict for precedent.

        Args:
            aggregation_result: Aggregation result
            additional_metadata: Optional additional metadata

        Returns:
            Metadata dict
        """
        metadata = {
            "ingestion_source": "aggregator",
            "num_critics": len(aggregation_result.contributing_critics),
            "critics": aggregation_result.contributing_critics,
            "weighted_scores": aggregation_result.weighted_scores,
            "total_weight": aggregation_result.total_weight,
            "had_conflicts": len(aggregation_result.conflicts_detected) > 0
        }

        # Merge additional metadata
        if additional_metadata:
            metadata.update(additional_metadata)

        return metadata

    def add_ingestion_hook(self, hook: Callable):
        """
        Add a hook to be called after successful ingestion.

        Hook signature: hook(precedent_id, query, aggregation_result)

        Args:
            hook: Callback function
        """
        self._ingestion_hooks.append(hook)
        logger.debug(f"Added ingestion hook: {hook.__name__}")

    def _trigger_hooks(
        self,
        precedent_id: str,
        query: str,
        aggregation_result: AggregationResult
    ):
        """Trigger all registered hooks."""
        for hook in self._ingestion_hooks:
            try:
                hook(precedent_id, query, aggregation_result)
            except Exception as e:
                logger.error(f"Hook {hook.__name__} failed: {e}")

    def get_ingestion_stats(self) -> Dict[str, Any]:
        """
        Get ingestion statistics.

        Returns:
            Stats dict from storage
        """
        return self.storage.get_statistics()


def create_ingestion_pipeline(
    storage: Optional[PrecedentStorage] = None,
    config: Optional[IngestionConfig] = None
) -> PrecedentIngestionPipeline:
    """
    Convenience function to create ingestion pipeline.

    Args:
        storage: Optional storage backend (creates default if None)
        config: Optional configuration

    Returns:
        PrecedentIngestionPipeline instance
    """
    if storage is None:
        storage = PrecedentStorage()

    return PrecedentIngestionPipeline(storage, config)
