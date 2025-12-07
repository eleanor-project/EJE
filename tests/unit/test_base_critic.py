"""Unit tests for core critic base classes"""
import pytest

from ejc.core.base_critic import BaseCritic, CriticBase, RuleBasedCritic


class DummySupplier:
    """Simple supplier used for CriticBase tests."""

    def __init__(self, output):
        self.output = output

    def run(self, prompt: str, **kwargs):
        if isinstance(self.output, Exception):
            raise self.output
        return self.output


class DummyRuleCritic(RuleBasedCritic):
    """Minimal rule-based critic for testing."""

    def apply_rules(self, case):
        if isinstance(case.get("raise"), Exception):
            raise case["raise"]
        return case["output"]


class ConcreteCritic(BaseCritic):
    """Concrete implementation used to validate BaseCritic behaviors."""

    def evaluate(self, case):
        self.validate_case(case)
        return self._enrich_output(
            {
                "verdict": "ALLOW",
                "confidence": 1.0,
                "justification": "ok",
            }
        )


def test_base_critic_init_validation():
    """Invalid constructor arguments should raise ValueError."""
    with pytest.raises(ValueError):
        ConcreteCritic(name="", weight=1.0)
    with pytest.raises(ValueError):
        ConcreteCritic(name="critic", weight=-1)
    with pytest.raises(ValueError):
        ConcreteCritic(name="critic", weight=1.0, timeout=0)


@pytest.mark.parametrize(
    "case",
    [
        None,
        {},
        {"text": 123},
    ],
)
def test_validate_case_errors(case):
    """validate_case should enforce presence and type of text field."""
    critic = DummyRuleCritic(name="rule", weight=1.0)
    with pytest.raises(ValueError):
        critic.validate_case(case)  # type: ignore[arg-type]


def test_validate_output_structure():
    """validate_output should reject outputs missing required fields."""
    critic = DummyRuleCritic(name="rule", weight=1.0)
    bad_output = {"verdict": "ALLOW", "confidence": 0.7}
    with pytest.raises(ValueError):
        critic.validate_output(bad_output)


def test_validate_output_value_ranges():
    """validate_output should reject invalid verdicts or confidence ranges."""
    critic = DummyRuleCritic(name="rule", weight=1.0)

    with pytest.raises(ValueError):
        critic.validate_output(
            {"verdict": "UNKNOWN", "confidence": 0.7, "justification": "bad"}
        )

    with pytest.raises(ValueError):
        critic.validate_output(
            {"verdict": "ALLOW", "confidence": -0.1, "justification": "bad"}
        )

    with pytest.raises(ValueError):
        critic.validate_output(
            {"verdict": "ALLOW", "confidence": 2, "justification": "bad"}
        )


def test_critic_base_propagates_supplier_exceptions():
    """CriticBase should surface supplier exceptions such as timeouts."""
    critic = CriticBase(
        name="supplier",
        supplier=DummySupplier(TimeoutError("timed out")),
        weight=1.0,
    )
    with pytest.raises(TimeoutError):
        critic.evaluate({"text": "example"})


def test_rule_based_critic_enriches_output():
    """RuleBasedCritic should enrich outputs with metadata and validation."""
    critic = DummyRuleCritic(name="rule", weight=2.0)
    result = critic.evaluate(
        {
            "text": "test",
            "output": {
                "verdict": "ALLOW",
                "confidence": 0.9,
                "justification": "ok",
            },
            "context": {"source": "unit"},
            "metadata": {"request_id": "req-123"},
        }
    )

    assert result["critic"] == "rule"
    assert result["weight"] == 2.0
    assert "timestamp" in result
    assert result["priority"] is None


def test_base_critic_enrich_output_applies_priority_and_weight():
    """_enrich_output should attach critic metadata consistently."""
    critic = ConcreteCritic(name="concrete", weight=1.5, priority="override")

    enriched = critic.evaluate({"text": "case"})

    assert enriched["critic"] == "concrete"
    assert enriched["weight"] == 1.5
    assert enriched["priority"] == "override"
    assert "timestamp" in enriched
