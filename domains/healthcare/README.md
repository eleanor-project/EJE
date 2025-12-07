# Healthcare Domain Module

Comprehensive AI governance for healthcare applications with HIPAA, HITECH, and clinical compliance.

## Overview

The Healthcare Domain Module provides specialized governance and compliance validation for AI systems operating in healthcare contexts. It ensures protection of Protected Health Information (PHI), adherence to HIPAA Privacy and Security Rules, clinical validation, and medical ethics compliance.

## Key Features

- **PHI Detection & Protection**: Automatic identification and protection of 18 HIPAA identifiers
- **HIPAA Compliance**: Privacy Rule, Security Rule, and Breach Notification enforcement
- **Clinical Validation**: Evidence-based medicine checks and clinical decision support
- **Medical Ethics**: Beneficence, non-maleficence, autonomy, and justice principles
- **Consent Management**: Patient consent tracking and enforcement
- **De-identification**: Safe Harbor and Expert Determination methods

## Regulatory Compliance

### HIPAA Privacy Rule (45 CFR Part 160 and Part 164, Subparts A and E)

**Minimum Necessary Standard**
- Only minimum PHI needed for intended purpose
- Automatic filtering of non-essential data elements
- Purpose-based disclosure controls

**Individual Rights**
- Right to access
- Right to amend
- Right to accounting of disclosures
- Right to request restrictions

**Authorization Requirements**
- Valid patient authorization for uses/disclosures
- Consent management and tracking
- Revocation handling

### HIPAA Security Rule (45 CFR Part 164, Subpart C)

**Administrative Safeguards**
- Risk assessment and management
- Workforce security and training
- Contingency planning

**Physical Safeguards**
- Facility access controls
- Workstation and device security

**Technical Safeguards**
- Access controls (unique user IDs, automatic logoff)
- Audit controls and logging
- Integrity controls
- Transmission security (encryption)

### HITECH Act

**Breach Notification**
- 60-day notification requirement
- Risk assessment for breaches
- Media notification for large breaches

**Business Associate Requirements**
- BA agreements required
- Direct HIPAA liability

### Additional Regulations

- **21st Century Cures Act**: Information blocking prevention
- **FDA Medical Device Regulations**: For AI diagnostic tools
- **State Privacy Laws**: California, Texas, and other state-specific requirements
- **AMA Code of Medical Ethics**: Professional ethical standards

## Configuration

### Basic Configuration

```python
from domains.domain_config import get_config_system
from domains import DomainType

# Initialize healthcare domain
config = get_config_system()
config.switch_domain('healthcare')

# Load healthcare critics
critics = config.load_critics()
```

### Domain Profile (healthcare.yaml)

```yaml
name: healthcare
domain_type: healthcare
description: Healthcare domain with HIPAA and clinical compliance

critics:
  - HealthcareHIPAAComplianceCritic
  - HealthcarePHIProtectionCritic
  - HealthcareClinicalValidationCritic
  - HealthcareMedicalEthicsCritic

critic_config:
  phi_detection:
    enabled: true
    strict_mode: true
    check_unstructured_text: true
  hipaa_validation:
    check_minimum_necessary: true
    require_business_associate: true
    audit_logging_required: true
```

### Critic Configuration

**PHI Detection Settings**
```python
phi_config = {
    "enabled": True,
    "identifiers": [
        "names", "dates", "phone", "fax", "email",
        "ssn", "mrn", "account_numbers", "certificates",
        "vehicle_identifiers", "device_ids", "urls",
        "ip_addresses", "biometric", "photos",
        "geographic", "other_unique_ids"
    ],
    "strict_mode": True,
    "check_unstructured_text": True
}
```

**HIPAA Validation Settings**
```python
hipaa_config = {
    "check_minimum_necessary": True,
    "require_business_associate": True,
    "audit_logging_required": True,
    "breach_notification_hours": 60,
    "encryption_required": True
}
```

## Use Cases

### 1. Clinical Documentation Review

**Scenario**: AI assistant helps clinicians with documentation

```python
from domains.healthcare.healthcare_critics import (
    HealthcarePHIProtectionCritic,
    HealthcareClinicalValidationCritic
)

# Input: Draft clinical note
note = """
Patient: Jane Smith, DOB 05/12/1975
Chief Complaint: Chest pain
Assessment: Likely angina, rule out MI
Plan: EKG, troponin, cardiology consult
"""

# Run critics
phi_critic = HealthcarePHIProtectionCritic()
clinical_critic = HealthcareClinicalValidationCritic()

phi_result = phi_critic.evaluate(note)
clinical_result = clinical_critic.evaluate(note)

# phi_result.phi_detected = True
# phi_result.recommendation = "de_identify_before_storage"
# clinical_result.evidence_based = True
```

### 2. Patient Data Sharing

**Scenario**: Sharing patient data with insurance for billing

```python
from domains.healthcare.healthcare_critics import HealthcareHIPAAComplianceCritic

critic = HealthcareHIPAAComplianceCritic()

request = {
    "purpose": "billing",
    "recipient": "insurance_company",
    "data": {
        "diagnosis": "Type 2 Diabetes",
        "medications": ["Metformin"],
        "social_history": "...",  # Not needed for billing
        "mental_health": "..."   # Not needed for billing
    }
}

result = critic.check_minimum_necessary(request)
# result.approved_fields = ["diagnosis", "medications"]
# result.withheld_fields = ["social_history", "mental_health"]
```

### 3. Clinical Decision Support

**Scenario**: AI provides treatment recommendations

```python
from domains.healthcare.healthcare_critics import HealthcareClinicalValidationCritic

critic = HealthcareClinicalValidationCritic()

patient_case = {
    "condition": "acute_myocardial_infarction",
    "contraindications": ["aspirin_allergy"],
    "current_medications": ["lisinopril", "atorvastatin"]
}

recommendations = critic.generate_recommendations(patient_case)
# Returns evidence-based alternatives considering contraindications
```

### 4. De-identification

**Scenario**: De-identify data for research

```python
from domains.healthcare.healthcare_critics import HealthcarePHIProtectionCritic

critic = HealthcarePHIProtectionCritic()

original = "Patient Mary Johnson, SSN 123-45-6789, lives at 456 Oak St"

result = critic.de_identify(original, method="safe_harbor")
# result.de_identified = "Patient [NAME], SSN [REDACTED], lives at [ADDRESS]"
# result.method_compliant = True
```

## Integration Guide

### Adding to Existing Application

```python
from ejc.core.judgment_core import JudgmentCore
from domains.healthcare.healthcare_critics import (
    HealthcareHIPAAComplianceCritic,
    HealthcarePHIProtectionCritic
)

# Initialize judgment core
judgment = JudgmentCore()

# Add healthcare critics
judgment.register_critic(HealthcareHIPAAComplianceCritic())
judgment.register_critic(HealthcarePHIProtectionCritic())

# Process healthcare content
input_text = "Patient data requiring HIPAA review..."
result = judgment.judge(input_text, context={"domain": "healthcare"})
```

### API Integration

```python
from fastapi import FastAPI, HTTPException
from domains.healthcare import HealthcareDomainValidator

app = FastAPI()
validator = HealthcareDomainValidator()

@app.post("/validate/clinical-note")
async def validate_note(note: dict):
    result = validator.validate_clinical_note(
        text=note["text"],
        context=note.get("context", {})
    )
    
    if not result.compliant:
        raise HTTPException(
            status_code=400,
            detail=result.violations
        )
    
    return {"status": "compliant", "details": result.summary}
```

## Troubleshooting

### Common Issues

**Issue**: PHI not being detected

**Solution**: 
```python
# Enable strict mode
config.critic_config["phi_detection"]["strict_mode"] = True
config.critic_config["phi_detection"]["check_unstructured_text"] = True
```

**Issue**: False positives in PHI detection

**Solution**:
```python
# Configure whitelist for non-PHI patterns
config.critic_config["phi_detection"]["whitelist"] = [
    "common_medical_terms",
    "medication_names"
]
```

**Issue**: Minimum necessary check too restrictive

**Solution**:
```python
# Configure purpose-based rules
config.critic_config["hipaa_validation"]["purpose_rules"] = {
    "treatment": ["all_clinical_data"],
    "billing": ["diagnosis", "procedures", "medications"],
    "research": ["de_identified_only"]
}
```

### Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("domains.healthcare")

# Enable detailed critic logging
critic.set_log_level(logging.DEBUG)
```

## Testing

### Running Healthcare Tests

```bash
# Run all healthcare domain tests
pytest tests/domain/healthcare_tests.py

# Run specific test scenarios
pytest tests/domain/healthcare_tests.py::test_phi_detection_scenario
pytest tests/domain/healthcare_tests.py::test_minimum_necessary_scenario

# Run with coverage
pytest tests/domain/healthcare_tests.py --cov=domains.healthcare
```

### Test Scenarios Included

- **HC-001**: PHI Detection in Clinical Notes
- **HC-002**: Minimum Necessary Disclosure
- **HC-003**: Evidence-Based Clinical Recommendations
- **HC-004**: Patient Consent Validation
- **HC-005**: Safe Harbor De-identification

## Best Practices

### 1. Always Check for PHI

```python
# Before processing any healthcare text
phi_result = phi_critic.evaluate(text)
if phi_result.phi_detected:
    text = phi_critic.de_identify(text)
```

### 2. Implement Minimum Necessary

```python
# Filter data based on purpose
def filter_for_purpose(data, purpose):
    return hipaa_critic.apply_minimum_necessary(
        data=data,
        purpose=purpose
    )
```

### 3. Maintain Audit Logs

```python
# Log all PHI access
audit_logger.log_access(
    user=user_id,
    action="phi_access",
    data_elements=accessed_fields,
    purpose=access_reason,
    timestamp=datetime.now()
)
```

### 4. Validate Clinical Content

```python
# Ensure evidence-based recommendations
recommendation = clinical_critic.validate(
    recommendation=ai_suggestion,
    evidence_level="A",  # Require high-quality evidence
    guidelines=["ACC/AHA", "WHO"]
)
```

## Performance Considerations

- **PHI Detection**: ~50ms per 1000 words
- **HIPAA Validation**: ~30ms per request
- **Clinical Validation**: ~100ms per recommendation
- **De-identification**: ~75ms per document

## Support & Resources

### Documentation
- [HIPAA Privacy Rule Summary](https://www.hhs.gov/hipaa/for-professionals/privacy/)
- [HIPAA Security Rule Guidance](https://www.hhs.gov/hipaa/for-professionals/security/)
- [OCR HIPAA Enforcement](https://www.hhs.gov/hipaa/for-professionals/compliance-enforcement/)

### Compliance Resources
- HHS Office for Civil Rights (OCR)
- National Institute of Standards and Technology (NIST)
- Healthcare Information and Management Systems Society (HIMSS)

### Contact
For healthcare domain questions: healthcare-compliance@eje-project.org

## License

Part of the EJE AI Governance Framework.
