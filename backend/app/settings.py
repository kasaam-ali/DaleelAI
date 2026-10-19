"""Loads the YAML config and fills ${ENV} values from the environment."""

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
    vector_store: Literal["qdrant", "memory"] = "qdrant"
    embedder: Literal["fastembed", "fake"] = "fastembed"
    reranker: Literal["fastembed", "fake"] = "fastembed"
    classifier: Literal["onnx", "keyword"] = "onnx"
    repository: Literal["postgres", "sqlite"] = "postgres"
    agent_runner: Literal["langgraph", "simple"] = "langgraph"


class QdrantCollections(BaseModel):
    verified: str = "documents"
    web: str = "web_pages"


class QdrantSettings(BaseModel):
    url: str = ""
    api_key: str = ""
    collections: QdrantCollections = QdrantCollections()


class EmbeddingModels(BaseModel):
    dense: str = "BAAI/bge-small-en-v1.5"
    sparse: str = "Qdrant/bm25"
    reranker: str = "Xenova/ms-marco-MiniLM-L-12-v2"
    classifier_path: str = "models/classifier.onnx"


class RetrievalSettings(BaseModel):
    prefetch_k: int = 30
    rerank_keep: int = 6
    context_tokens: int = 6000
    domain_boost: float = 1.2


class SufficiencySettings(BaseModel):
    """Rerank bands from config. The dev set has not fitted these yet."""

    sufficient_at: float = 0.7
    borderline_at: float = 0.4


class WebFallbackSettings(BaseModel):
    enabled: bool = True
    rerank_keep: int = 5
    min_rerank_score: float = 0.5
    max_confidence: Literal["high", "medium", "low"] = "medium"
    abstain_links: int = 3


class BudgetSettings(BaseModel):
    calls_target: int = 3
    calls_cap: int = 5
    daily_tokens: int = 400000


class UploadSettings(BaseModel):
    max_mb: int = 10
    max_pages: int = 10


class Settings(BaseModel):
    env: Literal["development", "production"] = "development"
    cors_origins: list[str] = []
    adapters: Adapters = Adapters()
    database_url: str = ""
    qdrant: QdrantSettings = QdrantSettings()
    models: EmbeddingModels = EmbeddingModels()
    retrieval: RetrievalSettings = RetrievalSettings()
    sufficiency: SufficiencySettings = SufficiencySettings()
    web_fallback: WebFallbackSettings = WebFallbackSettings()
    action_links_file: str = "config/action_links.yaml"
    budget: BudgetSettings = BudgetSettings()
    uploads: UploadSettings = UploadSettings()
    internal_token: str = ""


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
