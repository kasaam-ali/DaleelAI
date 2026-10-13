from app.settings import expand_env, load_models_config, load_settings


def test_expand_env_replaces_references(monkeypatch):
    monkeypatch.setenv("QDRANT_URL", "http://qdrant:6333")
    config = {"qdrant": {"url": "${QDRANT_URL}"}, "hosts": ["${QDRANT_URL}/a"], "port": 1}

    assert expand_env(config) == {
        "qdrant": {"url": "http://qdrant:6333"},
        "hosts": ["http://qdrant:6333/a"],
        "port": 1,
    }


def test_expand_env_missing_variable_becomes_empty(monkeypatch):
    monkeypatch.delenv("DALEEL_NOT_SET", raising=False)

    assert expand_env("${DALEEL_NOT_SET}") == ""


def test_committed_config_files_are_valid():
    settings = load_settings()
    models = load_models_config()

    assert settings.adapters.llm in ("litellm", "fake")
    assert set(models.roles) == {"reasoning", "fast", "vision", "judge"}
    assert all(models.roles.values())
