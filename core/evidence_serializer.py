"""
Evidence Bundle Serialization/Deserialization

Provides strict methods for converting evidence bundles to/from JSON with
validation and error handling.

Task 1.4: Implement Serialization/Deserialization
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import logging

logger = logging.getLogger("ejc.core.evidence_serializer")

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    logger.warning("jsonschema not installed - validation will be limited")


class EvidenceSerializerError(Exception):
    """Base exception for serialization errors."""
    pass


class ValidationError(EvidenceSerializerError):
    """Raised when bundle fails validation."""
    pass


class DeserializationError(EvidenceSerializerError):
    """Raised when deserialization fails."""
    pass


class EvidenceSerializer:
    """
    Handles serialization and deserialization of evidence bundles with validation.

    Provides strict to_json() and from_json() methods with schema validation
    and descriptive error messages.
    """

    def __init__(self, schema_path: Optional[Union[str, Path]] = None):
        """
        Initialize Evidence Serializer.

        Args:
            schema_path: Optional path to evidence_bundle.json schema
        """
        self.schema = None
        self.schema_path = schema_path

        if schema_path:
            self.load_schema(schema_path)
        elif HAS_JSONSCHEMA:
            # Try to find schema in default location
            default_path = Path(__file__).parent.parent / "schemas" / "evidence_bundle.json"
            if default_path.exists():
                self.load_schema(default_path)

    def load_schema(self, schema_path: Union[str, Path]):
        """
        Load JSON schema from file.

        Args:
            schema_path: Path to schema file

        Raises:
            EvidenceSerializerError: If schema cannot be loaded
        """
        try:
            with open(schema_path) as f:
                self.schema = json.load(f)

            self.schema_path = Path(schema_path)
            logger.info(f"Loaded schema from {schema_path}")

        except FileNotFoundError:
            raise EvidenceSerializerError(f"Schema file not found: {schema_path}")
        except json.JSONDecodeError as e:
            raise EvidenceSerializerError(f"Invalid JSON in schema: {e}")

    def to_json(
        self,
        bundle: Dict[str, Any],
        validate: bool = True,
        indent: Optional[int] = 2
    ) -> str:
        """
        Convert evidence bundle to JSON string.

        Args:
            bundle: Evidence bundle dict
            validate: Whether to validate against schema before serialization
            indent: JSON indentation (None for compact)

        Returns:
            JSON string representation

        Raises:
            ValidationError: If bundle fails validation
            EvidenceSerializerError: If serialization fails
        """
        try:
            # Validate if requested
            if validate:
                self.validate(bundle)

            # Serialize to JSON
            json_str = json.dumps(bundle, indent=indent, sort_keys=True)
            return json_str

        except ValidationError:
            raise
        except TypeError as e:
            raise EvidenceSerializerError(f"Bundle contains non-serializable data: {e}")
        except Exception as e:
            raise EvidenceSerializerError(f"Serialization failed: {e}")

    def from_json(
        self,
        json_str: str,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Parse evidence bundle from JSON string.

        Args:
            json_str: JSON string
            validate: Whether to validate against schema after parsing

        Returns:
            Evidence bundle dict

        Raises:
            DeserializationError: If JSON parsing fails
            ValidationError: If bundle fails validation
        """
        try:
            # Parse JSON
            bundle = json.loads(json_str)

            # Validate if requested
            if validate:
                self.validate(bundle)

            return bundle

        except json.JSONDecodeError as e:
            raise DeserializationError(f"Invalid JSON: {e.msg} at line {e.lineno}")
        except ValidationError:
            raise
        except Exception as e:
            raise DeserializationError(f"Deserialization failed: {e}")

    def to_file(
        self,
        bundle: Dict[str, Any],
        file_path: Union[str, Path],
        validate: bool = True,
        indent: Optional[int] = 2
    ):
        """
        Write evidence bundle to JSON file.

        Args:
            bundle: Evidence bundle dict
            file_path: Output file path
            validate: Whether to validate before writing
            indent: JSON indentation

        Raises:
            ValidationError: If bundle fails validation
            EvidenceSerializerError: If file write fails
        """
        try:
            json_str = self.to_json(bundle, validate=validate, indent=indent)

            with open(file_path, 'w') as f:
                f.write(json_str)

            logger.info(f"Wrote bundle to {file_path}")

        except (ValidationError, EvidenceSerializerError):
            raise
        except IOError as e:
            raise EvidenceSerializerError(f"Failed to write file: {e}")

    def from_file(
        self,
        file_path: Union[str, Path],
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Read evidence bundle from JSON file.

        Args:
            file_path: Input file path
            validate: Whether to validate after reading

        Returns:
            Evidence bundle dict

        Raises:
            DeserializationError: If file read or parse fails
            ValidationError: If bundle fails validation
        """
        try:
            with open(file_path) as f:
                json_str = f.read()

            bundle = self.from_json(json_str, validate=validate)
            logger.info(f"Loaded bundle from {file_path}")
            return bundle

        except FileNotFoundError:
            raise DeserializationError(f"File not found: {file_path}")
        except (DeserializationError, ValidationError):
            raise
        except Exception as e:
            raise DeserializationError(f"Failed to read file: {e}")

    def validate(self, bundle: Dict[str, Any]) -> bool:
        """
        Validate evidence bundle against schema.

        Args:
            bundle: Evidence bundle dict to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If validation fails with detailed error message
        """
        # Basic structure validation (always done)
        self._validate_basic_structure(bundle)

        # Schema validation (if available)
        if HAS_JSONSCHEMA and self.schema:
            self._validate_with_schema(bundle)
        else:
            logger.debug("Schema validation skipped (jsonschema not available)")

        return True

    def _validate_basic_structure(self, bundle: Dict[str, Any]):
        """
        Validate basic required fields are present.

        Args:
            bundle: Bundle to validate

        Raises:
            ValidationError: If required fields missing
        """
        if not isinstance(bundle, dict):
            raise ValidationError("Bundle must be a dictionary")

        required_top_level = ["bundle_id", "version", "critic_output", "metadata", "input_snapshot"]

        for field in required_top_level:
            if field not in bundle:
                raise ValidationError(f"Required field '{field}' missing at top level")

        # Validate critic_output fields
        critic_output = bundle.get("critic_output", {})
        required_critic = ["critic_name", "verdict", "confidence", "justification"]

        for field in required_critic:
            if field not in critic_output:
                raise ValidationError(f"Required field '{field}' missing in critic_output")

        # Validate metadata fields
        metadata = bundle.get("metadata", {})
        required_metadata = ["timestamp", "critic_name", "config_version"]

        for field in required_metadata:
            if field not in metadata:
                raise ValidationError(f"Required field '{field}' missing in metadata")

        # Validate input_snapshot fields
        input_snapshot = bundle.get("input_snapshot", {})
        if "prompt" not in input_snapshot:
            raise ValidationError("Required field 'prompt' missing in input_snapshot")

        # Validate verdict values
        valid_verdicts = ["ALLOW", "DENY", "ESCALATE", "ABSTAIN", "ERROR"]
        verdict = critic_output.get("verdict")
        if verdict not in valid_verdicts:
            raise ValidationError(
                f"Invalid verdict '{verdict}'. Must be one of: {', '.join(valid_verdicts)}"
            )

        # Validate confidence range
        confidence = critic_output.get("confidence")
        try:
            confidence_float = float(confidence)
            if not (0.0 <= confidence_float <= 1.0):
                raise ValidationError(
                    f"Confidence {confidence_float} out of range (must be 0.0-1.0)"
                )
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid confidence value: {confidence}")

    def _validate_with_schema(self, bundle: Dict[str, Any]):
        """
        Validate bundle against JSON schema.

        Args:
            bundle: Bundle to validate

        Raises:
            ValidationError: If schema validation fails
        """
        try:
            jsonschema.validate(bundle, self.schema)
        except jsonschema.ValidationError as e:
            # Build detailed error message
            path = ".".join(str(p) for p in e.path) if e.path else "root"
            error_msg = f"Validation error at {path}: {e.message}"

            # Add value context if available
            if e.instance is not None and len(str(e.instance)) < 100:
                error_msg += f"\nValue: {e.instance}"

            raise ValidationError(error_msg)
        except jsonschema.SchemaError as e:
            raise ValidationError(f"Schema itself is invalid: {e.message}")

    def batch_to_json(
        self,
        bundles: List[Dict[str, Any]],
        validate: bool = True
    ) -> str:
        """
        Serialize multiple bundles to JSON array.

        Args:
            bundles: List of evidence bundle dicts
            validate: Whether to validate each bundle

        Returns:
            JSON string with array of bundles

        Raises:
            ValidationError: If any bundle fails validation
            EvidenceSerializerError: If serialization fails
        """
        if validate:
            for i, bundle in enumerate(bundles):
                try:
                    self.validate(bundle)
                except ValidationError as e:
                    raise ValidationError(f"Bundle {i} invalid: {e}")

        try:
            return json.dumps(bundles, indent=2, sort_keys=True)
        except Exception as e:
            raise EvidenceSerializerError(f"Batch serialization failed: {e}")

    def batch_from_json(
        self,
        json_str: str,
        validate: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Deserialize multiple bundles from JSON array.

        Args:
            json_str: JSON string containing array of bundles
            validate: Whether to validate each bundle

        Returns:
            List of evidence bundle dicts

        Raises:
            DeserializationError: If JSON parsing fails
            ValidationError: If any bundle fails validation
        """
        try:
            bundles = json.loads(json_str)

            if not isinstance(bundles, list):
                raise DeserializationError("Expected JSON array of bundles")

            if validate:
                for i, bundle in enumerate(bundles):
                    try:
                        self.validate(bundle)
                    except ValidationError as e:
                        raise ValidationError(f"Bundle {i} invalid: {e}")

            return bundles

        except json.JSONDecodeError as e:
            raise DeserializationError(f"Invalid JSON: {e.msg}")
        except ValidationError:
            raise


# Convenience functions

def to_json(bundle: Dict[str, Any], validate: bool = True, indent: int = 2) -> str:
    """
    Convert bundle to JSON string (convenience function).

    Args:
        bundle: Evidence bundle dict
        validate: Whether to validate
        indent: JSON indentation

    Returns:
        JSON string
    """
    serializer = EvidenceSerializer()
    return serializer.to_json(bundle, validate=validate, indent=indent)


def from_json(json_str: str, validate: bool = True) -> Dict[str, Any]:
    """
    Parse bundle from JSON string (convenience function).

    Args:
        json_str: JSON string
        validate: Whether to validate

    Returns:
        Evidence bundle dict
    """
    serializer = EvidenceSerializer()
    return serializer.from_json(json_str, validate=validate)


def to_file(bundle: Dict[str, Any], file_path: Union[str, Path], validate: bool = True):
    """
    Write bundle to file (convenience function).

    Args:
        bundle: Evidence bundle dict
        file_path: Output file path
        validate: Whether to validate
    """
    serializer = EvidenceSerializer()
    serializer.to_file(bundle, file_path, validate=validate)


def from_file(file_path: Union[str, Path], validate: bool = True) -> Dict[str, Any]:
    """
    Read bundle from file (convenience function).

    Args:
        file_path: Input file path
        validate: Whether to validate

    Returns:
        Evidence bundle dict
    """
    serializer = EvidenceSerializer()
    return serializer.from_file(file_path, validate=validate)
