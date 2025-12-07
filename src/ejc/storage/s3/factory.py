"""
Factory for creating object store instances.

Provides easy initialization based on environment variables or configuration.
"""

import os
import logging
from typing import Optional

from .base import ObjectStore
from .s3_store import S3Store

logger = logging.getLogger(__name__)


def get_objectstore_backend() -> str:
    """
    Get the configured object storage backend from environment.

    Returns:
        Backend name (currently only 's3')

    Raises:
        ValueError: If no backend is configured
    """
    backend = os.getenv("OBJECTSTORE_BACKEND", "s3").lower()

    if backend not in ["s3"]:
        raise ValueError(
            f"Invalid OBJECTSTORE_BACKEND: {backend}. "
            "Currently only 's3' is supported"
        )

    return backend


def init_objectstore(
    backend: Optional[str] = None,
    **kwargs
) -> ObjectStore:
    """
    Initialize an object store based on configuration.

    Args:
        backend: Backend to use (s3). If None, uses OBJECTSTORE_BACKEND env var
        **kwargs: Backend-specific parameters (override env vars)

    Returns:
        Initialized ObjectStore instance

    Raises:
        ValueError: If backend is invalid or required config is missing

    Environment Variables:
        OBJECTSTORE_BACKEND: Backend to use (default: s3)

        For S3:
            S3_BUCKET_NAME: S3 bucket name (required)
            AWS_ACCESS_KEY_ID: AWS access key (optional, from ~/.aws/credentials)
            AWS_SECRET_ACCESS_KEY: AWS secret key (optional, from ~/.aws/credentials)
            AWS_REGION: AWS region (default: us-east-1)
            S3_ENDPOINT_URL: Custom endpoint for MinIO/etc (optional)
            S3_SIGNATURE_VERSION: Signature version (default: s3v4)
            S3_MAX_RETRIES: Maximum retries (default: 3)

    Examples:
        # Using environment variables
        store = init_objectstore()

        # Explicit backend selection
        store = init_objectstore(backend="s3")

        # With custom parameters
        store = init_objectstore(
            backend="s3",
            bucket_name="my-bucket",
            aws_access_key_id="...",
            aws_secret_access_key="...",
        )

        # For MinIO
        store = init_objectstore(
            backend="s3",
            bucket_name="my-bucket",
            endpoint_url="http://localhost:9000",
            aws_access_key_id="minioadmin",
            aws_secret_access_key="minioadmin",
        )
    """
    if backend is None:
        backend = get_objectstore_backend()

    backend = backend.lower()
    logger.info(f"Initializing object store with backend: {backend}")

    if backend == "s3":
        return _init_s3(**kwargs)
    else:
        raise ValueError(
            f"Unknown backend: {backend}. "
            "Currently only 's3' is supported"
        )


def _init_s3(**kwargs) -> S3Store:
    """Initialize S3 object store."""
    bucket_name = kwargs.get("bucket_name") or os.getenv("S3_BUCKET_NAME")
    if not bucket_name:
        raise ValueError(
            "S3 bucket name not found. "
            "Set S3_BUCKET_NAME environment variable or pass bucket_name parameter"
        )

    config = {
        "bucket_name": bucket_name,
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "region_name": os.getenv("AWS_REGION", "us-east-1"),
        "endpoint_url": os.getenv("S3_ENDPOINT_URL"),
        "signature_version": os.getenv("S3_SIGNATURE_VERSION", "s3v4"),
        "max_retries": int(os.getenv("S3_MAX_RETRIES", "3")),
        "connect_timeout": float(os.getenv("S3_CONNECT_TIMEOUT", "60.0")),
        "read_timeout": float(os.getenv("S3_READ_TIMEOUT", "60.0")),
    }

    # Override with kwargs
    config.update(kwargs)

    logger.info(
        f"Initializing S3 with bucket '{config['bucket_name']}' "
        f"in region '{config['region_name']}'"
    )

    return S3Store(**config)


def create_bucket_if_not_exists(store: ObjectStore, **kwargs) -> None:
    """
    Create bucket if it doesn't exist.

    Args:
        store: ObjectStore instance
        **kwargs: Backend-specific parameters

    Example:
        store = init_objectstore()
        store.connect()
        create_bucket_if_not_exists(store)
    """
    try:
        exists = store.bucket_exists()
        if not exists:
            logger.info(f"Creating bucket '{store.bucket_name}'")
            store.create_bucket(**kwargs)
        else:
            logger.info(f"Bucket '{store.bucket_name}' already exists")
    except Exception as e:
        logger.error(f"Failed to create bucket: {e}")
        raise
