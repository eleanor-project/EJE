# MESSAGE FOR CLAUDE CODE: MIF/RBJA/EJC Rebranding

## Context

We have rebranded the ELEANOR project with new nomenclature. The old "Constitutional AI" terminology has been replaced with the **Mutual Intelligence Framework (MIF)** brand architecture.

## CRITICAL: Apply This Nomenclature to ALL Code

### The New Framework Hierarchy

```
┌─────────────────────────────────────────┐
│  MIF (Mutual Intelligence Framework)    │
│  → Overarching philosophy               │
└──────────────────┬──────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│  ELEANOR                                 │
│  → Ethical Leadership Engine            │
└──────────────────┬──────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│  RBJA (Rights-Based Jurisprudence       │
│  Architecture)                          │
│  → Technical Specification              │
└──────────────────┬──────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│  EJC (Ethical Jurisprudence Core)       │
│  → Reference Implementation (code)      │
└─────────────────────────────────────────┘
```

## Complete Terminology Mapping

**YOU MUST USE THESE NEW TERMS EVERYWHERE:**

| OLD TERM (Never use) | NEW TERM (Always use) |
|---------------------|----------------------|
| Constitutional AI | Mutual Intelligence Framework (MIF) |
| ELEANOR Governance Specification | Rights-Based Jurisprudence Architecture (RBJA) |
| EJE (Ethics Jurisprudence Engine) | EJC (Ethical Jurisprudence Core) |
| Constitutional Constraints | Rights-Based Safeguards |
| Constitutional Principles | Ethical Jurisprudence Principles |
| Constitutional Tests | Rights-Based Tests |
| Decision Engine | Ethical Reasoning Engine |
| Critic System | Ethical Deliberation System |
| Precedent System | Jurisprudence Repository |
| GCR (Governance Change Request) | RCR (RBJA Change Request) |

## Code Refactoring Instructions

### 1. File and Directory Names

**Rename these:**
```bash
# Python package
eje/ → ejc/

# Main files
eje_api_main.py → ejc_api_main.py
eje_core.py → ejc_core.py
eje_critics.py → ejc_critics.py
eje_precedents.py → ejc_precedents.py

# Test files
test_eje.py → test_ejc.py

# Config files
eje_config.yaml → ejc_config.yaml
eje.env → ejc.env
```

### 2. Python Package Structure

**Old:**
```python
from eje.core.decision_engine import DecisionEngine
from eje.critics.critic_system import CriticSystem
```

**New:**
```python
from ejc.core.ethical_reasoning_engine import EthicalReasoningEngine
from ejc.critics.ethical_deliberation import EthicalDeliberationSystem
```

### 3. Class Names

**Rename these classes:**
```python
# OLD → NEW
DecisionEngine → EthicalReasoningEngine
CriticSystem → EthicalDeliberationSystem
PrecedentSystem → JurisprudenceRepository
ConstitutionalValidator → RightsBasedValidator
GCRManager → RCRManager
```

### 4. Variable and Function Names

**Update naming conventions:**
```python
# OLD
constitutional_check()
critic_system
decision_engine
precedent_db

# NEW
rights_based_check()
ethical_deliberation_system
ethical_reasoning_engine
jurisprudence_repository
```

### 5. Comments and Docstrings

**Update all documentation:**
```python
# OLD
"""
Constitutional AI decision engine.
Uses critic system for governance.
"""

# NEW
"""
Ethical Reasoning Engine for the Mutual Intelligence Framework (MIF).
Uses ethical deliberation system with rights-based safeguards.
Part of the Rights-Based Jurisprudence Architecture (RBJA).
Reference implementation: Ethical Jurisprudence Core (EJC).
"""
```

### 6. Configuration Variables

**Update environment variables:**
```bash
# OLD
CONSTITUTIONAL_MODE=strict
EJE_API_KEY=...
CRITIC_ENDPOINT=...

# NEW
RBJA_MODE=strict
EJC_API_KEY=...
ETHICAL_DELIBERATION_ENDPOINT=...
```

### 7. API Endpoints (Keep Unchanged But Update Docs)

**Endpoints stay the same, but documentation changes:**
```python
@app.post("/evaluate")  # Endpoint unchanged
async def evaluate_decision():
    """
    RBJA-compliant evaluation endpoint.
    Uses EJC ethical reasoning engine with rights-based safeguards.
    Part of the Mutual Intelligence Framework (MIF).
    """
```

### 8. Database Tables (Add Migration)

**Create migration for table names:**
```sql
-- Optional: Rename tables (or keep for backward compatibility)
ALTER TABLE eje_precedents RENAME TO ejc_jurisprudence;
ALTER TABLE eje_verdicts RENAME TO ejc_verdicts;
ALTER TABLE eje_audit_log RENAME TO ejc_audit_log;

-- Update references in code to use new names
```

### 9. Docker Images

**Update Docker references:**
```dockerfile
# OLD
FROM eleanor/eje:latest

# NEW
FROM eleanor/ejc:latest
```

```yaml
# docker-compose.yml
services:
  ejc-api:  # renamed from eje-api
    image: eleanor/ejc:latest
    container_name: ejc-api
```

### 10. Import Statements

**Update all imports systematically:**
```python
# OLD
import eje
from eje.core import DecisionEngine
from eje.critics import CriticSystem

# NEW
import ejc
from ejc.core import EthicalReasoningEngine
from ejc.critics import EthicalDeliberationSystem
```

## Specific Code Patterns to Replace

### Pattern 1: Initialization
```python
# OLD
engine = DecisionEngine(config)
critics = CriticSystem()

# NEW
engine = EthicalReasoningEngine(config)
deliberation = EthicalDeliberationSystem()
```

### Pattern 2: Validation
```python
# OLD
def constitutional_check(decision):
    """Check constitutional constraints"""
    pass

# NEW
def rights_based_validation(decision):
    """Validate against rights-based safeguards"""
    pass
```

### Pattern 3: Logging
```python
# OLD
logger.info("EJE decision engine initialized")
logger.debug("Constitutional check passed")

# NEW
logger.info("EJC ethical reasoning engine initialized")
logger.debug("Rights-based validation passed")
```

### Pattern 4: Error Messages
```python
# OLD
raise ConstitutionalViolation("Decision violates constitutional constraints")

# NEW
raise RightsViolation("Decision violates rights-based safeguards")
```

## README and Documentation Updates

### Repository README.md

**Update the header:**
```markdown
# Ethical Jurisprudence Core (EJC)

**Part of the Mutual Intelligence Framework (MIF)**

Production implementation of ELEANOR (Ethical Leadership Engine for 
Autonomous Navigation of Rights-Based Reasoning), powered by the 
Rights-Based Jurisprudence Architecture (RBJA) specification.

## What is MIF/RBJA/EJC?

- **MIF**: Philosophical framework for co-developing ethical AI
- **ELEANOR**: The ethical leadership system design
- **RBJA**: Complete technical specification
- **EJC**: This repository - the reference implementation

[Previously known as: EJE (Ethics Jurisprudence Engine) / Constitutional AI]
```

### Code Documentation Standards

**Every file should have this header:**
```python
"""
Ethical Jurisprudence Core (EJC)
Part of the Mutual Intelligence Framework (MIF)

This module implements [specific functionality] as specified in the
Rights-Based Jurisprudence Architecture (RBJA) v3.0.

Copyright (c) 2024 William Parris
License: CC BY 4.0
"""
```

## Testing Updates

### Update Test Names
```python
# OLD
class TestConstitutionalEngine(unittest.TestCase):
    def test_critic_system(self):
        pass

# NEW
class TestEthicalReasoningEngine(unittest.TestCase):
    def test_ethical_deliberation_system(self):
        pass
```

### Update Test Fixtures
```python
# OLD
@pytest.fixture
def eje_engine():
    return DecisionEngine()

# NEW
@pytest.fixture
def ejc_engine():
    return EthicalReasoningEngine()
```

## Package Distribution

### PyPI Package
```python
# setup.py or pyproject.toml

# OLD
name="eje"
packages=["eje"]

# NEW
name="ethical-jurisprudence-core"
packages=["ejc"]
```

### GitHub Repository

**Update:**
- Repository name: `EJE` → `EJC`
- Repository description: Use MIF/RBJA/EJC terminology
- Set up redirect from old URL
- Update all links in documentation

## Migration Script Template

```python
#!/usr/bin/env python3
"""
Migration script to update codebase from EJE to EJC nomenclature.
Run this to automatically update your code.
"""

import os
import re
from pathlib import Path

REPLACEMENTS = {
    # Package names
    r'\beje\b': 'ejc',
    r'\bEJE\b': 'EJC',
    
    # Class names
    r'\bDecisionEngine\b': 'EthicalReasoningEngine',
    r'\bCriticSystem\b': 'EthicalDeliberationSystem',
    r'\bPrecedentSystem\b': 'JurisprudenceRepository',
    
    # Terminology
    r'\bconstitutional_check\b': 'rights_based_validation',
    r'\bconstitutional constraints\b': 'rights-based safeguards',
    r'\bConstitutional AI\b': 'Mutual Intelligence Framework (MIF)',
    
    # Comments
    r'Ethics Jurisprudence Engine': 'Ethical Jurisprudence Core',
    r'ELEANOR Governance Specification': 'Rights-Based Jurisprudence Architecture (RBJA)',
}

def migrate_file(filepath):
    """Apply all replacements to a file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    for old, new in REPLACEMENTS.items():
        content = re.sub(old, new, content)
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"Updated: {filepath}")

def migrate_codebase(root_dir):
    """Migrate entire codebase."""
    for filepath in Path(root_dir).rglob('*.py'):
        migrate_file(filepath)
    for filepath in Path(root_dir).rglob('*.md'):
        migrate_file(filepath)
    for filepath in Path(root_dir).rglob('*.yaml'):
        migrate_file(filepath)

if __name__ == '__main__':
    migrate_codebase('.')
    print("Migration complete!")
```

## Backward Compatibility (Optional)

If you need to maintain backward compatibility temporarily:

```python
# ejc/__init__.py

# New names (primary)
from ejc.core import EthicalReasoningEngine
from ejc.critics import EthicalDeliberationSystem

# Deprecated aliases (with warnings)
import warnings

def _deprecated_import(old_name, new_name):
    warnings.warn(
        f"{old_name} is deprecated. Use {new_name} instead.",
        DeprecationWarning,
        stacklevel=2
    )

DecisionEngine = EthicalReasoningEngine  # Deprecated
def get_decision_engine(*args, **kwargs):
    _deprecated_import("DecisionEngine", "EthicalReasoningEngine")
    return EthicalReasoningEngine(*args, **kwargs)
```

## Summary Checklist for Claude Code

When you work on this codebase, **ALWAYS**:

- [ ] Use EJC, never EJE
- [ ] Use "Mutual Intelligence Framework (MIF)" not "Constitutional AI"
- [ ] Use "Rights-Based Jurisprudence Architecture (RBJA)" not "ELEANOR Governance Spec"
- [ ] Use "Ethical Reasoning Engine" not "Decision Engine"
- [ ] Use "Ethical Deliberation System" not "Critic System"
- [ ] Use "Jurisprudence Repository" not "Precedent System"
- [ ] Use "rights-based safeguards" not "constitutional constraints"
- [ ] Update all docstrings with MIF/RBJA/EJC references
- [ ] Update all comments with new terminology
- [ ] Update all variable names to match new conventions
- [ ] Update all class names to match new conventions

## Questions?

Refer to these documents in the package:
- **MIF_REBRANDING_GUIDE.md** - Complete terminology reference
- **MIF_MANIFESTO.md** - Philosophical foundation
- **RBJA_Specification_v3_0.html** - Technical specification

## Example: Complete Before/After

### BEFORE (Old Code - Never Use This Style)
```python
"""
EJE Constitutional AI Engine
"""
from eje.core.decision_engine import DecisionEngine
from eje.critics.critic_system import CriticSystem

class ConstitutionalValidator:
    def __init__(self):
        self.engine = DecisionEngine()
        self.critics = CriticSystem()
    
    def constitutional_check(self, decision):
        """Check constitutional constraints."""
        # EJE critic evaluation
        result = self.critics.evaluate(decision)
        return result.constitutional_verdict
```

### AFTER (New Code - Always Use This Style)
```python
"""
Ethical Jurisprudence Core (EJC)
Part of the Mutual Intelligence Framework (MIF)

Rights-based validation implementation per RBJA v3.0 specification.

Copyright (c) 2024 William Parris
License: CC BY 4.0
"""
from ejc.core.ethical_reasoning_engine import EthicalReasoningEngine
from ejc.critics.ethical_deliberation import EthicalDeliberationSystem

class RightsBasedValidator:
    """
    Validates decisions against rights-based safeguards.
    
    Part of the EJC implementation of the RBJA specification,
    powered by the Mutual Intelligence Framework (MIF).
    """
    
    def __init__(self):
        self.engine = EthicalReasoningEngine()
        self.deliberation = EthicalDeliberationSystem()
    
    def rights_based_validation(self, decision):
        """
        Validate decision against rights-based safeguards.
        
        Uses multi-critic ethical deliberation with lexicographic
        priority enforcement per RBJA specification.
        
        Args:
            decision: Decision to validate
            
        Returns:
            ValidationResult with verdict and justification
        """
        # EJC ethical deliberation with rights-based safeguards
        result = self.deliberation.evaluate(decision)
        return result.rights_based_verdict
```

---

## TL;DR for Claude Code

**OLD:** Constitutional AI, EJE, Decision Engine, Critic System  
**NEW:** MIF, EJC, Ethical Reasoning Engine, Ethical Deliberation System

**Rename everything. Update all references. Use new terminology everywhere.**

**The complete documentation package is attached. Read MIF_REBRANDING_GUIDE.md for full details.**

---

**End of Instructions**

Use this message when working with Claude Code to ensure it applies the new nomenclature consistently throughout the codebase.
