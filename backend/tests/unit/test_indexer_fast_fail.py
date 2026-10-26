"""N6: replay must not wait the 30 s client timeout per item when Qdrant is down."""

import socket
import time

import pytest

from app.core.updates import indexer


def test_client_fails_fast_when_qdrant_unreachable(monkeypatch):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    monkeypatch.setenv("QDRANT_URL", f"http://127.0.0.1:{port}")
    started = time.monotonic()
    with pytest.raises(ConnectionError):
        indexer._client()
    assert time.monotonic() - started < indexer.CONNECT_TIMEOUT_S + 1


def test_reachable_true_for_listening_port():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        assert indexer._reachable(f"http://127.0.0.1:{server.getsockname()[1]}")
