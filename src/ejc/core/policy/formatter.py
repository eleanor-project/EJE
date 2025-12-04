"""
Policy Outcome Formatter

Formats policy evaluation results into structured, human-readable outputs.
Supports multiple output formats and detail levels.

Features:
- Structured JSON output
- Human-readable summaries
- Detailed policy reports
- Compliance documentation
- Audit trail formatting
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from .policy_engine import PolicyRuleResult, RuleAction, RulePriority
from .compliance import ComplianceFlags, ComplianceStatus, RiskLevel
from ...utils.logging import get_logger


logger = get_logger("ejc.policy.formatter")


class PolicyOutcomeFormatter:
    """
    Formats policy evaluation results for various audiences and purposes.

    Provides flexible output formatting for policy decisions,
    compliance checks, and audit documentation.
    """

    def __init__(self, include_metadata: bool = True, verbose: bool = False):
        """
        Initialize policy outcome formatter.

        Args:
            include_metadata: Include detailed metadata in outputs
            verbose: Include verbose details in formatted output
        """
        self.include_metadata = include_metadata
        self.verbose = verbose

    def format_policy_results(
        self,
        rule_results: List[PolicyRuleResult],
        decision_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format policy rule results into structured output.

        Args:
            rule_results: List of policy rule evaluation results
            decision_data: Original decision data (optional)

        Returns:
            Formatted policy outcome dictionary
        """
        triggered = [r for r in rule_results if r.triggered]

        # Determine overall recommendation
        if triggered:
            # Get highest priority action
            action_precedence = {
                RuleAction.DENY: 0,
                RuleAction.ESCALATE: 1,
                RuleAction.REVIEW: 2,
                RuleAction.WARN: 3,
                RuleAction.ALLOW: 4
            }
            triggered.sort(key=lambda r: action_precedence.get(r.action, 5))
            recommended_action = triggered[0].action.value
        else:
            recommended_action = RuleAction.ALLOW.value

        # Build output
        output = {
            'policy_evaluation': {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'recommended_action': recommended_action,
                'total_rules_evaluated': len(rule_results),
                'rules_triggered': len(triggered),
                'triggered_rules': [
                    {
                        'name': r.rule_name,
                        'action': r.action.value if r.action else None,
                        'priority': r.priority.value,
                        'reason': r.reason,
                        'confidence': r.confidence
                    }
                    for r in triggered
                ],
                'summary': self._generate_summary(triggered)
            }
        }

        # Add metadata if requested
        if self.include_metadata:
            output['policy_evaluation']['metadata'] = {
                'all_results': [r.to_dict() for r in rule_results]
            }

        # Add decision context if provided
        if decision_data and self.verbose:
            output['policy_evaluation']['decision_context'] = {
                'verdict': decision_data.get('overall_verdict'),
                'confidence': decision_data.get('avg_confidence'),
                'ambiguity': decision_data.get('ambiguity')
            }

        return output

    def format_compliance_report(
        self,
        compliance_flags: ComplianceFlags,
        decision_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format compliance check results into structured report.

        Args:
            compliance_flags: Compliance flags from checker
            decision_data: Original decision data (optional)

        Returns:
            Formatted compliance report
        """
        report = {
            'compliance_report': {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'jurisdiction': compliance_flags.jurisdiction,
                'overall_status': compliance_flags.overall_status.value,
                'requires_human_review': compliance_flags.requires_human_review,
                'applicable_standards': [s.value for s in compliance_flags.applicable_standards],
                'summary': compliance_flags.to_dict()['summary'],
                'violations': [
                    {
                        'standard': f.standard.value,
                        'requirement': f.requirement,
                        'risk_level': f.risk_level.value,
                        'reason': f.reason,
                        'status': f.status.value
                    }
                    for f in compliance_flags.get_non_compliant_flags()
                ],
                'warnings': [
                    {
                        'standard': f.standard.value,
                        'requirement': f.requirement,
                        'reason': f.reason
                    }
                    for f in compliance_flags.get_triggered_flags()
                    if f.status != ComplianceStatus.NON_COMPLIANT
                ]
            }
        }

        # Add all flags if verbose
        if self.verbose:
            report['compliance_report']['all_flags'] = [f.to_dict() for f in compliance_flags.flags]

        # Add decision context if provided
        if decision_data and self.include_metadata:
            report['compliance_report']['decision_context'] = {
                'decision_id': decision_data.get('request_id', decision_data.get('decision_id')),
                'timestamp': decision_data.get('timestamp')
            }

        return report

    def format_combined_outcome(
        self,
        rule_results: List[PolicyRuleResult],
        compliance_flags: ComplianceFlags,
        decision_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format combined policy and compliance outcome.

        Args:
            rule_results: Policy rule evaluation results
            compliance_flags: Compliance check results
            decision_data: Original decision data

        Returns:
            Combined formatted outcome
        """
        # Get individual formats
        policy_output = self.format_policy_results(rule_results, decision_data)
        compliance_output = self.format_compliance_report(compliance_flags, decision_data)

        # Determine final action
        final_action = self._determine_final_action(
            policy_output['policy_evaluation']['recommended_action'],
            compliance_flags.overall_status
        )

        # Build combined output
        combined = {
            'governance_outcome': {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'decision_id': decision_data.get('request_id', decision_data.get('decision_id')),
                'final_action': final_action,
                'policy_evaluation': policy_output['policy_evaluation'],
                'compliance_report': compliance_output['compliance_report'],
                'requires_human_review': (
                    compliance_flags.requires_human_review or
                    final_action in ['ESCALATE', 'REVIEW']
                ),
                'executive_summary': self._generate_executive_summary(
                    rule_results,
                    compliance_flags,
                    final_action
                )
            }
        }

        return combined

    def format_human_readable(
        self,
        rule_results: List[PolicyRuleResult],
        compliance_flags: Optional[ComplianceFlags] = None
    ) -> str:
        """
        Format policy results as human-readable text.

        Args:
            rule_results: Policy rule results
            compliance_flags: Optional compliance flags

        Returns:
            Human-readable formatted string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("POLICY EVALUATION REPORT")
        lines.append("=" * 60)
        lines.append("")

        # Policy rules section
        triggered = [r for r in rule_results if r.triggered]
        if triggered:
            lines.append(f"TRIGGERED RULES: {len(triggered)}")
            lines.append("-" * 60)
            for result in triggered:
                lines.append(f"  [{result.priority.value.upper()}] {result.rule_name}")
                lines.append(f"  Action: {result.action.value}")
                lines.append(f"  Reason: {result.reason}")
                lines.append("")
        else:
            lines.append("No policy rules triggered")
            lines.append("")

        # Compliance section
        if compliance_flags:
            lines.append("COMPLIANCE STATUS")
            lines.append("-" * 60)
            lines.append(f"Overall Status: {compliance_flags.overall_status.value.upper()}")
            lines.append(f"Jurisdiction: {compliance_flags.jurisdiction}")
            lines.append("")

            violations = compliance_flags.get_non_compliant_flags()
            if violations:
                lines.append(f"VIOLATIONS: {len(violations)}")
                for flag in violations:
                    lines.append(f"  [{flag.standard.value}] {flag.requirement}")
                    lines.append(f"  Risk: {flag.risk_level.value.upper()}")
                    lines.append(f"  Reason: {flag.reason}")
                    lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    def _generate_summary(self, triggered_rules: List[PolicyRuleResult]) -> str:
        """Generate human-readable summary of triggered rules"""
        if not triggered_rules:
            return "All policy rules passed - no violations detected"

        critical = [r for r in triggered_rules if r.priority == RulePriority.CRITICAL]
        high = [r for r in triggered_rules if r.priority == RulePriority.HIGH]

        summary_parts = []
        if critical:
            summary_parts.append(f"{len(critical)} critical rule(s)")
        if high:
            summary_parts.append(f"{len(high)} high-priority rule(s)")

        total_triggered = len(triggered_rules)
        if total_triggered > (len(critical) + len(high)):
            other_count = total_triggered - (len(critical) + len(high))
            summary_parts.append(f"{other_count} other rule(s)")

        return f"Triggered: {', '.join(summary_parts)}"

    def _determine_final_action(
        self,
        policy_action: str,
        compliance_status: ComplianceStatus
    ) -> str:
        """Determine final action based on policy and compliance"""
        # Non-compliance overrides policy recommendation
        if compliance_status == ComplianceStatus.NON_COMPLIANT:
            return "DENY"
        elif compliance_status == ComplianceStatus.REQUIRES_REVIEW:
            return "REVIEW"

        # Use policy recommendation
        return policy_action

    def _generate_executive_summary(
        self,
        rule_results: List[PolicyRuleResult],
        compliance_flags: ComplianceFlags,
        final_action: str
    ) -> str:
        """Generate executive summary for combined outcome"""
        triggered_count = len([r for r in rule_results if r.triggered])
        compliance_ok = compliance_flags.overall_status == ComplianceStatus.COMPLIANT

        summary_parts = []

        # Action summary
        summary_parts.append(f"Final Action: {final_action}")

        # Policy summary
        if triggered_count > 0:
            summary_parts.append(f"{triggered_count} policy rule(s) triggered")
        else:
            summary_parts.append("All policy rules passed")

        # Compliance summary
        if compliance_ok:
            summary_parts.append("Compliant with all applicable standards")
        else:
            violations = len(compliance_flags.get_non_compliant_flags())
            if violations > 0:
                summary_parts.append(f"{violations} compliance violation(s) detected")
            else:
                summary_parts.append("Compliance review required")

        return " | ".join(summary_parts)

    def export_to_json(
        self,
        data: Dict[str, Any],
        pretty: bool = True
    ) -> str:
        """
        Export formatted data to JSON string.

        Args:
            data: Data to export
            pretty: Pretty print JSON

        Returns:
            JSON string
        """
        if pretty:
            return json.dumps(data, indent=2, sort_keys=False)
        else:
            return json.dumps(data)

    def export_to_file(
        self,
        data: Dict[str, Any],
        file_path: str,
        pretty: bool = True
    ):
        """
        Export formatted data to JSON file.

        Args:
            data: Data to export
            file_path: Output file path
            pretty: Pretty print JSON
        """
        json_str = self.export_to_json(data, pretty)
        with open(file_path, 'w') as f:
            f.write(json_str)
        logger.info(f"Exported policy outcome to {file_path}")


# Convenience functions

def format_policy_decision(
    rule_results: List[PolicyRuleResult],
    decision_data: Optional[Dict[str, Any]] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to format policy decision.

    Args:
        rule_results: Policy rule results
        decision_data: Original decision data
        verbose: Include verbose details

    Returns:
        Formatted policy outcome
    """
    formatter = PolicyOutcomeFormatter(verbose=verbose)
    return formatter.format_policy_results(rule_results, decision_data)


def format_compliance_check(
    compliance_flags: ComplianceFlags,
    decision_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function to format compliance check.

    Args:
        compliance_flags: Compliance flags
        decision_data: Original decision data

    Returns:
        Formatted compliance report
    """
    formatter = PolicyOutcomeFormatter()
    return formatter.format_compliance_report(compliance_flags, decision_data)
