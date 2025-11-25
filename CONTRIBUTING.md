# Contributing to EJE

## Code Style Guidelines

### Python Code Style

EJE follows **PEP 8** with some project-specific conventions.

#### Tools

We use the following tools for code quality:

- **black**: Code formatting (line length: 100)
- **ruff**: Fast linting
- **mypy**: Type checking
- **isort**: Import sorting
- **bandit**: Security scanning

#### Setup Development Environment

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### Formatting Standards

#### 1. Line Length

Maximum line length: **100 characters**

```python
# ✅ Good
def evaluate_case_with_multiple_critics(
    case: Dict[str, Any], critics: List[BaseCritic], timeout: float = 30.0
) -> Dict[str, Any]:
    pass

# ❌ Bad (line too long)
def evaluate_case_with_multiple_critics(case: Dict[str, Any], critics: List[BaseCritic], timeout: float = 30.0) -> Dict[str, Any]:
    pass
```

#### 2. Imports

Use `isort` for consistent import ordering:

```python
# Standard library
import os
import sys
from typing import Dict, Any, Optional

# Third-party
import numpy as np
from flask import Flask
from sqlalchemy import create_engine

# Local application
from ejc.core.base_critic import BaseCritic
from ejc.utils.logging import get_logger
```

#### 3. Type Hints

**Always** use type hints for:
- Function parameters
- Return values
- Class attributes

```python
# ✅ Good
def compute_similarity(text1: str, text2: str) -> float:
    """Compute similarity between two texts."""
    # Implementation
    return 0.95

# ❌ Bad (no type hints)
def compute_similarity(text1, text2):
    return 0.95
```

#### 4. Docstrings

Use **Google-style docstrings**:

```python
def evaluate(self, case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate a case and return verdict.

    Args:
        case: Dictionary containing case data with 'text' field

    Returns:
        Dictionary with verdict, confidence, and justification

    Raises:
        ValueError: If case format is invalid
        TimeoutError: If evaluation exceeds timeout

    Example:
        >>> critic = MyCritic()
        >>> result = critic.evaluate({'text': 'test case'})
        >>> print(result['verdict'])
        'ALLOW'
    """
    pass
```

### Code Organization

#### 1. File Structure

```python
"""
Module docstring explaining purpose.
"""
# Imports
import os
from typing import Dict, Any

# Constants
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3

# Classes
class MyClass:
    """Class docstring."""
    pass

# Functions
def my_function():
    """Function docstring."""
    pass

# Main execution (if applicable)
if __name__ == "__main__":
    main()
```

#### 2. Class Structure

```python
class MyClass:
    """Class docstring."""

    # Class variables
    class_var: int = 10

    def __init__(self, param: str):
        """Initialize instance."""
        # Instance variables
        self.param = param
        self._private_var = None

    # Public methods
    def public_method(self) -> None:
        """Public method docstring."""
        pass

    # Private methods
    def _private_method(self) -> None:
        """Private method docstring."""
        pass

    # Properties
    @property
    def my_property(self) -> str:
        """Property docstring."""
        return self._private_var

    # Special methods
    def __str__(self) -> str:
        """String representation."""
        return f"MyClass({self.param})"
```

### Naming Conventions

#### Variables and Functions

```python
# ✅ Good - descriptive, snake_case
user_count = 10
max_retry_attempts = 3

def calculate_similarity_score(text1: str, text2: str) -> float:
    pass

# ❌ Bad - unclear, abbreviated
uc = 10
mra = 3

def calc_sim(t1: str, t2: str) -> float:
    pass
```

#### Classes

```python
# ✅ Good - PascalCase, descriptive
class CriticSecurityManager:
    pass

class JurisprudenceRepository:
    pass

# ❌ Bad
class critic_security_manager:  # Wrong case
    pass

class PM:  # Too abbreviated
    pass
```

#### Constants

```python
# ✅ Good - UPPER_SNAKE_CASE
MAX_PARALLEL_CALLS = 5
DEFAULT_TIMEOUT = 30.0
VERDICT_ALLOW = "ALLOW"

# ❌ Bad
max_parallel_calls = 5  # Not uppercase
MaxParallelCalls = 5  # Wrong case
```

#### Private Members

```python
class MyClass:
    def __init__(self):
        self.public_var = "public"
        self._private_var = "private"  # Single underscore
        self.__very_private = "very private"  # Double underscore (name mangling)

    def public_method(self):
        pass

    def _private_method(self):
        pass
```

### Error Handling

#### 1. Specific Exceptions

```python
# ✅ Good - specific exceptions
try:
    result = api_call()
except TimeoutError:
    logger.error("API call timed out")
    raise
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    return default_value
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    raise

# ❌ Bad - bare except
try:
    result = api_call()
except:  # Don't do this!
    pass
```

#### 2. Custom Exceptions

```python
class CriticException(Exception):
    """Base exception for critic errors."""
    pass

class TimeoutException(CriticException):
    """Raised when critic execution times out."""
    pass

# Usage
def evaluate(self, case):
    if not self._is_valid(case):
        raise CriticException("Invalid case format")
```

### Testing Standards

#### 1. Test Organization

```python
# tests/unit/test_my_module.py

import pytest
from ejc.core.my_module import MyClass


class TestMyClass:
    """Test suite for MyClass."""

    @pytest.fixture
    def instance(self):
        """Create MyClass instance for testing."""
        return MyClass(param="test")

    def test_basic_functionality(self, instance):
        """Test basic functionality works."""
        result = instance.do_something()
        assert result == expected

    def test_error_handling(self, instance):
        """Test error handling."""
        with pytest.raises(ValueError):
            instance.do_something_invalid()

    @pytest.mark.slow
    def test_slow_operation(self, instance):
        """Test slow operation (marked for optional execution)."""
        # Long-running test
        pass
```

#### 2. Test Naming

```python
# ✅ Good - descriptive test names
def test_critic_blocks_sensitive_content():
    pass

def test_aggregator_handles_tie_votes():
    pass

def test_precedent_lookup_returns_similar_cases():
    pass

# ❌ Bad - unclear test names
def test1():
    pass

def test_critic():
    pass
```

#### 3. Test Coverage

- Aim for **≥80% code coverage**
- Cover edge cases and error paths
- Include integration tests for critical paths

```bash
# Run tests with coverage
pytest --cov=src/eje --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Logging

#### 1. Logger Setup

```python
import logging

logger = logging.getLogger(__name__)

# Or use utility
from ejc.utils.logging import get_logger
logger = get_logger("MyModule")
```

#### 2. Log Levels

```python
# DEBUG - Detailed diagnostic information
logger.debug(f"Processing case with hash: {case_hash}")

# INFO - General informational messages
logger.info("Successfully loaded 10 critics")

# WARNING - Warning messages for potentially problematic situations
logger.warning(f"Plugin {plugin_name} took {duration}s (slow)")

# ERROR - Error messages for serious problems
logger.error(f"Failed to load critic: {error}")

# CRITICAL - Critical errors that may cause system failure
logger.critical("Database connection failed, system unusable")
```

#### 3. Logging Best Practices

```python
# ✅ Good - structured, informative
logger.info(
    f"Decision completed: request_id={request_id}, "
    f"verdict={verdict}, confidence={confidence:.2f}"
)

# ✅ Good - use exceptions parameter
try:
    risky_operation()
except Exception as e:
    logger.exception("Operation failed")  # Includes traceback

# ❌ Bad - too verbose, unstructured
logger.debug("Starting...")
logger.debug("Doing something...")
logger.debug("Done!")
```

### Security Guidelines

#### 1. Input Validation

```python
# Always validate external input
def process_case(case: Dict[str, Any]) -> Dict[str, Any]:
    # Validate structure
    if not isinstance(case, dict):
        raise ValueError("Case must be dictionary")

    # Validate required fields
    if 'text' not in case:
        raise ValueError("Case must contain 'text' field")

    # Validate types
    if not isinstance(case['text'], str):
        raise ValueError("Text must be string")

    # Sanitize input
    text = case['text'].strip()
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError("Text exceeds maximum length")

    # Check for malicious content
    if contains_dangerous_patterns(text):
        raise ValueError("Text contains potentially malicious content")
```

#### 2. Secrets Management

```python
# ✅ Good - use environment variables or secrets manager
import os

api_key = os.getenv('OPENAI_API_KEY')
# Or
from ejc.core.secrets_manager import get_api_keys
api_keys = get_api_keys(secrets_manager)

# ❌ Bad - hardcoded secrets
api_key = "sk-abc123xyz"  # NEVER do this!
```

#### 3. SQL Injection Prevention

```python
# ✅ Good - use parameterized queries
session.query(AuditEvent).filter(AuditEvent.id == event_id).first()

# ❌ Bad - string concatenation
query = f"SELECT * FROM events WHERE id = {event_id}"  # Dangerous!
```

### Performance Guidelines

#### 1. Avoid Premature Optimization

```python
# ✅ Good - clear, maintainable code first
def process_items(items: List[str]) -> List[str]:
    return [item.upper() for item in items]

# Only optimize if profiling shows it's a bottleneck
```

#### 2. Use Appropriate Data Structures

```python
# ✅ Good - use set for membership testing
allowed_verdicts = {'ALLOW', 'DENY', 'REVIEW', 'BLOCK'}
if verdict in allowed_verdicts:
    pass

# ❌ Bad - list is slower for membership testing
allowed_verdicts = ['ALLOW', 'DENY', 'REVIEW', 'BLOCK']
if verdict in allowed_verdicts:  # O(n) instead of O(1)
    pass
```

#### 3. Cache Expensive Operations

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def compute_expensive_embedding(text: str) -> np.ndarray:
    """Compute embedding (cached)."""
    return model.encode(text)
```

### Git Workflow

#### 1. Branching Strategy

```bash
# Feature branches
git checkout -b feature/add-new-critic

# Bug fixes
git checkout -b fix/timeout-handling

# Documentation
git checkout -b docs/update-api-guide
```

#### 2. Commit Messages

Follow conventional commits:

```bash
# Format: <type>(<scope>): <subject>

# Examples:
git commit -m "feat(critics): add timeout support for plugin execution"
git commit -m "fix(aggregator): handle tie votes correctly"
git commit -m "docs(api): add critic marketplace guide"
git commit -m "test(security): add plugin validation tests"
git commit -m "refactor(engine): extract retry logic to separate method"
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Tests
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `chore`: Maintenance tasks

#### 3. Pull Request Guidelines

- Clear title and description
- Reference related issues
- Include tests for new features
- Update documentation
- Ensure CI passes

### Code Review Checklist

Before submitting PR, verify:

- [ ] Code follows style guidelines
- [ ] Type hints added for all functions
- [ ] Docstrings added/updated
- [ ] Tests added for new functionality
- [ ] Tests pass locally (`pytest`)
- [ ] Code formatted (`black`, `isort`)
- [ ] Linting passes (`ruff`)
- [ ] Type checking passes (`mypy`)
- [ ] Security scan passes (`bandit`)
- [ ] Documentation updated
- [ ] CHANGELOG updated (for significant changes)

### Running Quality Checks

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/

# Security scan
bandit -r src/

# Run tests
pytest

# Run all checks
./scripts/run_checks.sh  # If available
```

### Documentation Standards

#### 1. README Files

- Clear project description
- Installation instructions
- Quick start example
- Links to detailed docs

#### 2. API Documentation

- All public functions documented
- Parameter types and descriptions
- Return value descriptions
- Example usage
- Exception documentation

#### 3. Inline Comments

```python
# ✅ Good - explain WHY, not WHAT
# Use exponential backoff to avoid overwhelming the API
time.sleep(2 ** attempt)

# ❌ Bad - states the obvious
# Sleep for 2 to the power of attempt
time.sleep(2 ** attempt)
```

## Getting Help

- **Documentation**: Check [docs/](./docs/) directory
- **Issues**: Search [GitHub issues](https://github.com/your-org/eje/issues)
- **Discussions**: Use GitHub Discussions for questions
- **Community**: Join our Slack/Discord channel

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT/Apache 2.0).
