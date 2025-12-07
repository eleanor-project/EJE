# EJC Adversarial Testing Framework

Comprehensive security, bias, and robustness testing for the Ethical Jurisprudence Core.

## Overview

The EJC Adversarial Testing Framework provides systematic validation against:
- **Security threats** - Prompt injection, context poisoning
- **Bias issues** - Systematic discrimination, fairness violations
- **Robustness failures** - Malformed input, boundary conditions

## Quick Start

### Python API

```python
from ejc.testing import run_all_tests
from ejc import EJC

# Initialize your EJC instance
ejc = EJC()

# Run all tests
results = run_all_tests(ejc, output_path="test_report.txt")

# Check results
print(f"Tests run: {results['total_tests']}")
print(f"Pass rate: {results['passed']/results['total_tests']*100:.1f}%")

if results['failed'] > 0:
    print("⚠️  Some tests failed!")
```

### CLI

```bash
# Run all tests
python -m ejc.testing.cli run-all

# Run specific suite
python -m ejc.testing.cli run-suite prompt_injection

# Run only critical tests
python -m ejc.testing.cli run-critical

# Generate JSON report
python -m ejc.testing.cli run-all --format json --output results.json

# List available suites
python -m ejc.testing.cli list-suites
```

## Test Suites

### Task 15.1 - Prompt Injection Suite (CRITICAL)

Tests resilience against adversarial prompts:

**Hidden Instructions:**
- System message hijacking
- Base64/hex encoded commands
- Delimiter injection
- Unicode tricks

**Role Hijacking:**
- Critic impersonation
- Aggregator manipulation
- Developer mode exploitation
- Privilege escalation

**Nested Structures:**
- Recursive injection
- JSON/template injection
- Nested prompt evaluation

```python
from ejc.testing import PromptInjectionSuite

suite = PromptInjectionSuite()
results = suite.run_all(ejc=ejc_instance)

# Check for critical failures
critical_failures = [r for r in results if not r.passed and r.is_critical]
if critical_failures:
    print("🚨 CRITICAL: Prompt injection vulnerabilities found!")
```

### Task 15.2 - Bias Probe Suite (HIGH)

Tests for systematic bias and fairness violations:

**Protected Attributes Tested:**
- Gender, race, age
- Religion, nationality
- Disability, sexual orientation

**Tests Performed:**
- Fairness across attribute values
- Demographic parity
- Intersectional bias
- Confidence disparities

```python
from ejc.testing import BiasProbeSuite

suite = BiasProbeSuite()
results = suite.run_all(ejc=ejc_instance)

# Check for bias
bias_failures = [r for r in results if not r.passed]
for failure in bias_failures:
    print(f"Bias detected: {failure.message}")
    print(f"Details: {failure.details}")
```

### Task 15.3 - Context Poisoning Suite (MEDIUM)

Tests resilience against poisoned context:

**Attack Vectors:**
- Contradictory metadata
- Conflicting precedent suggestions
- Malicious context injection
- Fabricated audit trails

```python
from ejc.testing import ContextPoisoningSuite

suite = ContextPoisoningSuite()
results = suite.run_all(ejc=ejc_instance)
```

### Task 15.4 - Malformed Input Suite (MEDIUM)

Tests handling of corrupted inputs:

**Tests:**
- Null values
- Empty strings
- Non-UTF8 encoding
- Missing required fields
- Invalid data types
- Special/control characters
- Deeply nested structures

```python
from ejc.testing import MalformedInputSuite

suite = MalformedInputSuite()
results = suite.run_all(ejc=ejc_instance)
```

### Task 15.5 - Boundary Suite (LOW)

Tests boundary conditions:

**Limits Tested:**
- Max input size (100KB)
- Max critic count (50)
- Max evidence depth (10 levels)

```python
from ejc.testing import BoundarySuite

suite = BoundarySuite()
results = suite.run_all(ejc=ejc_instance)
```

## Advanced Usage

### Custom Test Runner

```python
from ejc.testing import TestRunner, Severity

# Initialize runner
runner = TestRunner(ejc_instance=ejc)

# Run all tests
results = runner.run_all()

# Run specific suite
suite_results = runner.run_suite("prompt_injection")

# Run only critical tests
critical_results = runner.run_critical_only()

# Get summary
summary = runner.get_summary()
print(f"Critical failures: {summary['critical_failures']}")
print(f"High failures: {summary['high_failures']}")

# Generate report
report = runner.generate_report(format="text")
print(report)

# Save JSON report
json_report = runner.generate_report(
    format="json",
    output_path=Path("test_results.json")
)
```

### Creating Custom Tests

```python
from ejc.testing import TestSuite, TestResult, Severity

class CustomTestSuite(TestSuite):
    def __init__(self):
        super().__init__(
            name="Custom Security Tests",
            description="My custom security tests",
            category="security"
        )

        # Add custom test
        self.add_test(
            name="custom_security_check",
            description="Check for custom vulnerability",
            test_func=self._test_custom_security,
            severity=Severity.HIGH,
            tags=["custom", "security"],
        )

    def _test_custom_security(self, ejc=None, **kwargs) -> TestResult:
        """Custom security test."""
        if ejc is None:
            return TestResult(
                test_name="custom_security_check",
                passed=False,
                severity=Severity.HIGH,
                message="No EJC instance provided",
            )

        try:
            # Your test logic here
            result = ejc.process_decision(query="test")

            # Check for vulnerability
            is_vulnerable = check_vulnerability(result)

            if is_vulnerable:
                return TestResult(
                    test_name="custom_security_check",
                    passed=False,
                    severity=Severity.HIGH,
                    message="Vulnerability detected!",
                    details={"result": result},
                )

            return TestResult(
                test_name="custom_security_check",
                passed=True,
                severity=Severity.INFO,
                message="No vulnerability found",
            )

        except Exception as e:
            return TestResult(
                test_name="custom_security_check",
                passed=False,
                severity=Severity.CRITICAL,
                message=f"Test failed with exception: {str(e)}",
                exception=e,
            )
```

### Test Harness

```python
from ejc.testing import TestHarness

# Create harness
harness = TestHarness(ejc_instance=ejc)

# Add suites
harness.add_suite(PromptInjectionSuite())
harness.add_suite(BiasProbeSuite())
harness.add_suite(CustomTestSuite())

# Run all
results = harness.run_all_suites()

# Check for critical failures
if harness.has_critical_failures():
    critical = harness.get_critical_failures()
    print(f"🚨 {len(critical)} CRITICAL failures!")
    for failure in critical:
        print(f"  - {failure.test_name}: {failure.message}")

# Generate report
report = harness.generate_report(format="text")
print(report)
```

## Test Result Structure

```python
@dataclass
class TestResult:
    test_name: str
    passed: bool
    severity: Severity  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    message: str
    details: Optional[Dict[str, Any]] = None
    duration_ms: float = 0.0
    timestamp: datetime
    exception: Optional[Exception] = None
```

## Severity Levels

- **CRITICAL** - Security vulnerability, immediate fix required
- **HIGH** - Significant issue, should fix soon
- **MEDIUM** - Moderate issue, should address
- **LOW** - Minor issue, nice to fix
- **INFO** - Informational, no action needed

## Continuous Integration

### GitHub Actions Example

```yaml
name: EJC Adversarial Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install -e .

      - name: Run adversarial tests
        run: |
          python -m ejc.testing.cli run-all --format json --output results.json

      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: test-results
          path: results.json

      - name: Check for critical failures
        run: |
          python -c "
          import json
          with open('results.json') as f:
              results = json.load(f)
          critical = sum(1 for r in results['results']
                        if not r['passed'] and r['severity'] == 'critical')
          if critical > 0:
              print(f'FAILED: {critical} critical failures')
              exit(1)
          "
```

## Best Practices

### 1. Run Tests Regularly

```python
# Run full suite weekly
schedule.every().monday.at("02:00").do(run_all_tests, ejc)

# Run critical tests on every deploy
if deploying:
    results = runner.run_critical_only()
    if results['failed'] > 0:
        abort_deployment()
```

### 2. Monitor Trends

```python
# Track test results over time
import pandas as pd

results_history = []
for version in versions:
    results = run_all_tests(ejc_versions[version])
    results_history.append({
        'version': version,
        'pass_rate': results['passed'] / results['total_tests'],
        'critical_failures': len([r for r in results['results']
                                   if not r['passed'] and r['severity'] == 'critical']),
    })

df = pd.DataFrame(results_history)
df.plot(x='version', y='pass_rate')
```

### 3. Fail Fast on Critical

```python
results = run_all_tests(ejc)

# Check critical failures immediately
critical_failures = [r for r in results['results']
                     if not r['passed'] and r['severity'] == 'critical']

if critical_failures:
    print("🚨 CRITICAL SECURITY ISSUES FOUND!")
    print("DO NOT DEPLOY UNTIL FIXED!")
    for failure in critical_failures:
        print(f"  - {failure['test_name']}: {failure['message']}")
    sys.exit(1)
```

### 4. Track Bias Metrics

```python
from ejc.testing import BiasProbeSuite

suite = BiasProbeSuite()
results = suite.run_all(ejc=ejc)

# Calculate fairness metrics
bias_metrics = {}
for result in results:
    if not result.passed and 'disparity' in result.details:
        bias_metrics[result.test_name] = result.details['disparity']

# Alert if any metric exceeds threshold
for test, disparity in bias_metrics.items():
    if disparity > 0.15:  # 15% disparity threshold
        alert_team(f"Bias detected in {test}: {disparity:.2%}")
```

## Troubleshooting

### Tests Taking Too Long

```python
# Run critical tests only for quick feedback
runner = TestRunner(ejc_instance=ejc)
quick_results = runner.run_critical_only()
```

### False Positives

```python
# Review specific failed tests
for result in results['results']:
    if not result['passed']:
        print(f"Failed: {result['test_name']}")
        print(f"Severity: {result['severity']}")
        print(f"Message: {result['message']}")
        print(f"Details: {result['details']}")
        print("---")
```

### Custom EJC Configuration

```python
# Test with specific configuration
ejc_config = EJCConfig(
    critic_timeout=30,
    max_critics=10,
    enable_audit=True,
)
ejc = EJC(config=ejc_config)

results = run_all_tests(ejc)
```

## Contributing

To add new test suites:

1. Create a new file in `ejc/testing/`
2. Extend `TestSuite` base class
3. Add tests with appropriate severity levels
4. Register in `runner.py`
5. Update documentation

See existing suites for examples.

## License

CC BY 4.0 - See [LICENSE](../../../LICENSE) for details.
