"""
Abstract base class for object storage backends.

Defines the interface that all object storage implementations must follow.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, BinaryIO
from datetime import datetime
import io


@dataclass
class ObjectMetadata:
    """Metadata associated with a stored object."""

    key: str
    size: int
    content_type: str
    etag: Optional[str] = None
    last_modified: Optional[datetime] = None
    metadata: Optional[Dict[str, str]] = None
    version_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "size": self.size,
            "content_type": self.content_type,
            "etag": self.etag,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "metadata": self.metadata or {},
            "version_id": self.version_id,
        }


@dataclass
class UploadResult:
    """Result from an upload operation."""

    key: str
    etag: str
    version_id: Optional[str] = None
    location: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "etag": self.etag,
            "version_id": self.version_id,
            "location": self.location,
        }


class ObjectStore(ABC):
    """
    Abstract base class for object storage backends.

    All object storage implementations (S3, MinIO, etc.)
    must implement this interface.
    """

    def __init__(self, bucket_name: str):
        """
        Initialize object store.

        Args:
            bucket_name: Name of the bucket to use
        """
        self.bucket_name = bucket_name

    # Connection and Health

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the object storage."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the object storage."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the object storage is healthy and reachable.

        Returns:
            True if healthy, False otherwise
        """
        pass

    # Bucket Management

    @abstractmethod
    def create_bucket(self, **kwargs) -> None:
        """
        Create a new bucket.

        Args:
            **kwargs: Backend-specific parameters
        """
        pass

    @abstractmethod
    def delete_bucket(self, force: bool = False) -> None:
        """
        Delete the bucket.

        Args:
            force: If True, delete even if bucket is not empty
        """
        pass

    @abstractmethod
    def bucket_exists(self) -> bool:
        """
        Check if the bucket exists.

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    def get_bucket_info(self) -> Dict[str, Any]:
        """
        Get information about the bucket.

        Returns:
            Dictionary with bucket metadata
        """
        pass

    # Object Operations

    @abstractmethod
    def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> UploadResult:
        """
        Upload an object.

        Args:
            key: Object key (path)
            data: Binary data to upload
            content_type: MIME type
            metadata: Custom metadata
            **kwargs: Backend-specific parameters

        Returns:
            Upload result with etag and version
        """
        pass

    @abstractmethod
    def put_object_from_file(
        self,
        key: str,
        file_path: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> UploadResult:
        """
        Upload an object from a file.

        Args:
            key: Object key (path)
            file_path: Path to file to upload
            content_type: MIME type (auto-detected if None)
            metadata: Custom metadata
            **kwargs: Backend-specific parameters

        Returns:
            Upload result
        """
        pass

    @abstractmethod
    def get_object(
        self,
        key: str,
        byte_range: Optional[tuple[int, int]] = None,
    ) -> bytes:
        """
        Download an object.

        Args:
            key: Object key (path)
            byte_range: Optional (start, end) byte range

        Returns:
            Binary data
        """
        pass

    @abstractmethod
    def get_object_to_file(
        self,
        key: str,
        file_path: str,
    ) -> None:
        """
        Download an object to a file.

        Args:
            key: Object key (path)
            file_path: Path to save file
        """
        pass

    @abstractmethod
    def delete_object(self, key: str) -> bool:
        """
        Delete an object.

        Args:
            key: Object key (path)

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def delete_objects(self, keys: List[str]) -> int:
        """
        Delete multiple objects.

        Args:
            keys: List of object keys

        Returns:
            Number of objects deleted
        """
        pass

    @abstractmethod
    def object_exists(self, key: str) -> bool:
        """
        Check if an object exists.

        Args:
            key: Object key (path)

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    def get_object_metadata(self, key: str) -> Optional[ObjectMetadata]:
        """
        Get metadata for an object.

        Args:
            key: Object key (path)

        Returns:
            Object metadata or None if not found
        """
        pass

    # Multipart Upload

    @abstractmethod
    def multipart_upload(
        self,
        key: str,
        file_path: str,
        part_size: int = 5 * 1024 * 1024,  # 5 MB
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        progress_callback: Optional[callable] = None,
    ) -> UploadResult:
        """
        Upload a large file using multipart upload.

        Args:
            key: Object key (path)
            file_path: Path to file to upload
            part_size: Size of each part in bytes (min 5MB)
            content_type: MIME type
            metadata: Custom metadata
            progress_callback: Optional callback(bytes_uploaded, total_bytes)

        Returns:
            Upload result
        """
        pass

    # Presigned URLs

    @abstractmethod
    def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        method: str = "GET",
    ) -> str:
        """
        Generate a presigned URL for temporary access.

        Args:
            key: Object key (path)
            expiration: URL expiration in seconds
            method: HTTP method (GET, PUT, etc.)

        Returns:
            Presigned URL
        """
        pass

    @abstractmethod
    def generate_presigned_post(
        self,
        key: str,
        expiration: int = 3600,
        conditions: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate presigned POST data for browser uploads.

        Args:
            key: Object key (path)
            expiration: Expiration in seconds
            conditions: Upload conditions

        Returns:
            Dictionary with URL and form fields
        """
        pass

    # List Operations

    @abstractmethod
    def list_objects(
        self,
        prefix: str = "",
        delimiter: str = "",
        max_keys: int = 1000,
    ) -> List[ObjectMetadata]:
        """
        List objects in the bucket.

        Args:
            prefix: Filter by prefix
            delimiter: Delimiter for hierarchical listing
            max_keys: Maximum number of keys to return

        Returns:
            List of object metadata
        """
        pass

    # Copy Operations

    @abstractmethod
    def copy_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> UploadResult:
        """
        Copy an object within the same bucket.

        Args:
            source_key: Source object key
            dest_key: Destination object key
            metadata: New metadata (if None, copies from source)

        Returns:
            Upload result for destination
        """
        pass

    # Statistics

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the object store.

        Returns:
            Dictionary with stats (count, size, etc.)
        """
        pass
