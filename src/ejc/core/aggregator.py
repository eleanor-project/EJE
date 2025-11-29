from statistics import mean, variance
from typing import Dict, List, Any

class Aggregator:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.block_threshold: float = config.get('block_threshold', 0.5)
        self.ambiguity_threshold: float = config.get('ambiguity_threshold', 0.25)
        self.critic_priorities: Dict[str, Any] = config.get('critic_priorities', {})

    def aggregate(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not results:
            return {
                'overall_verdict': 'REVIEW',
                'reason': 'No critic results available',
                'details': [],
                'verdict_scores': {'ALLOW': 0, 'BLOCK': 0, 'REVIEW': 0},
                'avg_confidence': 0.0,
                'ambiguity': 0.0
            }

        verdict_scores = {'ALLOW': 0, 'BLOCK': 0, 'REVIEW': 0, 'DENY': 0}
        error_count = 0
        confidences = []
        overall, reason = None, ""
        for r in results:
            score = r['confidence'] * r['weight']
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
            }
        if not overall:
            top = max(verdict_scores, key=verdict_scores.get)
            ambiguity = variance(confidences) if len(confidences) > 1 else 0
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

            # High confidence block threshold overrides
            if verdict_scores['BLOCK'] >= self.block_threshold:
                overall = 'BLOCK'
                reason = "Block threshold exceeded"

            if reason == "":
                reason = "Weighted aggregation"
        return {
            'overall_verdict': overall,
            'reason': reason,
            'details': results,
            'verdict_scores': verdict_scores,
            'avg_confidence': mean(confidences),
            'ambiguity': ambiguity if 'ambiguity' in locals() else 0
        }
