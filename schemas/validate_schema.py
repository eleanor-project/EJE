#!/usr/bin/env python3
"""
Validate JSON schemas and test bundles.

Usage:
    python schemas/validate_schema.py
"""

import json
import jsonschema
from pathlib import Path


def validate_schema_file(schema_path: Path) -> bool:
    """
    Validate that a schema file is valid JSON Schema.

    Args:
        schema_path: Path to schema file

    Returns:
        True if valid
    """
    try:
        with open(schema_path) as f:
            schema = json.load(f)

        # Check it's a valid JSON Schema
        jsonschema.Draft7Validator.check_schema(schema)
        print(f"✅ Schema {schema_path.name} is valid JSON Schema")
        return True

    except json.JSONDecodeError as e:
        print(f"❌ {schema_path.name}: Invalid JSON - {e}")
        return False
    except jsonschema.SchemaError as e:
        print(f"❌ {schema_path.name}: Invalid schema - {e.message}")
        return False
    except Exception as e:
        print(f"❌ {schema_path.name}: Error - {e}")
        return False


def validate_bundle_examples(schema_path: Path) -> bool:
    """
    Validate example bundles in the schema.

    Args:
        schema_path: Path to schema file

    Returns:
        True if all examples valid
    """
    try:
        with open(schema_path) as f:
            schema = json.load(f)

        examples = schema.get("examples", [])
        if not examples:
            print(f"⚠️  No examples found in {schema_path.name}")
            return True

        validator = jsonschema.Draft7Validator(schema)
        all_valid = True

        for i, example in enumerate(examples, 1):
            errors = list(validator.iter_errors(example))
            if errors:
                print(f"❌ Example {i} failed validation:")
                for error in errors:
                    path = ".".join(str(p) for p in error.path)
                    print(f"   - {path}: {error.message}")
                all_valid = False
            else:
                bundle_id = example.get("bundle_id", f"example-{i}")
                print(f"✅ Example {i} ({bundle_id}) is valid")

        return all_valid

    except Exception as e:
        print(f"❌ Error validating examples: {e}")
        return False


def validate_test_bundle(schema_path: Path, bundle_data: dict) -> bool:
    """
    Validate a test bundle against schema.

    Args:
        schema_path: Path to schema file
        bundle_data: Bundle dictionary to validate

    Returns:
        True if valid
    """
    try:
        with open(schema_path) as f:
            schema = json.load(f)

        jsonschema.validate(bundle_data, schema)
        bundle_id = bundle_data.get("bundle_id", "unknown")
        print(f"✅ Test bundle ({bundle_id}) is valid")
        return True

    except jsonschema.ValidationError as e:
        path = ".".join(str(p) for p in e.path)
        print(f"❌ Validation error at {path}: {e.message}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run schema validation tests."""
    print("=" * 60)
    print("EJE Schema Validation")
    print("=" * 60)

    schemas_dir = Path(__file__).parent
    schema_path = schemas_dir / "evidence_bundle.json"

    if not schema_path.exists():
        print(f"❌ Schema file not found: {schema_path}")
        return False

    # Validate schema itself
    print("\n[1/3] Validating schema file...")
    if not validate_schema_file(schema_path):
        return False

    # Validate examples in schema
    print("\n[2/3] Validating example bundles in schema...")
    if not validate_bundle_examples(schema_path):
        return False

    # Test with minimal bundle
    print("\n[3/3] Validating minimal test bundle...")
    minimal_bundle = {
        "bundle_id": "test-minimal-001",
        "version": "1.0",
        "critic_output": {
            "critic_name": "TestCritic",
            "verdict": "ALLOW",
            "confidence": 0.8,
            "justification": "This is a test justification for validation purposes."
        },
        "metadata": {
            "timestamp": "2025-12-04T10:00:00Z",
            "critic_name": "TestCritic",
            "config_version": "1.0"
        },
        "input_snapshot": {
            "prompt": "Test input prompt for validation"
        }
    }

    if not validate_test_bundle(schema_path, minimal_bundle):
        return False

    print("\n" + "=" * 60)
    print("✅ All validation tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
