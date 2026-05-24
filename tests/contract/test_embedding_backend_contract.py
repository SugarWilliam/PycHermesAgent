"""Embedding backend resolution (trigram default, dense optional)."""

from __future__ import annotations

from pathlib import Path

from pyc_hermes_agent.mrag_core.embedding_backend import (
    reset_sentence_backend_singleton_for_tests,
    resolve_embedding_backend,
)


def test_dense_request_falls_back_when_sentence_transformers_missing(monkeypatch, tmp_path: Path) -> None:
    reset_sentence_backend_singleton_for_tests()
    monkeypatch.delenv("PYC_HERMES_MRAG_EMBEDDING_BACKEND", raising=False)

    backend, warns = resolve_embedding_backend(
        workspace_root=tmp_path,
        request_override="sentence_transformer",
    )

    assert backend.name == "trigram"
    assert any("dense_embedding_fallback" in w for w in warns)


def test_explicit_trigram_requests_no_fallback_warning(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PYC_HERMES_MRAG_EMBEDDING_BACKEND", raising=False)

    backend, warns = resolve_embedding_backend(
        workspace_root=tmp_path,
        request_override="trigram",
    )

    assert backend.name == "trigram"
    assert not warns
