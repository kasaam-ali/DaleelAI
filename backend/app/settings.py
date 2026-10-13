import os
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
_ENV_REF = re.compile(r"\$\{([A-Z0-9_]+)\}")


def expand_env(value: Any) -> Any:
    """Replace ${VAR} references in config values with environment variables."""
    if isinstance(value, str):
        return _ENV_REF.sub(lambda m: os.environ.get(m.group(1), ""), value)
    if isinstance(value, dict):
        return {key: expand_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [expand_env(item) for item in value]
    return value


def load_yaml(name: str, config_dir: Path = CONFIG_DIR) -> dict[str, Any]:
    with open(config_dir / name, encoding="utf-8") as file:
        return expand_env(yaml.safe_load(file) or {})


class Adapters(BaseModel):
    llm: Literal["litellm", "fake"] = "litellm"


class Settings(BaseModel):
    env: Literal["development", "production"] = "development"
    cors_origins: list[str] = []
    adapters: Adapters = Adapters()


class RetryConfig(BaseModel):
    attempts: int = 1
    cooldown_s: float = 60
    timeout_s: float = 45


class ModelsConfig(BaseModel):
    roles: dict[str, list[str]]
    retry: RetryConfig = RetryConfig()


def load_settings(config_dir: Path = CONFIG_DIR) -> Settings:
    return Settings.model_validate(load_yaml("settings.yaml", config_dir))


def load_models_config(config_dir: Path = CONFIG_DIR) -> ModelsConfig:
    return ModelsConfig.model_validate(load_yaml("models.yaml", config_dir))
