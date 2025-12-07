from statistics import mean, variance
from typing import Any, Dict, List, Optional

class Aggregator:
    def __init__(self, config: Optional[Dict[str, Any]] = None, root_config: Optional[Dict[str, Any]] = None) -> None:
        config = config or {}
        root_config = root_config or {}

        self.block_threshold: float = config.get('block_threshold', root_config.get('block_threshold', 0.5))
        self.ambiguity_threshold: float = config.get('ambiguity_threshold', root_config.get('ambiguity_threshold', 0.25))
        self.critic_priorities: Dict[str, Any] = config.get('critic_priorities', root_config.get('critic_priorities', {}))
        raw_weights = config.get('critic_weights', root_config.get('critic_weights', {}))
        self.critic_weights: Dict[str, float] = {str(k).lower(): float(v) for k, v in raw_weights.items()} if raw_weights else {}
        self.moral_mode: str = config.get('moral_mode', root_config.get('moral_mode', 'balanced'))
        self.error_review_threshold: float = config.get(
            'error_review_threshold',
            root_config.get('error_review_threshold', 0.5),
        )

    def _resolve_weight(self, result: Dict[str, Any]) -> float:
        """Determine the effective weight for a critic result."""

        critic_name = str(result.get('critic', '')).lower()
        base_weight = result.get('weight', self.critic_weights.get(critic_name, 1.0))
        try:
            base_weight = float(base_weight)
        except (TypeError, ValueError):
            base_weight = 1.0
        mode_multiplier = self._moral_mode_multiplier(critic_name, result.get('confidence', 0.0))
        weight = base_weight * mode_multiplier
        result['applied_weight'] = weight
        return weight

    def _moral_mode_multiplier(self, critic_name: str, confidence: float) -> float:
        """Adjust weights according to the configured moral style."""

        mode = self.moral_mode.lower()

        if mode == 'utilitarian':
            if critic_name.startswith('fairness'):
                return 1.4
            if critic_name.startswith('safety'):
                return 0.8
        elif mode == 'deontological':
            if critic_name.startswith('rights') or critic_name.startswith('autonomy'):
                return 1.5
        elif mode == 'diplomatic':
            fallback = confidence if confidence > 0 else 0.01
            return min(3.0, 1 + (1 / fallback) * 0.2)

        return 1.0

    def aggregate(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not results:
            return {
                'overall_verdict': 'REVIEW',
                'reason': 'No critic results available',
                'details': [],
                'verdict_scores': {'ALLOW': 0, 'BLOCK': 0, 'REVIEW': 0},
                'avg_confidence': 0.0,
                'ambiguity': 0.0,
                'errors': {'count': 0, 'rate': 0.0},
            }

        verdict_scores = {'ALLOW': 0, 'BLOCK': 0, 'REVIEW': 0, 'DENY': 0}
        error_count = 0
        confidences = []
        overall, reason = None, ""
        conflict_escalation = False

        for r in results:
            weight = self._resolve_weight(r)
            score = r['confidence'] * weight
            verdict = r.get('verdict', 'REVIEW')

            if verdict == 'ERROR':
                error_count += 1
                continue

            if verdict == 'DENY':
                verdict_scores['DENY'] += score
                # Treat DENY as a strong BLOCK signal
                verdict_scores['BLOCK'] += score
            elif verdict in verdict_scores:
                verdict_scores[verdict] += score
            else:
                # Unknown verdicts are treated as neutral review signals
                verdict_scores['REVIEW'] += score
            confidences.append(r['confidence'])
            if r.get('priority') == "override" and r['verdict'] != "ALLOW":
                overall = r['verdict']
                reason = f"Override by {r['critic']}"

        if not confidences:
            return {
                'overall_verdict': 'ERROR',
                'reason': 'All critics failed',
                'details': results,
                'verdict_scores': verdict_scores,
                'avg_confidence': 0.0,
                'ambiguity': 0.0,
                'errors': {'count': error_count, 'rate': 1.0},
            }
        if not overall:
            top = max(verdict_scores, key=verdict_scores.get)
            ambiguity = variance(confidences) if len(confidences) > 1 else 0
            if len(confidences) > 1:
                ambiguity = max(ambiguity, max(confidences) - min(confidences))
            overall = top

            # Check for meaningful disagreement (not just any disagreement)
            # Only trigger REVIEW if disagreement is significant AND ambiguity is high
            non_zero_scores = [s for s in verdict_scores.values() if s > 0]
            if len(non_zero_scores) > 1:
                disagreement_ratio = min(non_zero_scores) / max(non_zero_scores)
                # If minority opinion is >30% of majority AND high ambiguity, escalate
                if disagreement_ratio > 0.3 and ambiguity > self.ambiguity_threshold:
                    overall = 'REVIEW'
                    reason = "Significant disagreement with high ambiguity"
                    conflict_escalation = True

            # High confidence block threshold overrides
            if verdict_scores['BLOCK'] >= self.block_threshold and not conflict_escalation:
                overall = 'BLOCK'
                reason = "Block threshold exceeded"

            if reason == "":
                reason = "Weighted aggregation"
        total = len(results)
        error_rate = error_count / total if total else 0.0
        if error_rate >= self.error_review_threshold and overall != 'ERROR':
            overall = 'REVIEW'
            if reason:
                reason = f"{reason}; high critic failure rate"
            else:
                reason = "High critic failure rate"
        return {
            'overall_verdict': overall,
            'reason': reason,
            'details': results,
            'verdict_scores': verdict_scores,
            'avg_confidence': mean(confidences),
            'ambiguity': ambiguity if 'ambiguity' in locals() else 0,
            'errors': {'count': error_count, 'rate': error_rate},
        }
