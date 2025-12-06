"""
Counterfactual Explanation Generator for EJE Decisions

Generates "what-if" scenarios showing minimal changes needed for different outcomes.
Implements Issue #167: Counterfactual Explanation Generator

References:
- Wachter et al. (2017): "Counterfactual Explanations without Opening the Black Box"
- Mothilal et al. (2020): "Explaining Machine Learning Classifiers through Diverse Counterfactual Explanations"
"""

from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
import copy
import time


class CounterfactualMode(Enum):
    """Modes for counterfactual generation."""
    NEAREST = "nearest"        # Find closest alternative with different verdict
    DIVERSE = "diverse"        # Generate diverse set of alternatives
    MINIMAL = "minimal"        # Minimal feature changes
    PLAUSIBLE = "plausible"    # Most realistic alternatives


@dataclass
class Counterfactual:
    """A single counterfactual explanation."""
    original_verdict: str
    counterfactual_verdict: str
    original_confidence: float
    counterfactual_confidence: float
    changed_factors: Dict[str, Any]
    change_magnitude: float
    plausibility_score: float
    explanation: str
    critic_impacts: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class CounterfactualGenerator:
    """
    Generates counterfactual explanations for EJE decisions.

    Answers questions like:
    - "What would need to change for this to be APPROVED?"
    - "What's the minimal change to get a different outcome?"
    - "What are plausible alternative scenarios?"
    """

    def __init__(
        self,
        max_counterfactuals: int = 5,
        max_changes: int = 3,
        timeout_seconds: float = 2.0
    ):
        """
        Initialize CounterfactualGenerator.

        Args:
            max_counterfactuals: Maximum number of counterfactuals to generate
            max_changes: Maximum number of factors to change per counterfactual
            timeout_seconds: Maximum time to spend generating counterfactuals
        """
        self.max_counterfactuals = max_counterfactuals
        self.max_changes = max_changes
        self.timeout_seconds = timeout_seconds

    def generate(
        self,
        decision: Dict[str, Any],
        mode: CounterfactualMode = CounterfactualMode.NEAREST,
        target_verdict: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate counterfactual explanations for a decision.

        Args:
            decision: EJE Decision object (as dict)
            mode: Counterfactual generation mode
            target_verdict: Specific verdict to target (if None, any different verdict)
            **kwargs: Additional parameters

        Returns:
            Dictionary containing:
                - counterfactuals: List of Counterfactual objects
                - generation_time: Time taken to generate
                - mode: Mode used
                - key_factors: Most influential factors identified
        """
        start_time = time.time()

        # Extract key information from decision
        original_verdict = self._extract_verdict(decision)
        original_confidence = self._extract_confidence(decision)
        key_factors = self._identify_key_factors(decision)

        # Generate counterfactuals based on mode
        if mode == CounterfactualMode.NEAREST:
            counterfactuals = self._generate_nearest(
                decision, original_verdict, target_verdict, key_factors
            )
        elif mode == CounterfactualMode.DIVERSE:
            counterfactuals = self._generate_diverse(
                decision, original_verdict, target_verdict, key_factors
            )
        elif mode == CounterfactualMode.MINIMAL:
            counterfactuals = self._generate_minimal(
                decision, original_verdict, target_verdict, key_factors
            )
        elif mode == CounterfactualMode.PLAUSIBLE:
            counterfactuals = self._generate_plausible(
                decision, original_verdict, target_verdict, key_factors
            )
        else:
            counterfactuals = []

        generation_time = time.time() - start_time

        # Ensure we didn't exceed timeout
        if generation_time > self.timeout_seconds:
            counterfactuals = counterfactuals[:max(1, len(counterfactuals) // 2)]

        return {
            'counterfactuals': [self._counterfactual_to_dict(cf) for cf in counterfactuals],
            'generation_time': generation_time,
            'mode': mode.value,
            'key_factors': key_factors,
            'original_verdict': original_verdict,
            'original_confidence': original_confidence,
            'within_timeout': generation_time <= self.timeout_seconds
        }

    def _extract_verdict(self, decision: Dict[str, Any]) -> str:
        """Extract the verdict from decision."""
        # Try governance_outcome first, then aggregation
        if 'governance_outcome' in decision and decision['governance_outcome']:
            return decision['governance_outcome'].get('verdict', 'UNKNOWN')
        elif 'aggregation' in decision and decision['aggregation']:
            return decision['aggregation'].get('verdict', 'UNKNOWN')
        return 'UNKNOWN'

    def _extract_confidence(self, decision: Dict[str, Any]) -> float:
        """Extract confidence from decision."""
        if 'governance_outcome' in decision and decision['governance_outcome']:
            return decision['governance_outcome'].get('confidence', 0.5)
        elif 'aggregation' in decision and decision['aggregation']:
            return decision['aggregation'].get('confidence', 0.5)
        return 0.5

    def _identify_key_factors(self, decision: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify key factors that influenced the decision.

        Returns:
            List of factors with their importance scores
        """
        factors = []

        # Extract from critic reports
        critic_reports = decision.get('critic_reports', [])
        for report in critic_reports:
            critic_name = report.get('critic_name', 'unknown')
            verdict = report.get('verdict', 'UNKNOWN')
            confidence = report.get('confidence', 0.5)
            justification = report.get('justification', '')

            # Calculate importance based on confidence and agreement
            importance = confidence
            if verdict == self._extract_verdict(decision):
                importance *= 1.2  # Boost factors that agree with final verdict

            factors.append({
                'critic': critic_name,
                'verdict': verdict,
                'confidence': confidence,
                'importance': min(1.0, importance),
                'justification': justification,
                'type': 'critic_verdict'
            })

        # Extract from input data (domain-specific factors)
        input_data = decision.get('input_data', {})
        for key, value in input_data.items():
            # Skip non-meaningful fields
            if key in ['id', 'timestamp', 'metadata']:
                continue

            factors.append({
                'name': key,
                'value': value,
                'type': 'input_feature',
                'importance': 0.5  # Default importance
            })

        # Sort by importance
        factors.sort(key=lambda x: x.get('importance', 0), reverse=True)

        return factors[:10]  # Return top 10 factors

    def _generate_nearest(
        self,
        decision: Dict[str, Any],
        original_verdict: str,
        target_verdict: Optional[str],
        key_factors: List[Dict[str, Any]]
    ) -> List[Counterfactual]:
        """Generate nearest counterfactual (minimal changes)."""
        counterfactuals = []

        # Try changing each critic's verdict one at a time
        for factor in key_factors[:self.max_changes]:
            if factor['type'] == 'critic_verdict':
                cf = self._create_critic_change_counterfactual(
                    decision, factor, original_verdict, target_verdict
                )
                if cf:
                    counterfactuals.append(cf)
                    if len(counterfactuals) >= self.max_counterfactuals:
                        break

        return counterfactuals

    def _generate_diverse(
        self,
        decision: Dict[str, Any],
        original_verdict: str,
        target_verdict: Optional[str],
        key_factors: List[Dict[str, Any]]
    ) -> List[Counterfactual]:
        """Generate diverse set of counterfactuals."""
        counterfactuals = []

        # Strategy 1: Change most important critic
        if key_factors:
            cf1 = self._create_critic_change_counterfactual(
                decision, key_factors[0], original_verdict, target_verdict
            )
            if cf1:
                counterfactuals.append(cf1)

        # Strategy 2: Change least confident critic
        low_confidence_factors = [f for f in key_factors
                                   if f['type'] == 'critic_verdict'
                                   and f['confidence'] < 0.7]
        if low_confidence_factors:
            cf2 = self._create_critic_change_counterfactual(
                decision, low_confidence_factors[0], original_verdict, target_verdict
            )
            if cf2 and cf2 not in counterfactuals:
                counterfactuals.append(cf2)

        # Strategy 3: Change multiple critics simultaneously
        if len(key_factors) >= 2:
            cf3 = self._create_multi_critic_counterfactual(
                decision, key_factors[:2], original_verdict, target_verdict
            )
            if cf3:
                counterfactuals.append(cf3)

        return counterfactuals[:self.max_counterfactuals]

    def _generate_minimal(
        self,
        decision: Dict[str, Any],
        original_verdict: str,
        target_verdict: Optional[str],
        key_factors: List[Dict[str, Any]]
    ) -> List[Counterfactual]:
        """Generate counterfactuals with minimal changes."""
        # Find the single most impactful change
        counterfactuals = []

        for factor in key_factors:
            if factor['type'] == 'critic_verdict':
                cf = self._create_critic_change_counterfactual(
                    decision, factor, original_verdict, target_verdict,
                    minimal=True
                )
                if cf:
                    counterfactuals.append(cf)
                    break  # Only return the first minimal change

        return counterfactuals

    def _generate_plausible(
        self,
        decision: Dict[str, Any],
        original_verdict: str,
        target_verdict: Optional[str],
        key_factors: List[Dict[str, Any]]
    ) -> List[Counterfactual]:
        """Generate most plausible counterfactuals."""
        counterfactuals = []

        # Focus on low-confidence critics (easiest to flip)
        plausible_factors = [
            f for f in key_factors
            if f['type'] == 'critic_verdict' and f['confidence'] < 0.8
        ]

        for factor in plausible_factors[:self.max_counterfactuals]:
            cf = self._create_critic_change_counterfactual(
                decision, factor, original_verdict, target_verdict,
                plausibility_weight=1.5
            )
            if cf:
                counterfactuals.append(cf)

        # Sort by plausibility
        counterfactuals.sort(key=lambda x: x.plausibility_score, reverse=True)

        return counterfactuals[:self.max_counterfactuals]

    def _create_critic_change_counterfactual(
        self,
        decision: Dict[str, Any],
        factor: Dict[str, Any],
        original_verdict: str,
        target_verdict: Optional[str],
        minimal: bool = False,
        plausibility_weight: float = 1.0
    ) -> Optional[Counterfactual]:
        """Create a counterfactual by changing a critic's verdict."""
        critic_name = factor.get('critic', 'unknown')
        current_verdict = factor.get('verdict', 'UNKNOWN')
        current_confidence = factor.get('confidence', 0.5)

        # Determine new verdict
        if target_verdict:
            new_verdict = target_verdict
        else:
            # Flip to opposite
            if current_verdict == 'APPROVE':
                new_verdict = 'DENY'
            elif current_verdict == 'DENY':
                new_verdict = 'APPROVE'
            else:
                new_verdict = 'REVIEW'

        # Calculate impact of this change
        # Simulate what the aggregated verdict would be
        simulated_verdict = self._simulate_verdict_change(
            decision, critic_name, new_verdict
        )

        # Only create counterfactual if it actually changes the outcome
        if simulated_verdict == original_verdict:
            return None

        # Calculate change magnitude
        confidence_change = abs(current_confidence - 0.5)  # How much confidence needs to flip
        change_magnitude = confidence_change

        # Calculate plausibility (easier to flip low-confidence critics)
        plausibility_score = (1.0 - current_confidence) * plausibility_weight

        # Create explanation
        explanation = self._create_explanation(
            critic_name, current_verdict, new_verdict,
            simulated_verdict, factor.get('justification', '')
        )

        return Counterfactual(
            original_verdict=original_verdict,
            counterfactual_verdict=simulated_verdict,
            original_confidence=factor.get('confidence', 0.5),
            counterfactual_confidence=0.5,  # Simulated
            changed_factors={
                critic_name: {
                    'original': current_verdict,
                    'counterfactual': new_verdict,
                    'confidence_change': confidence_change
                }
            },
            change_magnitude=change_magnitude,
            plausibility_score=plausibility_score,
            explanation=explanation,
            critic_impacts={critic_name: factor}
        )

    def _create_multi_critic_counterfactual(
        self,
        decision: Dict[str, Any],
        factors: List[Dict[str, Any]],
        original_verdict: str,
        target_verdict: Optional[str]
    ) -> Optional[Counterfactual]:
        """Create counterfactual by changing multiple critics."""
        changed_factors = {}
        total_change = 0.0

        for factor in factors:
            if factor['type'] != 'critic_verdict':
                continue

            critic_name = factor.get('critic', 'unknown')
            current_verdict = factor.get('verdict', 'UNKNOWN')

            # Determine new verdict
            if current_verdict == 'APPROVE':
                new_verdict = 'DENY'
            elif current_verdict == 'DENY':
                new_verdict = 'APPROVE'
            else:
                new_verdict = 'REVIEW'

            changed_factors[critic_name] = {
                'original': current_verdict,
                'counterfactual': new_verdict,
                'confidence_change': factor.get('confidence', 0.5)
            }
            total_change += factor.get('confidence', 0.5)

        # Simulate outcome with all changes
        simulated_verdict = self._simulate_multi_critic_change(
            decision, changed_factors
        )

        if simulated_verdict == original_verdict:
            return None

        explanation = f"If {len(changed_factors)} critics changed their verdicts, the final decision would be {simulated_verdict}"

        return Counterfactual(
            original_verdict=original_verdict,
            counterfactual_verdict=simulated_verdict,
            original_confidence=self._extract_confidence(decision),
            counterfactual_confidence=0.5,
            changed_factors=changed_factors,
            change_magnitude=total_change / len(changed_factors),
            plausibility_score=0.3,  # Lower plausibility for multi-critic changes
            explanation=explanation
        )

    def _simulate_verdict_change(
        self,
        decision: Dict[str, Any],
        critic_name: str,
        new_verdict: str
    ) -> str:
        """
        Simulate what the final verdict would be if one critic changed.

        Simple aggregation: majority vote with confidence weighting.
        """
        critic_reports = decision.get('critic_reports', [])

        # Count weighted verdicts
        verdict_weights = {'APPROVE': 0.0, 'DENY': 0.0, 'REVIEW': 0.0}

        for report in critic_reports:
            name = report.get('critic_name', '')
            verdict = report.get('verdict', 'UNKNOWN')
            confidence = report.get('confidence', 0.5)

            # Use new verdict for the changed critic
            if name == critic_name:
                verdict = new_verdict

            if verdict in verdict_weights:
                verdict_weights[verdict] += confidence

        # Return verdict with highest weight
        return max(verdict_weights.items(), key=lambda x: x[1])[0]

    def _simulate_multi_critic_change(
        self,
        decision: Dict[str, Any],
        changes: Dict[str, Dict[str, Any]]
    ) -> str:
        """Simulate verdict change for multiple critics."""
        critic_reports = decision.get('critic_reports', [])

        verdict_weights = {'APPROVE': 0.0, 'DENY': 0.0, 'REVIEW': 0.0}

        for report in critic_reports:
            name = report.get('critic_name', '')
            verdict = report.get('verdict', 'UNKNOWN')
            confidence = report.get('confidence', 0.5)

            # Use new verdict if this critic is in changes
            if name in changes:
                verdict = changes[name]['counterfactual']

            if verdict in verdict_weights:
                verdict_weights[verdict] += confidence

        return max(verdict_weights.items(), key=lambda x: x[1])[0]

    def _create_explanation(
        self,
        critic_name: str,
        original_verdict: str,
        new_verdict: str,
        final_verdict: str,
        justification: str
    ) -> str:
        """Create human-readable explanation for counterfactual."""
        explanation = f"If the {critic_name} critic changed its verdict from {original_verdict} to {new_verdict}, "
        explanation += f"the final decision would be {final_verdict}. "

        if justification:
            # Extract key reason from justification (first sentence)
            key_reason = justification.split('.')[0]
            explanation += f"This critic currently believes: '{key_reason}...'"

        return explanation

    def _counterfactual_to_dict(self, cf: Counterfactual) -> Dict[str, Any]:
        """Convert Counterfactual object to dictionary."""
        return {
            'original_verdict': cf.original_verdict,
            'counterfactual_verdict': cf.counterfactual_verdict,
            'original_confidence': cf.original_confidence,
            'counterfactual_confidence': cf.counterfactual_confidence,
            'changed_factors': cf.changed_factors,
            'change_magnitude': cf.change_magnitude,
            'plausibility_score': cf.plausibility_score,
            'explanation': cf.explanation,
            'critic_impacts': cf.critic_impacts
        }

    def validate_counterfactual(
        self,
        counterfactual: Dict[str, Any],
        decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate a counterfactual against the system.

        Args:
            counterfactual: Generated counterfactual
            decision: Original decision

        Returns:
            Validation results with coherence score
        """
        validation = {
            'is_valid': True,
            'coherence_score': 0.0,
            'issues': []
        }

        # Check if changed factors exist in decision
        changed_factors = counterfactual.get('changed_factors', {})
        critic_reports = decision.get('critic_reports', [])
        critic_names = {r.get('critic_name', '') for r in critic_reports}

        for critic in changed_factors.keys():
            if critic not in critic_names:
                validation['is_valid'] = False
                validation['issues'].append(f"Critic '{critic}' not found in decision")

        # Check plausibility
        plausibility = counterfactual.get('plausibility_score', 0.5)
        if plausibility < 0.2:
            validation['issues'].append("Low plausibility score")

        # Calculate coherence score
        coherence_score = plausibility * 0.6
        if validation['is_valid']:
            coherence_score += 0.4

        validation['coherence_score'] = coherence_score

        return validation


class CounterfactualTemplatePlaceholder:
    """
    Simple template-based counterfactual explanation generator.

    Task 5.3: Counterfactual Placeholder
    Provides basic template generation without model-based reasoning.
    Generates simple "Decision would change if X differed" explanations.

    This is a lightweight alternative to CounterfactualGenerator for cases
    where full counterfactual analysis is not needed or too expensive.
    """

    # Predefined templates for different scenarios
    TEMPLATES = {
        'critic_flip': "The decision would change from {original} to {target} if the {critic} critic's verdict changed from {from_verdict} to {to_verdict}.",
        'confidence_change': "If the overall confidence {direction} from {original_conf:.0%} to {target_conf:.0%}, the decision might change to {target}.",
        'factor_change': "Decision would change to {target} if {factor} changed from {from_value} to {to_value}.",
        'threshold': "If the decision threshold were {direction}, this case would be {target} instead of {original}.",
        'consensus': "With {consensus_level} consensus among critics, the decision would be {target} instead of {original}.",
        'generic': "The decision would change from {original} to {target} if key factors differed."
    }

    def __init__(self):
        """Initialize template placeholder."""
        pass

    def generate_simple_counterfactual(
        self,
        original_verdict: str,
        target_verdict: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a simple template-based counterfactual explanation.

        Args:
            original_verdict: The current verdict
            target_verdict: Desired alternative verdict (if None, uses generic)
            context: Optional context dict with:
                - critic: Critic name for critic_flip template
                - from_verdict: Original critic verdict
                - to_verdict: Target critic verdict
                - factor: Factor name for factor_change template
                - from_value: Original factor value
                - to_value: Target factor value
                - original_conf: Original confidence
                - target_conf: Target confidence
                - direction: "higher" or "lower"
                - consensus_level: Consensus level description

        Returns:
            Template-based counterfactual explanation string
        """
        context = context or {}

        # If no target verdict, use generic template
        if not target_verdict:
            target_verdict = "a different outcome"
            return self.TEMPLATES['generic'].format(
                original=original_verdict,
                target=target_verdict
            )

        # Select template based on available context
        if 'critic' in context and 'from_verdict' in context:
            template = self.TEMPLATES['critic_flip']
            return template.format(
                original=original_verdict,
                target=target_verdict,
                critic=context['critic'],
                from_verdict=context['from_verdict'],
                to_verdict=context.get('to_verdict', 'a different verdict')
            )

        elif 'original_conf' in context and 'target_conf' in context:
            template = self.TEMPLATES['confidence_change']
            direction = context.get('direction', 'increased' if context['target_conf'] > context['original_conf'] else 'decreased')
            return template.format(
                original=original_verdict,
                target=target_verdict,
                direction=direction,
                original_conf=context['original_conf'],
                target_conf=context['target_conf']
            )

        elif 'factor' in context and 'from_value' in context:
            template = self.TEMPLATES['factor_change']
            return template.format(
                original=original_verdict,
                target=target_verdict,
                factor=context['factor'],
                from_value=context['from_value'],
                to_value=context.get('to_value', 'a different value')
            )

        elif 'direction' in context:
            template = self.TEMPLATES['threshold']
            return template.format(
                original=original_verdict,
                target=target_verdict,
                direction=context['direction']
            )

        elif 'consensus_level' in context:
            template = self.TEMPLATES['consensus']
            return template.format(
                original=original_verdict,
                target=target_verdict,
                consensus_level=context['consensus_level']
            )

        else:
            # Generic fallback
            template = self.TEMPLATES['generic']
            return template.format(
                original=original_verdict,
                target=target_verdict
            )

    def generate_multiple_counterfactuals(
        self,
        original_verdict: str,
        possible_verdicts: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Generate multiple counterfactual explanations for different target verdicts.

        Args:
            original_verdict: Current verdict
            possible_verdicts: List of alternative verdicts
            context: Optional context for template generation

        Returns:
            List of counterfactual explanation strings
        """
        counterfactuals = []

        for target in possible_verdicts:
            if target != original_verdict:
                cf = self.generate_simple_counterfactual(
                    original_verdict,
                    target,
                    context
                )
                counterfactuals.append(cf)

        return counterfactuals

    def generate_from_decision(
        self,
        decision: Dict[str, Any],
        max_counterfactuals: int = 3
    ) -> List[str]:
        """
        Generate counterfactual explanations from a decision object.

        Args:
            decision: EJE Decision object (as dict)
            max_counterfactuals: Maximum number to generate

        Returns:
            List of counterfactual explanation strings
        """
        counterfactuals = []

        # Extract verdict
        original_verdict = self._extract_verdict(decision)

        # Get possible verdicts
        possible_verdicts = ['ALLOW', 'DENY', 'ESCALATE', 'REVIEW']

        # Get critic information
        critic_reports = decision.get('critic_reports', [])

        # Generate counterfactuals based on critics
        for report in critic_reports[:max_counterfactuals]:
            critic_name = report.get('critic_name', 'unknown')
            critic_verdict = report.get('verdict', 'UNKNOWN')

            # Find what would happen if this critic changed
            if critic_verdict != original_verdict:
                # This critic disagrees - what if it agreed?
                context = {
                    'critic': critic_name,
                    'from_verdict': critic_verdict,
                    'to_verdict': original_verdict
                }
                cf = self.generate_simple_counterfactual(
                    original_verdict,
                    original_verdict,  # Would strengthen current verdict
                    context
                )
            else:
                # This critic agrees - what if it disagreed?
                target = next((v for v in possible_verdicts if v != original_verdict), 'DENY')
                context = {
                    'critic': critic_name,
                    'from_verdict': critic_verdict,
                    'to_verdict': target
                }
                cf = self.generate_simple_counterfactual(
                    original_verdict,
                    target,
                    context
                )

            counterfactuals.append(cf)

            if len(counterfactuals) >= max_counterfactuals:
                break

        # If no critic-based counterfactuals, add generic one
        if not counterfactuals:
            for target in possible_verdicts:
                if target != original_verdict:
                    cf = self.generate_simple_counterfactual(original_verdict, target)
                    counterfactuals.append(cf)
                    if len(counterfactuals) >= max_counterfactuals:
                        break

        return counterfactuals[:max_counterfactuals]

    def _extract_verdict(self, decision: Dict[str, Any]) -> str:
        """Extract the verdict from decision."""
        if 'governance_outcome' in decision and decision['governance_outcome']:
            return decision['governance_outcome'].get('verdict', 'UNKNOWN')
        elif 'aggregation' in decision and decision['aggregation']:
            return decision['aggregation'].get('verdict', 'UNKNOWN')
        return 'UNKNOWN'


# Export
__all__ = [
    'CounterfactualGenerator',
    'CounterfactualMode',
    'Counterfactual',
    'CounterfactualTemplatePlaceholder'
]
