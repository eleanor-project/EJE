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

    def test_threshold_failures_integration(self):
        """Test integration scenario with multiple threshold failures"""
        # Create engine with multiple threshold rules
        engine = PolicyEngine([
            ThresholdRule(
                name="min_confidence",
                metric_path="avg_confidence",
                threshold=0.8,
                operator="<",
                action=RuleAction.REVIEW,
                priority=RulePriority.HIGH
            ),
            ThresholdRule(
                name="max_ambiguity",
                metric_path="ambiguity",
                threshold=0.2,
                operator=">",
                action=RuleAction.ESCALATE,
                priority=RulePriority.HIGH
            ),
            ThresholdRule(
                name="min_critics",
                metric_path="critic_count",
                threshold=3,
                operator="<",
                action=RuleAction.REVIEW,
                priority=RulePriority.MEDIUM
            )
        ])

        # Decision data that fails all thresholds
        decision_data = {
            'avg_confidence': 0.5,  # Below 0.8 - fails
            'ambiguity': 0.4,       # Above 0.2 - fails
            'critic_count': 2       # Below 3 - fails
        }

        # Evaluate all rules
        results = engine.evaluate_all(decision_data, stop_on_critical=False)
        triggered = [r for r in results if r.triggered]

        # All 3 rules should trigger
        assert len(triggered) == 3
        assert all(r.triggered for r in triggered)

        # Verify each rule has proper metadata
        for result in triggered:
            assert result.reason != ""
            assert 'metric_value' in result.metadata or 'threshold' in result.metadata

        # Get recommended action (ESCALATE should win)
        action = engine.get_recommended_action(decision_data)
        assert action == RuleAction.ESCALATE

        # Format results
        formatter = PolicyOutcomeFormatter(verbose=True)
        output = formatter.format_policy_results(results, decision_data)

        assert output['policy_evaluation']['rules_triggered'] == 3
        assert output['policy_evaluation']['recommended_action'] == 'ESCALATE'
        assert 'decision_context' in output['policy_evaluation']

    def test_rule_conflicts_integration(self):
        """Test integration scenario with conflicting rule recommendations"""
        # Create rules with different priority levels and conflicting actions
        engine = PolicyEngine([
            ThresholdRule(
                name="critical_deny",
                metric_path="risk_score",
                threshold=0.9,
                operator=">",
                action=RuleAction.DENY,
                priority=RulePriority.CRITICAL
            ),
            ThresholdRule(
                name="high_review",
                metric_path="confidence",
                threshold=0.7,
                operator="<",
                action=RuleAction.REVIEW,
                priority=RulePriority.HIGH
            ),
            ThresholdRule(
                name="medium_warn",
                metric_path="ambiguity",
                threshold=0.3,
                operator=">",
                action=RuleAction.WARN,
                priority=RulePriority.MEDIUM
            )
        ])

        # Decision data that triggers all rules
        decision_data = {
            'risk_score': 0.95,  # Triggers DENY
            'confidence': 0.6,   # Triggers REVIEW
            'ambiguity': 0.4     # Triggers WARN
        }

        # Evaluate - should stop on critical
        results_stop = engine.evaluate_all(decision_data, stop_on_critical=True)
        assert len(results_stop) == 1  # Only critical rule evaluated
        assert results_stop[0].priority == RulePriority.CRITICAL

        # Evaluate without stop - all should trigger
        results_all = engine.evaluate_all(decision_data, stop_on_critical=False)
        triggered = [r for r in results_all if r.triggered]
        assert len(triggered) == 3

        # DENY should be recommended (highest priority)
        action = engine.get_recommended_action(decision_data)
        assert action == RuleAction.DENY

        # Format and verify
        formatter = PolicyOutcomeFormatter()
        output = formatter.format_policy_results(results_all, decision_data)

        assert output['policy_evaluation']['recommended_action'] == 'DENY'
        # Verify critical rule is first in triggered list
        assert output['policy_evaluation']['triggered_rules'][0]['priority'] == 'critical'

    def test_complete_workflow_all_components(self):
        """Test complete workflow integrating rules, compliance, and formatting"""
        # Step 1: Create policy engine with rules
        engine = PolicyEngine([
            create_confidence_threshold_rule(threshold=0.75),
            create_ambiguity_threshold_rule(threshold=0.25)
        ])

        # Step 2: Create compliance checker
        checker = ComplianceChecker(
            jurisdiction="EU",
            applicable_standards=[
                ComplianceStandard.GDPR,
                ComplianceStandard.EU_AI_ACT
            ]
        )

        # Step 3: Decision data with both policy and compliance issues
        decision_data = {
            'avg_confidence': 0.65,  # Below threshold
            'ambiguity': 0.3,        # Above threshold
            'request_id': 'test-123',
            # GDPR-related
            'uses_personal_data': True,
            'data_minimization_applied': False,  # GDPR issue
            'requires_consent': True,
            'user_consent_obtained': True,
            'is_automated_decision': True,
            'explanation_available': True,
            # EU AI Act-related
            'is_high_risk_ai': True,
            'risk_management_system': False,  # Violation
            'human_oversight_enabled': True
        }

        # Step 4: Evaluate policy rules
        rule_results = engine.evaluate_all(decision_data)
        triggered_rules = [r for r in rule_results if r.triggered]
        assert len(triggered_rules) == 2  # confidence and ambiguity

        # Step 5: Check compliance
        compliance_flags = checker.check_compliance(decision_data)
        assert compliance_flags.overall_status == ComplianceStatus.NON_COMPLIANT
        violations = compliance_flags.get_non_compliant_flags()
        assert len(violations) >= 1

        # Step 6: Format combined outcome
        formatter = PolicyOutcomeFormatter(include_metadata=True, verbose=True)
        combined_outcome = formatter.format_combined_outcome(
            rule_results,
            compliance_flags,
            decision_data
        )

        # Verify combined outcome structure
        assert 'governance_outcome' in combined_outcome
        gov = combined_outcome['governance_outcome']

        assert 'final_action' in gov
        assert 'policy_evaluation' in gov
        assert 'compliance_report' in gov
        assert 'executive_summary' in gov
        assert 'requires_human_review' in gov

        # Final action should be DENY due to compliance violation
        assert gov['final_action'] == 'DENY'
        assert gov['requires_human_review'] is True

        # Verify executive summary is present
        assert 'compliance violation' in gov['executive_summary'].lower()

    def test_explainability_output_integration(self):
        """Test explainability and human-readable formatting"""
        # Create rules
        engine = PolicyEngine([
            ThresholdRule(
                name="confidence_check",
                metric_path="confidence",
                threshold=0.8,
                operator="<",
                action=RuleAction.REVIEW,
                priority=RulePriority.HIGH,
                custom_reason="Confidence is too low for automated decision"
            ),
            ThresholdRule(
                name="error_check",
                metric_path="error_rate",
                threshold=0.1,
                operator=">",
                action=RuleAction.ESCALATE,
                priority=RulePriority.CRITICAL,
                custom_reason="Error rate exceeds acceptable threshold"
            )
        ])

        # Decision data triggering both rules
        decision_data = {
            'confidence': 0.6,
            'error_rate': 0.15
        }

        # Evaluate
        results = engine.evaluate_all(decision_data, stop_on_critical=False)

        # Create compliance flags
        compliance_flags = ComplianceFlags(jurisdiction="US")
        compliance_flags.add_flag(ComplianceFlag(
            standard=ComplianceStandard.FCRA,
            requirement="adverse_action_notice",
            triggered=True,
            status=ComplianceStatus.REQUIRES_REVIEW,
            risk_level=RiskLevel.HIGH,
            reason="Denial requires adverse action notice under FCRA"
        ))

        # Test human-readable formatting
        formatter = PolicyOutcomeFormatter()
        human_readable = formatter.format_human_readable(results, compliance_flags)

        # Verify human-readable output contains key information
        assert "POLICY EVALUATION REPORT" in human_readable
        assert "TRIGGERED RULES" in human_readable
        assert "COMPLIANCE STATUS" in human_readable
        assert "confidence_check" in human_readable
        assert "error_check" in human_readable
        assert "CRITICAL" in human_readable
        assert "REQUIRES_REVIEW" in human_readable  # Compliance status should be present

        # Test JSON formatting
        json_output = formatter.format_policy_results(results, decision_data)
        json_str = formatter.export_to_json(json_output, pretty=True)

        assert '"policy_evaluation"' in json_str
        assert '"triggered_rules"' in json_str
        assert 'Confidence is too low' in json_str

    def test_edge_cases_integration(self):
        """Test edge cases and error handling in integration"""
        # Test 1: Empty rules - should pass
        engine = PolicyEngine([])
        results = engine.evaluate_all({'test': 'data'})
        assert len(results) == 0

        action = engine.get_recommended_action({'test': 'data'})
        assert action == RuleAction.ALLOW

        # Test 2: Missing metrics - rules should handle gracefully
        engine = PolicyEngine([
            ThresholdRule(
                name="missing_metric",
                metric_path="nonexistent.field",
                threshold=0.5,
                operator=">"
            )
        ])

        results = engine.evaluate_all({'other_field': 0.9})
        assert len(results) == 1
        assert results[0].triggered is False
        assert "not found" in results[0].reason.lower()

        # Test 3: Disabled rules - should not trigger
        rule = ThresholdRule(
            name="disabled",
            metric_path="value",
            threshold=0.5,
            operator=">",
            enabled=False
        )
        engine = PolicyEngine([rule])

        results = engine.evaluate_all({'value': 0.9})
        assert len(results) == 1
        assert results[0].triggered is False

        # Test 4: Lambda rule integration
        engine = PolicyEngine([
            LambdaRule(
                name="custom_check",
                evaluator=lambda data: data.get('status') == 'BLOCKED',
                action=RuleAction.DENY,
                reason_generator=lambda data: f"Status is {data.get('status')}",
                priority=RulePriority.HIGH
            )
        ])

        results = engine.evaluate_all({'status': 'BLOCKED'})
        assert len(results) == 1
        assert results[0].triggered is True
        assert 'BLOCKED' in results[0].reason

    def test_compliance_and_policy_combined_scenarios(self):
        """Test various combined policy and compliance scenarios"""
        # Scenario 1: Policy passes, compliance fails
        engine = PolicyEngine([
            create_confidence_threshold_rule(threshold=0.6)
        ])

        checker = ComplianceChecker(
            jurisdiction="US",
            applicable_standards=[ComplianceStandard.HIPAA]
        )

        decision_data = {
            'avg_confidence': 0.9,  # Policy OK
            'uses_protected_health_info': True,
            'data_encrypted': False  # Compliance violation
        }

        rule_results = engine.evaluate_all(decision_data)
        compliance_flags = checker.check_compliance(decision_data)

        triggered_rules = [r for r in rule_results if r.triggered]
        assert len(triggered_rules) == 0  # No policy violations
        assert compliance_flags.overall_status == ComplianceStatus.NON_COMPLIANT

        formatter = PolicyOutcomeFormatter()
        outcome = formatter.format_combined_outcome(rule_results, compliance_flags, decision_data)

        # Final action should be DENY due to compliance
        assert outcome['governance_outcome']['final_action'] == 'DENY'

        # Scenario 2: Policy fails, compliance passes
        decision_data2 = {
            'avg_confidence': 0.4,  # Policy violation
            'uses_protected_health_info': True,
            'data_encrypted': True,  # Compliance OK
            'access_controls_enabled': True
        }

        rule_results2 = engine.evaluate_all(decision_data2)
        compliance_flags2 = checker.check_compliance(decision_data2)

        triggered_rules2 = [r for r in rule_results2 if r.triggered]
        assert len(triggered_rules2) == 1  # Policy violation
        assert compliance_flags2.overall_status == ComplianceStatus.COMPLIANT

        outcome2 = formatter.format_combined_outcome(rule_results2, compliance_flags2, decision_data2)

        # Final action should be REVIEW (from policy)
        assert outcome2['governance_outcome']['final_action'] == 'REVIEW'

        # Scenario 3: Both pass
        decision_data3 = {
            'avg_confidence': 0.9,  # Policy OK
            'uses_protected_health_info': True,
            'data_encrypted': True,  # Compliance OK
            'access_controls_enabled': True
        }

        rule_results3 = engine.evaluate_all(decision_data3)
        compliance_flags3 = checker.check_compliance(decision_data3)

        triggered_rules3 = [r for r in rule_results3 if r.triggered]
        assert len(triggered_rules3) == 0
        assert compliance_flags3.overall_status == ComplianceStatus.COMPLIANT

        outcome3 = formatter.format_combined_outcome(rule_results3, compliance_flags3, decision_data3)

        # Final action should be ALLOW
        assert outcome3['governance_outcome']['final_action'] == 'ALLOW'

    def test_multi_jurisdiction_compliance_integration(self):
        """Test compliance checks across multiple jurisdictions"""
        # EU jurisdiction with strict requirements
        eu_checker = ComplianceChecker(
            jurisdiction="EU",
            applicable_standards=[
                ComplianceStandard.GDPR,
                ComplianceStandard.EU_AI_ACT
            ]
        )

        # US jurisdiction
        us_checker = ComplianceChecker(
            jurisdiction="US",
            applicable_standards=[
                ComplianceStandard.HIPAA,
                ComplianceStandard.FCRA
            ]
        )

        # Decision data
        decision_data = {
            'request_id': 'multi-jurisdic-001',
            # GDPR
            'uses_personal_data': True,
            'data_minimization_applied': True,
            'requires_consent': True,
            'user_consent_obtained': True,
            'is_automated_decision': True,
            'explanation_available': True,
            # EU AI Act
            'is_high_risk_ai': True,
            'risk_management_system': True,
            'human_oversight_enabled': True,
            # HIPAA
            'uses_protected_health_info': True,
            'data_encrypted': True,
            'access_controls_enabled': True,
            # FCRA
            'is_credit_decision': False
        }

        # Check EU compliance
        eu_flags = eu_checker.check_compliance(decision_data)
        assert eu_flags.overall_status == ComplianceStatus.COMPLIANT
        assert ComplianceStandard.GDPR in eu_flags.applicable_standards
        assert ComplianceStandard.EU_AI_ACT in eu_flags.applicable_standards

        # Check US compliance
        us_flags = us_checker.check_compliance(decision_data)
        assert us_flags.overall_status == ComplianceStatus.COMPLIANT
        assert ComplianceStandard.HIPAA in us_flags.applicable_standards

        # Format both reports
        formatter = PolicyOutcomeFormatter()
        eu_report = formatter.format_compliance_report(eu_flags, decision_data)
        us_report = formatter.format_compliance_report(us_flags, decision_data)

        assert eu_report['compliance_report']['jurisdiction'] == 'EU'
        assert us_report['compliance_report']['jurisdiction'] == 'US'
        assert len(eu_report['compliance_report']['violations']) == 0
        assert len(us_report['compliance_report']['violations']) == 0
