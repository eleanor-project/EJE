"""Unit tests for input validation"""
import pytest
from ejc.utils.validation import validate_case


class TestValidateCase:
    """Test suite for validate_case function"""

    def test_valid_minimal_case(self):
        """Test that a minimal valid case passes validation"""
        case = {"text": "This is a test case"}
        assert validate_case(case) is True

    def test_valid_case_with_all_fields(self):
        """Test that a case with all optional fields passes"""
        case = {
            "text": "Test case",
            "context": {"user_id": "123"},
            "metadata": {"source": "api"},
            "tags": ["test", "example"]
        }
        assert validate_case(case) is True

    def test_missing_text_field(self):
        """Test that case without 'text' field raises ValueError"""
        case = {"context": "some context"}
        with pytest.raises(ValueError, match="must include a 'text' field"):
            validate_case(case)

    def test_non_dict_case(self):
        """Test that non-dictionary input raises TypeError"""
        with pytest.raises(TypeError, match="must be a dictionary"):
            validate_case("not a dict")

    def test_non_string_text(self):
        """Test that non-string text field raises TypeError"""
        case = {"text": 123}
        with pytest.raises(TypeError, match="'text' field must be a string"):
            validate_case(case)

    def test_empty_text(self):
        """Test that empty or whitespace-only text raises ValueError"""
        case = {"text": "   "}
        with pytest.raises(ValueError, match="cannot be empty or whitespace-only"):
            validate_case(case)

    def test_text_too_long(self):
        """Test that excessively long text raises ValueError"""
        case = {"text": "a" * 60000}  # Exceeds 50000 character limit
        with pytest.raises(ValueError, match="Input text too long"):
            validate_case(case)

    def test_invalid_keys(self):
        """Test that invalid keys raise ValueError"""
        case = {"text": "test", "invalid_key": "value"}
        with pytest.raises(ValueError, match="Invalid keys"):
            validate_case(case)

    def test_invalid_context_type(self):
        """Test that non-dict context raises TypeError"""
        case = {"text": "test", "context": "not a dict"}
        with pytest.raises(TypeError, match="'context' field must be a dictionary"):
            validate_case(case)

    def test_invalid_tags_type(self):
        """Test that non-list tags raises TypeError"""
        case = {"text": "test", "tags": "not a list"}
        with pytest.raises(TypeError, match="'tags' field must be a list"):
            validate_case(case)

    def test_invalid_tag_item(self):
        """Test that non-string items in tags raise TypeError"""
        case = {"text": "test", "tags": ["valid", 123]}
        with pytest.raises(TypeError, match="All tags must be strings"):
            validate_case(case)
