"""
Secrets Management Module for EJE.
Supports multiple secret backends: environment variables, AWS Secrets Manager, HashiCorp Vault.
"""
import os
import json
from typing import Dict, Any, Optional, Protocol
from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging


logger = logging.getLogger(__name__)


class SecretsBackend(Protocol):
    """Protocol for secrets backend implementations."""

    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret value by key."""
        ...

    def get_secrets_batch(self, keys: list[str]) -> Dict[str, Optional[str]]:
        """Retrieve multiple secrets at once."""
        ...


@dataclass
class SecretRotationConfig:
    """Configuration for API key rotation."""
    rotation_enabled: bool = False
    rotation_interval_days: int = 30
    notify_before_expiry_days: int = 7
    auto_rotate: bool = False


class EnvironmentSecretsBackend:
    """
    Secrets backend using environment variables.
    Simple and suitable for development/testing.
    """

    def __init__(self, prefix: str = ""):
        """
        Initialize environment secrets backend.

        Args:
            prefix: Optional prefix for environment variable names (e.g., "EJE_")
        """
        self.prefix = prefix

    def get_secret(self, key: str) -> Optional[str]:
        """
        Retrieve secret from environment variable.

        Args:
            key: Secret key name

        Returns:
            Secret value or None if not found
        """
        env_key = f"{self.prefix}{key}"
        value = os.getenv(env_key)
        if value:
            logger.debug(f"Retrieved secret '{key}' from environment")
        else:
            logger.warning(f"Secret '{key}' not found in environment")
        return value

    def get_secrets_batch(self, keys: list[str]) -> Dict[str, Optional[str]]:
        """Retrieve multiple secrets from environment."""
        return {key: self.get_secret(key) for key in keys}


class AWSSecretsManagerBackend:
    """
    Secrets backend using AWS Secrets Manager.
    Suitable for production deployments on AWS.
    """

    def __init__(self, region_name: str = "us-east-1"):
        """
        Initialize AWS Secrets Manager backend.

        Args:
            region_name: AWS region for Secrets Manager
        """
        self.region_name = region_name
        self._client = None

    @property
    def client(self):
        """Lazy-load boto3 client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    service_name='secretsmanager',
                    region_name=self.region_name
                )
                logger.info(f"Initialized AWS Secrets Manager client (region: {self.region_name})")
            except ImportError:
                raise ImportError(
                    "boto3 is required for AWS Secrets Manager backend. "
                    "Install it with: pip install boto3"
                )
            except Exception as e:
                logger.error(f"Failed to initialize AWS Secrets Manager: {e}")
                raise
        return self._client

    def get_secret(self, key: str) -> Optional[str]:
        """
        Retrieve secret from AWS Secrets Manager.

        Args:
            key: Secret name in AWS Secrets Manager

        Returns:
            Secret value or None if not found
        """
        try:
            response = self.client.get_secret_value(SecretId=key)
            if 'SecretString' in response:
                logger.debug(f"Retrieved secret '{key}' from AWS Secrets Manager")
                return response['SecretString']
            else:
                logger.error(f"Secret '{key}' is not a string secret")
                return None
        except self.client.exceptions.ResourceNotFoundException:
            logger.warning(f"Secret '{key}' not found in AWS Secrets Manager")
            return None
        except Exception as e:
            logger.error(f"Error retrieving secret '{key}' from AWS: {e}")
            return None

    def get_secrets_batch(self, keys: list[str]) -> Dict[str, Optional[str]]:
        """Retrieve multiple secrets from AWS Secrets Manager."""
        return {key: self.get_secret(key) for key in keys}


class HashiCorpVaultBackend:
    """
    Secrets backend using HashiCorp Vault.
    Suitable for enterprise deployments with Vault infrastructure.
    """

    def __init__(
        self,
        vault_url: str,
        vault_token: Optional[str] = None,
        mount_point: str = "secret",
        namespace: Optional[str] = None
    ):
        """
        Initialize HashiCorp Vault backend.

        Args:
            vault_url: Vault server URL (e.g., "https://vault.example.com:8200")
            vault_token: Vault authentication token (can also use env var VAULT_TOKEN)
            mount_point: Secret engine mount point (default: "secret")
            namespace: Vault namespace (for Vault Enterprise)
        """
        self.vault_url = vault_url
        self.vault_token = vault_token or os.getenv("VAULT_TOKEN")
        self.mount_point = mount_point
        self.namespace = namespace
        self._client = None

    @property
    def client(self):
        """Lazy-load hvac client."""
        if self._client is None:
            try:
                import hvac
                self._client = hvac.Client(
                    url=self.vault_url,
                    token=self.vault_token,
                    namespace=self.namespace
                )
                if not self._client.is_authenticated():
                    raise RuntimeError("Failed to authenticate with Vault")
                logger.info(f"Initialized HashiCorp Vault client (url: {self.vault_url})")
            except ImportError:
                raise ImportError(
                    "hvac is required for HashiCorp Vault backend. "
                    "Install it with: pip install hvac"
                )
            except Exception as e:
                logger.error(f"Failed to initialize Vault client: {e}")
                raise
        return self._client

    def get_secret(self, key: str) -> Optional[str]:
        """
        Retrieve secret from HashiCorp Vault.

        Args:
            key: Secret path in Vault (e.g., "eje/api_keys/openai")

        Returns:
            Secret value or None if not found
        """
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=key,
                mount_point=self.mount_point
            )
            data = response['data']['data']
            # If the secret has a 'value' field, return that, otherwise return the whole data as JSON
            if 'value' in data:
                logger.debug(f"Retrieved secret '{key}' from Vault")
                return data['value']
            else:
                logger.debug(f"Retrieved secret '{key}' from Vault (as JSON)")
                return json.dumps(data)
        except Exception as e:
            logger.warning(f"Error retrieving secret '{key}' from Vault: {e}")
            return None

    def get_secrets_batch(self, keys: list[str]) -> Dict[str, Optional[str]]:
        """Retrieve multiple secrets from Vault."""
        return {key: self.get_secret(key) for key in keys}


class CascadingSecretsManager:
    """
    Secrets manager that tries multiple backends in order.
    Falls back to next backend if secret not found in current backend.
    """

    def __init__(self, backends: list[SecretsBackend], cache_secrets: bool = True):
        """
        Initialize cascading secrets manager.

        Args:
            backends: List of secrets backends to try in order
            cache_secrets: Whether to cache retrieved secrets in memory
        """
        self.backends = backends
        self.cache_secrets = cache_secrets
        self._cache: Dict[str, str] = {}

    def get_secret(self, key: str, use_cache: bool = True) -> Optional[str]:
        """
        Retrieve secret from backends in order.

        Args:
            key: Secret key name
            use_cache: Whether to use cached value if available

        Returns:
            Secret value or None if not found in any backend
        """
        # Check cache first
        if use_cache and self.cache_secrets and key in self._cache:
            logger.debug(f"Retrieved secret '{key}' from cache")
            return self._cache[key]

        # Try each backend in order
        for backend in self.backends:
            value = backend.get_secret(key)
            if value is not None:
                if self.cache_secrets:
                    self._cache[key] = value
                return value

        logger.error(f"Secret '{key}' not found in any backend")
        return None

    def get_secrets_batch(self, keys: list[str]) -> Dict[str, Optional[str]]:
        """Retrieve multiple secrets, trying all backends for each."""
        return {key: self.get_secret(key) for key in keys}

    def clear_cache(self):
        """Clear the secrets cache."""
        self._cache.clear()
        logger.info("Secrets cache cleared")


class SecretsManagerFactory:
    """Factory for creating secrets manager instances based on configuration."""

    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> CascadingSecretsManager:
        """
        Create secrets manager from configuration.

        Args:
            config: Configuration dictionary with secrets_backend settings

        Returns:
            Configured CascadingSecretsManager instance

        Example config:
            {
                'secrets': {
                    'backends': ['environment', 'aws', 'vault'],
                    'aws_region': 'us-east-1',
                    'vault_url': 'https://vault.example.com:8200',
                    'vault_mount_point': 'secret',
                    'env_prefix': 'EJE_',
                    'cache_enabled': True
                }
            }
        """
        secrets_config = config.get('secrets', {})
        backend_names = secrets_config.get('backends', ['environment'])
        cache_enabled = secrets_config.get('cache_enabled', True)

        backends = []

        for backend_name in backend_names:
            if backend_name == 'environment':
                env_prefix = secrets_config.get('env_prefix', '')
                backends.append(EnvironmentSecretsBackend(prefix=env_prefix))
                logger.info("Added environment secrets backend")

            elif backend_name == 'aws':
                aws_region = secrets_config.get('aws_region', 'us-east-1')
                backends.append(AWSSecretsManagerBackend(region_name=aws_region))
                logger.info(f"Added AWS Secrets Manager backend (region: {aws_region})")

            elif backend_name == 'vault':
                vault_url = secrets_config.get('vault_url')
                if not vault_url:
                    logger.warning("Vault backend requested but vault_url not configured")
                    continue
                vault_token = secrets_config.get('vault_token')
                vault_mount = secrets_config.get('vault_mount_point', 'secret')
                vault_namespace = secrets_config.get('vault_namespace')
                backends.append(HashiCorpVaultBackend(
                    vault_url=vault_url,
                    vault_token=vault_token,
                    mount_point=vault_mount,
                    namespace=vault_namespace
                ))
                logger.info(f"Added HashiCorp Vault backend (url: {vault_url})")

            else:
                logger.warning(f"Unknown secrets backend: {backend_name}")

        if not backends:
            logger.warning("No secrets backends configured, using environment variables")
            backends.append(EnvironmentSecretsBackend())

        return CascadingSecretsManager(backends=backends, cache_secrets=cache_enabled)


# Convenience function for common use case
def get_api_keys(secrets_manager: CascadingSecretsManager) -> Dict[str, Optional[str]]:
    """
    Retrieve all API keys needed for EJE critics.

    Args:
        secrets_manager: Configured secrets manager instance

    Returns:
        Dictionary of API keys
    """
    keys = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY']
    return secrets_manager.get_secrets_batch(keys)


# Key rotation utilities
class APIKeyRotationManager:
    """Manages API key rotation schedules and notifications."""

    def __init__(self, secrets_manager: CascadingSecretsManager, config: SecretRotationConfig):
        """
        Initialize key rotation manager.

        Args:
            secrets_manager: Secrets manager instance
            config: Rotation configuration
        """
        self.secrets_manager = secrets_manager
        self.config = config
        self._rotation_schedule: Dict[str, Any] = {}

    def register_key(self, key_name: str, created_at: str, expires_at: Optional[str] = None):
        """
        Register a key for rotation tracking.

        Args:
            key_name: Name of the API key
            created_at: ISO 8601 timestamp when key was created
            expires_at: Optional expiry timestamp
        """
        self._rotation_schedule[key_name] = {
            'created_at': created_at,
            'expires_at': expires_at,
            'last_rotated': None
        }
        logger.info(f"Registered key '{key_name}' for rotation tracking")

    def check_rotation_needed(self, key_name: str) -> bool:
        """
        Check if a key needs rotation.

        Args:
            key_name: Name of the API key

        Returns:
            True if rotation is needed
        """
        if key_name not in self._rotation_schedule:
            return False

        # Implementation would check creation date, expiry, etc.
        # Placeholder for now
        return False

    def rotate_key(self, key_name: str, new_value: str):
        """
        Rotate an API key.

        Args:
            key_name: Name of the API key
            new_value: New key value
        """
        # In production, this would update the secret in the backend
        # and trigger application reload/restart
        logger.info(f"Key rotation requested for '{key_name}'")
        # Clear cache to force reload
        self.secrets_manager.clear_cache()
