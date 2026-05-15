"""Execution snapshot persistence for MetaFramework v0.1."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


class SnapshotStore:
    def __init__(self, root_dir: str | Path | None = None) -> None:
        if root_dir is None:
            root_dir = Path(__file__).resolve().parents[2] / "metaframework_snapshots"
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def save_execution(self, result: Dict[str, Any], request: Dict[str, Any]) -> Dict[str, Any]:
        snapshot_id = f"snap_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
        snapshot_path = self.root_dir / f"{snapshot_id}.json"
        payload = {
            "snapshot_id": snapshot_id,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "request": request,
            "result": result,
        }
        with snapshot_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return {
            "snapshot_id": snapshot_id,
            "snapshot_path": str(snapshot_path),
        }

    def load_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        snapshot_path = self.root_dir / f"{snapshot_id}.json"
        with snapshot_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def list_snapshots(self) -> Dict[str, Any]:
        snapshots = []
        for path in sorted(self.root_dir.glob("snap_*.json"), reverse=True):
            snapshots.append({"snapshot_id": path.stem, "snapshot_path": str(path)})
        return {"count": len(snapshots), "snapshots": snapshots}


default_snapshot_store = SnapshotStore()
