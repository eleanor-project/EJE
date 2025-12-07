"""
Evidence Bundle Serialization/Deserialization

Provides strict methods for converting evidence bundles to/from JSON
with comprehensive validation and error handling.
"""

import json
from typing import Any, Dict, List, Optional, Union

from pydantic import ValidationError

from .evidence_normalizer import EvidenceBundle


class SerializationError(Exception):
    """Exception raised when serialization fails"""
    pass


class DeserializationError(ValueError):
    """Exception raised when deserialization fails"""
    pass


class EvidenceBundleSerializer:
    """
    Handles serialization and deserialization of evidence bundles.

    Provides:
    - Strict JSON serialization with validation
    - Deserialization with comprehensive error messages
    - Batch operations for multiple bundles
    - Pretty-printing options
    """

    @staticmethod
    def to_json(
        bundle: EvidenceBundle,
        pretty: bool = False,
        indent: Optional[int] = 2,
        validate: bool = False
    ) -> str:
        """
        Serialize an evidence bundle to JSON string.

        Args:
            bundle: EvidenceBundle instance to serialize
            pretty: Whether to format JSON with indentation
            indent: Number of spaces for indentation (if pretty=True)

        Returns:
            JSON string representation of the bundle

        Raises:
            SerializationError: If serialization fails
        """
        try:
            if validate:
                EvidenceBundle.model_validate(bundle.model_dump())

            # Use Pydantic's model_dump_json for efficient serialization
            if pretty:
                json_str = bundle.model_dump_json(indent=indent, exclude_none=False)
            else:
                json_str = bundle.model_dump_json(exclude_none=False)

            return json_str
        except Exception as e:
            raise SerializationError(f"Failed to serialize evidence bundle: {str(e)}") from e

    @staticmethod
    def to_dict(bundle: EvidenceBundle) -> Dict[str, Any]:
        """
        Convert an evidence bundle to a dictionary.

        Args:
            bundle: EvidenceBundle instance to convert

        Returns:
            Dictionary representation of the bundle

        Raises:
            SerializationError: If conversion fails
        """
        try:
            return bundle.model_dump(exclude_none=False)
        except Exception as e:
            raise SerializationError(f"Failed to convert bundle to dict: {str(e)}") from e

    @staticmethod
    def from_json(json_str: str) -> EvidenceBundle:
        """
        Deserialize an evidence bundle from JSON string.

        Args:
            json_str: JSON string representation of a bundle

        Returns:
            Validated EvidenceBundle instance

        Raises:
            DeserializationError: If deserialization or validation fails
        """
        # Parse JSON string (may raise json.JSONDecodeError)
        data = json.loads(json_str)

        # Validate and construct EvidenceBundle
        return EvidenceBundleSerializer.from_dict(data)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> EvidenceBundle:
        """
        Deserialize an evidence bundle from a dictionary.

        Args:
            data: Dictionary representation of a bundle

        Returns:
            Validated EvidenceBundle instance

        Raises:
            DeserializationError: If validation fails
        """
        bundle = EvidenceBundle(**data)
        return bundle

    @staticmethod
    def to_json_file(
        bundle: EvidenceBundle,
        file_path: str,
        pretty: bool = True
    ) -> None:
        """
        Serialize an evidence bundle to a JSON file.

        Args:
            bundle: EvidenceBundle instance to serialize
            file_path: Path where the JSON file will be written
            pretty: Whether to format JSON with indentation

        Raises:
            SerializationError: If serialization or file writing fails
        """
        try:
            json_str = EvidenceBundleSerializer.to_json(bundle, pretty=pretty)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
        except SerializationError:
            raise
        except Exception as e:
            raise SerializationError(f"Failed to write bundle to file: {str(e)}") from e

    @staticmethod
    def from_json_file(file_path: str) -> EvidenceBundle:
        """
        Deserialize an evidence bundle from a JSON file.

        Args:
            file_path: Path to the JSON file

        Returns:
            Validated EvidenceBundle instance

        Raises:
            DeserializationError: If file reading or deserialization fails
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            json_str = f.read()
        return EvidenceBundleSerializer.from_json(json_str)

    @staticmethod
    def to_json_batch(
        bundles: List[EvidenceBundle],
        pretty: bool = False
    ) -> str:
        """
        Serialize multiple evidence bundles to a JSON array string.

        Args:
            bundles: List of EvidenceBundle instances
            pretty: Whether to format JSON with indentation

        Returns:
            JSON array string containing all bundles

        Raises:
            SerializationError: If serialization fails
        """
        try:
            bundles_data = [bundle.model_dump(exclude_none=False) for bundle in bundles]
            if pretty:
                return json.dumps(bundles_data, indent=2)
            else:
                return json.dumps(bundles_data)
        except Exception as e:
            raise SerializationError(f"Failed to serialize bundle batch: {str(e)}") from e

    @staticmethod
    def serialize_batch(
        bundles: List[EvidenceBundle],
        pretty: bool = False
    ) -> str:
        """Alias for to_json_batch for compatibility with tests."""

        return EvidenceBundleSerializer.to_json_batch(bundles, pretty=pretty)

    @staticmethod
    def from_json_batch(json_str: str) -> List[EvidenceBundle]:
        """
        Deserialize multiple evidence bundles from a JSON array string.

        Args:
            json_str: JSON array string containing bundle representations

        Returns:
            List of validated EvidenceBundle instances

        Raises:
            DeserializationError: If deserialization fails
        """
        data = json.loads(json_str)

        if not isinstance(data, list):
            raise ValueError(
                f"Expected JSON array, got {type(data).__name__}"
            )

        bundles = []

        for bundle_data in data:
            bundle = EvidenceBundleSerializer.from_dict(bundle_data)
            bundles.append(bundle)

        return bundles

    @staticmethod
    def validate_json_schema(json_str: str) -> tuple[bool, Optional[str]]:
        """
        Validate a JSON string against the evidence bundle schema.

        Args:
            json_str: JSON string to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if valid, False otherwise
            - error_message: None if valid, error description if invalid
        """
        try:
            EvidenceBundleSerializer.from_json(json_str)
            return True, None
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            return False, str(e)

    @staticmethod
    def validate_dict_schema(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate a dictionary against the evidence bundle schema.

        Args:
            data: Dictionary to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if valid, False otherwise
            - error_message: None if valid, error description if invalid
        """
        try:
            EvidenceBundleSerializer.from_dict(data)
            return True, None
        except ValidationError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected validation error: {str(e)}"


# Convenience functions
def bundle_to_json(bundle: EvidenceBundle, pretty: bool = False) -> str:
    """
    Convenience function to serialize an evidence bundle to JSON.

    Args:
        bundle: EvidenceBundle instance
        pretty: Whether to format with indentation

    Returns:
        JSON string
    """
    return EvidenceBundleSerializer.to_json(bundle, pretty=pretty)


def bundle_from_json(json_str: str) -> EvidenceBundle:
    """
    Convenience function to deserialize an evidence bundle from JSON.

    Args:
        json_str: JSON string

    Returns:
        EvidenceBundle instance
    """
    try:
        return EvidenceBundleSerializer.from_json(json_str)
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise DeserializationError(f"Invalid JSON format: {exc}") from exc


def bundle_to_dict(bundle: EvidenceBundle) -> Dict[str, Any]:
    """
    Convenience function to convert an evidence bundle to dictionary.

    Args:
        bundle: EvidenceBundle instance

    Returns:
        Dictionary representation
    """
    return EvidenceBundleSerializer.to_dict(bundle)


def bundle_from_dict(data: Dict[str, Any]) -> EvidenceBundle:
    """
    Convenience function to create an evidence bundle from dictionary.

    Args:
        data: Dictionary representation

    Returns:
        EvidenceBundle instance
    """
    try:
        return EvidenceBundleSerializer.from_dict(data)
    except ValidationError as exc:
        raise DeserializationError(f"Evidence bundle validation failed: {exc}") from exc


def validate_bundle_json(json_str: str) -> tuple[bool, Optional[str]]:
    """
    Convenience function to validate JSON against evidence bundle schema.

    Args:
        json_str: JSON string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    return EvidenceBundleSerializer.validate_json_schema(json_str)


def validate_bundle_dict(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Convenience function to validate dictionary against evidence bundle schema.

    Args:
        data: Dictionary to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    return EvidenceBundleSerializer.validate_dict_schema(data)
