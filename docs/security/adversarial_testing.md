# Automated Adversarial Testing Documentation

## Overview

The Automated Adversarial Testing System provides continuous security validation for EJE through systematic attack execution, result analysis, regression detection, and CI/CD integration.

**Implements**: Issue #174 - Implement Automated Adversarial Testing

---

## Quick Start

### Basic Usage

```python
from src.ejc.security import AdversarialTestRunner
from src.ejc.core.decision_engine import EJEDecisionEngine

# Initialize system under test
system = EJEDecisionEngine()

# Create test runner
runner = AdversarialTestRunner(system_under_test=system)

# Run full test suite
results = runner.run_full_suite()

# Print summary
print(f"Total Tests: {results.total_tests}")
print(f"Passed: {results.passed}")
print(f"Failed: {results.failed}")
print(f"Pass Rate: {results.pass_rate:.1%}")
```

### CI/CD Integration

```python
from src.ejc.security import CICDIntegration

# Run in CI pipeline
exit_code = CICDIntegration.run_ci_tests(system)
# Exit codes: 0 = success, 1 = failures, 2 = blocking failures
```

---

## Core Components

### AdversarialTestRunner

Main class for automated adversarial testing.

**Initialization**:

```python
runner = AdversarialTestRunner(
    system_under_test=my_system,          # Required: system to test
    attack_library=None,                   # Optional: custom attack library
    enable_regression_detection=True,      # Optional: enable regression checking
    results_directory='./test_results'     # Optional: results storage path
)
```

### Test Execution Methods

#### Full Test Suite

```python
results = runner.run_full_suite(
    suite_name="Full Adversarial Test Suite",
    fail_fast=False,  # Stop on first blocking failure
    parallel=False    # Parallel execution (future)
)
```

Runs all 52+ attack patterns against the system.

**Use Case**: Nightly builds, comprehensive security audits

**Execution Time**: ~5-10 seconds

#### Critical Tests Only

```python
results = runner.run_critical_tests()
```

Runs only CRITICAL severity attacks for fast feedback.

**Use Case**: CI pipelines, pre-merge checks

**Execution Time**: ~1-2 seconds

#### High Severity Tests

```python
results = runner.run_high_severity_tests()
```

Runs CRITICAL and HIGH severity attacks.

**Use Case**: Pull request validation

**Execution Time**: ~2-4 seconds

#### Category-Specific Tests

```python
from src.ejc.security import AttackCategory

# Test specific category
results = runner.run_category_tests(AttackCategory.PROMPT_INJECTION)
```

**Available Categories**:
- `PROMPT_INJECTION` - Prompt injection attacks
- `INPUT_MANIPULATION` - Input validation attacks
- `BIAS_EXPLOITATION` - Fairness and bias attacks
- `BOUNDARY_CONDITIONS` - Edge case attacks
- `MALFORMED_INPUT` - Malformed data attacks

#### Regression Tests

```python
results = runner.run_regression_tests()
```

Runs only tests that previously passed to detect regressions.

**Use Case**: Post-deployment validation, continuous monitoring

---

## Result Analysis

### TestResult Structure

```python
TestResult(
    test_name="Test SQL Injection",           # Test name
    attack_pattern="SQL Injection",           # Attack pattern used
    category="input_manipulation",            # Attack category
    severity="critical",                      # Severity level
    status=TestStatus.PASSED,                 # Test status
    execution_time_ms=10.5,                   # Execution time
    timestamp="2024-01-01T00:00:00",         # Timestamp
    error_message=None,                       # Error if failed
    attack_succeeded=False,                   # Did attack succeed?
    system_response={'result': 'processed'},  # System response
    mitigation_suggested=None                 # Mitigation if vulnerable
)
```

### TestStatus Enum

- `PASSED` - System defended successfully (attack failed)
- `FAILED` - System vulnerable (attack succeeded)
- `ERROR` - Test execution error
- `SKIPPED` - Test skipped
- `BLOCKED` - CI blocking failure

### TestSuiteResult

```python
suite_result = TestSuiteResult(
    suite_name="Test Suite",
    total_tests=52,
    passed=48,
    failed=3,
    errors=1,
    skipped=0,
    execution_time_ms=5000.0,
    timestamp="2024-01-01T00:00:00",
    test_results=[...],                    # List of TestResult objects
    blocking_failures=["SQL Injection"],   # Critical failures
    regressions=["XSS Attack"]             # New vulnerabilities
)

# Computed properties
print(suite_result.pass_rate)              # 0.923 (92.3%)
print(suite_result.has_blocking_failures)  # True
```

---

## Blocking Failures

Tests that **block CI deployment** if they fail:

1. **CRITICAL severity** attacks that succeed
2. **HIGH severity** attacks that succeed

**Examples**:
- SQL Injection
- Command Injection
- Protected Attribute Exploitation
- Direct Instruction Override

**CI Behavior**:
```python
if results.has_blocking_failures:
    print("⚠️  DEPLOYMENT BLOCKED")
    for failure in results.blocking_failures:
        print(f"  - {failure}")
    exit(2)  # Blocking exit code
```

---

## Regression Detection

Automatically detects when previously passing tests now fail.

**How it Works**:
1. Stores historical test results
2. Compares current run to previous runs
3. Identifies tests that changed from PASSED → FAILED

**Example**:

```python
runner = AdversarialTestRunner(
    system_under_test=system,
    enable_regression_detection=True
)

results = runner.run_full_suite()

if results.regressions:
    print(f"⚠️  {len(results.regressions)} REGRESSIONS DETECTED:")
    for regression in results.regressions:
        print(f"  - {regression}")
```

---

## Historical Trends

Track security posture over time:

```python
trends = runner.get_historical_trends()

print(f"Total Runs: {trends['total_runs']}")
print(f"Current Pass Rate: {trends['current_pass_rate']:.1%}")
print(f"Average Pass Rate: {trends['average_pass_rate']:.1%}")
print(f"Best: {trends['best_pass_rate']:.1%}")
print(f"Worst: {trends['worst_pass_rate']:.1%}")
print(f"Trend: {trends['trend']}")  # improving/declining/stable
```

**Trend Values**:
- `improving` - Pass rate increasing
- `declining` - Pass rate decreasing
- `stable` - Pass rate unchanged
- `insufficient_data` - Need more runs

---

## CI/CD Integration

### GitHub Actions

Complete workflow provided in `.github/workflows/adversarial-testing.yml`:

```yaml
name: Adversarial Security Testing

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'  # Nightly at 2 AM

jobs:
  adversarial-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Critical Tests
        run: python -m src.ejc.security.ci_runner
```

### CI Test Runner

```python
from src.ejc.security import CICDIntegration

# Returns exit code: 0, 1, or 2
exit_code = CICDIntegration.run_ci_tests(system)
```

**Exit Codes**:
- `0` - All tests passed
- `1` - Some tests failed (non-blocking)
- `2` - Blocking failures detected

### Nightly Tests

```python
results = CICDIntegration.run_nightly_tests(system)
# Runs full 52+ pattern suite
```

### Weekly Tests

```python
results = CICDIntegration.run_weekly_tests(system)
# Full suite + historical trend analysis
```

---

## Test Suites by Use Case

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

python -c "
from src.ejc.security import CICDIntegration
from src.ejc.core.decision_engine import EJEDecisionEngine

system = EJEDecisionEngine()
exit_code = CICDIntegration.run_ci_tests(system)
exit(exit_code)
"
```

### Pull Request Validation

```python
# Run high-severity tests
runner = AdversarialTestRunner(system)
results = runner.run_high_severity_tests()

if results.has_blocking_failures:
    print("❌ PR blocked due to security vulnerabilities")
    sys.exit(1)
```

### Nightly Build

```python
# Full comprehensive suite
results = CICDIntegration.run_nightly_tests(system)

# Email report if pass rate < 95%
if results.pass_rate < 0.95:
    send_alert_email(results)
```

### Weekly Security Audit

```python
results = CICDIntegration.run_weekly_tests(system)

# Generate PDF report
generate_security_report(results)
```

---

## Results Storage

### File Structure

```
test_results/
├── adversarial_test_results_20240101_120000.json
├── adversarial_test_results_20240102_120000.json
├── adversarial_test_results_20240103_120000.json
└── latest_results.json
```

### Result Format

```json
{
  "suite_name": "Full Adversarial Test Suite",
  "total_tests": 52,
  "passed": 48,
  "failed": 3,
  "errors": 1,
  "skipped": 0,
  "pass_rate": 0.923,
  "execution_time_ms": 5234.5,
  "timestamp": "2024-01-01T12:00:00",
  "blocking_failures": ["SQL Injection"],
  "regressions": ["XSS Attack"],
  "test_results": [
    {
      "test_name": "Test SQL Injection",
      "status": "failed",
      "severity": "critical",
      "execution_time_ms": 12.3
    }
  ]
}
```

---

## Performance Optimization

### Fail-Fast Mode

Stop on first blocking failure (faster feedback):

```python
results = runner.run_full_suite(fail_fast=True)
```

### Parallel Execution

*(Future enhancement)*

```python
results = runner.run_full_suite(parallel=True)
```

### Selective Testing

Run only relevant categories:

```python
# Test only input validation for API changes
results = runner.run_category_tests(AttackCategory.INPUT_MANIPULATION)
```

---

## Best Practices

### 1. Layer Your Testing

```python
# Fast: Pre-commit hook (< 2s)
runner.run_critical_tests()

# Medium: CI/PR validation (< 5s)
runner.run_high_severity_tests()

# Slow: Nightly (10s)
runner.run_full_suite()
```

### 2. Monitor Trends

```python
# Weekly review
trends = runner.get_historical_trends()
if trends['trend'] == 'declining':
    alert_security_team()
```

### 3. Act on Regressions

```python
results = runner.run_regression_tests()
if results.regressions:
    # Block deployment
    raise SecurityRegressionError(results.regressions)
```

### 4. Set Pass Rate Thresholds

```python
MINIMUM_PASS_RATE = 0.95  # 95%

results = runner.run_full_suite()
if results.pass_rate < MINIMUM_PASS_RATE:
    print(f"⚠️  Pass rate {results.pass_rate:.1%} below threshold")
    sys.exit(1)
```

### 5. Customize for Your Domain

```python
# Add domain-specific patterns
custom_pattern = AttackPattern(...)
runner.attack_library.add_pattern(custom_pattern)

# Run domain-specific suite
results = runner.run_category_tests(AttackCategory.BIAS_EXPLOITATION)
```

---

## Troubleshooting

### Tests Always Passing

```python
# Verify system is actually being tested
class DebugSystem:
    def process(self, input_data):
        print(f"Processing: {input_data}")
        return {'result': 'processed'}

runner = AdversarialTestRunner(DebugSystem())
results = runner.run_critical_tests()
```

### High False Positive Rate

```python
# Review specific failures
for result in results.test_results:
    if result.status == TestStatus.FAILED:
        print(f"Failed: {result.attack_pattern}")
        print(f"  Severity: {result.severity}")
        print(f"  Response: {result.system_response}")
```

### Regressions Not Detected

```python
# Ensure historical results exist
trends = runner.get_historical_trends()
print(f"Historical runs: {trends['total_runs']}")

# Need at least 2 runs for regression detection
```

### Slow Execution

```python
# Use smaller test suites
runner.run_critical_tests()  # Instead of run_full_suite()

# Or fail-fast mode
runner.run_full_suite(fail_fast=True)
```

---

## Examples

### Complete CI Pipeline

```python
#!/usr/bin/env python3
"""
CI adversarial testing script
"""
import sys
from src.ejc.security import CICDIntegration
from src.ejc.core.decision_engine import EJEDecisionEngine

def main():
    system = EJEDecisionEngine()

    print("Running adversarial security tests...")
    exit_code = CICDIntegration.run_ci_tests(system)

    if exit_code == 0:
        print("✓ All tests passed")
    elif exit_code == 1:
        print("⚠️  Some tests failed")
    else:  # exit_code == 2
        print("❌ BLOCKING FAILURES - deployment blocked")

    return exit_code

if __name__ == '__main__':
    sys.exit(main())
```

### Scheduled Nightly Tests

```python
#!/usr/bin/env python3
"""
Nightly comprehensive adversarial testing
"""
from src.ejc.security import CICDIntegration, AdversarialTestRunner
from src.ejc.core.decision_engine import EJEDecisionEngine
import smtplib
from email.mime.text import MIMEText

def send_report(results):
    """Send email report."""
    msg = MIMEText(f"""
    Nightly Adversarial Test Report

    Total Tests: {results.total_tests}
    Passed: {results.passed}
    Failed: {results.failed}
    Pass Rate: {results.pass_rate:.1%}

    Blocking Failures: {len(results.blocking_failures)}
    Regressions: {len(results.regressions)}
    """)

    msg['Subject'] = f'Nightly Security Test Report - {results.pass_rate:.1%} Pass Rate'
    msg['From'] = 'security@example.com'
    msg['To'] = 'team@example.com'

    # Send email (configure SMTP)
    # smtp.send_message(msg)

def main():
    system = EJEDecisionEngine()
    results = CICDIntegration.run_nightly_tests(system)

    # Send report
    send_report(results)

    # Fail if pass rate too low
    if results.pass_rate < 0.95:
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
```

---

## Metrics & Reporting

### Key Metrics

- **Pass Rate**: `passed / total_tests`
- **Blocking Failure Count**: Number of critical/high failures
- **Regression Count**: New vulnerabilities introduced
- **Execution Time**: Time to run test suite
- **Historical Trend**: improving/declining/stable

### Reporting

```python
def generate_report(results, trends):
    """Generate security report."""
    report = f"""
    === Adversarial Test Report ===

    Suite: {results.suite_name}
    Timestamp: {results.timestamp}

    RESULTS:
      Total Tests: {results.total_tests}
      Passed: {results.passed} ✓
      Failed: {results.failed} ✗
      Errors: {results.errors}
      Pass Rate: {results.pass_rate:.1%}

    CRITICAL ISSUES:
      Blocking Failures: {len(results.blocking_failures)}
      Regressions: {len(results.regressions)}

    HISTORICAL TRENDS:
      Total Runs: {trends['total_runs']}
      Average Pass Rate: {trends['average_pass_rate']:.1%}
      Trend: {trends['trend']}

    EXECUTION:
      Time: {results.execution_time_ms:.0f}ms
      Tests/sec: {results.total_tests / (results.execution_time_ms / 1000):.1f}
    """

    return report
```

---

## Next Steps

After implementing automated testing:

1. **Robustness Scoring** (Issue #175): Quantify security metrics
2. **Red Team Daemon** (Issue #176): Continuous background testing
3. **Failure Mode Catalog** (Issue #177): Document all attack results

---

## References

- [Attack Pattern Library Documentation](./attack_pattern_library.md)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [CI/CD Best Practices](../development/cicd.md)

---

**Version**: 1.0
**Last Updated**: 2025-12-02
**Maintainer**: EJE Security Team
