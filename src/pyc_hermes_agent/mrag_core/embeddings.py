"""Lightweight deterministic chunk/query vectors for local-first semantic-style retrieval."""

from __future__ import annotations

import hashlib

import numpy as np


def _bucket_index(trigram: str, *, dim: int) -> int:
    digest = hashlib.blake2b(trigram.encode("utf-8", errors="ignore"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % dim


def character_trigram_embedding(text: str, *, dim: int = 256) -> np.ndarray:
    """Dense bag-of-trigram histogram hashed into *dim* dimensions, L2-normalized (cross-run stable)."""
    padded = f" {text.lower()} "
    vector = np.zeros(dim, dtype=np.float64)
    if len(padded) < 3:
        return vector
    for i in range(len(padded) - 2):
        tri = padded[i : i + 3]
        vector[_bucket_index(tri, dim=dim)] += 1.0
    norm = float(np.linalg.norm(vector))
    if norm <= 0.0:
        return vector
    return vector / norm


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.dot(left, right))


__all__ = ["character_trigram_embedding", "cosine_similarity"]
