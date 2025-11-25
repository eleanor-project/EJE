from statistics import mean, variance
from typing import Dict, List, Any

class Aggregator:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.block_threshold: float = config.get('block_threshold', 0.5)
        self.ambiguity_threshold: float = config.get('ambiguity_threshold', 0.25)
        self.critic_priorities: Dict[str, Any] = config.get('critic_priorities', {})

    def aggregate(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        verdict_scores = {'ALLOW': 0, 'BLOCK': 0, 'REVIEW': 0}
        confidences = []
        overall, reason = None, ""
        for r in results:
            score = r['confidence'] * r['weight']
            verdict_scores[r['verdict']] += score
            confidences.append(r['confidence'])
            if r.get('priority') == "override" and r['verdict'] != "ALLOW":
                overall = r['verdict']
                reason = f"Override by {r['critic']}"
        if not overall:
            top = max(verdict_scores, key=verdict_scores.get)
            ambiguity = variance(confidences) if len(confidences) > 1 else 0
            overall = top
            if ambiguity > self.ambiguity_threshold or len(set([r['verdict'] for r in results])) > 1:
                overall = 'REVIEW'
            if verdict_scores['BLOCK'] >= self.block_threshold:
                overall = 'BLOCK'
            reason = "Weighted aggregation"
        return {
            'overall_verdict': overall,
            'reason': reason,
            'details': results,
            'verdict_scores': verdict_scores,
            'avg_confidence': mean(confidences),
            'ambiguity': ambiguity if 'ambiguity' in locals() else 0
        }
