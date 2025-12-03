"""
Comprehensive tests for Policy Engine functionality.

Tests cover:
- Policy rule interface and evaluation
- Threshold-based rules
- Compliance checking and flags
- Policy outcome formatting
- Edge cases and error handling
"""

import pytest
from datetime import datetime

from ejc.core.policy.policy_engine import (
    PolicyEngine,
    PolicyRule,
    ThresholdRule,
    LambdaRule,
    RuleAction,
    RulePriority,
    PolicyRuleResult,
    create_confidence_threshold_rule,
    create_ambiguity_threshold_rule,
    create_error_rate_threshold_rule,
)
from ejc.core.policy.compliance import (
    ComplianceChecker,
    ComplianceFlags,
    ComplianceFlag,
    ComplianceStandard,
    ComplianceStatus,
    RiskLevel,
)
from ejc.core.policy.formatter import (
    PolicyOutcomeFormatter,
    format_policy_decision,
    format_compliance_check,
)


class TestPolicyRules:
    """Tests for policy rule base classes and implementations"""

    def test_threshold_rule_creation(self):
        """Test creating a threshold rule"""
        rule = ThresholdRule(
            name="low_confidence_check",
            metric_path="avg_confidence",
            threshold=0.7,
            operator="<",
            action=RuleAction.REVIEW,
            priority=RulePriority.HIGH
        )

        assert rule.name == "low_confidence_check"
        assert rule.threshold == 0.7
        assert rule.action == RuleAction.REVIEW

    def test_threshold_rule_evaluation_triggered(self):
        """Test threshold rule triggers when condition met"""
        rule = ThresholdRule(
            name="high_ambiguity",
            metric_path="ambiguity",
            threshold=0.3,
            operator=">",
            action=RuleAction.ESCALATE
        )

        decision_data = {
            'ambiguity': 0.5,
            'avg_confidence': 0.8
        }

        result = rule.evaluate(decision_data)

        assert result.triggered is True
        assert result.action == RuleAction.ESCALATE
        assert "0.5" in result.reason  # Should mention the value

    def test_threshold_rule_not_triggered(self):
        """Test threshold rule doesn't trigger when condition not met"""
        rule = ThresholdRule(
            name="min_confidence",
            metric_path="avg_confidence",
            threshold=0.6,
            operator="<",
            action=RuleAction.REVIEW
        )

        decision_data = {
            'avg_confidence': 0.85  # Above threshold, won't trigger
        }

        result = rule.evaluate(decision_data)

        assert result.triggered is False

    def test_threshold_rule_nested_path(self):
        """Test threshold rule with nested metric path"""
        rule = ThresholdRule(
            name="error_rate_check",
            metric_path="errors.rate",
            threshold=0.2,
            operator=">",
            action=RuleAction.REVIEW
        )

        decision_data = {
            'errors': {
                'rate': 0.35,
                'count': 7
            }
        }

        result = rule.evaluate(decision_data)

        assert result.triggered is True
        assert result.metadata['metric_value'] == 0.35

    def test_threshold_rule_missing_metric(self):
        """Test threshold rule when metric doesn't exist"""
        rule = ThresholdRule(
            name="test_rule",
            metric_path="nonexistent.field",
            threshold=0.5,
            operator=">"
        )

        decision_data = {'other_field': 0.8}

        result = rule.evaluate(decision_data)

        assert result.triggered is False
        assert "not found" in result.reason

    def test_lambda_rule_basic(self):
        """Test lambda rule with custom evaluator"""
        rule = LambdaRule(
            name="custom_check",
            evaluator=lambda data: data.get('verdict') == 'DENY',
            action=RuleAction.ESCALATE,
            reason_generator=lambda data: f"Verdict is {data.get('verdict')}"
        )

        decision_data = {'verdict': 'DENY'}

        result = rule.evaluate(decision_data)

        assert result.triggered is True
        assert result.action == RuleAction.ESCALATE
        assert "DENY" in result.reason

    def test_lambda_rule_not_triggered(self):
        """Test lambda rule when condition not met"""
        rule = LambdaRule(
            name="allow_check",
            evaluator=lambda data: data.get('verdict') == 'ALLOW',
            action=RuleAction.WARN
        )

        decision_data = {'verdict': 'DENY'}

        result = rule.evaluate(decision_data)

        assert result.triggered is False

    def test_disabled_rule(self):
        """Test that disabled rules don't trigger"""
        rule = ThresholdRule(
            name="disabled_test",
            metric_path="value",
            threshold=0.5,
            operator=">",
            enabled=False  # Disabled
        )

        decision_data = {'value': 0.9}  # Would normally trigger

        result = rule.evaluate(decision_data)

        assert result.triggered is False

    def test_pre_defined_confidence_rule(self):
        """Test pre-defined confidence threshold rule"""
        rule = create_confidence_threshold_rule(
            threshold=0.75,
            action=RuleAction.REVIEW
        )

        # Below threshold
        result = rule.evaluate({'avg_confidence': 0.6})
        assert result.triggered is True

        # Above threshold
        result = rule.evaluate({'avg_confidence': 0.85})
        assert result.triggered is False

    def test_pre_defined_ambiguity_rule(self):
        """Test pre-defined ambiguity threshold rule"""
        rule = create_ambiguity_threshold_rule(
            threshold=0.25,
            action=RuleAction.ESCALATE
        )

        # Above threshold (high ambiguity)
        result = rule.evaluate({'ambiguity': 0.4})
        assert result.triggered is True
        assert result.action == RuleAction.ESCALATE

    def test_pre_defined_error_rate_rule(self):
        """Test pre-defined error rate threshold rule"""
        rule = create_error_rate_threshold_rule(
            threshold=0.3,
            action=RuleAction.REVIEW
        )

        # High error rate
        result = rule.evaluate({'errors': {'rate': 0.45}})
        assert result.triggered is True


class TestPolicyEngine:
    """Tests for policy engine orchestration"""

    def test_engine_initialization(self):
        """Test policy engine initialization"""
        rules = [
            create_confidence_threshold_rule(),
            create_ambiguity_threshold_rule()
        ]

        engine = PolicyEngine(rules)

        assert len(engine.rules) == 2
        assert len(engine._rule_index) == 2

    def test_add_remove_rules(self):
        """Test adding and removing rules"""
        engine = PolicyEngine()

        rule = ThresholdRule(
            name="test_rule",
            metric_path="value",
            threshold=0.5,
            operator=">"
        )

        # Add rule
        engine.add_rule(rule)
        assert len(engine.rules) == 1
        assert engine.get_rule("test_rule") is not None

        # Remove rule
        success = engine.remove_rule("test_rule")
        assert success is True
        assert len(engine.rules) == 0

    def test_enable_disable_rules(self):
        """Test enabling and disabling rules"""
        rule = ThresholdRule(
            name="toggle_rule",
            metric_path="value",
            threshold=0.5,
            operator=">"
        )

        engine = PolicyEngine([rule])

        # Disable rule
        engine.disable_rule("toggle_rule")
        assert rule.enabled is False

        # Enable rule
        engine.enable_rule("toggle_rule")
        assert rule.enabled is True

    def test_evaluate_all_rules(self):
        """Test evaluating all rules"""
        rules = [
            ThresholdRule(
                name="rule1",
                metric_path="confidence",
                threshold=0.7,
                operator="<",
                action=RuleAction.REVIEW
            ),
            ThresholdRule(
                name="rule2",
                metric_path="ambiguity",
                threshold=0.3,
                operator=">",
                action=RuleAction.ESCALATE
            )
        ]

        engine = PolicyEngine(rules)

        decision_data = {
            'confidence': 0.5,  # Triggers rule1
            'ambiguity': 0.4    # Triggers rule2
        }

        results = engine.evaluate_all(decision_data)

        assert len(results) == 2
        triggered = [r for r in results if r.triggered]
        assert len(triggered) == 2

    def test_stop_on_critical(self):
        """Test stopping evaluation on critical rule trigger"""
        rules = [
            ThresholdRule(
                name="critical_rule",
                metric_path="value",
                threshold=0.5,
                operator=">",
                action=RuleAction.DENY,
                priority=RulePriority.CRITICAL
            ),
            ThresholdRule(
                name="normal_rule",
                metric_path="other_value",
                threshold=0.5,
                operator=">",
                action=RuleAction.WARN
            )
        ]

        engine = PolicyEngine(rules)

        decision_data = {
            'value': 0.9,        # Triggers critical
            'other_value': 0.8   # Would trigger normal
        }

        results = engine.evaluate_all(decision_data, stop_on_critical=True)

        # Should stop after critical rule
        assert len(results) == 1
        assert results[0].priority == RulePriority.CRITICAL

    def test_get_recommended_action(self):
        """Test getting recommended action from triggered rules"""
        rules = [
            ThresholdRule(
                name="deny_rule",
                metric_path="risk",
                threshold=0.8,
                operator=">",
                action=RuleAction.DENY
            ),
            ThresholdRule(
                name="review_rule",
                metric_path="confidence",
                threshold=0.6,
                operator="<",
                action=RuleAction.REVIEW
            )
        ]

        engine = PolicyEngine(rules)

        # DENY should take precedence
        decision_data = {
            'risk': 0.9,
            'confidence': 0.4
        }

        action = engine.get_recommended_action(decision_data)
        assert action == RuleAction.DENY

    def test_get_triggered_rules(self):
        """Test getting only triggered rules"""
        rules = [
            ThresholdRule(name="rule1", metric_path="a", threshold=0.5, operator=">"),
            ThresholdRule(name="rule2", metric_path="b", threshold=0.5, operator=">"),
            ThresholdRule(name="rule3", metric_path="c", threshold=0.5, operator=">"),
        ]

        engine = PolicyEngine(rules)

        decision_data = {
            'a': 0.7,  # Triggers
            'b': 0.3,  # Doesn't trigger
            'c': 0.8   # Triggers
        }

        triggered = engine.get_triggered_rules(decision_data)
        assert len(triggered) == 2
        assert all(r.triggered for r in triggered)


class TestComplianceChecker:
    """Tests for compliance checking functionality"""

    def test_compliance_checker_initialization(self):
        """Test compliance checker initialization"""
        checker = ComplianceChecker(
            jurisdiction="EU",
            applicable_standards=[ComplianceStandard.GDPR, ComplianceStandard.EU_AI_ACT]
        )

        assert checker.jurisdiction == "EU"
        assert len(checker.applicable_standards) == 2

    def test_gdpr_data_minimization(self):
        """Test GDPR data minimization check"""
        checker = ComplianceChecker(
            jurisdiction="EU",
            applicable_standards=[ComplianceStandard.GDPR]
        )

        # Violation: uses personal data without minimization
        decision_data = {
            'uses_personal_data': True,
            'data_minimization_applied': False
        }

        flags = checker.check_compliance(decision_data)

        assert flags.overall_status == ComplianceStatus.REQUIRES_REVIEW
        triggered = [f for f in flags.flags if f.requirement == "data_minimization"]
        assert len(triggered) > 0

    def test_gdpr_consent_requirement(self):
        """Test GDPR consent requirement"""
        checker = ComplianceChecker(
            jurisdiction="EU",
            applicable_standards=[ComplianceStandard.GDPR]
        )

        # Critical violation: consent required but not obtained
        decision_data = {
            'requires_consent': True,
            'user_consent_obtained': False
        }

        flags = checker.check_compliance(decision_data)

        assert flags.overall_status == ComplianceStatus.NON_COMPLIANT
        assert flags.has_critical_violations() is True

    def test_hipaa_phi_encryption(self):
        """Test HIPAA PHI encryption requirement"""
        checker = ComplianceChecker(
            jurisdiction="US",
            applicable_standards=[ComplianceStandard.HIPAA]
        )

        # Violation: PHI not encrypted
        decision_data = {
            'uses_protected_health_info': True,
            'data_encrypted': False
        }

        flags = checker.check_compliance(decision_data)

        assert flags.overall_status == ComplianceStatus.NON_COMPLIANT
        violations = flags.get_non_compliant_flags()
        assert any(f.requirement == "phi_encryption" for f in violations)

    def test_eu_ai_act_high_risk(self):
        """Test EU AI Act high-risk system requirements"""
        checker = ComplianceChecker(
            jurisdiction="EU",
            applicable_standards=[ComplianceStandard.EU_AI_ACT]
        )

        # High-risk AI without proper safeguards
        decision_data = {
            'is_high_risk_ai': True,
            'risk_management_system': False,
            'human_oversight_enabled': False
        }

        flags = checker.check_compliance(decision_data)

        assert flags.overall_status == ComplianceStatus.NON_COMPLIANT
        violations = flags.get_non_compliant_flags()
        assert len(violations) >= 1  # Should have multiple violations

    def test_fcra_adverse_action_notice(self):
        """Test FCRA adverse action notice requirement"""
        checker = ComplianceChecker(
            jurisdiction="US",
            applicable_standards=[ComplianceStandard.FCRA]
        )

        # Credit denial without adverse action notice
        decision_data = {
            'is_credit_decision': True,
            'overall_verdict': 'DENY',
            'adverse_action_notice': False
        }

        flags = checker.check_compliance(decision_data)

        violations = flags.get_non_compliant_flags()
        assert any(f.requirement == "adverse_action_notice" for f in violations)

    def test_compliance_flags_operations(self):
        """Test ComplianceFlags operations"""
        flags = ComplianceFlags(jurisdiction="US")

        # Add flags
        flag1 = ComplianceFlag(
            standard=ComplianceStandard.GDPR,
            requirement="test_req",
            triggered=True,
            status=ComplianceStatus.NON_COMPLIANT,
            risk_level=RiskLevel.HIGH
        )

        flags.add_flag(flag1)

        assert len(flags.flags) == 1
        assert ComplianceStandard.GDPR in flags.applicable_standards

        # Test filtering
        triggered = flags.get_triggered_flags()
        assert len(triggered) == 1

        non_compliant = flags.get_non_compliant_flags()
        assert len(non_compliant) == 1

    def test_critical_violations_detection(self):
        """Test detection of critical violations"""
        flags = ComplianceFlags()

        # Add critical violation
        flags.add_flag(ComplianceFlag(
            standard=ComplianceStandard.HIPAA,
            requirement="critical_test",
            triggered=True,
            status=ComplianceStatus.NON_COMPLIANT,
            risk_level=RiskLevel.CRITICAL
        ))

        assert flags.has_critical_violations() is True
        assert flags.requires_human_review is True


class TestPolicyOutcomeFormatter:
    """Tests for policy outcome formatting"""

    def test_format_policy_results_basic(self):
        """Test basic policy results formatting"""
        formatter = PolicyOutcomeFormatter()

        results = [
            PolicyRuleResult(
                rule_name="test_rule",
                triggered=True,
                action=RuleAction.REVIEW,
                priority=RulePriority.HIGH,
                reason="Test reason"
            )
        ]

        output = formatter.format_policy_results(results)

        assert 'policy_evaluation' in output
        assert output['policy_evaluation']['recommended_action'] == 'REVIEW'
        assert output['policy_evaluation']['rules_triggered'] == 1

    def test_format_compliance_report(self):
        """Test compliance report formatting"""
        formatter = PolicyOutcomeFormatter()

        flags = ComplianceFlags(jurisdiction="US")
        flags.add_flag(ComplianceFlag(
            standard=ComplianceStandard.GDPR,
            requirement="test",
            triggered=True,
            status=ComplianceStatus.COMPLIANT
        ))

        report = formatter.format_compliance_report(flags)

        assert 'compliance_report' in report
        assert report['compliance_report']['jurisdiction'] == 'US'
        assert report['compliance_report']['overall_status'] == 'compliant'

    def test_format_combined_outcome(self):
        """Test combined policy and compliance formatting"""
        formatter = PolicyOutcomeFormatter()

        rule_results = [
            PolicyRuleResult(
                rule_name="test",
                triggered=True,
                action=RuleAction.ALLOW,
                priority=RulePriority.MEDIUM,
                reason="OK"
            )
        ]

        flags = ComplianceFlags()
        decision_data = {'request_id': 'test-001'}

        combined = formatter.format_combined_outcome(
            rule_results,
            flags,
            decision_data
        )

        assert 'governance_outcome' in combined
        assert 'policy_evaluation' in combined['governance_outcome']
        assert 'compliance_report' in combined['governance_outcome']
        assert 'executive_summary' in combined['governance_outcome']

    def test_format_human_readable(self):
        """Test human-readable formatting"""
        formatter = PolicyOutcomeFormatter()

        results = [
            PolicyRuleResult(
                rule_name="critical_test",
                triggered=True,
                action=RuleAction.DENY,
                priority=RulePriority.CRITICAL,
                reason="Critical issue detected"
            )
        ]

        text = formatter.format_human_readable(results)

        assert "POLICY EVALUATION REPORT" in text
        assert "CRITICAL" in text
        assert "DENY" in text

    def test_export_to_json(self):
        """Test JSON export"""
        formatter = PolicyOutcomeFormatter()

        data = {'test': 'value'}
        json_str = formatter.export_to_json(data, pretty=True)

        assert '"test"' in json_str
        assert '"value"' in json_str

    def test_convenience_functions(self):
        """Test convenience formatting functions"""
        results = [
            PolicyRuleResult(
                rule_name="test",
                triggered=False,
                priority=RulePriority.LOW,
                reason=""
            )
        ]

        # Test format_policy_decision
        output = format_policy_decision(results)
        assert 'policy_evaluation' in output

        # Test format_compliance_check
        flags = ComplianceFlags()
        report = format_compliance_check(flags)
        assert 'compliance_report' in report


class TestPolicyEngineIntegration:
    """Integration tests for complete policy engine workflow"""

    def test_end_to_end_policy_enforcement(self):
        """Test complete policy enforcement workflow"""
        # Create policy engine with multiple rules
        engine = PolicyEngine([
            create_confidence_threshold_rule(threshold=0.7),
            create_ambiguity_threshold_rule(threshold=0.3),
            create_error_rate_threshold_rule(threshold=0.2)
        ])

        # Decision data that triggers some rules
        decision_data = {
            'avg_confidence': 0.6,  # Triggers confidence rule
            'ambiguity': 0.15,      # OK
            'errors': {'rate': 0.35}  # Triggers error rate rule
        }

        # Evaluate
        results = engine.evaluate_all(decision_data)
        triggered = [r for r in results if r.triggered]

        assert len(triggered) == 2  # confidence and error_rate

        # Get recommendation
        action = engine.get_recommended_action(decision_data)
        assert action in [RuleAction.REVIEW, RuleAction.ESCALATE]

        # Format results
        formatter = PolicyOutcomeFormatter()
        output = formatter.format_policy_results(results, decision_data)

        assert output['policy_evaluation']['rules_triggered'] == 2

    def test_end_to_end_compliance_check(self):
        """Test complete compliance checking workflow"""
        # Create checker
        checker = ComplianceChecker(
            jurisdiction="US",
            applicable_standards=[
                ComplianceStandard.GDPR,
                ComplianceStandard.HIPAA
            ]
        )

        # Decision with compliance issues
        decision_data = {
            'uses_personal_data': True,
            'data_minimization_applied': True,
            'requires_consent': True,
            'user_consent_obtained': True,
            'uses_protected_health_info': True,
            'data_encrypted': False,  # HIPAA violation
            'access_controls_enabled': True
        }

        # Check compliance
        flags = checker.check_compliance(decision_data)

        assert flags.overall_status == ComplianceStatus.NON_COMPLIANT
        violations = flags.get_non_compliant_flags()
        assert len(violations) > 0

        # Format report
        formatter = PolicyOutcomeFormatter()
        report = formatter.format_compliance_report(flags)

        assert len(report['compliance_report']['violations']) > 0
