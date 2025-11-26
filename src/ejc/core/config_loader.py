import os
from typing import Any, Dict, List

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError, validator


class LLMConfig(BaseModel):
    critic_model_name: str
    security_model_name: str
    api_keys: Dict[str, str] = Field(default_factory=dict)

    @validator("api_keys")
    def require_keys(cls, v: Dict[str, str]) -> Dict[str, str]:
        for key in ("openai", "anthropic", "gemini"):
            v.setdefault(key, "")
        return v


class GlobalConfig(BaseModel):
    block_threshold: float = Field(0.5, ge=0.0, le=1.0)
    ambiguity_threshold: float = Field(0.25, ge=0.0, le=1.0)
    critic_priorities: Dict[str, str] = Field(default_factory=dict)
    plugin_critics: List[str] = Field(default_factory=list)
    governance: Dict[str, Any] = Field(default_factory=dict)
    critics: List[Any] = Field(default_factory=list)
    aggregation: Dict[str, Any] = Field(default_factory=dict)
    precedent: Dict[str, Any] = Field(default_factory=dict)
    llm: LLMConfig

    class Config:
        extra = "allow"

    @validator("plugin_critics", each_item=True)
    def validate_plugin_path(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Plugin path must be a non-empty string")
        if not v.endswith(".py"):
            raise ValueError("Plugin critic entries must point to .py files")
        return v


def _inject_env_api_keys(config: Dict[str, Any]) -> None:
    if 'llm' in config and 'api_keys' in config['llm']:
        api_keys = config['llm']['api_keys']

        api_keys['openai'] = os.getenv('OPENAI_API_KEY', api_keys.get('openai', ''))
        api_keys['anthropic'] = os.getenv('ANTHROPIC_API_KEY', api_keys.get('anthropic', ''))
        api_keys['gemini'] = os.getenv('GEMINI_API_KEY', api_keys.get('gemini', ''))


def load_global_config(config_path: str) -> Dict[str, Any]:
    # Load environment variables from .env file if it exists
    load_dotenv()

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f) or {}

    # Override API keys with environment variables if present
    _inject_env_api_keys(config)

    try:
        validated = GlobalConfig.model_validate(config)
    except ValidationError as exc:
        raise ValueError(f"Invalid global configuration: {exc}") from exc

    return validated.model_dump()
