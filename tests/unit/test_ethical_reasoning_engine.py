import yaml

from ejc.core.ethical_reasoning_engine import EthicalReasoningEngine


class AllowCritic:
    def evaluate(self, case):
        return {
            "verdict": "ALLOW",
            "confidence": 0.9,
            "justification": "Allows the request",
        }


class OverrideBlockCritic:
    def evaluate(self, case):
        return {
            "verdict": "BLOCK",
            "confidence": 0.6,
            "justification": "Overrides due to policy",
        }


def build_minimal_config(tmp_path):
    return {
        "data_path": str(tmp_path / "data"),
        "db_uri": f"sqlite:///{tmp_path}/audit.db",
        "plugin_critics": [],
        "critic_weights": {
            "AllowCritic": 1.0,
            "OverrideBlockCritic": 1.0,
        },
        "critic_priorities": {
            "OverrideBlockCritic": "override",
        },
        "llm": {
            "critic_model_name": "dummy-model",
            "security_model_name": "dummy-security",
            "api_keys": {
                "openai": "", "anthropic": "", "gemini": "",
            },
        },
    }


def test_engine_runs_and_aggregates_with_stub_critics(tmp_path):
    config_path = tmp_path / "config.yaml"
    config = build_minimal_config(tmp_path)
    config_path.write_text(yaml.safe_dump(config))

    engine = EthicalReasoningEngine(str(config_path))
    engine.critics = [AllowCritic(), OverrideBlockCritic()]

    case = {"text": "Example case"}
    result = engine.evaluate(case)

    assert result["final_decision"]["overall_verdict"] == "BLOCK"
    assert "Override" in result["final_decision"].get("reason", "")
    assert {entry["critic"] for entry in result["critic_outputs"]} == {
        "AllowCritic",
        "OverrideBlockCritic",
    }
