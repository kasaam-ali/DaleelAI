"""Per-dependency probes for GET /health.

Each probe stays inside a 1.5s budget and they run together, so a down
Qdrant or a missing model file cannot stretch /health toward its 5s cap.
Embedder weights are not downloaded here.
"""

import asyncio
import os
import socket
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from app.adapters.llm_litellm import PROVIDER_KEYS
from app.settings import Settings, load_models_config

CHECK_NAMES = ("api", "qdrant", "postgres", "llm", "embeddings")
TIMEOUT_S = 1.5
SLOW_MS = 800

_PROVIDER_HOSTS = {
    "groq": "api.groq.com",
    "gemini": "generativelanguage.googleapis.com",
    "openrouter": "openrouter.ai",
}

Probe = Callable[[], str]


def default_probes(settings: Settings) -> dict[str, Probe]:
    return {
        "api": lambda: "ok",
        "qdrant": lambda: check_qdrant(settings),
        "postgres": lambda: check_postgres(settings),
        "llm": lambda: check_llm(settings),
        "embeddings": lambda: check_embeddings(settings),
    }


async def collect_checks(
    settings: Settings,
    *,
    probes: dict[str, Probe] | None = None,
    timeout_s: float = TIMEOUT_S,
    slow_ms: int = SLOW_MS,
) -> dict[str, dict[str, int | str]]:
    chosen = probes or default_probes(settings)

    async def one(name: str, probe: Probe) -> tuple[str, dict[str, int | str]]:
        started = time.perf_counter()
        try:
            status = await asyncio.wait_for(asyncio.to_thread(probe), timeout_s)
        except TimeoutError:
            return name, {"status": "down", "latency_ms": int(timeout_s * 1000)}
        except Exception:
            elapsed = int((time.perf_counter() - started) * 1000)
            return name, {"status": "down", "latency_ms": elapsed}
        elapsed = int((time.perf_counter() - started) * 1000)
        if status not in {"ok", "slow", "down", "off"}:
            status = "down"
        if status == "ok" and elapsed >= slow_ms:
            status = "slow"
        return name, {"status": status, "latency_ms": elapsed}

    pairs = await asyncio.gather(*(one(name, chosen[name]) for name in CHECK_NAMES))
    return {name: payload for name, payload in pairs}


def check_qdrant(settings: Settings) -> str:
    if settings.adapters.vector_store != "qdrant" or not settings.qdrant.url.strip():
        return "down"
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        return "down"
    client = QdrantClient(
        url=settings.qdrant.url,
        api_key=settings.qdrant.api_key or None,
        timeout=TIMEOUT_S,
        check_compatibility=False,
    )
    client.get_collection(settings.qdrant.collections.verified)
    return "ok"


def check_postgres(settings: Settings) -> str:
    # No DATABASE_URL means the in-memory store is in use on purpose (local real mode).
    if not settings.database_url.strip():
        return "off"
    import psycopg

    with psycopg.connect(settings.database_url, connect_timeout=1) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    return "ok"


def check_llm(settings: Settings) -> str:
    if settings.adapters.llm == "fake":
        return "ok"
    providers = keyed_providers()
    if not providers:
        return "down"
    hosts = [_PROVIDER_HOSTS[name] for name in providers if name in _PROVIDER_HOSTS]
    if not hosts:
        return "ok"
    open_hosts = sum(1 for host in hosts if _tcp_open(host, 1.0))
    if open_hosts == 0:
        return "down"
    if open_hosts < len(hosts):
        return "slow"
    return "ok"


def check_embeddings(settings: Settings) -> str:
    if settings.adapters.embedder == "fake":
        return "ok"
    if not settings.models.dense.strip() or not settings.models.sparse.strip():
        return "down"
    # Same default as fastembed.common.utils.define_cache_dir. The old ~/.cache/fastembed
    # path never existed, so a working embedder was reported as down.
    default = Path(tempfile.gettempdir()) / "fastembed_cache"
    cache = Path(os.environ.get("FASTEMBED_CACHE_PATH") or default)
    if cache.is_dir() and any(cache.iterdir()):
        return "ok"
    return "down"


def keyed_providers() -> set[str]:
    found: set[str] = set()
    for models in load_models_config().roles.values():
        for entry in models:
            model, sep, env_name = entry.partition("|")
            provider = model.split("/", 1)[0]
            if not sep:
                env_name = PROVIDER_KEYS.get(provider, "")
            if env_name and os.environ.get(env_name):
                found.add(provider)
    return found


def _tcp_open(host: str, timeout: float) -> bool:
    try:
        with socket.create_connection((host, 443), timeout=timeout):
            return True
    except OSError:
        return False
