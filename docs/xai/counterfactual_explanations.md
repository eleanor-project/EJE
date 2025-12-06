# Counterfactual Explanations for EJE

**Issue**: #167 - Implement Counterfactual Explanation Generator

Counterfactual explanations answer the question: _"What would need to change for this decision to be different?"_

## Overview

The CounterfactualGenerator analyzes EJE decisions and generates alternative scenarios showing minimal changes needed for different outcomes. This helps users understand:

- **Decision boundaries**: What factors separate different verdicts
- **Sensitivity**: How stable is this decision?
- **Trust**: What would make me trust/distrust this decision?
- **Recourse**: What can I do to get a different outcome?

## Features

### 1. Multiple Generation Modes

- **NEAREST**: Find the closest alternative with a different verdict
- **DIVERSE**: Generate a varied set of alternatives
- **MINIMAL**: Show the absolute minimum change needed
- **PLAUSIBLE**: Generate most realistic alternatives

### 2. Key Capabilities

- Identifies most influential factors from critic reports
- Calculates minimal changes for different verdicts
- Validates counterfactuals for coherence
- Completes within 2 seconds (performance requirement)
- Integrates seamlessly with XAIPipeline

## Usage

### Basic Usage

```python
from src.ejc.core.explainability import CounterfactualGenerator, CounterfactualMode

# Create generator
generator = CounterfactualGenerator(
    max_counterfactuals=5,
    max_changes=3,
    timeout_seconds=2.0
)

# Generate counterfactuals for a decision
result = generator.generate(
    decision=my_decision,  # EJE Decision dict
    mode=CounterfactualMode.NEAREST
)

# Access counterfactuals
for cf in result['counterfactuals']:
    print(f"Original: {cf['original_verdict']}")
    print(f"Alternative: {cf['counterfactual_verdict']}")
    print(f"Changes needed: {cf['changed_factors']}")
    print(f"Explanation: {cf['explanation']}")
```

### Using with XAIPipeline

```python
from src.ejc.core.explainability import XAIPipeline, XAIMethod, ExplanationLevel

pipeline = XAIPipeline()

# Generate counterfactual explanation
explanation = pipeline.generate_explanation(
    model=None,  # Not needed for EJE decisions
    instance=my_decision,
    method=XAIMethod.COUNTERFACTUAL,
    level=ExplanationLevel.NARRATIVE,
    mode='nearest'
)

print(explanation['explanation'])
```

### Target Specific Verdict

```python
# Find what changes would lead to APPROVAL
result = generator.generate(
    decision=my_decision,
    mode=CounterfactualMode.MINIMAL,
    target_verdict='APPROVE'
)
```

## Generation Modes

### NEAREST Mode

Finds the closest alternative scenario with a different verdict.

**Use case**: "What's the smallest change that would flip this decision?"

**Example**:
```
Original verdict: DENY (confidence: 0.8)
Counterfactual: APPROVE

If the FraudCritic changed its verdict from DENY to APPROVE,
the final decision would be APPROVE.
This critic currently believes: 'Fraud indicators detected above threshold...'
```

### DIVERSE Mode

Generates multiple diverse alternatives using different strategies.

**Use case**: "What are different ways this decision could change?"

**Strategies**:
1. Change most important critic
2. Change least confident critic
3. Change multiple critics simultaneously

### MINIMAL Mode

Shows the absolute minimum change needed.

**Use case**: "What's the ONE thing that would change this?"

**Returns**: Single counterfactual with minimal factor changes

### PLAUSIBLE Mode

Generates most realistic alternatives by targeting low-confidence critics.

**Use case**: "What are realistic alternative outcomes?"

**Sorts by**: Plausibility score (based on critic confidence)

## Output Format

### Result Structure

```python
{
    'counterfactuals': [
        {
            'original_verdict': 'DENY',
            'counterfactual_verdict': 'APPROVE',
            'original_confidence': 0.8,
            'counterfactual_confidence': 0.7,
            'changed_factors': {
                'FraudCritic': {
                    'original': 'DENY',
                    'counterfactual': 'APPROVE',
                    'confidence_change': 0.6
                }
            },
            'change_magnitude': 0.6,
            'plausibility_score': 0.4,
            'explanation': 'If the FraudCritic changed...',
            'critic_impacts': {...}
        }
    ],
    'generation_time': 0.15,
    'mode': 'nearest',
    'key_factors': [...],
    'original_verdict': 'DENY',
    'original_confidence': 0.8,
    'within_timeout': True
}
```

### Counterfactual Fields

| Field | Type | Description |
|-------|------|-------------|
| `original_verdict` | str | Original decision verdict |
| `counterfactual_verdict` | str | Alternative verdict |
| `original_confidence` | float | Original confidence (0-1) |
| `counterfactual_confidence` | float | Estimated alternative confidence |
| `changed_factors` | dict | Factors that changed |
| `change_magnitude` | float | Size of changes (0-1) |
| `plausibility_score` | float | How realistic (0-1) |
| `explanation` | str | Human-readable explanation |

## Validation

Validate generated counterfactuals for coherence:

```python
validation = generator.validate_counterfactual(
    counterfactual=cf,
    decision=my_decision
)

print(f"Valid: {validation['is_valid']}")
print(f"Coherence: {validation['coherence_score']}")
print(f"Issues: {validation['issues']}")
```

**Validation checks**:
- Changed factors exist in original decision
- Plausibility score is reasonable
- Counterfactual is internally consistent

## Performance

- **Target**: < 2 seconds per generation
- **Typical**: 0.1 - 0.5 seconds
- **Worst case**: Timeout cuts off at 2 seconds

**Performance factors**:
- Number of critics (more = slower)
- Mode (DIVERSE > NEAREST > MINIMAL)
- Max counterfactuals requested

**Optimization tips**:
```python
# Fast generation
generator = CounterfactualGenerator(
    max_counterfactuals=3,
    max_changes=2,
    timeout_seconds=1.0
)

# Use MINIMAL mode for fastest results
result = generator.generate(decision, mode=CounterfactualMode.MINIMAL)
```

## Algorithm

### High-Level Process

1. **Extract key factors** from critic reports and input data
2. **Rank by importance** (confidence × agreement with final verdict)
3. **Generate alternatives** by:
   - Flipping critic verdicts
   - Modifying input features
   - Combining multiple changes
4. **Simulate outcomes** using weighted majority vote
5. **Validate** for coherence and plausibility
6. **Sort and filter** by mode-specific criteria

### Verdict Simulation

The generator simulates what the final verdict would be using weighted majority vote:

```python
def simulate_verdict(original_decision, changes):
    verdict_weights = {'APPROVE': 0, 'DENY': 0, 'REVIEW': 0}

    for critic_report in decision.critic_reports:
        verdict = apply_changes(critic_report, changes)
        confidence = critic_report.confidence
        verdict_weights[verdict] += confidence

    return max(verdict_weights, key=verdict_weights.get)
```

### Plausibility Scoring

Plausibility measures how realistic a counterfactual is:

```
plausibility = (1 - critic_confidence) × weighting_factor
```

- **High plausibility**: Low-confidence critics are easy to flip
- **Low plausibility**: High-confidence critics are hard to flip

## Integration with EJE Pipeline

### Decision Flow

```
User Input → Critics → Aggregator → Governance → Decision
                                                    ↓
                                          Counterfactual Generator
                                                    ↓
                                          Alternative Scenarios
```

### API Endpoints

Counterfactuals can be accessed via the explanation API:

```http
POST /api/v1/explain/counterfactual
Content-Type: application/json

{
  "decision_id": "dec_12345",
  "mode": "nearest",
  "target_verdict": "APPROVE"
}
```

Response:
```json
{
  "counterfactuals": [...],
  "generation_time": 0.23,
  "mode": "nearest"
}
```

## Use Cases

### 1. User Recourse

**Scenario**: Loan application denied

**Counterfactual**: "If your credit score was 650 instead of 620, the application would be approved."

**Value**: Provides actionable feedback

### 2. Model Debugging

**Scenario**: Unexpected decision

**Counterfactual**: "Changing just the FraudCritic's verdict flips the decision, suggesting high sensitivity to this one critic."

**Value**: Identifies model weaknesses

### 3. Trust Building

**Scenario**: Building user confidence

**Counterfactual**: "Even if the RiskCritic had denied, the decision would still be APPROVE. This decision is robust."

**Value**: Demonstrates decision stability

### 4. Compliance & Auditing

**Scenario**: Regulatory review

**Counterfactual**: "What factors most influence this high-risk decision?"

**Value**: Transparency for auditors

## Limitations

### Current Limitations

1. **Critic-level only**: Changes critic verdicts, not individual features within critics
2. **Simulation-based**: Doesn't re-run actual critics
3. **Majority vote assumption**: Uses simplified aggregation
4. **No feature constraints**: Doesn't enforce feasibility constraints on changes

### Future Enhancements (See Issue #172)

- **Feature-level counterfactuals**: Change specific input features
- **Actual re-execution**: Re-run critics with modified inputs
- **Constraint handling**: Ensure counterfactuals are feasible
- **Confidence recalculation**: More accurate confidence estimates
- **Optimization**: Use gradient-based methods for faster generation

## Testing

Comprehensive test suite covers:

- All generation modes
- Edge cases (unanimous, split decisions)
- Performance (timeout compliance)
- Validation
- Integration with XAIPipeline
- Explanation quality

**Run tests**:
```bash
pytest tests/explainability/test_counterfactual_generator.py -v
```

## References

- **Wachter et al. (2017)**: "Counterfactual Explanations without Opening the Black Box"
- **Mothilal et al. (2020)**: "Explaining Machine Learning Classifiers through Diverse Counterfactual Explanations"
- **DARPA XAI Program**: Explainable AI initiative
- **World Bank AI Governance Report (Section 5.1)**: Explainability Technologies

## Example: Complete Workflow

```python
from src.ejc.core.explainability import CounterfactualGenerator, CounterfactualMode

# 1. Create generator
generator = CounterfactualGenerator()

# 2. Get decision from EJE pipeline
decision = eje_pipeline.adjudicate(case_data)

# 3. Generate counterfactuals
result = generator.generate(
    decision=decision,
    mode=CounterfactualMode.DIVERSE
)

# 4. Present to user
print(f"Original decision: {result['original_verdict']}")
print(f"\nAlternative scenarios:\n")

for i, cf in enumerate(result['counterfactuals'], 1):
    print(f"{i}. {cf['explanation']}")
    print(f"   Plausibility: {cf['plausibility_score']:.2f}")
    print(f"   Changes: {list(cf['changed_factors'].keys())}")
    print()

# 5. Validate
for cf in result['counterfactuals']:
    validation = generator.validate_counterfactual(cf, decision)
    if not validation['is_valid']:
        print(f"Warning: {validation['issues']}")
```

## Configuration

### Generator Parameters

```python
CounterfactualGenerator(
    max_counterfactuals=5,  # Maximum number to generate
    max_changes=3,          # Maximum factors to change per counterfactual
    timeout_seconds=2.0     # Performance timeout
)
```

### Recommended Settings

**Interactive use** (fast response):
```python
generator = CounterfactualGenerator(
    max_counterfactuals=3,
    max_changes=2,
    timeout_seconds=1.0
)
```

**Batch processing** (thorough analysis):
```python
generator = CounterfactualGenerator(
    max_counterfactuals=10,
    max_changes=5,
    timeout_seconds=5.0
)
```

**Production** (balanced):
```python
generator = CounterfactualGenerator(
    max_counterfactuals=5,
    max_changes=3,
    timeout_seconds=2.0
)
```

---

**Version**: 1.0.0
**Last Updated**: 2025-12-02
**Issue**: #167
**Status**: Implemented
