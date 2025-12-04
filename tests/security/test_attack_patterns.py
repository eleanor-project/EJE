"""
Tests for Attack Pattern Library (Issue #173)

Tests comprehensive adversarial attack pattern library.
"""

import pytest
import json
import tempfile
import os
from src.ejc.security.attack_patterns import (
    AttackPattern,
    AttackCategory,
    AttackSeverity,
    AttackPatternLibrary
)


@pytest.fixture
def library():
    """Create attack pattern library instance."""
    return AttackPatternLibrary()


@pytest.fixture
def mock_system():
    """Mock system under test."""
    class MockSystem:
        def process(self, input_data):
            # Simulate processing - return input echoed back
            return {'result': 'processed', 'input': input_data}

    return MockSystem()


class TestAttackPattern:
    """Test suite for AttackPattern class."""

    def test_attack_pattern_creation(self):
        """Test creating an attack pattern."""
        pattern = AttackPattern(
            name="Test Attack",
            description="Test description",
            category=AttackCategory.PROMPT_INJECTION,
            severity=AttackSeverity.HIGH,
            example_input={'test': 'data'},
            expected_behavior="Should handle gracefully",
            detection_method="Pattern matching",
            mitigation="Input validation"
        )

        assert pattern.name == "Test Attack"
        assert pattern.category == AttackCategory.PROMPT_INJECTION
        assert pattern.severity == AttackSeverity.HIGH
        assert pattern.example_input == {'test': 'data'}

    def test_attack_pattern_with_tags(self):
        """Test attack pattern with tags."""
        pattern = AttackPattern(
            name="Tagged Attack",
            description="Test",
            category=AttackCategory.INPUT_MANIPULATION,
            severity=AttackSeverity.MEDIUM,
            example_input={},
            expected_behavior="Test",
            detection_method="Test",
            mitigation="Test",
            tags=['tag1', 'tag2', 'tag3']
        )

        assert len(pattern.tags) == 3
        assert 'tag1' in pattern.tags

    def test_attack_pattern_execute(self, mock_system):
        """Test executing an attack pattern."""
        pattern = AttackPattern(
            name="Test",
            description="Test",
            category=AttackCategory.PROMPT_INJECTION,
            severity=AttackSeverity.LOW,
            example_input={'test': 'input'},
            expected_behavior="Test",
            detection_method="Test",
            mitigation="Test"
        )

        result = pattern.execute(mock_system)

        assert 'attack' in result
        assert result['attack'] == "Test"
        assert 'success' in result
        assert 'result' in result

    def test_attack_pattern_to_dict(self):
        """Test converting attack pattern to dictionary."""
        pattern = AttackPattern(
            name="Test",
            description="Description",
            category=AttackCategory.BIAS_EXPLOITATION,
            severity=AttackSeverity.CRITICAL,
            example_input={'data': 'test'},
            expected_behavior="Behavior",
            detection_method="Detection",
            mitigation="Mitigation",
            tags=['test'],
            references=['ref1']
        )

        pattern_dict = pattern.to_dict()

        assert pattern_dict['name'] == "Test"
        assert pattern_dict['category'] == 'bias_exploitation'
        assert pattern_dict['severity'] == 'critical'
        assert pattern_dict['tags'] == ['test']
        assert pattern_dict['references'] == ['ref1']


class TestAttackPatternLibrary:
    """Test suite for AttackPatternLibrary."""

    def test_library_initialization(self, library):
        """Test library initializes with patterns."""
        assert len(library.patterns) >= 50
        assert len(library) >= 50

    def test_library_has_all_categories(self, library):
        """Test library includes all attack categories."""
        categories = library.get_categories()

        assert AttackCategory.PROMPT_INJECTION in categories
        assert AttackCategory.INPUT_MANIPULATION in categories
        assert AttackCategory.BIAS_EXPLOITATION in categories
        assert AttackCategory.BOUNDARY_CONDITIONS in categories
        assert AttackCategory.MALFORMED_INPUT in categories

    def test_prompt_injection_patterns(self, library):
        """Test prompt injection patterns are present."""
        patterns = library.get_patterns(category=AttackCategory.PROMPT_INJECTION)

        assert len(patterns) >= 10
        assert any('override' in p.name.lower() for p in patterns)
        assert any('role' in p.name.lower() for p in patterns)
        assert any('injection' in p.name.lower() for p in patterns)

    def test_input_manipulation_patterns(self, library):
        """Test input manipulation patterns are present."""
        patterns = library.get_patterns(category=AttackCategory.INPUT_MANIPULATION)

        assert len(patterns) >= 10
        assert any('sql' in p.name.lower() for p in patterns)
        assert any('xss' in p.name.lower() for p in patterns)
        assert any('injection' in p.name.lower() for p in patterns)

    def test_bias_exploitation_patterns(self, library):
        """Test bias exploitation patterns are present."""
        patterns = library.get_patterns(category=AttackCategory.BIAS_EXPLOITATION)

        assert len(patterns) >= 10
        assert any('bias' in p.name.lower() for p in patterns)
        assert any('protected' in p.name.lower() or 'attribute' in p.name.lower() for p in patterns)
        assert any('discrimination' in p.name.lower() or 'fairness' in p.description.lower() for p in patterns)

    def test_boundary_condition_patterns(self, library):
        """Test boundary condition patterns are present."""
        patterns = library.get_patterns(category=AttackCategory.BOUNDARY_CONDITIONS)

        assert len(patterns) >= 10
        assert any('empty' in p.name.lower() for p in patterns)
        assert any('maximum' in p.name.lower() or 'max' in p.name.lower() for p in patterns)
        assert any('zero' in p.name.lower() for p in patterns)

    def test_malformed_input_patterns(self, library):
        """Test malformed input patterns are present."""
        patterns = library.get_patterns(category=AttackCategory.MALFORMED_INPUT)

        assert len(patterns) >= 10
        assert any('json' in p.name.lower() for p in patterns)
        assert any('encoding' in p.name.lower() for p in patterns)
        assert any('malformed' in p.description.lower() or 'invalid' in p.description.lower() for p in patterns)

    def test_filter_by_severity(self, library):
        """Test filtering patterns by severity."""
        critical = library.get_patterns(severity=AttackSeverity.CRITICAL)
        high = library.get_patterns(severity=AttackSeverity.HIGH)
        medium = library.get_patterns(severity=AttackSeverity.MEDIUM)
        low = library.get_patterns(severity=AttackSeverity.LOW)

        assert len(critical) > 0
        assert len(high) > 0
        assert len(medium) > 0
        assert len(low) > 0

        # All critical should be CRITICAL
        for pattern in critical:
            assert pattern.severity == AttackSeverity.CRITICAL

    def test_get_critical_patterns(self, library):
        """Test getting critical severity patterns."""
        critical = library.get_critical_patterns()

        assert len(critical) > 0
        for pattern in critical:
            assert pattern.severity == AttackSeverity.CRITICAL

        # Should include SQL injection
        assert any('sql' in p.name.lower() for p in critical)

    def test_get_high_severity_patterns(self, library):
        """Test getting high and critical severity patterns."""
        high_and_critical = library.get_high_severity_patterns()

        assert len(high_and_critical) > 0
        for pattern in high_and_critical:
            assert pattern.severity in [AttackSeverity.CRITICAL, AttackSeverity.HIGH]

    def test_filter_by_tags(self, library):
        """Test filtering patterns by tags."""
        sql_patterns = library.get_patterns(tags=['sql_injection'])
        xss_patterns = library.get_patterns(tags=['xss'])

        assert len(sql_patterns) > 0
        assert len(xss_patterns) > 0

    def test_filter_by_multiple_criteria(self, library):
        """Test filtering by category and severity together."""
        critical_prompt = library.get_patterns(
            category=AttackCategory.PROMPT_INJECTION,
            severity=AttackSeverity.CRITICAL
        )

        for pattern in critical_prompt:
            assert pattern.category == AttackCategory.PROMPT_INJECTION
            assert pattern.severity == AttackSeverity.CRITICAL

    def test_get_pattern_by_name(self, library):
        """Test retrieving specific pattern by name."""
        pattern = library.get_pattern_by_name("Direct Instruction Override")

        assert pattern is not None
        assert pattern.name == "Direct Instruction Override"
        assert pattern.category == AttackCategory.PROMPT_INJECTION

    def test_get_nonexistent_pattern(self, library):
        """Test retrieving non-existent pattern returns None."""
        pattern = library.get_pattern_by_name("Nonexistent Attack")

        assert pattern is None

    def test_get_statistics(self, library):
        """Test getting library statistics."""
        stats = library.get_statistics()

        assert 'total_patterns' in stats
        assert stats['total_patterns'] >= 50

        assert 'by_category' in stats
        assert len(stats['by_category']) == 5

        assert 'by_severity' in stats
        assert 'critical' in stats['by_severity']
        assert 'high' in stats['by_severity']

        assert 'total_tags' in stats
        assert stats['total_tags'] > 0

    def test_add_custom_pattern(self, library):
        """Test adding custom attack pattern."""
        initial_count = len(library.patterns)

        custom_pattern = AttackPattern(
            name="Custom Attack",
            description="Custom test attack",
            category=AttackCategory.PROMPT_INJECTION,
            severity=AttackSeverity.LOW,
            example_input={'custom': 'input'},
            expected_behavior="Test",
            detection_method="Test",
            mitigation="Test"
        )

        library.add_pattern(custom_pattern)

        assert len(library.patterns) == initial_count + 1
        assert library.get_pattern_by_name("Custom Attack") is not None

    def test_export_to_json(self, library):
        """Test exporting patterns to JSON."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            filepath = f.name

        try:
            library.export_to_json(filepath)

            # Verify file was created
            assert os.path.exists(filepath)

            # Load and verify contents
            with open(filepath, 'r') as f:
                data = json.load(f)

            assert 'patterns' in data
            assert 'statistics' in data
            assert len(data['patterns']) >= 50

            # Verify pattern structure
            first_pattern = data['patterns'][0]
            assert 'name' in first_pattern
            assert 'category' in first_pattern
            assert 'severity' in first_pattern
            assert 'description' in first_pattern

        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_library_repr(self, library):
        """Test library string representation."""
        repr_str = repr(library)

        assert 'AttackPatternLibrary' in repr_str
        assert 'patterns' in repr_str


class TestSpecificAttackPatterns:
    """Test specific notable attack patterns."""

    def test_sql_injection_pattern(self, library):
        """Test SQL injection pattern details."""
        pattern = library.get_pattern_by_name("SQL Injection")

        assert pattern is not None
        assert pattern.category == AttackCategory.INPUT_MANIPULATION
        assert pattern.severity == AttackSeverity.CRITICAL
        assert 'sql' in pattern.tags

        # Check example includes SQL injection attempt
        example = str(pattern.example_input)
        assert 'OR' in example or 'DROP' in example

    def test_xss_pattern(self, library):
        """Test XSS attack pattern details."""
        pattern = library.get_pattern_by_name("Cross-Site Scripting (XSS)")

        assert pattern is not None
        assert pattern.category == AttackCategory.INPUT_MANIPULATION
        assert pattern.severity == AttackSeverity.HIGH
        assert 'xss' in pattern.tags

        # Check example includes script tag
        example = str(pattern.example_input)
        assert 'script' in example.lower()

    def test_protected_attribute_bias_pattern(self, library):
        """Test protected attribute exploitation pattern."""
        pattern = library.get_pattern_by_name("Protected Attribute Exploitation")

        assert pattern is not None
        assert pattern.category == AttackCategory.BIAS_EXPLOITATION
        assert pattern.severity == AttackSeverity.CRITICAL
        assert 'protected_attributes' in pattern.tags or 'discrimination' in pattern.tags

    def test_prompt_injection_pattern(self, library):
        """Test direct instruction override pattern."""
        pattern = library.get_pattern_by_name("Direct Instruction Override")

        assert pattern is not None
        assert pattern.category == AttackCategory.PROMPT_INJECTION
        assert pattern.severity == AttackSeverity.CRITICAL

        # Check mitigation suggestions
        assert pattern.mitigation
        assert 'sanitization' in pattern.mitigation.lower() or 'isolation' in pattern.mitigation.lower()

    def test_empty_input_pattern(self, library):
        """Test empty input boundary condition."""
        pattern = library.get_pattern_by_name("Empty Input Attack")

        assert pattern is not None
        assert pattern.category == AttackCategory.BOUNDARY_CONDITIONS
        assert pattern.example_input == {}

    def test_compression_bomb_pattern(self, library):
        """Test compression bomb pattern."""
        pattern = library.get_pattern_by_name("Compression Bomb")

        assert pattern is not None
        assert pattern.category == AttackCategory.MALFORMED_INPUT
        assert pattern.severity == AttackSeverity.HIGH
        assert 'compression' in pattern.tags or 'dos' in pattern.tags


class TestAttackPatternCoverage:
    """Test comprehensive coverage of attack surfaces."""

    def test_owasp_top10_coverage(self, library):
        """Test coverage of OWASP Top 10 vulnerabilities."""
        # Check for key OWASP vulnerabilities
        all_patterns = [p.name.lower() + ' ' + p.description.lower() for p in library.patterns]
        all_text = ' '.join(all_patterns)

        # Key OWASP categories that should be covered
        assert 'sql injection' in all_text or 'sql' in all_text
        assert 'xss' in all_text or 'cross-site scripting' in all_text
        assert 'command injection' in all_text

    def test_ai_specific_attacks_coverage(self, library):
        """Test coverage of AI/ML specific attacks."""
        all_patterns = [p.name.lower() + ' ' + p.description.lower() for p in library.patterns]
        all_text = ' '.join(all_patterns)

        # AI-specific vulnerabilities
        assert 'prompt' in all_text
        assert 'bias' in all_text
        assert 'injection' in all_text

    def test_governance_specific_coverage(self, library):
        """Test coverage of governance-specific concerns."""
        bias_patterns = library.get_patterns(category=AttackCategory.BIAS_EXPLOITATION)

        # Should cover various protected attributes
        all_bias_text = ' '.join([p.name.lower() + ' ' + p.description.lower() for p in bias_patterns])

        assert 'protected' in all_bias_text or 'discrimination' in all_bias_text
        assert 'bias' in all_bias_text
        assert 'fairness' in all_bias_text or 'fair' in all_bias_text

    def test_all_patterns_documented(self, library):
        """Test that all patterns have complete documentation."""
        for pattern in library.patterns:
            # Check all required fields are populated
            assert pattern.name
            assert pattern.description
            assert pattern.category
            assert pattern.severity
            assert pattern.example_input is not None
            assert pattern.expected_behavior
            assert pattern.detection_method
            assert pattern.mitigation

    def test_severity_distribution(self, library):
        """Test that severity levels are reasonably distributed."""
        stats = library.get_statistics()

        # Should have patterns at all severity levels
        assert stats['by_severity']['critical'] > 0
        assert stats['by_severity']['high'] > 0
        assert stats['by_severity']['medium'] > 0
        assert stats['by_severity']['low'] > 0

        # Most patterns should be medium or high severity
        total = stats['total_patterns']
        medium_and_high = stats['by_severity']['medium'] + stats['by_severity']['high']
        assert medium_and_high >= total * 0.4

    def test_category_distribution(self, library):
        """Test that patterns are distributed across categories."""
        stats = library.get_statistics()

        # Each category should have at least 8 patterns (requirement: 50+ total, 5 categories)
        for category in stats['by_category'].values():
            assert category >= 8


class TestAttackPatternExecution:
    """Test attack pattern execution against mock system."""

    def test_execute_against_mock(self, library, mock_system):
        """Test executing attack pattern against mock system."""
        pattern = library.get_critical_patterns()[0]
        result = pattern.execute(mock_system)

        assert 'attack' in result
        assert 'success' in result
        assert 'severity' in result
        assert result['severity'] == 'critical'

    def test_execute_with_error_handling(self, library):
        """Test execution handles errors gracefully."""
        class FailingSystem:
            def process(self, input_data):
                raise ValueError("Test error")

        pattern = library.patterns[0]
        result = pattern.execute(FailingSystem())

        assert 'error' in result
        assert result['success'] is False
        assert 'Test error' in result['error']


# Run tests if executed directly
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
