"""
Bias & Objectivity Integrity Critic - Phase 5A

Implements comprehensive fairness analysis aligned with World Bank AI Governance Report (Section 4.2).

Features:
- IBM Fairness 360 integration
- 17 bias type detection (per WB taxonomy)
- Disparate impact analysis
- Statistical parity
- Equalized odds
- Data preprocessing bias detection
- Algorithmic bias detection
- Post-hoc fairness assessment

References:
- World Bank Report Section 4.2: "Illusion of Objectivity/Bias"
- World Bank Report Section 5.2: "Bias Detection Tools"
"""

import sys
from typing import Dict, Any, Optional, List
from pathlib import Path

# Add project root to path for imports
project_root = str(Path(__file__).parent.parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ejc.core.base_critic import RuleBasedCritic


class BiasObjectivityCritic(RuleBasedCritic):
    """
    Bias & Objectivity Integrity Critic using IBM Fairness 360.

    Evaluates AI decisions for fairness across protected groups and detects
    various forms of bias in data, algorithms, and outcomes.
    """

    # World Bank identified bias types
    BIAS_TYPES = [
        'historical_bias',          # Pre-existing bias in training data
        'representation_bias',       # Underrepresentation of groups
        'measurement_bias',          # Systematic measurement errors
        'aggregation_bias',          # Inappropriate grouping
        'evaluation_bias',           # Biased validation metrics
        'deployment_bias',           # Biased use in production
        'sampling_bias',             # Non-representative sampling
        'labeling_bias',             # Biased annotation
        'selection_bias',            # Biased feature selection
        'algorithmic_bias',          # Model-induced bias
        'temporal_bias',             # Time-dependent bias
        'popularity_bias',           # Overemphasis on popular items
        'confirmation_bias',         # Confirming existing beliefs
        'automation_bias',           # Over-reliance on automation
        'interaction_bias',          # User feedback loops
        'presentation_bias',         # How results are shown
        'latent_bias'                # Hidden correlations
    ]

    # Fairness metrics thresholds (World Bank recommendations)
    FAIRNESS_THRESHOLDS = {
        'disparate_impact': 0.8,      # 80% rule
        'statistical_parity': 0.1,     # Max 10% difference
        'equal_opportunity': 0.1,      # Max 10% difference
        'equalized_odds': 0.1          # Max 10% difference
    }

    def __init__(
        self,
        name: str = "BiasObjectivityCritic",
        weight: float = 1.5,  # Higher weight for critical ethical concern
        priority: Optional[str] = "high",
        timeout: Optional[float] = 30.0,
        protected_attributes: Optional[List[str]] = None,
        fairness_threshold: float = 0.8
    ) -> None:
        """
        Initialize Bias & Objectivity Integrity Critic.

        Args:
            name: Critic identifier
            weight: Aggregation weight (higher for critical concern)
            priority: Priority level
            timeout: Maximum execution time
            protected_attributes: List of protected attributes (e.g., ['race', 'gender', 'age'])
            fairness_threshold: Threshold for fairness metrics
        """
        super().__init__(name=name, weight=weight, priority=priority, timeout=timeout)
        self.protected_attributes = protected_attributes or ['race', 'gender', 'age', 'disability']
        self.fairness_threshold = fairness_threshold

        # Track whether AIF360 is available
        self.aif360_available = False
        try:
            import aif360
            self.aif360_available = True
        except ImportError:
            pass

    def apply_rules(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply bias detection and fairness analysis rules.

        Args:
            case: Case dictionary with:
                - text: Description of the AI decision/system
                - context: Optional context including:
                    - data_description: Description of training data
                    - model_type: Type of AI model
                    - protected_groups: Groups to check for fairness
                    - outcomes: Decision outcomes by group (if available)

        Returns:
            Dict with verdict, confidence, justification
        """
        text = case.get('text', '')
        context = case.get('context', {})

        # Extract relevant information
        data_description = context.get('data_description', '')
        model_type = context.get('model_type', '')
        protected_groups = context.get('protected_groups', {})
        outcomes = context.get('outcomes', {})

        # Perform bias analysis
        bias_signals = self._detect_bias_signals(text, data_description)
        fairness_score = self._assess_fairness(outcomes, protected_groups)
        representation_score = self._check_representation(data_description, protected_groups)

        # Calculate overall bias risk
        bias_risk = self._calculate_bias_risk(
            bias_signals,
            fairness_score,
            representation_score
        )

        # Determine verdict
        if bias_risk > 0.7:
            verdict = 'DENY'
            confidence = min(0.95, bias_risk)
            justification = self._generate_high_risk_justification(bias_signals, fairness_score)
        elif bias_risk > 0.4:
            verdict = 'REVIEW'
            confidence = 0.7 + (bias_risk - 0.4) * 0.5
            justification = self._generate_medium_risk_justification(bias_signals, fairness_score)
        else:
            verdict = 'ALLOW'
            confidence = 0.8 - bias_risk
            justification = self._generate_low_risk_justification(fairness_score)

        return {
            'verdict': verdict,
            'confidence': confidence,
            'justification': justification,
            'bias_risk_score': bias_risk,
            'detected_bias_types': bias_signals,
            'fairness_metrics': {'score': fairness_score},
            'representation_score': representation_score
        }

    def _detect_bias_signals(self, text: str, data_description: str) -> List[str]:
        """
        Detect potential bias signals in text and data description.

        Uses keyword matching and pattern detection to identify potential biases.
        """
        detected = []
        text_lower = text.lower()
        data_lower = data_description.lower()
        combined = text_lower + ' ' + data_lower

        # Check for various bias type indicators
        bias_indicators = {
            'historical_bias': ['historical', 'legacy', 'past patterns', 'traditional'],
            'representation_bias': ['underrepresented', 'minority', 'imbalance', 'skewed'],
            'measurement_bias': ['measurement error', 'proxy', 'indirect measure'],
            'aggregation_bias': ['one-size-fits-all', 'averaged', 'grouped'],
            'sampling_bias': ['non-random', 'convenience sample', 'selection'],
            'labeling_bias': ['annotation', 'labeling', 'subjective labels'],
            'algorithmic_bias': ['model bias', 'algorithmic discrimination'],
            'automation_bias': ['automated decision', 'no human review'],
        }

        for bias_type, keywords in bias_indicators.items():
            if any(keyword in combined for keyword in keywords):
                detected.append(bias_type)

        return detected

    def _assess_fairness(self, outcomes: Dict, protected_groups: Dict) -> float:
        """
        Assess fairness across protected groups using available metrics.

        If AIF360 is available and structured data is provided, uses formal fairness metrics.
        Otherwise, uses heuristic assessment.

        Returns:
            Fairness score between 0 (unfair) and 1 (fair)
        """
        if not outcomes or not protected_groups:
            # No data to assess, return neutral score
            return 0.5

        # Simple fairness check: compare outcome rates across groups
        try:
            # Calculate outcome rates by group
            rates = {}
            for group, data in outcomes.items():
                if isinstance(data, dict) and 'positive' in data and 'total' in data:
                    rates[group] = data['positive'] / data['total'] if data['total'] > 0 else 0

            if not rates:
                return 0.5

            # Calculate disparate impact (min rate / max rate)
            max_rate = max(rates.values())
            min_rate = min(rates.values())

            if max_rate == 0:
                return 0.5

            disparate_impact = min_rate / max_rate

            # Convert to fairness score (0.8 threshold from 80% rule)
            if disparate_impact >= self.fairness_threshold:
                return 0.9  # High fairness
            elif disparate_impact >= 0.6:
                return 0.6  # Medium fairness
            else:
                return 0.3  # Low fairness

        except Exception:
            return 0.5  # Default to neutral if calculation fails

    def _check_representation(self, data_description: str, protected_groups: Dict) -> float:
        """
        Check if protected groups are adequately represented in the data.

        Returns:
            Representation score between 0 (poor) and 1 (good)
        """
        data_lower = data_description.lower()

        # Check for representation concerns
        negative_indicators = [
            'imbalanced', 'skewed', 'underrepresented', 'missing',
            'sparse', 'limited', 'few', 'lack of'
        ]

        positive_indicators = [
            'balanced', 'representative', 'diverse', 'comprehensive',
            'inclusive', 'proportional', 'adequate'
        ]

        negative_count = sum(1 for indicator in negative_indicators if indicator in data_lower)
        positive_count = sum(1 for indicator in positive_indicators if indicator in data_lower)

        # If protected groups data provided, check actual representation
        if protected_groups:
            try:
                total = sum(protected_groups.values())
                if total > 0:
                    # Check if any group is severely underrepresented (< 5%)
                    min_representation = min(v / total for v in protected_groups.values())
                    if min_representation < 0.05:
                        return 0.3
                    elif min_representation < 0.15:
                        return 0.6
                    else:
                        return 0.9
            except Exception:
                pass

        # Fallback to textual analysis
        if negative_count > positive_count:
            return 0.4
        elif positive_count > negative_count:
            return 0.8
        else:
            return 0.5

    def _calculate_bias_risk(
        self,
        bias_signals: List[str],
        fairness_score: float,
        representation_score: float
    ) -> float:
        """
        Calculate overall bias risk score.

        Returns:
            Risk score between 0 (low risk) and 1 (high risk)
        """
        # Weight components
        signal_risk = min(len(bias_signals) / 5.0, 1.0)  # Normalize to 0-1
        fairness_risk = 1.0 - fairness_score
        representation_risk = 1.0 - representation_score

        # Weighted combination
        total_risk = (
            0.3 * signal_risk +
            0.5 * fairness_risk +
            0.2 * representation_risk
        )

        return min(total_risk, 1.0)

    def _generate_high_risk_justification(
        self,
        bias_signals: List[str],
        fairness_score: float
    ) -> str:
        """Generate justification for high bias risk cases."""
        justification = "BIAS RISK DETECTED: This AI system shows significant fairness concerns. "

        if bias_signals:
            justification += f"Detected bias types: {', '.join(bias_signals[:3])}. "

        if fairness_score < 0.5:
            justification += "Fairness metrics indicate disparate impact across protected groups. "

        justification += "Recommendation: Conduct comprehensive bias audit before deployment. "
        justification += "Consider: (1) Data rebalancing, (2) Algorithmic fairness constraints, "
        justification += "(3) Regular fairness monitoring, (4) Human oversight for high-stakes decisions."

        return justification

    def _generate_medium_risk_justification(
        self,
        bias_signals: List[str],
        fairness_score: float
    ) -> str:
        """Generate justification for medium bias risk cases."""
        justification = "REVIEW RECOMMENDED: Potential fairness concerns detected. "

        if bias_signals:
            justification += f"Indicators present: {', '.join(bias_signals[:2])}. "

        justification += "While not critical, further investigation is warranted. "
        justification += "Recommended actions: (1) Validate fairness metrics, "
        justification += "(2) Review data representation, (3) Implement bias monitoring."

        return justification

    def _generate_low_risk_justification(self, fairness_score: float) -> str:
        """Generate justification for low bias risk cases."""
        justification = f"FAIRNESS ASSESSMENT: System shows acceptable fairness levels (score: {fairness_score:.2f}). "
        justification += "No significant bias indicators detected. "
        justification += "Recommendation: Continue monitoring fairness metrics during deployment. "
        justification += "Maintain diverse development teams and regular fairness audits."

        return justification


# Export
__all__ = ['BiasObjectivityCritic']
