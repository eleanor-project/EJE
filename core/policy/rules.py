"""
Policy Rule Interface

Task 4.1: Formalize Policy Rule Interface

Defines strongly-typed rule structures and policy evaluation interface
for governance and compliance checks.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum

logger = logging.getLogger("ejc.core.policy.rules")


class RuleType(Enum):
    """Types of policy rules."""

    THRESHOLD = "threshold"  # Numeric threshold checks
    REQUIRED = "required"  # Required field/condition checks
    FORBIDDEN = "forbidden"  # Forbidden actions/conditions
    CONDITIONAL = "conditional"  # Conditional rules (if-then)
    CUSTOM = "custom"  # Custom rule logic


class ComplianceLevel(Enum):
    """Compliance outcomes."""

    PASSES = "passes"  # Fully compliant
    BORDERLINE = "borderline"  # Marginally compliant (warning)
    FAILS = "fails"  # Non-compliant (violation)


class RuleSeverity(Enum):
    """Rule severity levels."""

    CRITICAL = "critical"  # Must pass (blocks decision)
    HIGH = "high"  # Should pass (strong warning)
    MEDIUM = "medium"  # Warning
    LOW = "low"  # Advisory


@dataclass
class RuleViolation:
    """Represents a rule violation."""

    rule_id: str
    rule_name: str
    severity: RuleSeverity
    description: str
    expected: Any
    actual: Any
    remediation: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleEvaluationResult:
    """Result of evaluating a single rule."""

    rule_id: str
    rule_name: str
    rule_type: RuleType
    passed: bool
    compliance_level: ComplianceLevel
    score: float  # 0.0 (fail) to 1.0 (pass)
    violations: List[RuleViolation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyEvaluationResult:
    """Result of evaluating a complete policy (multiple rules)."""

    policy_id: str
    policy_name: str
    overall_compliance: ComplianceLevel
    passed_rules: int
    total_rules: int
    rule_results: List[RuleEvaluationResult] = field(default_factory=list)
    violations: List[RuleViolation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PolicyRule(ABC):
    """
    Abstract base class for policy rules.

    All policy rules must implement evaluate() method.
    """

    def __init__(
        self,
        rule_id: str,
        name: str,
        rule_type: RuleType,
        severity: RuleSeverity,
        description: str
    ):
        """
        Initialize policy rule.

        Args:
            rule_id: Unique rule identifier
            name: Human-readable rule name
            rule_type: Type of rule
            severity: Severity level
            description: Rule description
        """
        self.rule_id = rule_id
        self.name = name
        self.rule_type = rule_type
        self.severity = severity
        self.description = description

    @abstractmethod
    def evaluate(self, decision_context: Dict[str, Any]) -> RuleEvaluationResult:
        """
        Evaluate rule against decision context.

        Args:
            decision_context: Dict containing:
                - aggregation_result: AggregationResult
                - evidence_bundles: List of evidence bundles
                - query: Original query
                - metadata: Additional context

        Returns:
            RuleEvaluationResult
        """
        pass

    def _create_result(
        self,
        passed: bool,
        score: float,
        violations: Optional[List[RuleViolation]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RuleEvaluationResult:
        """
        Helper to create RuleEvaluationResult.

        Args:
            passed: Whether rule passed
            score: Rule score (0.0-1.0)
            violations: Optional list of violations
            metadata: Optional metadata

        Returns:
            RuleEvaluationResult
        """
        # Determine compliance level
        if passed:
            compliance_level = ComplianceLevel.PASSES
        elif score >= 0.5:  # Partial pass
            compliance_level = ComplianceLevel.BORDERLINE
        else:
            compliance_level = ComplianceLevel.FAILS

        return RuleEvaluationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            rule_type=self.rule_type,
            passed=passed,
            compliance_level=compliance_level,
            score=score,
            violations=violations or [],
            metadata=metadata or {}
        )

    def _create_violation(
        self,
        description: str,
        expected: Any,
        actual: Any,
        remediation: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> RuleViolation:
        """
        Helper to create RuleViolation.

        Args:
            description: Violation description
            expected: Expected value/condition
            actual: Actual value/condition
            remediation: Optional remediation advice
            context: Optional context

        Returns:
            RuleViolation
        """
        return RuleViolation(
            rule_id=self.rule_id,
            rule_name=self.name,
            severity=self.severity,
            description=description,
            expected=expected,
            actual=actual,
            remediation=remediation,
            context=context or {}
        )


class PolicyEngine:
    """
    Policy evaluation engine.

    Evaluates a set of rules against a decision context and produces
    compliance assessment.
    """

    def __init__(
        self,
        policy_id: str,
        policy_name: str,
        rules: Optional[List[PolicyRule]] = None
    ):
        """
        Initialize policy engine.

        Args:
            policy_id: Unique policy identifier
            policy_name: Human-readable policy name
            rules: Optional list of rules
        """
        self.policy_id = policy_id
        self.policy_name = policy_name
        self.rules: List[PolicyRule] = rules or []

    def add_rule(self, rule: PolicyRule):
        """
        Add a rule to the policy.

        Args:
            rule: PolicyRule to add
        """
        self.rules.append(rule)
        logger.debug(f"Added rule {rule.rule_id} to policy {self.policy_id}")

    def remove_rule(self, rule_id: str) -> bool:
        """
        Remove a rule from the policy.

        Args:
            rule_id: Rule ID to remove

        Returns:
            True if removed, False if not found
        """
        original_count = len(self.rules)
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        removed = len(self.rules) < original_count

        if removed:
            logger.debug(f"Removed rule {rule_id} from policy {self.policy_id}")

        return removed

    def evaluate(self, decision_context: Dict[str, Any]) -> PolicyEvaluationResult:
        """
        Evaluate all rules against decision context.

        Args:
            decision_context: Decision context dict

        Returns:
            PolicyEvaluationResult
        """
        if not self.rules:
            logger.warning(f"Policy {self.policy_id} has no rules")
            return PolicyEvaluationResult(
                policy_id=self.policy_id,
                policy_name=self.policy_name,
                overall_compliance=ComplianceLevel.PASSES,
                passed_rules=0,
                total_rules=0
            )

        # Evaluate each rule
        rule_results = []
        all_violations = []

        for rule in self.rules:
            try:
                result = rule.evaluate(decision_context)
                rule_results.append(result)

                if result.violations:
                    all_violations.extend(result.violations)

            except Exception as e:
                logger.error(f"Error evaluating rule {rule.rule_id}: {e}")

                # Create failure result
                result = RuleEvaluationResult(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    rule_type=rule.rule_type,
                    passed=False,
                    compliance_level=ComplianceLevel.FAILS,
                    score=0.0,
                    violations=[
                        RuleViolation(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            description=f"Rule evaluation failed: {e}",
                            expected="Successful evaluation",
                            actual=f"Error: {e}"
                        )
                    ]
                )
                rule_results.append(result)
                all_violations.extend(result.violations)

        # Calculate overall compliance
        passed_rules = sum(1 for r in rule_results if r.passed)
        total_rules = len(rule_results)

        # Determine overall compliance level
        overall_compliance = self._determine_overall_compliance(rule_results)

        logger.info(
            f"Policy {self.policy_id} evaluation: {passed_rules}/{total_rules} rules passed "
            f"({overall_compliance.value})"
        )

        return PolicyEvaluationResult(
            policy_id=self.policy_id,
            policy_name=self.policy_name,
            overall_compliance=overall_compliance,
            passed_rules=passed_rules,
            total_rules=total_rules,
            rule_results=rule_results,
            violations=all_violations
        )

    def _determine_overall_compliance(
        self,
        rule_results: List[RuleEvaluationResult]
    ) -> ComplianceLevel:
        """
        Determine overall compliance level from rule results.

        Args:
            rule_results: List of rule results

        Returns:
            Overall ComplianceLevel
        """
        if not rule_results:
            return ComplianceLevel.PASSES

        # Check for any CRITICAL failures
        critical_failures = [
            r for r in rule_results
            if not r.passed and self._get_rule_severity(r.rule_id) == RuleSeverity.CRITICAL
        ]

        if critical_failures:
            return ComplianceLevel.FAILS

        # Check for any failures
        any_failures = [r for r in rule_results if not r.passed]

        if not any_failures:
            return ComplianceLevel.PASSES

        # Check for borderline cases
        borderline_count = sum(
            1 for r in rule_results
            if r.compliance_level == ComplianceLevel.BORDERLINE
        )

        # If most are borderline, overall is borderline
        if borderline_count >= len(rule_results) / 2:
            return ComplianceLevel.BORDERLINE

        # Otherwise, if there are failures, it fails
        return ComplianceLevel.FAILS

    def _get_rule_severity(self, rule_id: str) -> RuleSeverity:
        """Get severity of a rule by ID."""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule.severity
        return RuleSeverity.MEDIUM

    def get_rules(self) -> List[PolicyRule]:
        """Get all rules in this policy."""
        return self.rules.copy()

    def get_rule_by_id(self, rule_id: str) -> Optional[PolicyRule]:
        """Get a specific rule by ID."""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        return None
