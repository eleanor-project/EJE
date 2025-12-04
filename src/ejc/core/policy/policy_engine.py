"""
Policy Engine Core

Provides formalized policy rule interface, threshold-based rules, and policy evaluation
for governance decisions. Supports declarative policy definitions with flexible evaluation.

Features:
- Abstract policy rule interface
- Threshold-based rules for numeric metrics
- Configurable rule priorities and actions
- Rule composition and chaining
- Detailed evaluation results with reasons
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field

from ...utils.logging import get_logger
from ..error_handling import PolicyException


logger = get_logger("ejc.policy.engine")


class RuleAction(Enum):
    """Actions a policy rule can recommend"""
    ALLOW = "ALLOW"
    DENY = "DENY"
    REVIEW = "REVIEW"
    ESCALATE = "ESCALATE"
    WARN = "WARN"


class RulePriority(Enum):
    """Priority levels for policy rules"""
    CRITICAL = "critical"  # Override other rules
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ADVISORY = "advisory"  # Informational only


@dataclass
class PolicyRuleResult:
    """Result of policy rule evaluation"""
    rule_name: str
    triggered: bool
    action: Optional[RuleAction] = None
    priority: RulePriority = RulePriority.MEDIUM
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'rule_name': self.rule_name,
            'triggered': self.triggered,
            'action': self.action.value if self.action else None,
            'priority': self.priority.value,
            'reason': self.reason,
            'metadata': self.metadata,
            'confidence': self.confidence
        }


class PolicyRule(ABC):
    """
    Abstract base class for policy rules.

    All policy rules must implement the evaluate method.
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        priority: RulePriority = RulePriority.MEDIUM,
        enabled: bool = True
    ):
        """
        Initialize policy rule.

        Args:
            name: Unique rule name
            description: Human-readable description
            priority: Rule priority level
            enabled: Whether rule is active
        """
        self.name = name
        self.description = description
        self.priority = priority
        self.enabled = enabled

    @abstractmethod
    def evaluate(self, decision_data: Dict[str, Any]) -> PolicyRuleResult:
        """
        Evaluate the policy rule against decision data.

        Args:
            decision_data: Decision context and critic outputs

        Returns:
            PolicyRuleResult indicating if rule triggered and recommended action
        """
        pass

    def __repr__(self) -> str:
        return f"<PolicyRule: {self.name} (priority={self.priority.value}, enabled={self.enabled})>"


class ThresholdRule(PolicyRule):
    """
    Threshold-based policy rule.

    Triggers when a numeric metric exceeds or falls below a threshold.
    """

    def __init__(
        self,
        name: str,
        metric_path: str,
        threshold: float,
        operator: str = ">=",
        action: RuleAction = RuleAction.DENY,
        description: str = "",
        priority: RulePriority = RulePriority.MEDIUM,
        enabled: bool = True,
        custom_reason: Optional[str] = None
    ):
        """
        Initialize threshold rule.

        Args:
            name: Rule name
            metric_path: Dot-notation path to metric in decision_data (e.g., "avg_confidence")
            threshold: Threshold value
            operator: Comparison operator (>=, >, <=, <, ==, !=)
            action: Action to recommend when triggered
            description: Rule description
            priority: Rule priority
            enabled: Whether rule is enabled
            custom_reason: Custom reason message (uses template if None)
        """
        super().__init__(name, description, priority, enabled)
        self.metric_path = metric_path
        self.threshold = threshold
        self.operator = operator
        self.action = action
        self.custom_reason = custom_reason

        # Operator functions
        self.operators = {
            '>=': lambda x, y: x >= y,
            '>': lambda x, y: x > y,
            '<=': lambda x, y: x <= y,
            '<': lambda x, y: x < y,
            '==': lambda x, y: x == y,
            '!=': lambda x, y: x != y
        }

        if operator not in self.operators:
            raise PolicyException(f"Invalid operator: {operator}")

    def evaluate(self, decision_data: Dict[str, Any]) -> PolicyRuleResult:
        """Evaluate threshold rule"""
        if not self.enabled:
            return PolicyRuleResult(
                rule_name=self.name,
                triggered=False,
                priority=self.priority
            )

        # Extract metric value using dot notation
        metric_value = self._get_nested_value(decision_data, self.metric_path)

        if metric_value is None:
            logger.warning(f"Metric '{self.metric_path}' not found in decision data")
            return PolicyRuleResult(
                rule_name=self.name,
                triggered=False,
                priority=self.priority,
                reason=f"Metric '{self.metric_path}' not found"
            )

        # Evaluate threshold
        try:
            operator_fn = self.operators[self.operator]
            triggered = operator_fn(float(metric_value), self.threshold)

            if triggered:
                reason = self.custom_reason or (
                    f"{self.metric_path} ({metric_value}) {self.operator} {self.threshold}"
                )
                return PolicyRuleResult(
                    rule_name=self.name,
                    triggered=True,
                    action=self.action,
                    priority=self.priority,
                    reason=reason,
                    metadata={
                        'metric_value': metric_value,
                        'threshold': self.threshold,
                        'operator': self.operator
                    }
                )
            else:
                return PolicyRuleResult(
                    rule_name=self.name,
                    triggered=False,
                    priority=self.priority
                )

        except (ValueError, TypeError) as e:
            logger.error(f"Failed to evaluate threshold rule '{self.name}': {str(e)}")
            return PolicyRuleResult(
                rule_name=self.name,
                triggered=False,
                priority=self.priority,
                reason=f"Evaluation error: {str(e)}"
            )

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested dictionary value using dot notation"""
        keys = path.split('.')
        value = data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value


class LambdaRule(PolicyRule):
    """
    Policy rule based on a custom lambda function.

    Allows flexible rule definitions using custom evaluation logic.
    """

    def __init__(
        self,
        name: str,
        evaluator: Callable[[Dict[str, Any]], bool],
        action: RuleAction = RuleAction.REVIEW,
        reason_generator: Optional[Callable[[Dict[str, Any]], str]] = None,
        description: str = "",
        priority: RulePriority = RulePriority.MEDIUM,
        enabled: bool = True
    ):
        """
        Initialize lambda rule.

        Args:
            name: Rule name
            evaluator: Function that takes decision_data and returns bool
            action: Action when rule triggers
            reason_generator: Optional function to generate reason message
            description: Rule description
            priority: Rule priority
            enabled: Whether rule is enabled
        """
        super().__init__(name, description, priority, enabled)
        self.evaluator = evaluator
        self.action = action
        self.reason_generator = reason_generator

    def evaluate(self, decision_data: Dict[str, Any]) -> PolicyRuleResult:
        """Evaluate lambda rule"""
        if not self.enabled:
            return PolicyRuleResult(
                rule_name=self.name,
                triggered=False,
                priority=self.priority
            )

        try:
            triggered = self.evaluator(decision_data)

            if triggered:
                reason = (
                    self.reason_generator(decision_data)
                    if self.reason_generator
                    else f"Rule '{self.name}' triggered"
                )
                return PolicyRuleResult(
                    rule_name=self.name,
                    triggered=True,
                    action=self.action,
                    priority=self.priority,
                    reason=reason
                )
            else:
                return PolicyRuleResult(
                    rule_name=self.name,
                    triggered=False,
                    priority=self.priority
                )

        except Exception as e:
            logger.error(f"Failed to evaluate lambda rule '{self.name}': {str(e)}")
            return PolicyRuleResult(
                rule_name=self.name,
                triggered=False,
                priority=self.priority,
                reason=f"Evaluation error: {str(e)}"
            )


class PolicyEngine:
    """
    Policy evaluation engine.

    Manages and evaluates multiple policy rules against decision data.
    """

    def __init__(self, rules: Optional[List[PolicyRule]] = None):
        """
        Initialize policy engine.

        Args:
            rules: List of policy rules to enforce
        """
        self.rules: List[PolicyRule] = rules or []
        self._rule_index: Dict[str, PolicyRule] = {rule.name: rule for rule in self.rules}

    def add_rule(self, rule: PolicyRule):
        """Add a rule to the engine"""
        if rule.name in self._rule_index:
            logger.warning(f"Rule '{rule.name}' already exists, replacing")
            self.remove_rule(rule.name)

        self.rules.append(rule)
        self._rule_index[rule.name] = rule
        logger.info(f"Added policy rule: {rule.name}")

    def remove_rule(self, rule_name: str) -> bool:
        """Remove a rule by name"""
        if rule_name in self._rule_index:
            rule = self._rule_index[rule_name]
            self.rules.remove(rule)
            del self._rule_index[rule_name]
            logger.info(f"Removed policy rule: {rule_name}")
            return True
        return False

    def get_rule(self, rule_name: str) -> Optional[PolicyRule]:
        """Get a rule by name"""
        return self._rule_index.get(rule_name)

    def enable_rule(self, rule_name: str):
        """Enable a rule"""
        rule = self.get_rule(rule_name)
        if rule:
            rule.enabled = True

    def disable_rule(self, rule_name: str):
        """Disable a rule"""
        rule = self.get_rule(rule_name)
        if rule:
            rule.enabled = False

    def evaluate_all(
        self,
        decision_data: Dict[str, Any],
        stop_on_critical: bool = True
    ) -> List[PolicyRuleResult]:
        """
        Evaluate all rules against decision data.

        Args:
            decision_data: Decision context and metrics
            stop_on_critical: Stop evaluation if critical rule triggers

        Returns:
            List of rule evaluation results
        """
        results = []

        # Sort rules by priority (critical first)
        priority_order = {
            RulePriority.CRITICAL: 0,
            RulePriority.HIGH: 1,
            RulePriority.MEDIUM: 2,
            RulePriority.LOW: 3,
            RulePriority.ADVISORY: 4
        }
        sorted_rules = sorted(self.rules, key=lambda r: priority_order.get(r.priority, 5))

        for rule in sorted_rules:
            try:
                result = rule.evaluate(decision_data)
                results.append(result)

                # Stop on critical rule trigger
                if (stop_on_critical and
                    result.triggered and
                    result.priority == RulePriority.CRITICAL):
                    logger.warning(f"Critical rule triggered: {rule.name}, stopping evaluation")
                    break

            except Exception as e:
                logger.error(f"Error evaluating rule '{rule.name}': {str(e)}")
                results.append(PolicyRuleResult(
                    rule_name=rule.name,
                    triggered=False,
                    priority=rule.priority,
                    reason=f"Evaluation error: {str(e)}"
                ))

        return results

    def get_triggered_rules(
        self,
        decision_data: Dict[str, Any]
    ) -> List[PolicyRuleResult]:
        """
        Get only triggered rules.

        Args:
            decision_data: Decision context

        Returns:
            List of triggered rule results
        """
        all_results = self.evaluate_all(decision_data, stop_on_critical=False)
        return [r for r in all_results if r.triggered]

    def get_recommended_action(
        self,
        decision_data: Dict[str, Any]
    ) -> RuleAction:
        """
        Get recommended action based on triggered rules.

        Priority: DENY > ESCALATE > REVIEW > WARN > ALLOW

        Args:
            decision_data: Decision context

        Returns:
            Recommended action
        """
        triggered = self.get_triggered_rules(decision_data)

        if not triggered:
            return RuleAction.ALLOW

        # Action precedence
        action_precedence = {
            RuleAction.DENY: 0,
            RuleAction.ESCALATE: 1,
            RuleAction.REVIEW: 2,
            RuleAction.WARN: 3,
            RuleAction.ALLOW: 4
        }

        # Get highest priority action
        triggered.sort(key=lambda r: action_precedence.get(r.action, 5))
        return triggered[0].action

    def list_rules(self) -> List[Dict[str, Any]]:
        """List all rules with their status"""
        return [
            {
                'name': rule.name,
                'description': rule.description,
                'priority': rule.priority.value,
                'enabled': rule.enabled
            }
            for rule in self.rules
        ]


# Pre-defined threshold rules for common scenarios

def create_confidence_threshold_rule(
    threshold: float = 0.7,
    action: RuleAction = RuleAction.REVIEW,
    priority: RulePriority = RulePriority.HIGH
) -> ThresholdRule:
    """Create rule for minimum confidence threshold"""
    return ThresholdRule(
        name="min_confidence_threshold",
        metric_path="avg_confidence",
        threshold=threshold,
        operator="<",
        action=action,
        description=f"Trigger when average confidence < {threshold}",
        priority=priority,
        custom_reason=f"Average confidence below threshold ({threshold})"
    )


def create_ambiguity_threshold_rule(
    threshold: float = 0.3,
    action: RuleAction = RuleAction.ESCALATE,
    priority: RulePriority = RulePriority.HIGH
) -> ThresholdRule:
    """Create rule for maximum ambiguity threshold"""
    return ThresholdRule(
        name="max_ambiguity_threshold",
        metric_path="ambiguity",
        threshold=threshold,
        operator=">",
        action=action,
        description=f"Trigger when ambiguity > {threshold}",
        priority=priority,
        custom_reason=f"High ambiguity detected (>{threshold})"
    )


def create_error_rate_threshold_rule(
    threshold: float = 0.2,
    action: RuleAction = RuleAction.REVIEW,
    priority: RulePriority = RulePriority.HIGH
) -> ThresholdRule:
    """Create rule for maximum critic error rate"""
    return ThresholdRule(
        name="max_error_rate_threshold",
        metric_path="errors.rate",
        threshold=threshold,
        operator=">",
        action=action,
        description=f"Trigger when critic error rate > {threshold}",
        priority=priority,
        custom_reason=f"High critic failure rate (>{threshold})"
    )
