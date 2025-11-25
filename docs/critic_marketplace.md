# Critic Marketplace API Guide

## Overview

The EJE Critic Marketplace provides a standardized way to build, register, and test custom critics. This guide covers everything you need to know to create and integrate your own critics into the EJE ecosystem.

## Critic Architecture

### Base Classes

EJE provides three abstract base classes for critic implementations:

1. **`BaseCritic`** - Root abstract class with validation and metadata handling
2. **`CriticBase`** - Legacy-compatible class using the supplier pattern
3. **`RuleBasedCritic`** - Specialized class for rule-based critics

### Critic Interface Contract

All critics must implement the `evaluate()` method with the following signature:

```python
def evaluate(self, case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate a case and return verdict.

    Args:
        case: Dictionary containing:
            - text: str (required) - the case text to evaluate
            - context: dict (optional) - additional context
            - metadata: dict (optional) - metadata about the case

    Returns:
        Dictionary containing:
            - verdict: str (required) - one of: ALLOW, DENY, REVIEW, BLOCK
            - confidence: float (required) - value between 0.0 and 1.0
            - justification: str (required) - explanation of the verdict
    """
```

## Building Your First Critic

### Option 1: Rule-Based Critic

For simple, deterministic logic:

```python
from ejc.core.base_critic import RuleBasedCritic
from typing import Dict, Any


class MyRuleCritic(RuleBasedCritic):
    """Custom rule-based critic implementation."""

    def __init__(self, name: str = "MyRule", weight: float = 1.0):
        super().__init__(name=name, weight=weight, timeout=10.0)

    def apply_rules(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Apply custom rule logic."""
        text = case.get("text", "").lower()

        # Example: Check for sensitive keywords
        sensitive_keywords = ["password", "ssn", "credit card"]

        for keyword in sensitive_keywords:
            if keyword in text:
                return {
                    "verdict": "BLOCK",
                    "confidence": 1.0,
                    "justification": f"Contains sensitive keyword: {keyword}"
                }

        return {
            "verdict": "ALLOW",
            "confidence": 0.8,
            "justification": "No sensitive content detected"
        }
```

### Option 2: LLM-Based Critic (Supplier Pattern)

For AI-powered evaluation:

```python
from ejc.core.base_critic import CriticBase
from typing import Dict, Any


class MyLLMSupplier:
    """LLM backend supplier."""

    def __init__(self, config):
        self.api_key = config['llm']['api_keys']['my_llm']
        # Initialize your LLM client here

    def run(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Execute LLM evaluation."""
        # Call your LLM API
        # response = my_llm_client.complete(prompt)

        return {
            "verdict": "ALLOW",  # Parse from LLM response
            "confidence": 0.9,
            "justification": "LLM reasoning here"
        }


# Usage in EJE
def create_my_llm_critic(config):
    supplier = MyLLMSupplier(config)
    return CriticBase(
        name="MyLLM",
        supplier=supplier,
        weight=1.0,
        timeout=30.0
    )
```

### Option 3: Advanced Custom Critic

For complex logic with validation:

```python
from ejc.core.base_critic import BaseCritic
from typing import Dict, Any
import requests


class MyAPIBasedCritic(BaseCritic):
    """Critic that calls external API."""

    def __init__(self, api_endpoint: str, api_key: str):
        super().__init__(
            name="MyAPI",
            weight=1.0,
            priority=None,
            timeout=15.0
        )
        self.api_endpoint = api_endpoint
        self.api_key = api_key

    def evaluate(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate using external API."""
        # Validation is automatic via BaseCritic
        text = case.get("text", "")

        try:
            response = requests.post(
                self.api_endpoint,
                json={"text": text},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            output = {
                "verdict": data.get("verdict", "REVIEW"),
                "confidence": data.get("confidence", 0.5),
                "justification": data.get("reason", "API evaluation")
            }

            # Validation is automatic via BaseCritic
            return output

        except requests.Timeout:
            raise TimeoutError("API call timed out")
        except Exception as e:
            raise RuntimeError(f"API error: {e}")
```

## Registering Your Critic

### Method 1: Plugin File

1. Save your critic as a Python file in a plugins directory:
   ```
   plugins/
   └── my_custom_critic.py
   ```

2. Update `config/global.yaml`:
   ```yaml
   plugin_critics:
     - "./plugins/my_custom_critic.py"
   ```

3. Ensure your file exports a class named one of:
   - `CustomRuleCritic`
   - `CustomCriticSupplier`
   - `Critic`
   - Or contains a factory function `create_critic(config)`

### Method 2: Programmatic Registration

```python
from ejc.core.ethical_reasoning_engine import EthicalReasoningEngine
from my_module import MyCustomCritic

# Initialize engine
engine = EthicalReasoningEngine()

# Add critic
my_critic = MyCustomCritic()
engine.critics.append(my_critic)
```

### Method 3: Configuration-Based

For critics with configuration:

```python
# In your plugin file
def create_critic(config):
    """Factory function called by EJE."""
    api_key = config.get('my_api_key')
    endpoint = config.get('my_endpoint')
    return MyAPIBasedCritic(endpoint, api_key)
```

## Critic Configuration

Configure critic behavior in `config/global.yaml`:

```yaml
# Critic weights (influence in aggregation)
critic_weights:
  MyRule: 1.0
  MyLLM: 1.2
  MyAPI: 0.9

# Critic priorities (override capability)
critic_priorities:
  SecurityCritic: "override"  # Can veto other critics
  MyRule: null  # Standard priority

# Timeouts (seconds)
critic_timeout: 30.0  # Default timeout for all critics

# Plugin paths
plugin_critics:
  - "./plugins/my_custom_critic.py"
  - "./plugins/another_critic.py"
```

## Testing Your Critic

### Unit Testing

```python
import pytest
from my_critic import MyRuleCritic


def test_critic_blocks_sensitive_content():
    """Test that critic blocks sensitive keywords."""
    critic = MyRuleCritic()

    case = {
        "text": "User's password is abc123"
    }

    result = critic.evaluate(case)

    assert result['verdict'] == 'BLOCK'
    assert result['confidence'] == 1.0
    assert 'password' in result['justification'].lower()


def test_critic_allows_safe_content():
    """Test that critic allows safe content."""
    critic = MyRuleCritic()

    case = {
        "text": "User wants to update their profile"
    }

    result = critic.evaluate(case)

    assert result['verdict'] == 'ALLOW'
    assert 0.0 < result['confidence'] <= 1.0


def test_critic_validates_input():
    """Test that critic validates input."""
    critic = MyRuleCritic()

    # Missing 'text' field
    with pytest.raises(ValueError):
        critic.evaluate({})
```

### Integration Testing

```python
from ejc.core.ethical_reasoning_engine import EthicalReasoningEngine
from my_critic import MyRuleCritic


def test_critic_integration():
    """Test critic works with ethical reasoning engine."""
    engine = EthicalReasoningEngine()

    # Add custom critic
    my_critic = MyRuleCritic()
    engine.critics.append(my_critic)

    # Evaluate case
    case = {"text": "Test case for integration"}
    bundle = engine.evaluate(case)

    # Check critic was called
    critic_names = [c['critic'] for c in bundle['critic_outputs']]
    assert 'MyRule' in critic_names
```

## Security Best Practices

### 1. Input Validation

Always validate input before processing:

```python
def evaluate(self, case: Dict[str, Any]) -> Dict[str, Any]:
    # Automatic validation via BaseCritic
    self.validate_case(case)

    text = case.get("text", "")

    # Additional validation
    if len(text) > 50000:
        raise ValueError("Text too long")

    # Your logic here
```

### 2. Timeout Handling

Set appropriate timeouts:

```python
class MyCritic(BaseCritic):
    def __init__(self):
        super().__init__(
            name="MyCritic",
            timeout=30.0  # 30 second timeout
        )
```

### 3. Error Handling

Handle errors gracefully:

```python
def evaluate(self, case: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Your evaluation logic
        result = self._do_evaluation(case)
        return result
    except TimeoutError:
        # Let timeout errors propagate
        raise
    except Exception as e:
        # Return safe default for other errors
        return {
            "verdict": "REVIEW",
            "confidence": 0.0,
            "justification": f"Evaluation error: {str(e)}"
        }
```

### 4. API Key Security

Never hardcode API keys:

```python
# ❌ Bad
class BadCritic(BaseCritic):
    def __init__(self):
        self.api_key = "sk-1234567890"  # Never do this!

# ✅ Good
class GoodCritic(BaseCritic):
    def __init__(self, config):
        api_key = config['llm']['api_keys']['my_service']
        # Or use secrets manager
        # api_key = secrets_manager.get_secret('MY_API_KEY')
```

## Performance Optimization

### 1. Caching

Cache expensive computations:

```python
from functools import lru_cache

class MyOptimizedCritic(BaseCritic):
    def __init__(self):
        super().__init__(name="Optimized")
        self._embedding_cache = {}

    @lru_cache(maxsize=1000)
    def _get_embedding(self, text: str):
        """Cache embeddings for repeated text."""
        # Compute embedding
        return embedding
```

### 2. Async Operations

For I/O-bound critics:

```python
import asyncio

class AsyncCritic(BaseCritic):
    async def _async_evaluate(self, text: str):
        """Async evaluation for I/O operations."""
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={'text': text}) as resp:
                return await resp.json()

    def evaluate(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Sync wrapper for async operations."""
        text = case['text']
        result = asyncio.run(self._async_evaluate(text))
        return self._format_result(result)
```

## Publishing Your Critic

### 1. Package Structure

```
my-eje-critic/
├── README.md
├── setup.py
├── my_critic/
│   ├── __init__.py
│   └── critic.py
├── tests/
│   └── test_critic.py
└── examples/
    └── usage_example.py
```

### 2. Documentation

Include clear documentation:

```markdown
# My EJE Critic

## Installation
\`\`\`bash
pip install my-eje-critic
\`\`\`

## Usage
\`\`\`python
from my_critic import MyCritic

critic = MyCritic(api_key="your-key")
result = critic.evaluate({"text": "example case"})
\`\`\`

## Configuration
...
```

### 3. Versioning

Follow semantic versioning and tag releases:

```bash
git tag -a v1.0.0 -m "Initial release"
git push origin v1.0.0
```

## Community Guidelines

1. **Test Coverage**: Aim for >80% test coverage
2. **Documentation**: Provide clear README and docstrings
3. **Examples**: Include usage examples
4. **License**: Use MIT or Apache 2.0 for compatibility
5. **Dependencies**: Minimize dependencies

## Troubleshooting

### Common Issues

#### Critic Not Loading

- Check plugin path in `config/global.yaml`
- Verify class naming conventions
- Check Python import errors in logs

#### Timeout Errors

- Increase timeout value
- Check API endpoint availability
- Add retry logic

#### Validation Errors

- Ensure output format matches requirements
- Check verdict values are valid
- Verify confidence is between 0.0 and 1.0

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Support

- **Documentation**: https://eje-docs.example.com
- **Issues**: https://github.com/your-org/eje/issues
- **Community**: Slack/Discord channel
- **Email**: support@example.com
