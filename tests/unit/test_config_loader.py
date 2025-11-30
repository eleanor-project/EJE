import yaml

from ejc.core.config_loader import load_global_config


def test_load_global_config_prefers_env_keys(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config = {
        "data_path": str(tmp_path / "data"),
        "db_uri": f"sqlite:///{tmp_path}/audit.db",
        "plugin_critics": [],
        "llm": {
            "critic_model_name": "dummy-critic",
            "security_model_name": "dummy-security",
            "api_keys": {
                "openai": "file-openai",
                "anthropic": "file-anthropic",
                "gemini": "file-gemini",
            },
        },
    }
    config_path.write_text(yaml.safe_dump(config))

    monkeypatch.setenv("OPENAI_API_KEY", "env-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-anthropic")
    monkeypatch.setenv("GEMINI_API_KEY", "env-gemini")

    loaded = load_global_config(str(config_path))

    assert loaded["llm"]["api_keys"]["openai"] == "env-openai"
    assert loaded["llm"]["api_keys"]["anthropic"] == "env-anthropic"
    assert loaded["llm"]["api_keys"]["gemini"] == "env-gemini"

    # Ensure original config values remain when env vars are absent
    for env_var in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"]:
        monkeypatch.delenv(env_var)

    loaded_without_env = load_global_config(str(config_path))
    assert loaded_without_env["llm"]["api_keys"] == config["llm"]["api_keys"]
