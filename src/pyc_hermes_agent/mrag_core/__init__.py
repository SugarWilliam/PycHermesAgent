"""Local-first MRAG core skeleton."""

from .embedding_backend import resolve_embedding_backend
from .migrate import plan_migrations
from .ownership import MRAGStorageLockedError
from .service import MRAGService
from .persistence import MRAGManifestIncompatibleError, MRAG_INDEX_FORMAT_VERSION, MRAG_MANIFEST_VERSION

__all__ = [
    "resolve_embedding_backend",
    "MRAGService",
    "MRAGStorageLockedError",
    "MRAGManifestIncompatibleError",
    "MRAG_INDEX_FORMAT_VERSION",
    "MRAG_MANIFEST_VERSION",
    "plan_migrations",
]
