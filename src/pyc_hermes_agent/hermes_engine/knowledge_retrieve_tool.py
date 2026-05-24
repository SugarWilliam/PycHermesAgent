"""AgentLoop tool — local-first MRAG retrieval (JSON-backed MRAGService).

Mirrors HTTP ``POST /knowledge-bases/{id}/search`` via ``sidecar_api.services.mrag_service``
so the Hermes orchestration stays on one storage root resolver."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any, Callable

from pyc_hermes_agent.contracts import RetrievalRequest
from pyc_hermes_agent.sidecar_api.services import mrag_service as _mrag_svc

_VALID_MODES = frozenset({"lexical", "semantic", "hybrid"})
KNOWLEDGE_RETRIEVE_MODES: list[str] = sorted(_VALID_MODES)


def run_knowledge_retrieve_tool(arguments: dict[str, Any], *, workspace_root: Path | None = None) -> dict[str, Any]:
    query = str(arguments.get("query") or "").strip()
    if not query:
        raise ValueError("knowledge_retrieve requires a non-empty 'query'.")

    kb_id_in = str(arguments.get("knowledge_base_id") or "").strip()

    raw_top_k = arguments.get("top_k", 8)
    try:
        top_k = int(raw_top_k)
    except (TypeError, ValueError) as exc:
        raise ValueError("top_k must be an integer") from exc
    top_k = max(1, min(top_k, 32))

    mode = str(arguments.get("retrieval_mode") or "hybrid").strip().lower()
    if mode not in _VALID_MODES:
        raise ValueError(f"retrieval_mode must be one of {sorted(_VALID_MODES)}")

    sem_raw = arguments.get("semantic_weight", 0.35)
    try:
        sem = float(sem_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("semantic_weight must be a float") from exc

    ic_raw = arguments.get("include_citations", True)
    include_citations = ic_raw if isinstance(ic_raw, bool) else str(ic_raw).strip().lower() in {"1", "true", "yes"}

    root = workspace_root.resolve() if workspace_root is not None else None

    kb_id = kb_id_in
    if not kb_id:
        catalog = _mrag_svc.list_knowledge_bases(root)
        if not catalog:
            raise ValueError(
                "No knowledge bases found; ingest documents first or pass an explicit knowledge_base_id."
            )
        kb_id = str(catalog[0].get("knowledge_base_id") or "").strip()
        if not kb_id:
            raise ValueError("Knowledge base listing returned an empty knowledge_base_id.")

    req = RetrievalRequest(
        query=query,
        top_k=top_k,
        include_citations=include_citations,
        retrieval_mode=mode,
        semantic_weight=sem,
    )

    out = dict(_mrag_svc.search_knowledge_base(kb_id, req, root=root))
    out.setdefault("resolved_knowledge_base_id", kb_id)
    out.setdefault("_tool_source", "knowledge_retrieve")
    return out


def knowledge_retrieve_handler_for_workspace(workspace_root: Path | None) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Build a ToolRegistry-compatible handler bound to ``workspace_root``."""

    root = workspace_root.resolve() if workspace_root is not None else None
    return partial(run_knowledge_retrieve_tool, workspace_root=root)
