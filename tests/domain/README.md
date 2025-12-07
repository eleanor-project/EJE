# Domain Testing Framework

Comprehensive testing infrastructure for domain-specific validation in the EJE AI Governance Framework.

## Overview

The Domain Testing Framework provides specialized testing capabilities for validating AI system behavior across different domains (Healthcare, Financial, Education, Legal). It includes real-world scenarios, compliance checks, performance benchmarks, and cross-domain compatibility tests.

## Architecture

### Core Components

- **`DomainTestFixture`**: Abstract base class for domain-specific test fixtures
- **`DomainTestRunner`**: Test execution engine with compliance tracking
- **`ComplianceRequirement`**: Regulatory compliance specification
- **`TestScenario`**: Real-world test case definition
- **`PerformanceBenchmark`**: Performance measurement framework
- **`CrossDomainCompatibilityTest`**: Inter-domain validation

### Domain Implementations

- **Healthcare** (`healthcare_tests.py`): HIPAA, HITECH, clinical validation
- **Financial** (TBD): KYC, AML, PCI DSS compliance
- **Education** (TBD): FERPA, COPPA, accessibility
- **Legal** (TBD): GDPR, EU AI Act, contract analysis

## Usage

### Running Domain Tests

```bash
# Run all domain tests
pytest tests/domain/

# Run specific domain
pytest tests/domain/healthcare_tests.py

# Run with coverage
pytest tests/domain/ --cov=domains --cov-report=html

# Run compliance tests only
pytest tests/domain/ -m compliance

# Run performance benchmarks
pytest tests/domain/ -m benchmark
```

### Using Domain Fixtures

```python
import pytest
from tests.domain import healthcare_fixture

def test_phi_detection(healthcare_fixture):
    """Test PHI detection in clinical notes."""
    scenarios = healthcare_fixture.get_test_scenarios()
    phi_scenario = next(s for s in scenarios if s.scenario_id == "HC-001")
    
    # Execute test scenario
    runner = DomainTestRunner(healthcare_fixture)
    result = runner.run_scenario(phi_scenario)
    
    assert result["passed"]
    assert all(c["passed"] for c in result["compliance_checks"])
```

### Creating Custom Scenarios

```python
from tests.domain import TestScenario, DomainType, ComplianceRequirement

custom_scenario = TestScenario(
    scenario_id="HC-CUSTOM-001",
    name="Custom Healthcare Test",
    description="Test custom healthcare behavior",
    domain=DomainType.HEALTHCARE,
    input_data={
        "patient_data": {...},
        "context": "emergency_care"
    },
    expected_output={
        "action": "alert_on_call_physician",
        "priority": "high"
    },
    compliance_requirements=[
        ComplianceRequirement(
            framework="HIPAA",
            requirement_id="Emergency Access",
            description="Ensure emergency access protocols",
            test_method="test_emergency_access"
        )
    ],
    tags=["emergency", "access_control", "high"]
)
```

## Healthcare Domain

### Test Scenarios

| ID | Scenario | Compliance | Severity |
|----|----------|------------|----------|
| HC-001 | PHI Detection in Clinical Notes | HIPAA Privacy | Critical |
| HC-002 | Minimum Necessary Disclosure | HIPAA Privacy | Critical |
| HC-003 | Evidence-Based Clinical Recommendations | Best Practices | High |
| HC-004 | Patient Consent Validation | HIPAA Privacy | High |
| HC-005 | Safe Harbor De-identification | HIPAA Privacy | Critical |

### Compliance Requirements

- **HIPAA Privacy Rule** (45 CFR 164.502): Minimum necessary standard
- **HIPAA Security Rule** (45 CFR 164.312): Technical safeguards for ePHI
- **HITECH Act**: Breach notification requirements
- **21st Century Cures Act**: Information blocking prevention

### Test Data Generators

```python
fixture = HealthcareTestFixture(DomainType.HEALTHCARE)
test_data = fixture.setup_test_data()

# Available test data:
# - patient_records: Synthetic patient demographics and history
# - clinical_notes: Sample clinical documentation
# - phi_examples: PHI elements for detection testing
# - consent_forms: Consent status test data
# - medical_decisions: Clinical decision scenarios
```

## Performance Benchmarks

The framework includes performance benchmarking for domain operations:

```python
from tests.domain import PerformanceBenchmark, DomainType

benchmark = PerformanceBenchmark(
    operation="phi_detection",
    domain=DomainType.HEALTHCARE,
    max_duration_ms=100.0,
    sample_size=100
)

runner = DomainTestRunner(healthcare_fixture)
result = runner.run_performance_benchmark(benchmark)

print(f"Average: {result.measured_duration:.2f}ms")
print(f"Passed: {result.passed}")
```

## Cross-Domain Compatibility

Test data sharing and critic interoperability across domains:

```python
from tests.domain import CrossDomainCompatibilityTest

compat_test = CrossDomainCompatibilityTest(all_domain_fixtures)

# Test data sharing between domains
result = compat_test.test_data_sharing(
    from_domain=DomainType.HEALTHCARE,
    to_domain=DomainType.LEGAL
)

# Test critic isolation
result = compat_test.test_critic_interoperability()
```

## Continuous Integration

The framework integrates with CI/CD pipelines:

```yaml
# .github/workflows/domain-tests.yml
name: Domain Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Domain Tests
        run: |
          pytest tests/domain/ \
            --junitxml=test-results.xml \
            --cov=domains \
            --cov-report=xml
      - name: Upload Coverage
        uses: codecov/codecov-action@v2
```

## Development Guidelines

### Adding New Domain Tests

1. Create `{domain}_tests.py` file
2. Implement `{Domain}TestFixture` extending `DomainTestFixture`
3. Define compliance requirements for the domain
4. Create real-world test scenarios
5. Implement test data generators
6. Add pytest test cases
7. Update this README

### Test Severity Levels

- **CRITICAL**: Must pass for production deployment
- **HIGH**: Important for compliance and quality
- **MEDIUM**: Standard functionality validation
- **LOW**: Nice-to-have features

### Naming Conventions

- Scenario IDs: `{DOMAIN}-{NUMBER}` (e.g., `HC-001`)
- Test methods: `test_{domain}_{feature}` (e.g., `test_healthcare_phi_detection`)
- Fixtures: `{domain}_fixture` (e.g., `healthcare_fixture`)

## Test Coverage Goals

- **Compliance Coverage**: 100% of regulatory requirements
- **Scenario Coverage**: Minimum 5 scenarios per domain
- **Code Coverage**: >80% of domain critic code
- **Performance**: All benchmarks passing

## Contributing

When adding tests:
1. Ensure all compliance requirements are testable
2. Use realistic scenario data
3. Document expected outcomes clearly
4. Include both positive and negative test cases
5. Add performance benchmarks for critical operations

## License

Part of the EJE AI Governance Framework.
