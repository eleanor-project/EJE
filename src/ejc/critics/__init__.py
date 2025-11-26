"""
EJC Critics Module

Critic implementations for ethical evaluation.
"""

from ejc.core.base_critic import BaseCritic, RuleBasedCritic

# Import available critics
try:
    from .openai_critic import OpenAICritic
except ImportError:
    OpenAICritic = None

try:
    from .anthropic_critic import AnthropicCritic
except ImportError:
    AnthropicCritic = None

try:
    from .gemini_critic import GeminiCritic
except ImportError:
    GeminiCritic = None

__all__ = [
    "BaseCritic",
    "RuleBasedCritic",
    "OpenAICritic",
    "AnthropicCritic",
    "GeminiCritic"
]
