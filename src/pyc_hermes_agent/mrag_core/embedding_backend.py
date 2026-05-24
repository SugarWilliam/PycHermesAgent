"""Pluggable semantic backends for hybrid MRAG retrieval (local-first).

Default: deterministic character trigram vectors (numpy-only).

Optional: ``sentence-transformers`` when ``[mrag-dense]`` extras are installed and
``PYC_HERMES_MRAG_EMBEDDING_BACKEND`` requests a dense encoder.
"""

from __future__ import annotations

import importlib.util
import os
import threading
from pathlib import Path
from typing import Protocol

import numpy as np

from pyc_hermes_agent.common import ensure_runtime_directories, resolve_runtime_paths
from pyc_hermes_agent.mrag_core.embeddings import character_trigram_embedding


class EmbeddingBackend(Protocol):
    """Maps text to L2-ish normalized vectors comparable via dot product."""

    name: str
    dim: int

    def embed_query(self, text: str) -> np.ndarray:
        ...

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        ...


class TrigramEmbeddingBackend:
    """256-d deterministic bag-of-character-trigram (existing Phase 3 baseline)."""

    name = "trigram"

    def __init__(self, *, dim: int = 256) -> None:
        self.dim = dim

    def embed_query(self, text: str) -> np.ndarray:
        return character_trigram_embedding(text, dim=self.dim)

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float64)
        rows = [character_trigram_embedding(t, dim=self.dim) for t in texts]
        return np.stack(rows, axis=0)


_sentence_lock = threading.Lock()
_sentence_model_key: tuple[str, str] | None = None
_sentence_backend_singleton: EmbeddingBackend | None = None


class SentenceTransformerEmbeddingBackend:
    """Small sentence Transformer via ``sentence-transformers``."""

    name = "sentence_transformer"

    def __init__(self, model_name: str, workspace_root: Path) -> None:
        from sentence_transformers import SentenceTransformer

        resolved = workspace_root.expanduser().resolve()
        paths = ensure_runtime_directories(resolve_runtime_paths(resolved))
        hf_home = paths.models_dir / "sentence_transformers"
        hf_home.mkdir(parents=True, exist_ok=True)

        os.environ.setdefault("TRANSFORMERS_CACHE", str(paths.models_dir / "huggingface"))
        os.environ.setdefault("HF_HOME", str(paths.models_dir / "huggingface"))
        os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(hf_home))

        self._model = SentenceTransformer(model_name, cache_folder=str(hf_home))
        self.dim = int(self._model.get_sentence_embedding_dimension())

    def embed_query(self, text: str) -> np.ndarray:
        vec = self._model.encode(text, normalize_embeddings=True, convert_to_numpy=True)
        return np.asarray(vec, dtype=np.float64)

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float64)
        mat = self._model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return np.asarray(mat, dtype=np.float64)


def try_build_sentence_backend(workspace_root: Path) -> SentenceTransformerEmbeddingBackend | None:
    if importlib.util.find_spec("sentence_transformers") is None:
        return None

    model = os.environ.get("PYC_HERMES_MRAG_SENTENCE_MODEL", "all-MiniLM-L6-v2").strip()
    if not model:
        model = "all-MiniLM-L6-v2"

    key = (model, str(workspace_root.expanduser().resolve()))
    global _sentence_model_key, _sentence_backend_singleton

    with _sentence_lock:
        if _sentence_model_key == key and isinstance(_sentence_backend_singleton, SentenceTransformerEmbeddingBackend):
            return _sentence_backend_singleton

        backend = SentenceTransformerEmbeddingBackend(model, workspace_root)
        _sentence_model_key = key
        _sentence_backend_singleton = backend
        return backend


def reset_sentence_backend_singleton_for_tests() -> None:
    global _sentence_model_key, _sentence_backend_singleton

    with _sentence_lock:
        _sentence_model_key = None
        _sentence_backend_singleton = None


def resolve_embedding_backend(
    *,
    workspace_root: Path | None,
    request_override: str = "",
) -> tuple[EmbeddingBackend, list[str]]:
    """Pick backend from per-request ``embedding_backend`` or process env."""

    ws = workspace_root.expanduser().resolve() if workspace_root else Path.cwd().resolve()

    hints: list[str] = []
    req = (request_override or "").strip().lower()

    dense_aliases = frozenset(
        {"sentence_transformer", "sentence-transformer", "dense"},
    )

    wants_dense = req in dense_aliases
    wants_trigram_explicit = req in {"trigram", "lexical_trigram"}

    env_mode = os.environ.get("PYC_HERMES_MRAG_EMBEDDING_BACKEND", "trigram").strip().lower()

    effective_dense = wants_dense or (not wants_trigram_explicit and env_mode in dense_aliases)

    if wants_trigram_explicit or not effective_dense:
        return TrigramEmbeddingBackend(), hints

    st = try_build_sentence_backend(ws)
    if st is None:
        hints.append("dense_embedding_fallback_no_sentence_transformers")
        return TrigramEmbeddingBackend(), hints

    return st, hints


__all__ = [
    "EmbeddingBackend",
    "TrigramEmbeddingBackend",
    "SentenceTransformerEmbeddingBackend",
    "resolve_embedding_backend",
    "reset_sentence_backend_singleton_for_tests",
    "try_build_sentence_backend",
]
