"""
S3-compatible object storage for evidence bundles and attachments.

Provides abstract interface and S3/MinIO backend implementations
for storing and retrieving binary objects.
"""

from .base import ObjectStore, ObjectMetadata, UploadResult
from .factory import init_objectstore, get_objectstore_backend
from .s3_store import S3Store
from .evidence import EvidenceBundle, store_evidence_bundle, retrieve_evidence_bundle

__all__ = [
    "ObjectStore",
    "ObjectMetadata",
    "UploadResult",
    "init_objectstore",
    "get_objectstore_backend",
    "S3Store",
    "EvidenceBundle",
    "store_evidence_bundle",
    "retrieve_evidence_bundle",
]
