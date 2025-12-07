"""
S3-compatible object storage implementation using boto3.

Supports AWS S3, MinIO, and other S3-compatible services.
"""

import logging
import mimetypes
import os
from typing import Dict, List, Optional, Any, BinaryIO
from datetime import datetime
import math

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.client import Config
from botocore.exceptions import ClientError, BotoCoreError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .base import ObjectStore, ObjectMetadata, UploadResult

logger = logging.getLogger(__name__)


class S3Store(ObjectStore):
    """S3-compatible object storage implementation."""

    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        signature_version: str = "s3v4",
        max_retries: int = 3,
        connect_timeout: float = 60.0,
        read_timeout: float = 60.0,
    ):
        """
        Initialize S3 store.

        Args:
            bucket_name: Name of the S3 bucket
            aws_access_key_id: AWS access key (or from env/config)
            aws_secret_access_key: AWS secret key (or from env/config)
            region_name: AWS region
            endpoint_url: Custom endpoint (for MinIO, etc.)
            signature_version: Signature version (s3v4 recommended)
            max_retries: Maximum number of retries
            connect_timeout: Connection timeout in seconds
            read_timeout: Read timeout in seconds
        """
        super().__init__(bucket_name)
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name
        self.endpoint_url = endpoint_url
        self.signature_version = signature_version
        self.max_retries = max_retries
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.s3_client = None
        self.s3_resource = None

    def connect(self) -> None:
        """Establish connection to S3."""
        try:
            # Configure boto3
            config = Config(
                signature_version=self.signature_version,
                retries={"max_attempts": self.max_retries, "mode": "adaptive"},
                connect_timeout=self.connect_timeout,
                read_timeout=self.read_timeout,
            )

            # Create client
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region_name,
                endpoint_url=self.endpoint_url,
                config=config,
            )

            # Create resource (for higher-level operations)
            self.s3_resource = boto3.resource(
                "s3",
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region_name,
                endpoint_url=self.endpoint_url,
                config=config,
            )

            logger.info(f"Connected to S3 bucket '{self.bucket_name}'")
        except Exception as e:
            logger.error(f"Failed to connect to S3: {e}")
            raise

    def disconnect(self) -> None:
        """Close connection to S3."""
        # boto3 handles connection pooling, no explicit disconnect needed
        self.s3_client = None
        self.s3_resource = None
        logger.info("Disconnected from S3")

    def health_check(self) -> bool:
        """Check if S3 is healthy."""
        try:
            if not self.s3_client:
                return False
            # Try to list buckets as health check
            self.s3_client.list_buckets()
            return True
        except Exception as e:
            logger.error(f"S3 health check failed: {e}")
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
    )
    def create_bucket(self, **kwargs) -> None:
        """Create a new bucket."""
        if not self.s3_client:
            raise RuntimeError("Not connected to S3")

        try:
            # Create bucket with region-specific configuration
            if self.region_name == "us-east-1":
                self.s3_client.create_bucket(Bucket=self.bucket_name, **kwargs)
            else:
                location = {"LocationConstraint": self.region_name}
                self.s3_client.create_bucket(
                    Bucket=self.bucket_name,
                    CreateBucketConfiguration=location,
                    **kwargs
                )

            logger.info(f"Created S3 bucket '{self.bucket_name}'")
        except ClientError as e:
            if e.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
                logger.info(f"Bucket '{self.bucket_name}' already exists")
            else:
                logger.error(f"Failed to create bucket: {e}")
                raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
    )
    def delete_bucket(self, force: bool = False) -> None:
        """Delete the bucket."""
        if not self.s3_client:
            raise RuntimeError("Not connected to S3")

        try:
            if force:
                # Delete all objects first
                bucket = self.s3_resource.Bucket(self.bucket_name)
                bucket.objects.all().delete()

            self.s3_client.delete_bucket(Bucket=self.bucket_name)
            logger.info(f"Deleted bucket '{self.bucket_name}'")
        except Exception as e:
            logger.error(f"Failed to delete bucket: {e}")
            raise

    def bucket_exists(self) -> bool:
        """Check if bucket exists."""
        if not self.s3_client:
            raise RuntimeError("Not connected to S3")

        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def get_bucket_info(self) -> Dict[str, Any]:
        """Get bucket information."""
        if not self.s3_client:
            raise RuntimeError("Not connected to S3")

        try:
            # Get bucket location
            location = self.s3_client.get_bucket_location(Bucket=self.bucket_name)

            # Count objects (limited to first 1000)
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                MaxKeys=1000
            )
            object_count = response.get("KeyCount", 0)

            return {
                "name": self.bucket_name,
                "region": location.get("LocationConstraint", "us-east-1"),
                "object_count": object_count,
                "is_truncated": response.get("IsTruncated", False),
            }
        except Exception as e:
            logger.error(f"Failed to get bucket info: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
    )
    def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> UploadResult:
        """Upload an object."""
        if not self.s3_client:
            raise RuntimeError("Not connected to S3")

        try:
            extra_args = {
                "ContentType": content_type,
            }

            if metadata:
                extra_args["Metadata"] = metadata

            extra_args.update(kwargs)

            response = self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                **extra_args
            )

            logger.info(f"Uploaded object '{key}' ({len(data)} bytes)")

            return UploadResult(
                key=key,
                etag=response["ETag"].strip('"'),
                version_id=response.get("VersionId"),
            )
        except Exception as e:
            logger.error(f"Failed to upload object '{key}': {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
    )
    def put_object_from_file(
        self,
        key: str,
        file_path: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> UploadResult:
        """Upload an object from a file."""
        if not self.s3_client:
            raise RuntimeError("Not connected to S3")

        # Auto-detect content type if not provided
        if content_type is None:
            content_type, _ = mimetypes.guess_type(file_path)
            content_type = content_type or "application/octet-stream"

        try:
            extra_args = {
                "ContentType": content_type,
            }

            if metadata:
                extra_args["Metadata"] = metadata

            extra_args.update(kwargs)

            # Use upload_file for better performance
            self.s3_client.upload_file(
                Filename=file_path,
                Bucket=self.bucket_name,
                Key=key,
                ExtraArgs=extra_args,
            )

            # Get metadata to return etag
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )

            file_size = os.path.getsize(file_path)
            logger.info(f"Uploaded file '{file_path}' to '{key}' ({file_size} bytes)")

            return UploadResult(
                key=key,
                etag=response["ETag"].strip('"'),
                version_id=response.get("VersionId"),
            )
        except Exception as e:
            logger.error(f"Failed to upload file '{file_path}': {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
    )
    def get_object(
        self,
        key: str,
        byte_range: Optional[tuple[int, int]] = None,
    ) -> bytes:
        """Download an object."""
        if not self.s3_client:
            raise RuntimeError("Not connected to S3")

        try:
            kwargs = {"Bucket": self.bucket_name, "Key": key}

            if byte_range:
                kwargs["Range"] = f"bytes={byte_range[0]}-{byte_range[1]}"

            response = self.s3_client.get_object(**kwargs)
            data = response["Body"].read()

            logger.info(f"Downloaded object '{key}' ({len(data)} bytes)")
            return data
        except Exception as e:
            logger.error(f"Failed to download object '{key}': {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
    )
    def get_object_to_file(
        self,
        key: str,
        file_path: str,
    ) -> None:
        """Download an object to a file."""
        if not self.s3_client:
            raise RuntimeError("Not connected to S3")

        try:
            self.s3_client.download_file(
                Bucket=self.bucket_name,
                Key=key,
                Filename=file_path,
            )

            file_size = os.path.getsize(file_path)
            logger.info(f"Downloaded object '{key}' to '{file_path}' ({file_size} bytes)")
        except Exception as e:
            logger.error(f"Failed to download object '{key}' to file: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
    )
    def delete_object(self, key: str) -> bool:
        """Delete an object."""
        if not self.s3_client:
            raise RuntimeError("Not connected to S3")

        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            logger.info(f"Deleted object '{key}'")
            return True
        except Exception as e:
            logger.error(f"Failed to delete object '{key}': {e}")
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
    )
    def delete_objects(self, keys: List[str]) -> int:
        """Delete multiple objects."""
        if not self.s3_client:
            raise RuntimeError("Not connected to S3")

        if not keys:
            return 0

        try:
            # S3 delete API supports up to 1000 keys per request
            deleted_count = 0

            for i in range(0, len(keys), 1000):
                batch = keys[i:i + 1000]
                response = self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={
                        "Objects": [{"Key": key} for key in batch],
                        "Quiet": False,
                    }
                )

                deleted_count += len(response.get("Deleted", []))

            logger.info(f"Deleted {deleted_count} objects")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete objects: {e}")
            return 0

    def object_exists(self, key: str) -> bool:
        """Check if an object exists."""
        if not self.s3_client:
            raise RuntimeError("Not connected to S3")

        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def get_object_metadata(self, key: str) -> Optional[ObjectMetadata]:
        """Get metadata for an object."""
        if not self.s3_client:
            raise RuntimeError("Not connected to S3")

        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )

            return ObjectMetadata(
                key=key,
                size=response["ContentLength"],
                content_type=response.get("ContentType", "application/octet-stream"),
                etag=response["ETag"].strip('"'),
                last_modified=response.get("LastModified"),
                metadata=response.get("Metadata"),
                version_id=response.get("VersionId"),
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return None
            raise

    def multipart_upload(
        self,
        key: str,
        file_path: str,
        part_size: int = 5 * 1024 * 1024,  # 5 MB
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        progress_callback: Optional[callable] = None,
    ) -> UploadResult:
        """Upload a large file using multipart upload."""
        if not self.s3_client:
            raise RuntimeError("Not connected to S3")

        # Auto-detect content type
        if content_type is None:
            content_type, _ = mimetypes.guess_type(file_path)
            content_type = content_type or "application/octet-stream"

        file_size = os.path.getsize(file_path)
        logger.info(
            f"Starting multipart upload for '{file_path}' to '{key}' "
            f"({file_size} bytes, {part_size} bytes per part)"
        )

        try:
            # Configure transfer
            config = TransferConfig(
                multipart_threshold=part_size,
                multipart_chunksize=part_size,
                max_concurrency=10,
            )

            extra_args = {
                "ContentType": content_type,
            }

            if metadata:
                extra_args["Metadata"] = metadata

            # Track progress
            bytes_uploaded = 0

            def upload_progress(bytes_amount):
                nonlocal bytes_uploaded
                bytes_uploaded += bytes_amount
                if progress_callback:
                    progress_callback(bytes_uploaded, file_size)

            # Upload with progress tracking
            self.s3_client.upload_file(
                Filename=file_path,
                Bucket=self.bucket_name,
                Key=key,
                ExtraArgs=extra_args,
                Config=config,
                Callback=upload_progress,
            )

            # Get metadata
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )

            logger.info(f"Completed multipart upload for '{key}'")

            return UploadResult(
                key=key,
                etag=response["ETag"].strip('"'),
                version_id=response.get("VersionId"),
            )
        except Exception as e:
            logger.error(f"Failed multipart upload for '{key}': {e}")
            raise

    def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        method: str = "GET",
    ) -> str:
        """Generate a presigned URL."""
        if not self.s3_client:
            raise RuntimeError("Not connected to S3")

        try:
            # Map HTTP method to boto3 client method
            client_method_map = {
                "GET": "get_object",
                "PUT": "put_object",
                "DELETE": "delete_object",
            }

            client_method = client_method_map.get(method.upper(), "get_object")

            url = self.s3_client.generate_presigned_url(
                ClientMethod=client_method,
                Params={
                    "Bucket": self.bucket_name,
                    "Key": key,
                },
                ExpiresIn=expiration,
            )

            logger.info(f"Generated presigned URL for '{key}' (expires in {expiration}s)")
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for '{key}': {e}")
            raise

    def generate_presigned_post(
        self,
        key: str,
        expiration: int = 3600,
        conditions: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """Generate presigned POST data."""
        if not self.s3_client:
            raise RuntimeError("Not connected to S3")

        try:
            fields = {"key": key}

            if conditions is None:
                conditions = [{"key": key}]

            response = self.s3_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=key,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=expiration,
            )

            logger.info(f"Generated presigned POST for '{key}' (expires in {expiration}s)")
            return response
        except Exception as e:
            logger.error(f"Failed to generate presigned POST for '{key}': {e}")
            raise

    def list_objects(
        self,
        prefix: str = "",
        delimiter: str = "",
        max_keys: int = 1000,
    ) -> List[ObjectMetadata]:
        """List objects in the bucket."""
        if not self.s3_client:
            raise RuntimeError("Not connected to S3")

        try:
            kwargs = {
                "Bucket": self.bucket_name,
                "MaxKeys": max_keys,
            }

            if prefix:
                kwargs["Prefix"] = prefix
            if delimiter:
                kwargs["Delimiter"] = delimiter

            response = self.s3_client.list_objects_v2(**kwargs)

            objects = []
            for obj in response.get("Contents", []):
                objects.append(
                    ObjectMetadata(
                        key=obj["Key"],
                        size=obj["Size"],
                        content_type="application/octet-stream",  # Not provided in list
                        etag=obj["ETag"].strip('"'),
                        last_modified=obj.get("LastModified"),
                    )
                )

            logger.info(f"Listed {len(objects)} objects with prefix '{prefix}'")
            return objects
        except Exception as e:
            logger.error(f"Failed to list objects: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
    )
    def copy_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> UploadResult:
        """Copy an object."""
        if not self.s3_client:
            raise RuntimeError("Not connected to S3")

        try:
            copy_source = {
                "Bucket": self.bucket_name,
                "Key": source_key,
            }

            kwargs = {
                "CopySource": copy_source,
                "Bucket": self.bucket_name,
                "Key": dest_key,
            }

            if metadata:
                kwargs["Metadata"] = metadata
                kwargs["MetadataDirective"] = "REPLACE"

            response = self.s3_client.copy_object(**kwargs)

            logger.info(f"Copied object '{source_key}' to '{dest_key}'")

            return UploadResult(
                key=dest_key,
                etag=response["CopyObjectResult"]["ETag"].strip('"'),
                version_id=response.get("VersionId"),
            )
        except Exception as e:
            logger.error(f"Failed to copy object '{source_key}' to '{dest_key}': {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the bucket."""
        if not self.s3_client:
            raise RuntimeError("Not connected to S3")

        try:
            # List first 1000 objects to get basic stats
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                MaxKeys=1000
            )

            objects = response.get("Contents", [])
            total_size = sum(obj["Size"] for obj in objects)

            return {
                "backend": "s3",
                "bucket": self.bucket_name,
                "region": self.region_name,
                "object_count": len(objects),
                "total_size": total_size,
                "is_truncated": response.get("IsTruncated", False),
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise
