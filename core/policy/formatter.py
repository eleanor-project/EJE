"""
Policy Outcome Formatter

Task 4.4: Policy Outcome Formatter

Creates clean, human-readable policy explanations with rule matches/mismatches,
links to critic outputs, and structured reasoning.
"""

import logging
from typing import Dict, List, Any, Optional
from textwrap import wrap, indent

from core.decision import FinalDecision
from core.policy.rules import (
    PolicyEvaluationResult,
    RuleEvaluationResult,
    RuleViolation,
    ComplianceLevel,
    RuleSeverity
)

logger = logging.getLogger("ejc.core.policy.formatter")


class PolicyOutcomeFormatter:
    """
    Formats policy evaluation outcomes into human-readable explanations.

    Provides structured reasoning with rule matches/mismatches and
    links to critic outputs.
    """

    def __init__(self, include_technical_details: bool = False):
        """
        Initialize formatter.

        Args:
            include_technical_details: Include technical metadata
        """
        self.include_technical_details = include_technical_details

    def format_decision(
        self,
        decision: FinalDecision,
        include_remediation: bool = True
    ) -> str:
        """
        Format complete decision with policy outcome.

        Args:
            decision: FinalDecision object
            include_remediation: Include remediation suggestions

        Returns:
            Formatted explanation string
        """
        sections = []

        # Header
        sections.append(self._format_header(decision))

        # Decision summary
        sections.append(self._format_decision_summary(decision))

        # Critic analysis
        sections.append(self._format_critic_analysis(decision))

        # Policy evaluation
        if decision.policy_result:
            sections.append(self._format_policy_evaluation(decision.policy_result))

        # Violations
        if decision.policy_violations:
            sections.append(self._format_violations(
                decision.policy_violations,
                include_remediation
            ))

        # Compliance outcome
        sections.append(self._format_compliance_outcome(decision))

        # Technical details
        if self.include_technical_details:
            sections.append(self._format_technical_details(decision))

        return "\n\n".join(sections)

    def format_policy_result(
        self,
        policy_result: PolicyEvaluationResult,
        verbose: bool = False
    ) -> str:
        """
        Format policy evaluation result.

        Args:
            policy_result: PolicyEvaluationResult object
            verbose: Include individual rule details

        Returns:
            Formatted string
        """
        sections = []

        # Summary
        sections.append(
            f"Policy: {policy_result.policy_name} ({policy_result.policy_id})"
        )
        sections.append(
            f"Compliance: {policy_result.overall_compliance.value.upper()}"
        )
        sections.append(
            f"Rules: {policy_result.passed_rules}/{policy_result.total_rules} passed"
        )

        # Individual rules if verbose
        if verbose and policy_result.rule_results:
            sections.append("\nRule Details:")
            for result in policy_result.rule_results:
                sections.append(self._format_rule_result(result))

        return "\n".join(sections)

    def _format_header(self, decision: FinalDecision) -> str:
        """Format decision header."""
        return f"""{'=' * 70}
DECISION REPORT
{'=' * 70}
Decision ID: {decision.decision_id}
Timestamp: {decision.timestamp}
Query: {decision.query}"""

    def _format_decision_summary(self, decision: FinalDecision) -> str:
        """Format decision summary."""
        # Compliance indicator
        if decision.compliance_level == ComplianceLevel.PASSES:
            indicator = "✓"
            status = "APPROVED"
        elif decision.compliance_level == ComplianceLevel.BORDERLINE:
            indicator = "⚠"
            status = "BORDERLINE"
        else:
            indicator = "✗"
            status = "BLOCKED"

        return f"""DECISION SUMMARY
{'-' * 70}
{indicator} Final Verdict: {decision.final_verdict}
   Confidence: {decision.confidence:.0%}
   Status: {status}
   Compliance: {decision.compliance_level.value.upper()}"""

    def _format_critic_analysis(self, decision: FinalDecision) -> str:
        """Format critic analysis section."""
        agg = decision.aggregation_result

        lines = [
            "CRITIC ANALYSIS",
            "-" * 70,
            f"Contributing Critics: {', '.join(agg.contributing_critics)}"
        ]

        # Weighted scores
        if agg.weighted_scores:
            lines.append("\nWeighted Scores:")
            for verdict, score in sorted(
                agg.weighted_scores.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                bar = "█" * int(score * 10)
                lines.append(f"  {verdict:12} {score:6.2f} {bar}")

        # Conflicts
        if agg.conflicts_detected:
            lines.append(f"\n⚠ Conflicts Detected: {len(agg.conflicts_detected)}")
            for i, conflict in enumerate(agg.conflicts_detected[:3], 1):
                desc = conflict.get("description", "Unknown conflict")
                lines.append(f"  {i}. {desc}")

            if len(agg.conflicts_detected) > 3:
                lines.append(f"  ... and {len(agg.conflicts_detected) - 3} more")

        return "\n".join(lines)

    def _format_policy_evaluation(self, policy_result: PolicyEvaluationResult) -> str:
        """Format policy evaluation section."""
        lines = [
            "POLICY EVALUATION",
            "-" * 70,
            f"Policy: {policy_result.policy_name}",
            f"Rules Evaluated: {policy_result.total_rules}",
            f"Rules Passed: {policy_result.passed_rules}",
            f"Rules Failed: {policy_result.total_rules - policy_result.passed_rules}"
        ]

        # Rule breakdown
        if policy_result.rule_results:
            lines.append("\nRule Results:")
            for result in policy_result.rule_results:
                status_icon = "✓" if result.passed else "✗"
                compliance = result.compliance_level.value
                lines.append(
                    f"  {status_icon} {result.rule_name:30} "
                    f"[{compliance:10}] Score: {result.score:.2f}"
                )

        return "\n".join(lines)

    def _format_violations(
        self,
        violations: List[RuleViolation],
        include_remediation: bool
    ) -> str:
        """Format policy violations."""
        lines = [
            "POLICY VIOLATIONS",
            "-" * 70
        ]

        # Group by severity
        by_severity = {}
        for v in violations:
            severity = v.severity.value
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(v)

        # Display by severity (critical first)
        severity_order = ["critical", "high", "medium", "low"]
        for severity in severity_order:
            if severity not in by_severity:
                continue

            severity_violations = by_severity[severity]
            lines.append(f"\n{severity.upper()} Severity ({len(severity_violations)}):")

            for i, v in enumerate(severity_violations, 1):
                lines.append(f"\n  {i}. {v.rule_name} ({v.rule_id})")
                lines.append(f"     {v.description}")
                lines.append(f"     Expected: {v.expected}")
                lines.append(f"     Actual: {v.actual}")

                if include_remediation and v.remediation:
                    wrapped = wrap(v.remediation, width=60)
                    lines.append(f"     Remediation:")
                    for line in wrapped:
                        lines.append(f"       {line}")

        return "\n".join(lines)

    def _format_compliance_outcome(self, decision: FinalDecision) -> str:
        """Format compliance outcome section."""
        if decision.passes_policy:
            outcome = "DECISION APPROVED"
            message = "This decision meets all policy requirements and may proceed."
        elif decision.compliance_level == ComplianceLevel.BORDERLINE:
            outcome = "DECISION BORDERLINE"
            message = (
                "This decision partially meets policy requirements. "
                "Review violations and consider escalation."
            )
        else:
            outcome = "DECISION BLOCKED"
            message = (
                "This decision violates policy requirements and should not proceed "
                "without addressing the violations."
            )

        lines = [
            "COMPLIANCE OUTCOME",
            "-" * 70,
            f"Status: {outcome}",
            ""
        ]

        # Wrap message
        wrapped = wrap(message, width=70)
        lines.extend(wrapped)

        return "\n".join(lines)

    def _format_technical_details(self, decision: FinalDecision) -> str:
        """Format technical details section."""
        lines = [
            "TECHNICAL DETAILS",
            "-" * 70,
            f"Decision ID: {decision.decision_id}",
            f"Timestamp: {decision.timestamp}",
            f"Total Weight: {decision.aggregation_result.total_weight:.2f}",
        ]

        if decision.metadata:
            lines.append("\nMetadata:")
            for key, value in decision.metadata.items():
                lines.append(f"  {key}: {value}")

        return "\n".join(lines)

    def _format_rule_result(self, result: RuleEvaluationResult) -> str:
        """Format individual rule result."""
        status = "PASS" if result.passed else "FAIL"
        return (
            f"  [{status}] {result.rule_name}\n"
            f"          Type: {result.rule_type.value}\n"
            f"          Compliance: {result.compliance_level.value}\n"
            f"          Score: {result.score:.2f}"
        )


class CompactFormatter:
    """
    Compact formatter for brief policy explanations.

    Provides concise summaries suitable for logs or notifications.
    """

    @staticmethod
    def format_decision(decision: FinalDecision) -> str:
        """
        Format decision as compact one-liner.

        Args:
            decision: FinalDecision object

        Returns:
            Compact string
        """
        compliance_icon = {
            ComplianceLevel.PASSES: "✓",
            ComplianceLevel.BORDERLINE: "⚠",
            ComplianceLevel.FAILS: "✗"
        }[decision.compliance_level]

        return (
            f"{compliance_icon} {decision.final_verdict} "
            f"({decision.confidence:.0%}) | "
            f"Policy: {decision.compliance_level.value} | "
            f"Violations: {len(decision.policy_violations)}"
        )

    @staticmethod
    def format_violation(violation: RuleViolation) -> str:
        """
        Format violation as compact string.

        Args:
            violation: RuleViolation object

        Returns:
            Compact string
        """
        return (
            f"[{violation.severity.value.upper()}] "
            f"{violation.rule_name}: {violation.description}"
        )


def format_decision(decision: FinalDecision, verbose: bool = True) -> str:
    """
    Convenience function to format a decision.

    Args:
        decision: FinalDecision object
        verbose: Use verbose formatter (default: True)

    Returns:
        Formatted string
    """
    if verbose:
        formatter = PolicyOutcomeFormatter()
        return formatter.format_decision(decision)
    else:
        return CompactFormatter.format_decision(decision)
