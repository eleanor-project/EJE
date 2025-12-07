

 # S3-Compatible Object Storage

Production-ready object storage for evidence bundles, attachments, and artifacts using AWS S3 or compatible services (MinIO, etc.).

## Overview

The S3 storage layer provides reliable object storage with:

- **AWS S3 Support** - Native integration with Amazon S3
- **MinIO Support** - Works with MinIO and other S3-compatible services
- **Retry Logic** - Automatic retry with exponential backoff
- **Multipart Upload** - Efficient upload of large files
- **Presigned URLs** - Temporary access URLs for secure sharing
- **Evidence Bundles** - Structured storage for decision evidence
- **Attachments** - Binary file storage with metadata

## Quick Start

### 1. Configure S3

Set up environment variables:

```bash
export S3_BUCKET_NAME=eje-evidence
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_REGION=us-east-1
```

### 2. Initialize and Use

```python
from ejc.storage.s3 import init_objectstore

# Initialize object store
store = init_objectstore()
store.connect()

# Upload a file
result = store.put_object_from_file(
    key="evidence/decision/dec-123.json",
    file_path="/path/to/evidence.json",
    content_type="application/json",
)

# Download a file
data = store.get_object(key="evidence/decision/dec-123.json")

# List objects
objects = store.list_objects(prefix="evidence/decision/")

# Cleanup
store.disconnect()
```

### 3. Evidence Bundles

High-level API for evidence storage:

```python
from ejc.storage.s3 import (
    init_objectstore,
    EvidenceBundle,
    store_evidence_bundle,
    retrieve_evidence_bundle,
)
from datetime import datetime

store = init_objectstore()
store.connect()

# Create evidence bundle
bundle = EvidenceBundle(
    decision_id="dec-123",
    evidence_data={
        "verdict": "ALLOW",
        "confidence": 0.95,
        "critics": [
            {"name": "safety", "score": 0.9},
            {"name": "ethics", "score": 0.92},
        ],
    },
    created_at=datetime.utcnow(),
    evidence_type="decision",
)

# Store bundle
key = store_evidence_bundle(store, bundle)
print(f"Stored at: {key}")

# Retrieve bundle
retrieved = retrieve_evidence_bundle(store, decision_id="dec-123")
print(f"Verdict: {retrieved.evidence_data['verdict']}")
```

## Environment Variables

### Required

- `S3_BUCKET_NAME` - S3 bucket name

### Optional

- `AWS_ACCESS_KEY_ID` - AWS access key (or use ~/.aws/credentials)
- `AWS_SECRET_ACCESS_KEY` - AWS secret key (or use ~/.aws/credentials)
- `AWS_REGION` - AWS region (default: us-east-1)
- `S3_ENDPOINT_URL` - Custom endpoint for MinIO/etc (optional)
- `S3_SIGNATURE_VERSION` - Signature version (default: s3v4)
- `S3_MAX_RETRIES` - Maximum retries (default: 3)
- `S3_CONNECT_TIMEOUT` - Connection timeout in seconds (default: 60.0)
- `S3_READ_TIMEOUT` - Read timeout in seconds (default: 60.0)

## Using MinIO

MinIO is an S3-compatible object storage server that's perfect for development and self-hosted deployments.

### Start MinIO with Docker

```bash
docker run -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"
```

### Configure for MinIO

```bash
export S3_BUCKET_NAME=eje-evidence
export S3_ENDPOINT_URL=http://localhost:9000
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin
export AWS_REGION=us-east-1
```

```python
from ejc.storage.s3 import init_objectstore, create_bucket_if_not_exists

# Initialize
store = init_objectstore()
store.connect()

# Create bucket if needed
create_bucket_if_not_exists(store)
```

## Core Operations

### Upload Operations

```python
from ejc.storage.s3 import init_objectstore

store = init_objectstore()
store.connect()

# Upload bytes
data = b'{"test": "data"}'
result = store.put_object(
    key="test/file.json",
    data=data,
    content_type="application/json",
    metadata={"decision-id": "dec-123"},
)
print(f"Uploaded with etag: {result.etag}")

# Upload from file
result = store.put_object_from_file(
    key="test/large-file.bin",
    file_path="/path/to/file.bin",
    content_type="application/octet-stream",
)

# Upload with multipart (for large files > 5MB)
result = store.multipart_upload(
    key="test/very-large-file.bin",
    file_path="/path/to/large-file.bin",
    part_size=10 * 1024 * 1024,  # 10 MB parts
    progress_callback=lambda uploaded, total: print(f"{uploaded}/{total} bytes"),
)
```

### Download Operations

```python
# Download to memory
data = store.get_object(key="test/file.json")

# Download byte range
partial_data = store.get_object(
    key="test/file.bin",
    byte_range=(0, 1024),  # First 1KB
)

# Download to file
store.get_object_to_file(
    key="test/file.json",
    file_path="/path/to/save.json",
)
```

### Delete Operations

```python
# Delete single object
deleted = store.delete_object(key="test/file.json")

# Delete multiple objects
keys = ["test/file1.json", "test/file2.json", "test/file3.json"]
deleted_count = store.delete_objects(keys)
print(f"Deleted {deleted_count} objects")
```

### List Operations

```python
# List all objects
objects = store.list_objects()

# List with prefix
objects = store.list_objects(prefix="evidence/decision/2024/01/")

# List with delimiter (hierarchical)
objects = store.list_objects(
    prefix="evidence/",
    delimiter="/",
    max_keys=100,
)

for obj in objects:
    print(f"{obj.key} - {obj.size} bytes - {obj.last_modified}")
```

### Copy Operations

```python
# Copy object within bucket
result = store.copy_object(
    source_key="evidence/decision/dec-123.json",
    dest_key="archive/decision/dec-123.json",
    metadata={"archived": "true"},
)
```

### Metadata Operations

```python
# Check if object exists
exists = store.object_exists(key="test/file.json")

# Get object metadata
metadata = store.get_object_metadata(key="test/file.json")
if metadata:
    print(f"Size: {metadata.size} bytes")
    print(f"Content-Type: {metadata.content_type}")
    print(f"ETag: {metadata.etag}")
    print(f"Last Modified: {metadata.last_modified}")
    print(f"Custom Metadata: {metadata.metadata}")
```

## Presigned URLs

Generate temporary URLs for secure access without credentials:

```python
from ejc.storage.s3 import init_objectstore

store = init_objectstore()
store.connect()

# Generate GET URL (download)
url = store.generate_presigned_url(
    key="evidence/decision/dec-123.json",
    expiration=3600,  # 1 hour
    method="GET",
)
print(f"Share this URL: {url}")

# Generate PUT URL (upload)
upload_url = store.generate_presigned_url(
    key="uploads/new-file.json",
    expiration=1800,  # 30 minutes
    method="PUT",
)
print(f"Upload to this URL: {upload_url}")

# Generate presigned POST (for browser uploads)
post_data = store.generate_presigned_post(
    key="uploads/browser-upload.json",
    expiration=3600,
    conditions=[
        {"bucket": store.bucket_name},
        ["content-length-range", 0, 10485760],  # Max 10MB
    ],
)
print(f"POST to: {post_data['url']}")
print(f"Form fields: {post_data['fields']}")
```

## Evidence Bundles

Structured storage for decision evidence with metadata and checksums:

```python
from ejc.storage.s3 import (
    init_objectstore,
    EvidenceBundle,
    store_evidence_bundle,
    retrieve_evidence_bundle,
    list_evidence_bundles,
    delete_evidence_bundle,
    generate_presigned_url_for_evidence,
)
from datetime import datetime

store = init_objectstore()
store.connect()

# Create evidence bundle
bundle = EvidenceBundle(
    decision_id="dec-123",
    evidence_data={
        "query": "Should I process this request?",
        "verdict": "ALLOW",
        "confidence": 0.95,
        "critics": [
            {"name": "safety", "verdict": "ALLOW", "score": 0.9},
            {"name": "ethics", "verdict": "ALLOW", "score": 0.92},
            {"name": "legal", "verdict": "ALLOW", "score": 0.98},
        ],
        "reasoning": "All critics approved with high confidence",
    },
    created_at=datetime.utcnow(),
    evidence_type="decision",
    metadata={"environment": "production"},
)

# Store bundle (auto-generates key with date structure)
key = store_evidence_bundle(store, bundle, verify_checksum=True)
# Key format: evidence/decision/2024/01/dec-123.json

# Retrieve bundle by decision ID
retrieved = retrieve_evidence_bundle(
    store,
    decision_id="dec-123",
    verify_checksum=True,
)

if retrieved:
    print(f"Verdict: {retrieved.evidence_data['verdict']}")
    print(f"Confidence: {retrieved.evidence_data['confidence']}")
    print(f"Checksum: {retrieved.checksum}")

# List all bundles for a month
keys = list_evidence_bundles(
    store,
    evidence_type="decision",
    year="2024",
    month="01",
)
print(f"Found {len(keys)} evidence bundles")

# Generate shareable link
url = generate_presigned_url_for_evidence(
    store,
    decision_id="dec-123",
    expiration=7200,  # 2 hours
)
print(f"Share evidence: {url}")

# Delete bundle
deleted = delete_evidence_bundle(store, decision_id="dec-123")
```

### Evidence Bundle Structure

```json
{
  "decision_id": "dec-123",
  "evidence_type": "decision",
  "version": "1.0",
  "created_at": "2024-01-15T12:00:00",
  "checksum": "abc123...",
  "metadata": {
    "environment": "production"
  },
  "evidence_data": {
    "query": "...",
    "verdict": "ALLOW",
    "confidence": 0.95,
    "critics": [...],
    "reasoning": "..."
  }
}
```

## Attachments

Store binary files (images, PDFs, etc.) associated with decisions:

```python
from ejc.storage.s3 import (
    init_objectstore,
    store_attachment,
    retrieve_attachment,
)

store = init_objectstore()
store.connect()

# Store an image
with open("screenshot.png", "rb") as f:
    image_data = f.read()

key = store_attachment(
    store=store,
    decision_id="dec-123",
    attachment_name="screenshot.png",
    data=image_data,
    content_type="image/png",
    metadata={"source": "user-upload"},
)
# Key format: attachments/2024/01/dec-123/screenshot.png

# Retrieve attachment
data = retrieve_attachment(store, key=key)

# Save to file
with open("downloaded.png", "wb") as f:
    f.write(data)
```

## Retry Logic

All operations include automatic retry with exponential backoff:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

# Built into S3Store:
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ClientError, BotoCoreError)),
)
def put_object(self, ...):
    # Automatically retries up to 3 times
    # Waits 2s, 4s, 8s between retries
    ...
```

## Multipart Upload

For files larger than 5MB, use multipart upload for better performance and reliability:

```python
from ejc.storage.s3 import init_objectstore

store = init_objectstore()
store.connect()

# Upload large file with progress tracking
def progress_callback(bytes_uploaded, total_bytes):
    percent = (bytes_uploaded / total_bytes) * 100
    print(f"Progress: {percent:.1f}% ({bytes_uploaded}/{total_bytes} bytes)")

result = store.multipart_upload(
    key="large-files/dataset.bin",
    file_path="/path/to/large-file.bin",
    part_size=10 * 1024 * 1024,  # 10 MB parts
    content_type="application/octet-stream",
    metadata={"dataset": "training-v1"},
    progress_callback=progress_callback,
)

print(f"Upload complete! ETag: {result.etag}")
```

## Bucket Management

```python
from ejc.storage.s3 import init_objectstore, create_bucket_if_not_exists

store = init_objectstore()
store.connect()

# Check if bucket exists
if not store.bucket_exists():
    # Create bucket
    store.create_bucket()

# Or use helper
create_bucket_if_not_exists(store)

# Get bucket info
info = store.get_bucket_info()
print(f"Bucket: {info['name']}")
print(f"Region: {info['region']}")
print(f"Objects: {info['object_count']}")

# Get statistics
stats = store.get_stats()
print(f"Total size: {stats['total_size']} bytes")
```

## Error Handling

```python
from botocore.exceptions import ClientError

try:
    data = store.get_object(key="nonexistent.json")
except ClientError as e:
    error_code = e.response['Error']['Code']
    if error_code == '404' or error_code == 'NoSuchKey':
        print("Object not found")
    elif error_code == '403' or error_code == 'AccessDenied':
        print("Access denied")
    else:
        print(f"Error: {error_code}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Health Checks and Monitoring

```python
from ejc.storage.s3 import init_objectstore

store = init_objectstore()
store.connect()

# Health check
is_healthy = store.health_check()
if not is_healthy:
    print("S3 is not reachable!")

# Get statistics
stats = store.get_stats()
print(f"Backend: {stats['backend']}")
print(f"Bucket: {stats['bucket']}")
print(f"Region: {stats['region']}")
print(f"Objects: {stats['object_count']}")
print(f"Total Size: {stats['total_size']} bytes")
```

## Performance Tips

1. **Use multipart upload for large files** (> 5MB)
   ```python
   store.multipart_upload(key, file_path, part_size=10*1024*1024)
   ```

2. **Batch delete operations** when removing many objects
   ```python
   store.delete_objects(keys)  # Up to 1000 at once
   ```

3. **Use presigned URLs** for direct client uploads/downloads
   ```python
   url = store.generate_presigned_url(key, expiration=3600)
   ```

4. **Enable S3 Transfer Acceleration** for global transfers
   ```bash
   export S3_ENDPOINT_URL=https://bucket.s3-accelerate.amazonaws.com
   ```

5. **Use appropriate part sizes** for multipart uploads
   - 5-10 MB for most files
   - 50-100 MB for very large files (> 1GB)

6. **List with prefix filtering** to reduce response size
   ```python
   objects = store.list_objects(prefix="evidence/2024/01/")
   ```

## Troubleshooting

### Connection Issues

```python
# Check health
is_healthy = store.health_check()
if not is_healthy:
    # Check environment variables
    # Check AWS credentials
    # Check network connectivity
    # Check endpoint URL (for MinIO)
```

### Authentication Errors

```bash
# Verify credentials
aws configure list

# Test with AWS CLI
aws s3 ls s3://your-bucket --endpoint-url http://localhost:9000

# Check IAM permissions (AWS)
# Ensure bucket policies allow access
```

### Slow Uploads

```python
# Use multipart upload
result = store.multipart_upload(
    key=key,
    file_path=file_path,
    part_size=50 * 1024 * 1024,  # 50 MB parts
)

# Or enable S3 Transfer Acceleration (AWS)
export S3_ENDPOINT_URL=https://bucket.s3-accelerate.amazonaws.com
```

### Object Not Found

```python
# Check if object exists
if not store.object_exists(key):
    print("Object does not exist")

# List objects with prefix
objects = store.list_objects(prefix="evidence/")
for obj in objects:
    print(obj.key)
```

## Security Best Practices

1. **Never commit credentials** to version control
2. **Use IAM roles** on AWS (EC2, ECS, Lambda)
3. **Enable bucket encryption** at rest
4. **Use SSL/TLS** for all connections
5. **Set appropriate bucket policies**
6. **Use presigned URLs** for temporary access
7. **Enable versioning** for important data
8. **Set up lifecycle policies** for archival
9. **Monitor access logs**
10. **Rotate access keys regularly**

## AWS IAM Policy Example

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::eje-evidence/*",
        "arn:aws:s3:::eje-evidence"
      ]
    }
  ]
}
```

## Production Checklist

- [ ] Set `S3_BUCKET_NAME` environment variable
- [ ] Configure AWS credentials or IAM role
- [ ] Create S3 bucket
- [ ] Enable bucket versioning
- [ ] Enable server-side encryption
- [ ] Set up bucket lifecycle policies
- [ ] Configure bucket CORS (if needed for browser uploads)
- [ ] Set up CloudWatch alarms for errors
- [ ] Enable S3 access logging
- [ ] Test presigned URL generation
- [ ] Verify multipart upload for large files
- [ ] Set up backup/replication (if needed)

## Next Steps

- See [VectorDB Storage](../vectordb/README.md) for precedent embeddings
- See [PostgreSQL Storage](../README.md) for relational data
- See [Main Storage README](../README.md) for overall architecture

## License

CC BY 4.0 - See [LICENSE](../../../../LICENSE) for details.
